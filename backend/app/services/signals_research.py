"""Сигналы рынка — рой research-агентов (как у AI Cofounder, RU-first).

Фоновая задача гоняет несколько агентов-углов параллельно по смыслу
(каждый сканит свою площадку/аспект), складывает реальные источники и
прогресс в TaskManager (живой процесс на фронте), затем LLM сводит всё в
структурированный дашборд: сегменты-температура, воронка готовности,
топ болей, конкуренты, источники по площадкам.
"""

import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from .signals_service import SignalsService, _domain, _clip

logger = get_logger('pitchy.signals_research')


# Агенты-углы (RU-first). kind: web (ddg по доменам) | reddit.
AGENTS = [
    {"id": "reddit",     "name": "Голоса Reddit",            "kind": "reddit", "domains": [],
     "suffix": ""},
    {"id": "habr_vc",    "name": "Хабр / vc.ru — проф. обсуждения", "kind": "web",
     "domains": ["habr.com", "vc.ru"], "suffix": ""},
    {"id": "pikabu",     "name": "Пикабу / форумы — настроения",    "kind": "web",
     "domains": ["pikabu.ru"], "suffix": ""},
    {"id": "reviews",    "name": "Отзовики / маркетплейсы",          "kind": "web",
     "domains": ["otzovik.com", "irecommend.ru", "ozon.ru", "wildberries.ru"], "suffix": "отзывы"},
    {"id": "competitors", "name": "Конкуренты и аналоги",            "kind": "web",
     "domains": ["habr.com", "vc.ru", "pikabu.ru"], "suffix": "конкуренты аналоги обзор"},
    {"id": "willingness", "name": "Готовность платить",             "kind": "web",
     "domains": ["habr.com", "vc.ru", "pikabu.ru", "otzovik.com"], "suffix": "сколько стоит подписка готов платить"},
]


def _agent_search(agent: dict, query: str, n: int = 6) -> list[dict]:
    q = f"{query} {agent['suffix']}".strip()
    try:
        if agent["kind"] == "reddit":
            return SignalsService._search_reddit(q, n)
        # web через ddg с доменами агента
        return _ddg_domains(q, agent["domains"], n)
    except Exception as e:
        logger.error(f"Агент {agent['id']} ошибка: {e}")
        return []


def _ddg_domains(query: str, domains: list[str], n: int) -> list[dict]:
    """DuckDuckGo с фильтром по доменам конкретного агента."""
    try:
        from ddgs import DDGS
    except ImportError:
        logger.error("ddgs не установлен — web-агенты недоступны.")
        return []
    site = (' (' + ' OR '.join(f'site:{d}' for d in domains) + ')') if domains else ''
    out = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query + site, region='ru-ru', max_results=n):
                url = r.get('href') or r.get('url') or ''
                out.append({
                    "title": r.get('title') or 'Источник',
                    "url": url,
                    "domain": _domain(url),
                    "highlights": [_clip(r.get('body'))] if r.get('body') else [],
                    "source": "web",
                })
    except Exception as e:
        logger.error(f"ddg domains error: {e}")
    return out


