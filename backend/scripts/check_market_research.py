"""Run real discovery/collection against the deployed configuration.

Output contains coverage and public URLs only, never credentials or raw errors.
Use --full to also exercise Polza query planning and evidence synthesis.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
import contextlib
import io
import json
from pathlib import Path
import sys
import time
import tempfile
from urllib.parse import urlsplit

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
    analysis = result.get('analysis') or {}
    return {
        'sources': len(sources), 'russian_market_sources': result.get('russian_market_sources', 0),
        'international_reference_sources': result.get('international_reference_sources', 0),
        'comments': sum(len(item.get('comments') or []) for item in sources),
        'elapsed': result.get('elapsed'), 'analysis_available': result.get('analysis_available'),
        'evidence_version': result.get('evidence_version'),
        'claims': sum(len(item.get('claims') or []) for item in sources),
        'findings': len(analysis.get('findings') or []),
        'interview_questions': analysis.get('interview_questions') or [],
        'extraction_unavailable_count': result.get('extraction_unavailable_count'),
        'research_context': result.get('research_context'),
        'pages': [{'url': item.get('url'), 'platform': item.get('source'),
                   'crawl_status': item.get('crawl_status'), 'egress': item.get('egress'),
                   'error_type': item.get('error_type'), 'http_status': item.get('http_status'),
                   'collection_method': item.get('collection_method'),
                   'discussion_status': item.get('discussion_status'),
                   'discussion_http_status': item.get('discussion_http_status'),
                   'characters': item.get('content_characters', len(item.get('content') or '')),
                   'comments': item.get('comments_count', len(item.get('comments') or []))}
                  for item in result.get('discovered_sources') or sources],
    }


def discover(job):
    name, search = job
    try:
        items = search()
        return name, items, {'status': 'found' if items else 'empty', 'sources': len(items)}
    except Exception as exc:
        # Exception messages can contain authenticated proxy URLs.
        cause = exc.__cause__ or exc.__context__ or exc
        return name, [], {'status': 'failed', 'error_type': type(cause).__name__}


def verification_status(report, full=False):
    """A single readable Russian page must not turn all-platform checks green."""
    fetched = set()
    for page in report.get('collection', {}).get('pages', []):
        if page.get('crawl_status') != 'fetched':
            continue
        host = (urlsplit(page.get('url') or '').hostname or '').removeprefix('www.')
        fetched.add('reddit' if host == 'reddit.com' or host.endswith('.reddit.com')
                    else 'x' if host in ('x.com', 'twitter.com', 'mobile.twitter.com') else 'russia')
    if not fetched or (full and report.get('research_status') != 'completed'):
        return 'failed'
    if (fetched != {'russia', 'reddit', 'x'}
        or any(item.get('status') == 'failed' for item in report.get('discovery_status', {}).values())
        or (full and not report.get('research', {}).get('analysis_available'))
        or (full and report.get('research', {}).get('evidence_version') == 2
            and (not report['research'].get('claims') or not report['research'].get('interview_questions')
                 or report['research'].get('extraction_unavailable_count')))):
        return 'partial'
    return 'passed'


def run_research_check(query):
    """Standalone smoke tasks must never overwrite the application's task cache."""
    with tempfile.TemporaryDirectory(prefix='custdev-smoke-') as directory:
        TaskManager._tasks_file = str(Path(directory) / 'tasks.json')
        TaskManager._instance = None
        task_id = start_research(query, [], owner_id='server-smoke')
        deadline = time.monotonic() + Config.SIGNAL_RESEARCH_SECONDS + 10
        while time.monotonic() < deadline:
            task = TaskManager().get_task(task_id)
            if task and task.status.value in ('completed', 'failed'):
                return task.status.value, task.result or {}
            time.sleep(1)
        return 'timed_out', {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--query', default='Сервис для российских стартапов: автоматизация кастдева и анализа интервью с клиентами. '
                        'Проверить востребованность продукта, текущие альтернативы, расходы, условия выбора и причины отказа.')
    args = parser.parse_args()
    started = time.monotonic()
    report = {'provider': Config.SIGNAL_PROVIDER, 'proxy_configured': bool(Config.SIGNAL_HTTPS_PROXY),
              'browser_enabled': Config.SIGNAL_BROWSER_ENABLED, 'direct_egress': egress()}
    report['x_api_configured'] = bool(Config.X_API_BEARER_TOKEN)
    report['ddgs_version'] = version('ddgs')
    if Config.SIGNAL_HTTPS_PROXY:
        report['proxy_egress'] = egress(Config.SIGNAL_HTTPS_PROXY)
    jobs = [
        ('russian_market', lambda: SignalsService.search('интервью с клиентами автоматизация', 2, ['habr.com', 'vc.ru'])),
        ('reddit', lambda: SignalsService._search_reddit('customer discovery interviews pain', 2)),
        ('x', lambda: SignalsService._search_x('customer discovery interviews', 2)),
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        found = list(pool.map(discover, jobs))
    report['discovery'] = {name: len(items) for name, items, _ in found}
    report['discovery_status'] = {name: status for name, _, status in found}
    sources = [dict(item, source=name) for name, items, _ in found for item in items]
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
        report['research_status'], result = run_research_check(args.query)
        report['research'] = coverage(result)
    report['total_elapsed'] = round(time.monotonic() - started, 1)
    report['verification_status'] = verification_status(report, args.full)
    print(json.dumps({'phase': 'complete', **report}, ensure_ascii=False), flush=True)
    return {'passed': 0, 'partial': 2, 'failed': 1}[report['verification_status']]


if __name__ == '__main__':
    raise SystemExit(main())
