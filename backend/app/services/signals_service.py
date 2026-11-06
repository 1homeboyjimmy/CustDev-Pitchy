"""Сигналы рынка: pain-mining реальных болей из сообществ.

Две независимые опоры вердикта (отдельно от симуляции агентов):
  • Веб-поиск по RU-сообществам (Хабр/vc.ru/Пикабу) — провайдер подключаемый
    через Config.SIGNAL_PROVIDER: ddg (бесплатно, без ключей) | exa | google_cse | brave.
  • Reddit — бесплатный публичный поиск как ОПЕРЕЖАЮЩИЙ западный сигнал
    (то, что уже обсуждают на Западе, часто приходит на рынок РФ позже).

Мягкая деградация: если ни один источник недоступен — available=False,
фронт показывает gated-состояние. Любая ошибка провайдера не роняет ответ.
"""

import requests
from datetime import datetime, timezone
from urllib.parse import urlparse, urlsplit, urlunsplit, parse_qsl, urlencode
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('pitchy.signals_service')


class SearchUnavailable(RuntimeError):
    """A safe operational code, never a raw provider/proxy exception."""



def _domain(url: str) -> str:
    try:
        host = (urlparse(url).hostname or '').lower()
        return host[4:] if host.startswith('www.') else host
    except Exception:
        return ''


def _clip(text: str, n: int = 300) -> str:
    text = (text or '').strip().replace('\n', ' ')
    return text[:n] + ('…' if len(text) > n else '')


