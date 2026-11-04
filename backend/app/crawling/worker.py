"""Standalone Scrapy worker. Public pages only; no credentials or paid APIs.

The parent owns the hard deadline. Results are flushed per page so partial
collections survive a slow site, a browser failure or the deadline.
"""

import asyncio
from datetime import datetime, timezone
from functools import lru_cache
import ipaddress
import json
import re
import socket
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import IgnoreRequest


BLOCK_MARKERS = ('cloudflare ray id', 'verify you are human', 'checking your browser',
                 'you have been blocked', 'enable javascript and cookies to continue',
                 "you've been blocked by network security", 'whoa there, pardner',
                 'доступ ограничен', 'подтвердите, что вы не робот')
X_HOSTS = {'x.com', 'www.x.com', 'twitter.com', 'www.twitter.com', 'mobile.twitter.com'}


def clean_text(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def source_link(base, value):
    url = urljoin(base, str(value or ''))
    return url if urlsplit(url).scheme in ('https', 'http') else base


@lru_cache(maxsize=512)
def public_host(host):
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(row[4][0]).is_global for row in addresses)
    except (OSError, ValueError):
        return False


def public_url(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme in ('http', 'https') and not parsed.username and not parsed.password
                and parsed.port in (None, 80, 443) and bool(parsed.hostname)
                and public_host(parsed.hostname))
    except ValueError:
        return False


def blocked(response):
    text = response.text[:100000].lower()
    title = clean_text(response.css('title::text').get()).lower()
    return (response.status in (401, 403, 429, 451) or any(marker in text for marker in BLOCK_MARKERS)
            or any(marker in title for marker in ('just a moment', 'access denied', 'robot or human', 'attention required')))


def proxy_options(proxy):
    """Playwright contexts require credentials separately from the proxy URL."""
    from urllib.parse import unquote
    parsed = urlsplit(proxy)
    options = {'server': urlunsplit((parsed.scheme, parsed.netloc.rsplit('@', 1)[-1], '', '', ''))}
    if parsed.username:
        options['username'] = unquote(parsed.username)
    if parsed.password:
        options['password'] = unquote(parsed.password)
    return options


async def abort_browser_request(request):
    if request.resource_type in ('image', 'media', 'font'):
        return True
    return not await asyncio.to_thread(public_url, request.url)


