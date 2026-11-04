"""Evidence, deadlines, public discussions and scoped egress regressions."""

import json
from types import SimpleNamespace

import scrapy
from scrapy.http import HtmlResponse

from app.config import Config
from app.crawling import worker
from app.services import signals_research, page_crawler
from app.services.signals_service import SignalsService
from app.services.signals_service import _normalise_sources
from app.services.verdict_service import _market_evidence_stats


def html(body, url='https://habr.com/ru/articles/1/', meta=None, status=200):
    request = scrapy.Request(url, meta=meta or {})
    return HtmlResponse(url, body=body.encode(), encoding='utf-8', request=request, status=status)


def test_article_and_structured_replies_keep_provenance_and_drop_navigation():
    response = html('''<html><head><title>Опыт</title></head><body>
        <nav>Купить рекламу</nav><article><h1>Боль клиента</h1><p>'''
        + 'Автоматизация экономит пять часов каждую неделю. ' * 4 + '''</p></article>
        <div class="tm-comment__body-content" id="reply-1">Подписка слишком дорогая.</div>
        <script type="application/ld+json">{"@type":"Comment","text":"Нет интеграции", "url":"#reply-2"}</script>
        <footer>Политика cookies</footer></body></html>''')
    result = worker.extract_html(response)
    assert 'Купить рекламу' not in result['content']
    assert 'Политика cookies' not in result['content']
    assert [c['text'] for c in result['comments']] == ['Подписка слишком дорогая.', 'Нет интеграции']
    assert result['comments'][0]['url'].endswith('#reply-1')
    assert result['comments'][1]['url'].endswith('#reply-2')


def test_reddit_nested_replies_are_bounded_and_deleted_text_is_excluded():
    reply = lambda data: {'kind': 't1', 'data': data}
    payload = [
        {'data': {'children': [{'data': {'title': 'Pricing pain', 'selftext': 'Too expensive', 'num_comments': 10}}]}},
        {'data': {'children': [reply({'body': 'Expensive', 'name': 't1_a', 'parent_id': 't3_post',
                                     'permalink': '/r/startups/comments/post/a/', 'replies': {'data': {'children': [
                                         reply({'body': '[deleted]'}), reply({'body': 'I pay anyway', 'parent_id': 't1_a'})
                                     ]}}}), reply({'body': 'Beyond cap'})]}},
    ]
    result = worker.extract_reddit(payload, 'https://reddit.com/r/startups/comments/post/', 2)
    assert [item['text'] for item in result['comments']] == ['Expensive', 'I pay anyway']
    assert result['comments'][1]['parent_id'] == 't1_a'
    assert result['discussion_status'] == 'partial'


def test_x_extracts_target_post_and_visible_thread_without_login_page_evidence():
    def tweet(identifier, text):
        return f'<article data-testid="tweet"><a href="/someone/status/{identifier}"><time datetime="2026-11-01"/></a><div data-testid="tweetText">{text}</div></article>'
    response = html(tweet(123, 'Need a better workflow') + tweet(124, 'I use a spreadsheet'),
                    'https://x.com/someone/status/123')
    result = worker.extract_html(response)
    assert result['content'] == 'Need a better workflow'
    assert result['comments'][0]['url'] == 'https://x.com/someone/status/124'
    assert worker.extract_html(html('<main>Sign in to X</main>', 'https://x.com/someone/status/123')) is None


def test_proxy_fallback_is_scoped_once_and_handles_browser_credentials():
    middleware = worker.EgressMiddleware()
    spider = SimpleNamespace(proxy='http://user:password@proxy.example:8888')
    request = scrapy.Request('https://x.com/a/status/1', meta={'playwright': True})
    retry = middleware.process_response(request, html('blocked', request.url, status=403), spider)
    assert retry.meta['proxy'] == spider.proxy
    assert retry.meta['playwright_context_kwargs']['proxy'] == {
        'server': 'http://proxy.example:8888', 'username': 'user', 'password': 'password'}
    response = html('blocked', request.url, meta=retry.meta, status=403)
    assert middleware.process_response(retry, response, spider) is response


def test_private_redirect_targets_and_credentials_are_rejected(monkeypatch):
    worker.public_host.cache_clear()
    monkeypatch.setattr(worker.socket, 'getaddrinfo', lambda *a, **k: [(0, 0, 0, '', ('127.0.0.1', 0))])
    assert not worker.public_url('https://example.test/redirect')
    assert not worker.public_url('file:///etc/passwd')
    assert not worker.public_url('https://user:password@example.test')
    worker.public_host.cache_clear()


def test_each_angle_uses_selected_provider_with_correct_domain_and_region(monkeypatch):
    captured = []
    def provider(query, n, **kwargs):
        captured.append(kwargs)
        return [
            {'url': 'https://www.reddit.com/r/a/comments/123/title'},
            {'url': 'https://notreddit.com/comments/123'},
            {'url': 'https://reddit.com/r/a/'},
        ]
    monkeypatch.setattr(SignalsService, '_web_provider_usable', lambda: True)
    monkeypatch.setattr(SignalsService, '_web_provider', lambda: provider)
    result = SignalsService._search_reddit('pain', 6)
    assert len(result) == 1
    assert result[0]['market_scope'] == 'international_reference'
    assert captured == [{'domains': ['reddit.com'], 'region': 'wt-wt'}]


