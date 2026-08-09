"""Финальный вердикт: Сигналы рынка × Симуляция общества.

Сводит реальные сигналы (web/Reddit) и ответы фокус-группы агентов в один
честный go/no-go + масштабный markdown-разбор взаимодействия агентов.
LLM = routerai (Config.LLM_MODEL_NAME, сейчас MiMo).
"""

import os
import json
import re
import hashlib
from openai import OpenAI

from ..config import Config
from ..services.simulation_manager import SimulationManager
from ..services.simulation_runner import SimulationRunner
from ..services.signals_service import SignalsService
from ..utils.logger import get_logger

logger = get_logger('pitchy.verdict_service')

_SIM_ID_RE = re.compile(r'^[A-Za-z0-9_-]+$')


def load_custdev_answers(simulation_id: str) -> list[dict]:
    try:
        path = os.path.join(SimulationManager()._get_simulation_dir(simulation_id), 'custdev_answers.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"load custdev answers: {e}")
    return []


def load_simulation_reactions(simulation_id: str) -> list[dict]:
    """Load unique substantive reactions emitted by the agent society.

    OASIS mirrors the same agent post to Twitter and Reddit, so counting raw
    actions would double the apparent focus-group size. The verdict works with
    unique agent/content pairs and labels them as synthetic evidence.
    """
    try:
        actions = SimulationRunner.get_all_actions(simulation_id)
    except Exception as exc:
        logger.error("load simulation reactions: %s", exc)
        return []

    reactions = []
    seen = set()
    for action in actions:
        args = action.action_args if isinstance(action.action_args, dict) else {}
        content = str(args.get('content') or args.get('text') or '').strip()
        if not content or not action.success:
            continue
        normalized = re.sub(r'\s+', ' ', content).casefold()
        key = (str(action.agent_id), normalized)
        if key in seen:
            continue
        seen.add(key)
        reactions.append({
            'agent_name': action.agent_name or f'Агент {action.agent_id}',
            'agent_role': 'участник синтетической симуляции',
            'question': 'Реакция на проверяемую продуктовую гипотезу',
            'response': content,
            'source_type': 'synthetic_simulation',
            'action_type': action.action_type,
            'round_num': action.round_num,
        })
    return reactions


def load_saved_signals(simulation_id: str) -> dict | None:
    """Load the immutable research result attached to a simulation.

    The verdict must analyse the same evidence that the user saw in the
    Signals screen; re-running an external search would make history drift.
    """
    if not simulation_id or not _SIM_ID_RE.match(simulation_id):
        return None
    path = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id, 'signals.json')
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
    except Exception as e:
        logger.error(f"load saved signals: {e}")
    return None


def _answers_digest(answers: list[dict], limit: int = 60) -> str:
    lines = []
    for a in answers[:limit]:
        who = f"{a.get('agent_name', 'Агент')} ({a.get('agent_role', '')})".strip()
        lines.append(f"[{who}] В: {a.get('question', '')}\n    О: {(a.get('response') or '')[:400]}")
    return "\n".join(lines)[:9000]


def _signals_digest(sources: list[dict], limit: int = 40) -> str:
    lines = []
    for s in sources[:limit]:
        hl = (s.get('highlights') or [''])[0]
        lines.append(f"[{s.get('domain', 'web')}] {s.get('title', '')} — {hl}")
    return "\n".join(lines)[:6000]


def _market_evidence_stats(signals: dict, reactions: list[dict]) -> dict:
    sources = [s for s in signals.get('sources', []) if (s.get('highlights') or [])]
    domains = {str(s.get('domain') or '').lower() for s in sources if s.get('domain')}
    community_domains = {
        'reddit.com', 'habr.com', 'vc.ru', 'pikabu.ru', 'otzovik.com',
        'irecommend.ru', 'ozon.ru', 'wildberries.ru',
    }
    community_count = sum(
        1 for source in sources
        if any(str(source.get('domain') or '').lower().endswith(domain) for domain in community_domains)
    )
    # Evidence confidence is deliberately capped by observed coverage. The LLM
    # may lower it, but cannot claim more certainty than the dataset supports.
    quality_score = min(60, len(sources) * 4)
    quality_score += min(20, len(domains) * 4)
    quality_score += min(10, community_count)
    quality_score += min(10, len(reactions) * 2)
    return {
        'real_sources': len(sources),
        'unique_domains': len(domains),
        'community_sources': community_count,
        'synthetic_respondents': len({r.get('agent_name') for r in reactions}),
        'quality_score': min(100, quality_score),
        'real_market_weight': 70,
        'simulation_weight': 30,
    }


def _observed_dashboard_evidence(signals: dict, reactions: list[dict]) -> dict:
    def safe_count(value) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    analysis = signals.get('analysis') if isinstance(signals.get('analysis'), dict) else {}
    willingness = analysis.get('willingness') if isinstance(analysis.get('willingness'), dict) else {}
    complaining = safe_count(willingness.get('complaining'))
    paying = safe_count(willingness.get('paying'))
    pay_pct = min(100, round(paying * 100 / complaining)) if complaining else 0
    hot_segments = [
        str(segment.get('name')) for segment in analysis.get('segments') or []
        if isinstance(segment, dict) and segment.get('temperature') == 'hot' and segment.get('name')
    ]
    pains = [pain for pain in analysis.get('top_pains') or [] if isinstance(pain, dict)]
    pains.sort(key=lambda pain: safe_count(pain.get('count')), reverse=True)
    return {
        'pay_pct': pay_pct,
        'hot_segments': ', '.join(hot_segments[:3]) or 'не подтверждены',
        'hot_personas': f"{len({r.get('agent_name') for r in reactions})} синтетических респондентов",
        'top_pain': str(pains[0].get('text')) if pains else 'не подтверждена',
    }