def _llm_synthesize(query: str, segments: list[str], sources: list[dict]) -> dict | None:
    """LLM сводит сырые сигналы в структуру дашборда. None при недоступности."""
    if not Config.LLM_API_KEY or not Config.LLM_BASE_URL:
        return None
    # Компактный дайджест найденного (ограничиваем объём).
    lines = []
    for s in sources[:70]:
        hl = (s.get("highlights") or [""])[0]
        lines.append(f"[{s.get('domain','web')}] {s.get('title','')} — {hl}")
    digest = "\n".join(lines)[:8000]
    seg_line = ", ".join(segments) if segments else "не заданы"

    prompt = (
        "Ты аналитик CustDev. По СЫРЫМ сигналам из сообществ оцени спрос на продукт. "
        "Гипотеза/продукт: " + query + ". Сегменты ЦА: " + seg_line + ".\n\n"
        "СЫРЫЕ СИГНАЛЫ:\n" + digest + "\n\n"
        "Верни СТРОГО JSON без пояснений по схеме:\n"
        "{\n"
        '  "segments": [{"name": str, "temperature": "hot|warm|cold", "pain_count": int, "note": str}],\n'
        '  "willingness": {"complaining": int, "seeking": int, "paying": int},\n'
        '  "top_pains": [{"text": str, "count": int, "tag": "pain|pay", "evidence": [int]}],\n'
        '  "competitors": [{"name": str, "weakness": str}],\n'
        '  "verdict": "Есть|Слабый|Нет",\n'
        '  "summary": str\n'
        "}\n"
        "Все числа должны быть подсчётом сигналов из входного дайджеста, а не оценкой размера рынка. "
        "temperature: hot=много боли и спроса, "
        "cold=почти нет. Сегменты бери из заданных, если пусто — выдели сам. Только JSON."
    )
    try:
        client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
        resp = client.chat.completions.create(
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = resp.choices[0].message.content.strip()
        # Вырезаем JSON, если модель обернула в ```.
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip() if "```json" in text else text.split("```")[1].strip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
    except Exception as e:
        logger.error(f"LLM synthesize error: {e}")
    return None


def _sources_by_platform(sources: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for s in sources:
        key = s.get("domain") or "web"
        # Группируем reddit-сабреддиты в reddit.com
        if key.startswith("reddit.com"):
            key = "reddit.com"
        counts[key] = counts.get(key, 0) + 1
    total = sum(counts.values()) or 1
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:6]
    return [{"platform": k, "count": v, "percent": round(v * 100 / total)} for k, v in items]


def _normalise_analysis(analysis: dict, sources: list[dict]) -> dict:
    """Keep LLM-derived dashboard numbers bounded by observed evidence."""
    if not isinstance(analysis, dict):
        return {}
    max_count = len(sources)
    willingness = analysis.get('willingness')
    if isinstance(willingness, dict):
        for key in ('complaining', 'seeking', 'paying'):
            try:
                willingness[key] = max(0, min(int(willingness.get(key, 0)), max_count))
            except (TypeError, ValueError):
                willingness[key] = 0
    for segment in analysis.get('segments') or []:
        if isinstance(segment, dict):
            try:
                segment['pain_count'] = max(0, min(int(segment.get('pain_count', 0)), max_count))
            except (TypeError, ValueError):
                segment['pain_count'] = 0
    for pain in analysis.get('top_pains') or []:
        if isinstance(pain, dict):
            try:
                pain['count'] = max(0, min(int(pain.get('count', 0)), max_count))
            except (TypeError, ValueError):
                pain['count'] = 0
    analysis['observed_sources'] = max_count
    analysis['data_quality'] = 'evidence_bounded' if max_count else 'no_evidence'
    return analysis


def start_research(query: str, segments: list[str], owner_id: str | None = None) -> str:
    """Создаёт задачу и запускает рой агентов в фоне. Возвращает task_id."""
    tm = TaskManager()
    task_id = tm.create_task("signals_research", metadata={
        "query": query, "segments": segments, "owner_id": str(owner_id) if owner_id else None,
    })

    agents_state = [{"id": a["id"], "name": a["name"], "status": "queued",
                     "sources": 0, "done": False} for a in AGENTS]
    started = time.time()

    def _detail(msg_agents, total_sources):
        return {"agents": msg_agents, "total_sources": total_sources,
                "elapsed": int(time.time() - started)}

    tm.update_task(task_id, status=TaskStatus.PROCESSING, progress=1,
                   message="Запуск агентов разведки…",
                   progress_detail=_detail(agents_state, 0))

    def run():
        all_sources: list[dict] = []
        try:
            # Все углы независимы: параллельный запуск сокращает latency и
            # делает прогресс действительно отражающим работу роя.
            for state in agents_state:
                state["status"] = "searching"
            tm.update_task(task_id, message="Агенты ищут сигналы параллельно…",
                           progress=5, progress_detail=_detail(agents_state, 0))
            with ThreadPoolExecutor(max_workers=len(AGENTS)) as executor:
                futures = {
                    executor.submit(_agent_search, agent, query): i
                    for i, agent in enumerate(AGENTS)
                }
                completed = 0
                for future in as_completed(futures):
                    i = futures[future]
                    found = future.result()
                    all_sources.extend(found)
                    agents_state[i].update(status="Готово", sources=len(found), done=True)
                    completed += 1
                    tm.update_task(
                        task_id,
                        message=f"Готово: {agents_state[i]['name']}",
                        progress=5 + int(completed / len(AGENTS) * 70),
                        progress_detail=_detail(agents_state, len(all_sources)),
                    )

            tm.update_task(task_id, progress=80, message="Свожу сигналы в вердикт…",
                           progress_detail=_detail(agents_state, len(all_sources)))

            analysis = _normalise_analysis(_llm_synthesize(query, segments, all_sources) or {}, all_sources)
            result = {
                "query": query,
                "segments_input": segments,
                "sources": all_sources,
                "sources_count": len(all_sources),
                "sources_by_platform": _sources_by_platform(all_sources),
                "elapsed": int(time.time() - started),
                "analysis": analysis,
                "analysis_available": bool(analysis),
            }
            tm.complete_task(task_id, result)
            logger.info(f"Signals research {task_id}: {len(all_sources)} источников, analysis={bool(analysis)}")
        except Exception as e:
            logger.error(f"Signals research {task_id} failed: {e}")
            tm.fail_task(task_id, str(e))

    threading.Thread(target=run, daemon=True).start()
    return task_id
