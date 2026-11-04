"""Run real discovery/collection against the deployed configuration.

Output contains coverage and public URLs only, never credentials or raw errors.
Use --full to also exercise Polza query planning and evidence synthesis.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with contextlib.redirect_stdout(io.StringIO()):
    from app.config import Config
    from app.services.page_crawler import collect_pages
    from app.services.signals_service import SignalsService
    from app.services.signals_research import start_research
    from app.models.task import TaskManager


def egress(proxy=None):
    import requests
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.get('https://www.cloudflare.com/cdn-cgi/trace', timeout=10,
                                   proxies={'http': proxy, 'https': proxy} if proxy else {})
            fields = dict(line.split('=', 1) for line in response.text.splitlines() if '=' in line)
            return {'http_status': response.status_code, 'country': fields.get('loc')}
    except Exception as exc:
        return {'error_type': type(exc).__name__}


def coverage(result):
    sources = result.get('sources') or []
    return {
        'sources': len(sources), 'russian_market_sources': result.get('russian_market_sources', 0),
        'international_reference_sources': result.get('international_reference_sources', 0),
        'comments': sum(len(item.get('comments') or []) for item in sources),
        'elapsed': result.get('elapsed'), 'analysis_available': result.get('analysis_available'),
        'pages': [{'url': item.get('url'), 'platform': item.get('source'),
                   'crawl_status': item.get('crawl_status'), 'egress': item.get('egress'),
                   'error_type': item.get('error_type'), 'http_status': item.get('http_status'),
                   'characters': len(item.get('content') or ''),
                   'comments': len(item.get('comments') or [])}
                  for item in result.get('discovered_sources') or sources],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    started = time.monotonic()
    report = {'provider': Config.SIGNAL_PROVIDER, 'proxy_configured': bool(Config.SIGNAL_HTTPS_PROXY),
              'browser_enabled': Config.SIGNAL_BROWSER_ENABLED, 'direct_egress': egress()}
    if Config.SIGNAL_HTTPS_PROXY:
        report['proxy_egress'] = egress(Config.SIGNAL_HTTPS_PROXY)
    jobs = [
        ('russian_market', lambda: SignalsService.search('интервью с клиентами автоматизация', 2, ['habr.com', 'vc.ru'])),
        ('reddit', lambda: SignalsService._search_reddit('customer discovery interviews pain', 2)),
        ('x', lambda: SignalsService._search_x('customer discovery interviews', 2)),
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        found = list(pool.map(lambda job: (job[0], job[1]()), jobs))
    report['discovery'] = {name: len(items) for name, items in found}
    sources = [dict(item, source=name) for name, items in found for item in items]
    # Controls distinguish an empty search index from a broken downloader.
    sources += [
        {'url': 'https://habr.com/ru/articles/681444/', 'source': 'russian_control'},
        {'url': 'https://www.reddit.com/r/startups/comments/omajf9/need_your_advice_on_my_customer_discoverypain/', 'source': 'reddit_control'},
        {'url': 'https://x.com/KateBour/status/1541779978743939079', 'source': 'x_control'},
    ]
    collected = collect_pages(sources)
    report['collection'] = coverage({'sources': [item for item in collected if item.get('crawl_status') == 'fetched'],
                                     'discovered_sources': collected})
    print(json.dumps({'phase': 'collection', **report}, ensure_ascii=False), flush=True)
    if args.full:
        task_id = start_research('Сервис для российских стартапов: автоматизация кастдева и анализа интервью с клиентами. '
                                 'Проверить боли и готовность платить за экономию времени.', ['основатели стартапов'], owner_id='server-smoke')
        deadline = time.monotonic() + Config.SIGNAL_RESEARCH_SECONDS + 10
        while time.monotonic() < deadline:
            task = TaskManager().get_task(task_id)
            if task and task.status.value in ('completed', 'failed'):
                report['research_status'] = task.status.value
                report['research'] = coverage(task.result or {})
                break
            time.sleep(1)
        else:
            report['research_status'] = 'timed_out'
    report['total_elapsed'] = round(time.monotonic() - started, 1)
    print(json.dumps({'phase': 'complete', **report}, ensure_ascii=False), flush=True)
    return 0 if report['collection']['sources'] and report.get('research_status', 'completed') == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