def generate_full_report(simulation_id: str, query: str) -> dict:
    """Возвращает {verdict_struct, signals, custdev_count, report_markdown}."""
    manual_answers = load_custdev_answers(simulation_id)
    simulation_reactions = load_simulation_reactions(simulation_id)
    answers = manual_answers + simulation_reactions
    signals = load_saved_signals(simulation_id)
    if signals is None:
        signals = SignalsService.scan(query or '', max_results=12)
        signals['evidence_source'] = 'live_scan'
    else:
        signals['evidence_source'] = 'attached_research'
    sources = signals.get('sources', [])

    cache_path = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id, 'verdict.json')
    fingerprint_payload = {
        'query': query,
        'sources': sources,
        'answers': answers,
        'version': 2,
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode('utf-8')
    ).hexdigest()
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as stream:
                cached = json.load(stream)
            if cached.pop('_fingerprint', None) == fingerprint:
                cached['cached'] = True
                return cached
    except Exception as exc:
        logger.warning('verdict cache read failed: %s', exc)

    evidence_stats = _market_evidence_stats(signals, simulation_reactions)
    observed_evidence = _observed_dashboard_evidence(signals, simulation_reactions)
    result = {
        "signals": signals,
        "custdev_count": len(answers),
        "manual_interview_count": len(manual_answers),
        "simulation_reaction_count": len(simulation_reactions),
        "evidence_stats": evidence_stats,
        "verdict": {},
        "report_markdown": "",
        "available": bool(Config.LLM_API_KEY and Config.LLM_BASE_URL),
    }
    if not result["available"]:
        return result

    prompt = (
        "Ты ведущий аналитик CustDev. Сведи две опоры в честный вердикт по продукту. "
        "Реальные рыночные источники имеют вес 70%, синтетическая симуляция — 30%. "
        "Никогда не называй агентов реальными пользователями и не придумывай цитаты, проценты или факты.\n"
        f"Продукт/гипотеза: {query}\n\n"
        f"ОПОРА 1 — РЕАЛЬНЫЕ СИГНАЛЫ РЫНКА (из сообществ):\n{_signals_digest(sources) or 'нет данных'}\n\n"
        f"НАБЛЮДАЕМАЯ СТАТИСТИКА: {json.dumps(evidence_stats, ensure_ascii=False)}\n"
        f"ОПОРА 2 — СИНТЕТИЧЕСКИЕ РЕАКЦИИ ОБЩЕСТВА АГЕНТОВ (не реальные интервью):\n{_answers_digest(answers) or 'реакций нет'}\n\n"
        "Верни СТРОГО JSON (без пояснений вне JSON):\n"
        "{\n"
        '  "verdict": "Спрос есть|Спрос есть, но осторожно|Спрос слабый|Спроса нет",\n'
        '  "confidence": 0-100,\n'
        '  "summary": "1-2 фразы итога",\n'
        '  "signals_side": "1 фраза: что говорят реальные сигналы",\n'
        '  "simulation_side": "1 фраза: что говорит общество агентов",\n'
        '  "agreement": "согласны|частично|расходятся",\n'
        '  "evidence": {"pay_pct": int, "hot_segments": str, "hot_personas": str, "top_pain": str},\n'
        '  "red_flags": [str, str],\n'
        '  "recommendation": "что делать дальше, 1-2 фразы",\n'
        '  "report_markdown": "МАСШТАБНЫЙ разбор в markdown из ДВУХ разделов: ## Взаимодействие агентов в симуляции (подробно разбери ответы персон по вопросам CustDev — кто загорелся, кто скептичен, ключевые реплики и противоречия) и ## Оценка: Сигналы × Симуляция (где две опоры сходятся, где расходятся, риски, итоговый вывод). Сигналы отдельной секцией НЕ дублируй — они показаны выше."\n'
        "}\n"
        "report_markdown должен быть развёрнутым (не короче 400 слов), на русском, по делу. "
        "Каждый вывод отделяй как подтверждённый реальным рынком, синтетический или гипотезу."
    )
    try:
        client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL, timeout=60.0)
        resp = client.chat.completions.create(
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=2600,
        )
        text = resp.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(text[start:end + 1])
            result["report_markdown"] = parsed.pop("report_markdown", "")
            parsed['evidence'] = observed_evidence
            try:
                parsed['confidence'] = min(
                    max(0, int(parsed.get('confidence', 0))),
                    evidence_stats['quality_score'],
                )
            except (TypeError, ValueError):
                parsed['confidence'] = evidence_stats['quality_score']
            result["verdict"] = parsed
    except Exception as e:
        logger.error(f"verdict synthesize error: {e}")
    if result.get('verdict'):
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as stream:
                json.dump({**result, '_fingerprint': fingerprint}, stream, ensure_ascii=False)
        except Exception as exc:
            logger.warning('verdict cache write failed: %s', exc)
    return result
