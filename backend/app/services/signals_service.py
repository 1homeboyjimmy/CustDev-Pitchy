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
from urllib.parse import urlparse, quote
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
    def _site_filter() -> str:
        domains = Config.SIGNAL_DOMAINS or []
        return ' (' + ' OR '.join(f'site:{d}' for d in domains) + ')' if domains else ''

    @staticmethod
    def _web_ddg(query: str, n: int) -> list[dict]:
        try:
            from ddgs import DDGS
        except ImportError:
            logger.error("Пакет ddgs не установлен — провайдер ddg недоступен.")
            return []
        out = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query + SignalsService._site_filter(), region='ru-ru', max_results=n):
                    url = r.get('href') or r.get('url') or ''
                    out.append({
                        'title': r.get('title') or 'Источник',
                        'url': url,
                        'domain': _domain(url),
                        'highlights': [_clip(r.get('body'))] if r.get('body') else [],
                        'source': 'web',
                    })
        except Exception as e:
            logger.error(f"DDG search error: {e}")
        return out

    @staticmethod
    def _web_exa(query: str, n: int) -> list[dict]:
        if not Config.EXA_API_KEY:
            return []
        try:
            from exa_py import Exa
        except ImportError:
            return []
        out = []
        try:
            resp = Exa(Config.EXA_API_KEY).search_and_contents(
                query, type='auto', num_results=n,
                include_domains=Config.SIGNAL_DOMAINS or None, highlights=True,
            )
            for r in (getattr(resp, 'results', None) or []):
                url = getattr(r, 'url', '') or ''
                hl = list(getattr(r, 'highlights', None) or [])
                if not hl and getattr(r, 'text', ''):
                    hl = [_clip(r.text)]
                out.append({'title': getattr(r, 'title', None) or 'Источник', 'url': url,
                            'domain': _domain(url), 'highlights': hl[:3], 'source': 'web'})
        except Exception as e:
            logger.error(f"Exa search error: {e}")
        return out

    @staticmethod
    def _web_google_cse(query: str, n: int) -> list[dict]:
        if not (Config.GOOGLE_CSE_KEY and Config.GOOGLE_CSE_CX):
            return []
        out = []
        try:
            resp = requests.get('https://www.googleapis.com/customsearch/v1', params={
                'key': Config.GOOGLE_CSE_KEY, 'cx': Config.GOOGLE_CSE_CX,
                'q': query + SignalsService._site_filter(), 'num': min(n, 10),
            }, timeout=20)
            resp.raise_for_status()
            for item in (resp.json().get('items') or []):
                url = item.get('link', '')
                out.append({'title': item.get('title') or 'Источник', 'url': url,
                            'domain': _domain(url), 'highlights': [_clip(item.get('snippet'))] if item.get('snippet') else [],
                            'source': 'web'})
        except Exception as e:
            logger.error(f"Google CSE error: {e}")
        return out

    @staticmethod
    def _web_brave(query: str, n: int) -> list[dict]:
        if not Config.BRAVE_API_KEY:
            return []
        out = []
        try:
            resp = requests.get('https://api.search.brave.com/res/v1/web/search',
                                params={'q': query + SignalsService._site_filter(), 'count': min(n, 20)},
                                headers={'X-Subscription-Token': Config.BRAVE_API_KEY, 'Accept': 'application/json'},
                                timeout=20)
            resp.raise_for_status()
            for item in ((resp.json().get('web') or {}).get('results') or []):
                url = item.get('url', '')
                out.append({'title': item.get('title') or 'Источник', 'url': url,
                            'domain': _domain(url), 'highlights': [_clip(item.get('description'))] if item.get('description') else [],
                            'source': 'web'})
        except Exception as e:
            logger.error(f"Brave search error: {e}")
        return out

    @staticmethod
    def _web_searxng(query: str, n: int) -> list[dict]:
        if not Config.SEARXNG_URL:
            return []
        out = []
        try:
            resp = requests.get(
                Config.SEARXNG_URL.rstrip('/') + '/search',
                params={'q': query + SignalsService._site_filter(), 'format': 'json',
                        'language': 'ru', 'categories': 'general'},
                headers={'Accept': 'application/json', 'User-Agent': Config.REDDIT_USER_AGENT},
                timeout=20,
            )
            resp.raise_for_status()
            for item in (resp.json().get('results') or [])[:n]:
                url = item.get('url', '')
                out.append({'title': item.get('title') or 'Источник', 'url': url,
                            'domain': _domain(url),
                            'highlights': [_clip(item.get('content'))] if item.get('content') else [],
                            'source': 'web'})
        except Exception as e:
            logger.error(f"SearXNG search error: {e}")
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

    # ---- Reddit (бесплатный публичный поиск) ----

    @staticmethod
    def _reddit_token() -> str:
        """OAuth client_credentials токен (бесплатный script-app). '' если нет ключей."""
        if not (Config.REDDIT_CLIENT_ID and Config.REDDIT_CLIENT_SECRET):
            return ''
        try:
            resp = requests.post(
                'https://www.reddit.com/api/v1/access_token',
                data={'grant_type': 'client_credentials'},
                auth=(Config.REDDIT_CLIENT_ID, Config.REDDIT_CLIENT_SECRET),
                headers={'User-Agent': Config.REDDIT_USER_AGENT}, timeout=15,
            )
            return resp.json().get('access_token', '') or ''
        except Exception as e:
            logger.error(f"Reddit token error: {e}")
            return ''

    @staticmethod
    def _search_reddit(query: str, n: int) -> list[dict]:
        out = []
        try:
            token = SignalsService._reddit_token()
            if token:
                # Авторизованный путь (надёжно с серверных IP).
                resp = requests.get(
                    f'https://oauth.reddit.com/search?q={quote(query)}&sort=relevance&t=year&limit={min(n, 25)}',
                    headers={'User-Agent': Config.REDDIT_USER_AGENT, 'Authorization': f'Bearer {token}'},
                    timeout=20,
                )
            else:
                # Публичный путь (часто блокируется на серверных IP — деградирует мягко).
                resp = requests.get(
                    f'https://www.reddit.com/search.json?q={quote(query)}&sort=relevance&t=year&limit={min(n, 25)}',
                    headers={'User-Agent': Config.REDDIT_USER_AGENT}, timeout=20,
                )
            resp.raise_for_status()
            for child in (resp.json().get('data', {}).get('children') or []):
                d = child.get('data', {})
                permalink = d.get('permalink', '')
                url = f'https://www.reddit.com{permalink}' if permalink else (d.get('url') or '')
                snippet = _clip(d.get('selftext')) or _clip(d.get('title'))
                out.append({
                    'title': d.get('title') or 'Reddit',
                    'url': url,
                    'domain': f"reddit.com/r/{d.get('subreddit', '')}",
                    'highlights': [snippet] if snippet else [],
                    'source': 'reddit',
                })
        except Exception as e:
            logger.error(f"Reddit search error: {e}")
        return out

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
            sources += SignalsService._web_provider()(query, max_results)
        if reddit_on:
            sources += SignalsService._search_reddit(query, max(3, max_results // 2))

        # Сборка текстового контекста для вердикта.
        compiled = ""
        for idx, s in enumerate(sources, 1):
            if s['highlights']:
                compiled += f"### Сигнал {idx} ({s['domain']}): {s['title']}\n" + \
                            "\n".join(f"- {h}" for h in s['highlights'][:3]) + "\n\n"

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
            degraded=bool((web_usable or reddit_on) and not sources),
        )
        logger.info(f"Сигналы [{Config.SIGNAL_PROVIDER}+reddit]: {len(sources)} источников по «{query}».")
        return result