class EgressMiddleware:
    def process_request(self, request, spider):
        if not public_url(request.url):
            raise IgnoreRequest('non_public_url')

    def _retry(self, request, spider):
        if not spider.proxy or request.meta.get('via_proxy'):
            return None
        meta = dict(request.meta, via_proxy=True, proxy=spider.proxy)
        meta.pop('_auth_proxy', None)
        meta.pop('_scheme_proxy', None)
        if meta.get('playwright'):
            meta['playwright_context'] = 'german'
            meta['playwright_context_kwargs'] = {'proxy': proxy_options(spider.proxy)}
        retry = request.replace(meta=meta, dont_filter=True)
        retry.headers.pop('Proxy-Authorization', None)
        return retry

    def process_response(self, request, response, spider):
        if isinstance(response, scrapy.http.TextResponse) and (blocked(response) or response.status >= 500):
            return self._retry(request, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        if isinstance(exception, IgnoreRequest):
            return None
        return self._retry(request, spider)


def extract_reddit(payload, source_url, max_comments):
    if not isinstance(payload, list) or len(payload) < 2:
        return None
    posts = payload[0].get('data', {}).get('children', [])
    if not posts:
        return None
    post = posts[0].get('data', {})
    comments = []
    def walk(children):
        for child in children:
            if len(comments) >= max_comments:
                return
            data = child.get('data') or {}
            body = clean_text(data.get('body'))
            if child.get('kind') == 't1' and body and body not in ('[removed]', '[deleted]'):
                comments.append({
                    'id': data.get('name'), 'parent_id': data.get('parent_id'),
                    'text': body[:2500], 'author': data.get('author'),
                    'url': source_link('https://www.reddit.com', data.get('permalink') or source_url),
                    'published_at': data.get('created_utc'),
                })
            replies = data.get('replies')
            if isinstance(replies, dict):
                walk(replies.get('data', {}).get('children', []))
    walk(payload[1].get('data', {}).get('children', []))
    return {'title': clean_text(post.get('title')), 'content': clean_text(post.get('selftext') or post.get('title')),
            'author': post.get('author'), 'published_at': post.get('created_utc'),
            'comments': comments, 'discussion_status': 'partial' if post.get('num_comments', 0) > len(comments) else 'complete'}


def extract_html(response, max_comments=20):
    """Article text, visible comments and JSON-LD discussions across old sites."""
    host = urlsplit(response.url).hostname
    comments = []
    if host in X_HOSTS:
        post_id = re.search(r'/status/(\d+)', response.url)
        if not post_id:
            return None
        main = None
        for article in response.css('article[data-testid="tweet"]'):
            text = clean_text(' '.join(article.css('[data-testid="tweetText"] ::text').getall()))
            href = next((link for link in article.css('a::attr(href)').getall() if '/status/' in link and '/photo/' not in link), '')
            if not text or not href:
                continue
            item = {'text': text, 'url': urljoin('https://x.com', href),
                    'published_at': article.css('time::attr(datetime)').get()}
            if re.search(r'/status/' + post_id.group(1) + r'(?:[/?#]|$)', href):
                main = item
            elif len(comments) < max_comments:
                comments.append(item)
        if not main:
            return None
        return {'content': main['text'], 'comments': comments,
                'published_at': main['published_at'], 'discussion_status': 'partial'}

    comment_css = ('.tm-comment__body-content, .comment__message, .comment__content, '
                   '.comments__item .comment__text, .comment-body, [itemprop="commentText"], '
                   '[data-testid="comment"]')
    seen = set()
    for node in response.css(comment_css):
        text = clean_text(' '.join(node.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]').getall()))
        if text and text not in seen and len(comments) < max_comments:
            seen.add(text)
            identifier = node.attrib.get('id')
            comments.append({'text': text[:2500], 'url': response.url + ('#' + identifier if identifier else '')})
    # Structured comments complement visible comments without following
    # arbitrary links or treating recommendation feeds as replies.
    def structured(value):
        if isinstance(value, list):
            for item in value:
                structured(item)
        elif isinstance(value, dict):
            if value.get('@type') in ('Comment', 'UserComments'):
                text = clean_text(value.get('text') or value.get('description'))
                if text and text not in seen and len(comments) < max_comments:
                    seen.add(text)
                    comments.append({'text': text[:2500], 'url': source_link(response.url, value.get('url'))})
            for item in value.values():
                if isinstance(item, (list, dict)):
                    structured(item)
    for raw in response.css('script[type="application/ld+json"]::text').getall():
        try:
            structured(json.loads(raw))
        except (ValueError, TypeError):
            pass
    roots = (response.css('[itemprop="articleBody"], .tm-article-body, .story__content, .content--full')
             or response.css('article'))
    if not roots:
        roots = response.css('main') or response.css('body')
    content = clean_text(' '.join(roots[:1].xpath(
        './/text()[not(ancestor::script) and not(ancestor::style) and not(ancestor::nav) '
        'and not(ancestor::footer) and not(ancestor::header) and not(ancestor::aside) '
        'and not(ancestor::noscript)]'
    ).getall()))
    if len(content) < 80:
        return None
    return {'title': clean_text(response.css('h1 ::text').get() or response.css('title::text').get()),
            'content': content[:16000], 'comments': comments,
            'published_at': response.css('meta[property="article:published_time"]::attr(content), time::attr(datetime)').get(),
            'discussion_status': 'partial' if comments else 'not_available'}


class MarketSpider(scrapy.Spider):
    name = 'market_pages'

    def __init__(self, job, output, **kwargs):
        super().__init__(**kwargs)
        self.job, self.output = job, output
        self.proxy = job.get('proxy') or ''
        self.fetched = set()

    async def start(self):
        for index, source in enumerate(self.job['sources']):
            url = source.get('url') or ''
            parsed = urlsplit(url)
            if not parsed.hostname or parsed.scheme not in ('http', 'https'):
                self.save(index, crawl_status='invalid_url')
                continue
            meta = {'_index': index, 'handle_httpstatus_all': True, 'proxy': None}
            if (parsed.hostname == 'reddit.com' or parsed.hostname.endswith('.reddit.com')) and '/comments/' in parsed.path:
                # Public JSON contains the post plus a bounded tree of replies.
                url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/') + '.json',
                                  f'limit={self.job["max_comments"]}&depth=4&raw_json=1', ''))
                meta['reddit_json'] = True
            if parsed.hostname in X_HOSTS:
                if not self.job['browser']:
                    self.save(index, crawl_status='browser_disabled')
                    continue
                meta.update(self.browser_meta())
            yield scrapy.Request(url, callback=self.parse_page, errback=self.failed, meta=meta)

    def browser_meta(self, via_proxy=False):
        from scrapy_playwright.page import PageMethod
        meta = {'playwright': True, 'playwright_page_goto_kwargs': {'wait_until': 'domcontentloaded'},
                'playwright_page_methods': [
                    PageMethod('wait_for_timeout', 2200),
                    PageMethod('evaluate', 'window.scrollBy(0, 1200)'),
                    PageMethod('wait_for_timeout', 900),
                    PageMethod('evaluate', 'window.scrollBy(0, 1200)'),
                    PageMethod('wait_for_timeout', 900),
                ]}
        if via_proxy and self.proxy:
            meta.update(playwright_context='german', playwright_context_kwargs={'proxy': proxy_options(self.proxy)})
        return meta

    def save(self, index, **fields):
        if index in self.fetched and fields.get('crawl_status') != 'fetched':
            return
        if fields.get('crawl_status') == 'fetched':
            self.fetched.add(index)
        fields.update(_index=index, retrieved_at=datetime.now(timezone.utc).isoformat())
        with open(self.output, 'a', encoding='utf-8') as stream:
            stream.write(json.dumps(fields, ensure_ascii=False) + '\n')

    def parse_page(self, response):
        index = response.meta['_index']
        if not isinstance(response, scrapy.http.TextResponse):
            self.save(index, crawl_status='unsupported_content')
            return
        if blocked(response) or response.status >= 400:
            # Some sites block public JSON but still expose an HTML thread.
            if response.meta.get('reddit_json'):
                meta = dict(response.meta, reddit_json=False)
                yield scrapy.Request(self.job['sources'][index]['url'], callback=self.parse_page,
                                     errback=self.failed, meta=meta, dont_filter=True)
                return
            if blocked(response) and self.job['browser'] and not response.meta.get('playwright'):
                meta = dict(response.meta, **self.browser_meta(response.meta.get('via_proxy')))
                yield response.request.replace(meta=meta, dont_filter=True)
                return
            self.save(index, crawl_status='blocked' if blocked(response) else 'http_error', http_status=response.status)
            return
        if response.meta.get('reddit_json'):
            try:
                item = extract_reddit(response.json(), self.job['sources'][index]['url'], self.job['max_comments'])
            except (ValueError, TypeError, AttributeError):
                item = None
        else:
            item = extract_html(response, self.job['max_comments'])
        if not item:
            retry = EgressMiddleware()._retry(response.request, self)
            if retry:
                yield retry
                return
        if not item and self.job['browser'] and not response.meta.get('playwright'):
            meta = dict(response.meta, **self.browser_meta(response.meta.get('via_proxy')))
            meta['reddit_json'] = False
            yield scrapy.Request(self.job['sources'][index]['url'], callback=self.parse_page,
                                 errback=self.failed, meta=meta, dont_filter=True)
            return
        if not item or not item.get('content'):
            self.save(index, crawl_status='content_unavailable')
            return
        item['content'] = item['content'][:16000]
        item['highlights'] = [item['content'][:1200]] + [comment['text'][:700] for comment in item['comments'][:4]]
        if not item.get('title'):
            item.pop('title', None)
        self.save(index, **item, crawl_status='fetched', evidence_level='page',
                  final_url=response.url, egress='proxy' if response.meta.get('via_proxy') else 'direct')
        host = urlsplit(response.url).hostname or ''
        discussion_site = any(host == site or host.endswith('.' + site)
                              for site in ('habr.com', 'vc.ru', 'pikabu.ru', 'reddit.com'))
        if (discussion_site and not item['comments'] and self.job['browser']
                and not response.meta.get('playwright')):
            meta = dict(response.meta, **self.browser_meta(response.meta.get('via_proxy')))
            meta['reddit_json'] = False
            yield scrapy.Request(self.job['sources'][index]['url'], callback=self.parse_page,
                                 errback=self.failed, meta=meta, dont_filter=True)

    def failed(self, failure):
        self.save(failure.request.meta['_index'], crawl_status='request_failed', error_type=type(failure.value).__name__)