def test_blocked_snippets_are_excluded_and_foreign_data_cannot_establish_russian_demand():
    sources, dropped = signals_research._filter_market_evidence([
        {'url': 'https://x.com/a/status/1', 'title': 'Pain', 'highlights': ['Indexed snippet'], 'crawl_status': 'blocked'},
        {'url': 'https://reddit.com/post', 'title': 'Real post', 'highlights': ['I pay'], 'crawl_status': 'fetched',
         'market_scope': 'international_reference'},
    ])
    assert dropped == 1
    analysis = signals_research._normalise_analysis({'verdict': 'Есть', 'willingness': {'paying': 100}}, sources)
    assert analysis['verdict'] == 'Недостаточно данных'
    assert analysis['willingness']['paying'] == 0
    assert _market_evidence_stats({'sources': sources}, [])['real_sources'] == 0


def test_partial_crawl_output_survives_hard_timeout(monkeypatch):
    import subprocess
    killed = []
    class Process:
        pid = 12345
        def __init__(self, args, **kwargs):
            self.count = 0
            with open(args[-1], 'w') as stream:
                stream.write(json.dumps({'_index': 0, 'crawl_status': 'fetched', 'content': 'real page'}) + '\n')
                stream.write('{incomplete')
        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired('worker', timeout)
    monkeypatch.setattr(page_crawler.subprocess, 'Popen', Process)
    monkeypatch.setattr(page_crawler.os, 'killpg', lambda *args: killed.append(args))
    result = page_crawler.collect_pages([{'url': 'https://a.test'}, {'url': 'https://b.test'}], timeout=2)
    assert result[0]['crawl_status'] == 'fetched'
    assert result[1]['crawl_status'] == 'timed_out'
    assert killed


def test_render_failure_does_not_erase_already_fetched_article(tmp_path):
    output = tmp_path / 'out.jsonl'
    spider = worker.MarketSpider(job={'proxy': ''}, output=str(output))
    spider.save(0, crawl_status='fetched', content='article')
    spider.save(0, crawl_status='request_failed')
    assert len(output.read_text().splitlines()) == 1


def test_search_and_signal_models_survive_upstream_merge(monkeypatch):
    captured = []
    def create(**kwargs):
        captured.append(kwargs)
        content = {'x': 'workflow pain pricing', 'reddit': 'customer discovery interview problems'} if len(captured) == 1 else {'summary': 'Недостаточно данных'}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(content)))])
    monkeypatch.setattr(Config, 'LLM_API_KEY', 'test')
    monkeypatch.setattr(signals_research, 'OpenAI', lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    plan = signals_research._plan_search_queries('Интервью с клиентами', [])
    signals_research._llm_synthesize('Гипотеза', [], [])
    assert plan['reddit'] == 'customer discovery interview problems'
    assert captured[0]['model'] == Config.model_for('search')
    assert captured[1]['model'] == Config.model_for('signals')
    assert captured[0]['extra_body'] == {'reasoning': {'enabled': False}}


def test_llm_wall_time_limit_returns_without_waiting_for_slow_call():
    import threading
    event = threading.Event()
    try:
        assert signals_research._bounded_call(event.wait, 0.01) is None
    finally:
        event.set()


def test_twitter_aliases_and_tracking_do_not_inflate_source_counts():
    result = _normalise_sources([
        {'url': 'https://twitter.com/a/status/123?s=20', 'title': 'Pain'},
        {'url': 'https://x.com/a/status/123?utm_source=test', 'title': 'Same pain'},
    ])
    assert len(result) == 1


def test_research_orchestrator_publishes_collected_evidence_and_coverage(monkeypatch):
    import threading
    finished = threading.Event()
    stored = {}
    class Tasks:
        def create_task(self, *args, **kwargs):
            return 'test-research'
        def update_task(self, *args, **kwargs):
            pass
        def complete_task(self, task_id, result):
            stored.update(result)
            finished.set()
        def fail_task(self, *args):
            stored['failed'] = True
            finished.set()
    monkeypatch.setattr(signals_research, 'TaskManager', Tasks)
    monkeypatch.setattr(signals_research, '_plan_search_queries', lambda *args: {agent['id']: 'pain' for agent in signals_research.AGENTS})
    monkeypatch.setattr(signals_research, '_agent_search', lambda agent, query: [{
        'url': f'https://example.test/{agent["id"]}', 'title': 'A specific pain', 'highlights': ['indexed'],
        'search_angle': agent['id'], 'market_scope': 'international_reference' if agent['kind'] in ('reddit', 'x') else 'russian_market',
    }])
    def collect(sources, timeout):
        assert 0 < timeout <= Config.SIGNAL_RESEARCH_SECONDS
        return [dict(source, crawl_status='blocked' if source['search_angle'] == 'x' else 'fetched',
                     comments=[{'text': 'A reply', 'url': source['url']}]) for source in sources]
    monkeypatch.setattr(signals_research, 'collect_pages', collect)
    monkeypatch.setattr(signals_research, '_llm_synthesize', lambda *args, **kwargs: {'summary': 'Evidence collected'})
    signals_research.start_research('Product pain', [])
    assert finished.wait(3)
    assert not stored.get('failed')
    assert stored['unread_sources_count'] == 1
    assert all(item['crawl_status'] == 'fetched' for item in stored['sources'])
    assert stored['comments_count'] == stored['sources_count']
    assert stored['russian_market_sources'] > 0
    assert stored['international_reference_sources'] == 1