def _normalise_sources(sources: list[dict]) -> list[dict]:
    """Remove duplicate search hits while preserving source provenance.

    Search providers frequently return the same article for several query
    variants. Counting those hits as separate pains inflates the verdict.
    """
    unique = []
    seen = set()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    for source in sources:
        if not isinstance(source, dict):
            continue
        source = dict(source)
        raw_url = source.get('url')
        if not isinstance(raw_url, str) or len(raw_url) > 4096:
            continue
        url = raw_url.strip().split('#', 1)[0].rstrip('/')
        try:
            parts = urlsplit(url)
            if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password:
                continue
            host = parts.netloc.lower()
            if host in ('www.reddit.com', 'old.reddit.com', 'new.reddit.com', 'sh.reddit.com'):
                host = 'reddit.com'
            if host in ('twitter.com', 'www.twitter.com', 'mobile.twitter.com', 'www.x.com'):
                host = 'x.com'
            query = urlencode([(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                               if not key.startswith('utm_') and key not in ('fbclid', 'gclid')])
            if host == 'x.com' and '/status/' in parts.path:
                query = ''
            url = urlunsplit((parts.scheme, host, parts.path.rstrip('/'), query, ''))
        except ValueError:
            continue
        key = url
        if host == 'reddit.com':
            import re
            thread = re.search(r'/comments/([^/]+)', parts.path)
            if thread:
                key = 'reddit:' + thread.group(1)
        source['domain'] = _domain(url)
        if not key or key in seen:
            continue
        seen.add(key)
        source['url'] = url
        source['retrieved_at'] = source.get('retrieved_at') or retrieved_at
        unique.append(source)
    return unique


class SignalsService:
    """Собирает сигналы боли/спроса по гипотезе из веба и Reddit."""

    # ---- Веб-провайдеры (RU-сообщества) ----

    @staticmethod
    def _site_filter(domains=None) -> str:
        domains = Config.SIGNAL_DOMAINS if domains is None else domains
        return ' (' + ' OR '.join(f'site:{d}' for d in domains) + ')' if domains else ''

    @staticmethod
    def _web_ddg(query: str, n: int, domains=None, region="ru-ru") -> list[dict]:
        try:
            from ddgs import DDGS
        except ImportError:
            raise SearchUnavailable("provider_unavailable") from None
        out = []
        try:
            with DDGS(proxy=Config.SEARCH_HTTPS_PROXY or None, timeout=8) as ddgs:
                for r in ddgs.text(query + SignalsService._site_filter(domains), region=region, max_results=n):
                    url = r.get('href') or r.get('url') or ''
                    out.append({
                        'title': r.get('title') or 'Источник',
                        'url': url,
                        'domain': _domain(url),
                        'highlights': [_clip(r.get('body'))] if r.get('body') else [],
                        'source': 'web',
                    })
        except Exception as e:
            logger.warning("DDG search unavailable")
            raise SearchUnavailable("provider_failed") from None
        return out

    @staticmethod
    def _web_exa(query: str, n: int, domains=None, region="ru-ru") -> list[dict]:
        if not Config.EXA_API_KEY:
            return []
        out = []
        try:
            # As in main Pitchy, use REST to attach a scoped egress proxy.
            proxy = Config.EXA_HTTPS_PROXY
            resp = requests.post('https://api.exa.ai/search',
                json={'query': query, 'numResults': n, 'type': 'auto',
                      'includeDomains': Config.SIGNAL_DOMAINS if domains is None else domains},
                headers={'x-api-key': Config.EXA_API_KEY}, timeout=12,
                proxies={'http': proxy, 'https': proxy} if proxy else {})
            resp.raise_for_status()
            for item in resp.json().get('results') or []:
                url = item.get('url') or ''
                out.append({'title': item.get('title') or 'Источник', 'url': url,
                            'domain': _domain(url), 'highlights': [], 'source': 'web'})
        except Exception:
            logger.warning('Exa search unavailable')
            raise SearchUnavailable("provider_failed") from None
        return out

    @staticmethod
    def _web_google_cse(query: str, n: int, domains=None, region="ru-ru") -> list[dict]:
        if not (Config.GOOGLE_CSE_KEY and Config.GOOGLE_CSE_CX):
            return []
        out = []
        try:
            resp = requests.get('https://www.googleapis.com/customsearch/v1', params={
                'key': Config.GOOGLE_CSE_KEY, 'cx': Config.GOOGLE_CSE_CX,
                'q': query + SignalsService._site_filter(domains), 'num': min(n, 10),
            }, timeout=12, proxies=SignalsService._proxies())
            resp.raise_for_status()
            for item in (resp.json().get('items') or []):
                url = item.get('link', '')
                out.append({'title': item.get('title') or 'Источник', 'url': url,
                            'domain': _domain(url), 'highlights': [_clip(item.get('snippet'))] if item.get('snippet') else [],
                            'source': 'web'})
        except Exception as e:
            logger.warning("Google CSE search unavailable")
            raise SearchUnavailable("provider_failed") from None
        return out

    @staticmethod
    def _web_brave(query: str, n: int, domains=None, region="ru-ru") -> list[dict]:
        if not Config.BRAVE_API_KEY:
            return []
        out = []
        try:
            resp = requests.get('https://api.search.brave.com/res/v1/web/search',
                                params={'q': query + SignalsService._site_filter(domains), 'count': min(n, 20)},
                                headers={'X-Subscription-Token': Config.BRAVE_API_KEY, 'Accept': 'application/json'},
                                timeout=12, proxies=SignalsService._proxies())
            resp.raise_for_status()
            for item in ((resp.json().get('web') or {}).get('results') or []):
                url = item.get('url', '')
                out.append({'title': item.get('title') or 'Источник', 'url': url,
                            'domain': _domain(url), 'highlights': [_clip(item.get('description'))] if item.get('description') else [],
                            'source': 'web'})
        except Exception as e:
            logger.warning("Brave search unavailable")
            raise SearchUnavailable("provider_failed") from None
        return out

    @staticmethod
    def _web_searxng(query: str, n: int, domains=None, region="ru-ru") -> list[dict]:
        if not Config.SEARXNG_URL:
            return []
        out = []
        try:
            resp = requests.get(
                Config.SEARXNG_URL.rstrip('/') + '/search',
                params={'q': query + SignalsService._site_filter(domains), 'format': 'json',
                        'language': 'ru' if region == 'ru-ru' else 'en', 'categories': 'general'},
                headers={'Accept': 'application/json', 'User-Agent': Config.REDDIT_USER_AGENT},
                timeout=12, proxies=SignalsService._proxies(),
            )
            resp.raise_for_status()
            for item in (resp.json().get('results') or [])[:n]:
                url = item.get('url', '')
                out.append({'title': item.get('title') or 'Источник', 'url': url,
                            'domain': _domain(url),
                            'highlights': [_clip(item.get('content'))] if item.get('content') else [],
                            'source': 'web'})
        except Exception as e:
            logger.warning("SearXNG search unavailable")
            raise SearchUnavailable("provider_failed") from None
        return out

    @staticmethod
    def _web_provider():
        return {
            'ddg': SignalsService._web_ddg,
            'searxng': SignalsService._web_searxng,
            'exa': SignalsService._web_exa,
            'google_cse': SignalsService._web_google_cse,
            'brave': SignalsService._web_brave,
        }.get(Config.SIGNAL_PROVIDER, SignalsService._web_ddg)

    @staticmethod
    def _web_provider_usable() -> bool:
        p = Config.SIGNAL_PROVIDER
        if p == 'exa':
            return bool(Config.EXA_API_KEY)
        if p == 'google_cse':
            return bool(Config.GOOGLE_CSE_KEY and Config.GOOGLE_CSE_CX)
        if p == 'brave':
            return bool(Config.BRAVE_API_KEY)
        if p == 'searxng':
            return bool(Config.SEARXNG_URL)
        return True  # ddg — без ключей

    @staticmethod
    def _proxies():
        proxy = Config.SEARCH_HTTPS_PROXY
        return {'http': proxy, 'https': proxy} if proxy else {}

    @staticmethod
    def search(query: str, n: int, domains=None, region='ru-ru') -> list[dict]:
        if not SignalsService._web_provider_usable():
            raise SearchUnavailable("provider_not_configured")
        found = SignalsService._web_provider()(query, n, domains=domains, region=region)
        allowed = Config.SIGNAL_DOMAINS if domains is None else domains
        return [item for item in found if not allowed or any(
            _domain(item.get('url') or '') == domain or
            _domain(item.get('url') or '').endswith('.' + domain)
            for domain in allowed)]

    @staticmethod
    def _search_reddit(query: str, n: int) -> list[dict]:
        # Discover through the configured index; read posts/replies via Scrapy.
        return [dict(item, source='reddit', market_scope='international_reference')
                for item in SignalsService.search(query, n, ['reddit.com'], 'wt-wt')
                if '/comments/' in urlparse(item.get('url') or '').path]

    @staticmethod
    def _search_x(query: str, n: int) -> list[dict]:
        return [dict(item, source='x', market_scope='international_reference')
                for item in SignalsService.search(query, n, ['x.com', 'twitter.com'], 'wt-wt')
                if '/status/' in urlparse(item.get('url') or '').path]

    # ---- Оркестратор ----

    @staticmethod
    def scan(query: str, max_results: int = 8) -> dict:
        """Compatibility endpoint with the same verified-page evidence rules."""
        import time
        from concurrent.futures import ThreadPoolExecutor, wait
        from .page_crawler import collect_pages, source_diagnostics
        query = query.strip() if isinstance(query, str) else ''
        result = {'available': False, 'sources': [], 'context': '', 'query': query,
                  'provider': Config.SIGNAL_PROVIDER, 'market': 'russia'}
        if not query:
            return result
        deadline = time.monotonic() + Config.SIGNAL_RESEARCH_SECONDS
        jobs = [('web', lambda: [dict(item, market_scope='unknown') for item in SignalsService.search(query, max_results, domains=[])])]
        if Config.ENABLE_REDDIT_SIGNALS:
            jobs.append(('reddit', lambda: SignalsService._search_reddit(query, max(3, max_results // 2))))
        jobs.append(('x', lambda: SignalsService._search_x(query, max(3, max_results // 2))))
        pool = ThreadPoolExecutor(max_workers=len(jobs))
        futures = {pool.submit(function): name for name, function in jobs}
        completed, pending = wait(futures, timeout=min(35, Config.SIGNAL_RESEARCH_SECONDS / 3))
        sources, statuses = [], []
        for future in completed:
            try:
                found = future.result()
                sources.extend(found)
                statuses.append({'id': futures[future], 'status': 'found' if found else 'empty', 'sources': len(found)})
            except Exception:
                statuses.append({'id': futures[future], 'status': 'unavailable', 'sources': 0})
        for future in pending:
            future.cancel()
            statuses.append({'id': futures[future], 'status': 'timed_out', 'sources': 0})
        pool.shutdown(wait=False, cancel_futures=True)
        discovered = collect_pages(_normalise_sources(sources), timeout=max(0, deadline - time.monotonic() - 15))
        sources = [item for item in discovered if item.get('crawl_status') == 'fetched']
        from .signals_research import _extract_evidence, _bounded_call
        from .research_evidence import extraction_material, validate_pages, claims_digest
        from copy import deepcopy
        remaining = max(0, min(15, deadline - time.monotonic()))
        verified = _bounded_call(_extract_evidence, remaining, query, deepcopy(sources), timeout=remaining) if remaining > 1 else None
        sources = verified if verified is not None else validate_pages(None, sources, extraction_material(sources, query))
        context = '\n\n'.join(f"### {item.get('market_scope', 'unknown')} {item['url']}\n" +
                              '\n'.join(item.get('highlights') or []) for item in sources)
        result.update(available=bool(sources), sources=sources, context=claims_digest(sources), evidence_version=2,
                      discovered_sources=source_diagnostics(discovered), search_status=statuses,
                      source_count=len(sources), source_domains=sorted({item['domain'] for item in sources}),
                      unread_sources_count=len(discovered) - len(sources),
                      degraded=bool(len(discovered) != len(sources) or any(item['status'] not in ('found', 'empty') for item in statuses)))
        return result