def run(request_path, output_path):
    with open(request_path, encoding='utf-8') as stream:
        job = json.load(stream)
    settings = {
        'LOG_ENABLED': False, 'TELNETCONSOLE_ENABLED': False,
        'USER_AGENT': 'Pitchy-CustDev/1.0 (public market research)',
        'CONCURRENT_REQUESTS': 8, 'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'DOWNLOAD_TIMEOUT': 10, 'DOWNLOAD_MAXSIZE': 3 * 1024 * 1024,
        'DOWNLOAD_WARNSIZE': 0, 'DOWNLOAD_DELAY': 0.25,
        'RETRY_ENABLED': False, 'COOKIES_ENABLED': False,
        'HTTPPROXY_ENABLED': True, 'CLOSESPIDER_TIMEOUT': max(1, job['seconds'] - 3),
        'DOWNLOADER_MIDDLEWARES': {EgressMiddleware: 610},
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
    }
    if job['browser']:
        settings.update({
            'DOWNLOAD_HANDLERS': {
                'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
                'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            },
            'PLAYWRIGHT_MAX_CONTEXTS': 2, 'PLAYWRIGHT_MAX_PAGES_PER_CONTEXT': 2,
            'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 12000,
            'PLAYWRIGHT_ABORT_REQUEST': abort_browser_request,
        })
    process = CrawlerProcess(settings)
    process.crawl(MarketSpider, job=job, output=output_path)
    process.start(install_signal_handlers=False)


if __name__ == '__main__':
    run(*sys.argv[1:])
