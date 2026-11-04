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


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
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
        source = dict(source)
        url = (source.get('url') or '').strip().split('#', 1)[0].rstrip('/')
        try:
            parts = urlsplit(url)
            host = parts.netloc.lower()
            if host in ('twitter.com', 'www.twitter.com', 'mobile.twitter.com', 'www.x.com'):
                host = 'x.com'
            query = urlencode([(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                               if not key.startswith('utm_') and key not in ('fbclid', 'gclid')])
            if host == 'x.com' and '/status/' in parts.path:
                query = ''
            url = urlunsplit((parts.scheme, host, parts.path.rstrip('/'), query, ''))
        except ValueError:
            continue
        title = ' '.join((source.get('title') or '').lower().split())
        highlights = ' '.join(source.get('highlights') or []).lower().strip()
        key = url or f"{title}|{highlights[:180]}"
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
            logger.error("Пакет ddgs не установлен — провайдер ddg недоступен.")
            return []
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
            return []
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
        """Возвращает {available, sources:[{title,url,domain,highlights,source}], context, query, provider}."""
        result = {"available": False, "sources": [], "context": "", "query": query,
                  "provider": Config.SIGNAL_PROVIDER}
        query = (query or "").strip()
        if not query:
            return result

        web_usable = SignalsService._web_provider_usable()
        reddit_on = Config.ENABLE_REDDIT_SIGNALS
        if not web_usable and not reddit_on:
            return result  # gated: нечем искать

        sources = []
        if web_usable:
            sources += [dict(item, market_scope='russian_market')
                        for item in SignalsService.search(query, max_results)]
        if reddit_on:
            sources += SignalsService._search_reddit(query, max(3, max_results // 2))
        sources += SignalsService._search_x(query, max(3, max_results // 2))

        from .page_crawler import collect_pages
        discovered = collect_pages(_normalise_sources(sources))
        sources = [item for item in discovered if item.get('crawl_status') == 'fetched']
        result['discovered_sources'] = discovered
        result['unread_sources_count'] = len(discovered) - len(sources)

        sources = _normalise_sources(sources)
        compiled = ""
        for idx, s in enumerate(sources, 1):
            if s.get('highlights'):
                compiled += f"### Сигнал {idx} ({s.get('domain', '')}): {s.get('title', '')}\n" + \
                            "\n".join(f"- {h}" for h in s['highlights'][:3]) + "\n\n"

        result.update(
            available=bool(sources),
            sources=sources,
            context=compiled.strip(),
            source_count=len(sources),
            source_domains=sorted({s.get('domain') for s in sources if s.get('domain')}),
            degraded=bool(result['unread_sources_count'] or not sources),
        )
        logger.info(f"Сигналы [{Config.SIGNAL_PROVIDER}+reddit]: {len(sources)} источников по «{query}».")
        return result
