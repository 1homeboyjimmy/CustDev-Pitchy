"""Bounded official X API reads scheduled and downloaded by Scrapy.

Search-index discovery is unchanged. Only a small number of discovered posts
are read, with one unpaginated reply search per conversation. Credentials stay
in headers on fixed API URLs; API redirects and paid automatic retries stop.
"""

import re
from urllib.parse import urlencode, urlsplit

import scrapy


POST_FIELDS = 'created_at,conversation_id,note_post'


def post_id(url):
    match = re.search(r'/status/(\d{1,19})(?:/|$)', urlsplit(url).path)
    return match.group(1) if match else None


def post_text(post):
    note = post.get('note_post') or post.get('note_tweet') or {}
    return str(note.get('text') or post.get('text') or '').strip()[:16000]


def reply_parent(post):
    return next((str(ref.get('id')) for ref in
                 (post.get('referenced_posts') or post.get('referenced_tweets') or [])
                 if isinstance(ref, dict) and ref.get('type') == 'replied_to'), None)


def extract_replies(posts, target, conversation, limit):
    """For reply URLs, exclude siblings unless ancestry proves descent."""
    if limit <= 0:
        return []
    candidates = {str(post.get('id')): post for post in posts if isinstance(post, dict)
                  and str(post.get('id', '')).isdigit() and str(post.get('conversation_id')) == conversation}
    connected, replies = {target}, []
    for _ in range(len(candidates)):
        added = False
        for identifier, post in candidates.items():
            if identifier in connected or not post_text(post):
                continue
            # A conversation ID proves membership for a root post. For a
            # selected reply, the returned parent chain must prove descent.
            if target == conversation or reply_parent(post) in connected:
                connected.add(identifier)
                replies.append({'text': post_text(post), 'url': f'https://x.com/i/status/{identifier}',
                                'published_at': post.get('created_at')})
                added = True
                if len(replies) >= limit:
                    return replies
        if not added:
            break
    return replies


class XAPIMixin:
    def x_api_request(self, path, params, meta, callback, errback):
        return scrapy.Request('https://api.x.com/2/' + path + '?' + urlencode(params),
                              headers={'Authorization': 'Bearer ' + self.job['x_api_token'],
                                       'Accept': 'application/json'},
                              meta={**meta, 'x_api': True, 'handle_httpstatus_all': True,
                                    'dont_redirect': True, 'dont_retry': True,
                                    'proxy': self.proxy or None, 'via_proxy': bool(self.proxy)},
                              callback=callback, errback=errback, dont_filter=True, priority=10)

    def x_api_posts_request(self, targets):
        return self.x_api_request('tweets', {'ids': ','.join(targets), 'post.fields': POST_FIELDS},
                                  {'x_targets': targets}, self.parse_x_posts, self.failed_x_posts)

    def parse_x_posts(self, response):
        targets = response.meta['x_targets']
        if response.status != 200:
            for indices in targets.values():
                for index in indices:
                    self.save(index, crawl_status='api_unavailable', http_status=response.status,
                              collection_method='x_api')
            return
        try:
            data = response.json().get('data') or []
        except (ValueError, AttributeError):
            data = []
        posts = {str(post.get('id')): post for post in data if isinstance(post, dict)}
        for identifier, indices in targets.items():
            post = posts.get(identifier) or {}
            text = post_text(post)
            if not text:
                for index in indices:
                    self.save(index, crawl_status='content_unavailable', collection_method='x_api')
                continue
            for index in indices:
                self.save(index, title=text[:160], content=text, comments=[], highlights=[text[:1200]],
                          crawl_status='fetched', evidence_level='page', collection_method='x_api',
                          egress='proxy' if self.proxy else 'direct', published_at=post.get('created_at'),
                          discussion_status='not_available')
            conversation = str(post.get('conversation_id') or '')
            if self.job.get('x_api_max_replies', 0) and conversation.isdigit():
                yield self.x_api_request('tweets/search/all',
                                        {'query': f'conversation_id:{conversation} is:reply', 'max_results': 10,
                                         'post.fields': POST_FIELDS},
                                        {'x_indices': indices, 'x_target': identifier,
                                         'x_conversation': conversation}, self.parse_x_replies, self.failed_x_replies)

    def parse_x_replies(self, response):
        meta = response.meta
        if response.status != 200:
            for index in meta['x_indices']:
                self.save(index, **dict(self.best[index], discussion_status='unavailable',
                                       discussion_http_status=response.status))
            return
        try:
            data = response.json().get('data') or []
        except (ValueError, AttributeError):
            data = []
        comments = extract_replies(data, meta['x_target'], meta['x_conversation'], self.job['x_api_max_replies'])
        for index in meta['x_indices']:
            self.save(index, **dict(self.best[index], comments=comments,
                                   discussion_status='partial' if comments else 'not_available'))

    def failed_x_posts(self, failure):
        for indices in failure.request.meta['x_targets'].values():
            for index in indices:
                self.save(index, crawl_status='api_unavailable', collection_method='x_api',
                          error_type=type(failure.value).__name__)

    def failed_x_replies(self, failure):
        for index in failure.request.meta['x_indices']:
            self.save(index, **dict(self.best[index], discussion_status='unavailable'))
