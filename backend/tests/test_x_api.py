import asyncio
import json
from urllib.parse import parse_qs, urlsplit

from scrapy.http import TextResponse

from app.crawling import worker
from app.crawling.x_api import extract_replies


def spider(**overrides):
    return worker.MarketSpider(job={
        'sources': [], 'proxy': 'http://proxy.example:8888', 'browser': False,
        'x_api_token': 'test-token', 'x_api_max_posts': 3, 'x_api_max_replies': 10,
        'max_comments': 20, **overrides,
    }, output='/unused')


def response(request, payload, status=200):
    return TextResponse(request.url, request=request, body=json.dumps(payload).encode(),
                        encoding='utf-8', status=status)


def capture(spider):
    saved = {}
    def save(index, **fields):
        saved[index] = fields
        if fields.get('crawl_status') == 'fetched':
            spider.best[index] = fields
    spider.save = save
    return saved


def test_paid_reads_are_bounded_deduplicated_and_work_without_browser():
    s = spider(sources=[{'url': url} for url in [
        'https://x.com/a/status/1', 'https://twitter.com/a/status/1',
        'https://x.com/a/status/2', 'https://x.com/a/status/3',
        'https://x.com/a/status/4', 'https://x.com/a/profile', 'https://habr.com/ru/articles/1/']])
    saved = capture(s)
    async def requests():
        return [request async for request in s.start()]
    requests = asyncio.run(requests())
    assert len(requests) == 2
    public, paid = requests
    assert not public.headers.get('Authorization')
    assert paid.meta['x_targets'] == {'1': [0, 1], '2': [2], '3': [3]}
    assert paid.headers['Authorization'] == b'Bearer test-token'
    assert urlsplit(paid.url).hostname == 'api.x.com'
    assert 'test-token' not in paid.url
    assert paid.meta['dont_redirect'] and paid.meta['dont_retry']
    assert saved[4]['crawl_status'] == 'budget_limited'
    assert saved[5]['crawl_status'] == 'invalid_url'


def test_api_preserves_post_when_reply_access_fails_and_does_not_retry():
    s = spider()
    saved = capture(s)
    req = s.x_api_posts_request({'123': [0]})
    reply_req, = s.parse_x_posts(response(req, {'data': [{
        'id': '123', 'text': 'Short text', 'conversation_id': '123',
        'note_post': {'text': 'Complete long post'}, 'created_at': '2026-11-06T00:00:00Z'}]}))
    assert saved[0]['content'] == 'Complete long post'
    assert saved[0]['collection_method'] == 'x_api'
    assert parse_qs(urlsplit(reply_req.url).query)['max_results'] == ['10']
    blocked = response(reply_req, {}, status=402)
    assert worker.EgressMiddleware().process_response(reply_req, blocked, s) is blocked
    s.parse_x_replies(blocked)
    assert saved[0]['crawl_status'] == 'fetched'
    assert saved[0]['content'] == 'Complete long post'
    assert saved[0]['discussion_http_status'] == 402
    assert saved[0]['discussion_status'] == 'unavailable'


def test_root_replies_use_conversation_and_selected_reply_excludes_siblings():
    posts = [
        {'id': '3', 'conversation_id': '1', 'text': 'Nested',
         'referenced_posts': [{'type': 'replied_to', 'id': '2'}]},
        {'id': '2', 'conversation_id': '1', 'text': 'Selected reply',
         'referenced_posts': [{'type': 'replied_to', 'id': '1'}]},
        {'id': '4', 'conversation_id': '1', 'text': 'Sibling',
         'referenced_posts': [{'type': 'replied_to', 'id': '1'}]},
        {'id': '5', 'conversation_id': '9', 'text': 'Other conversation'},
    ]
    assert len(extract_replies(posts, '1', '1', 10)) == 3
    replies = extract_replies(posts, '2', '1', 10)
    assert [item['text'] for item in replies] == ['Nested']
    assert replies[0]['url'] == 'https://x.com/i/status/3'


def test_auth_errors_and_missing_posts_do_not_become_evidence():
    s = spider()
    saved = capture(s)
    req = s.x_api_posts_request({'123': [0], '456': [1]})
    assert list(s.parse_x_posts(response(req, {}, 401))) == []
    assert saved[0]['crawl_status'] == saved[1]['crawl_status'] == 'api_unavailable'
    assert list(s.parse_x_posts(response(req, {'data': []}))) == []
    assert saved[0]['crawl_status'] == 'content_unavailable'
