"""Финальный вердикт: Сигналы рынка × Симуляция общества.

Сводит реальные сигналы (web/Reddit) и ответы фокус-группы агентов в один
честный go/no-go + масштабный markdown-разбор взаимодействия агентов.
LLM = routerai (Config.LLM_MODEL_NAME, сейчас MiMo).
"""

import os
import json
import re
from openai import OpenAI

from ..config import Config
from ..services.simulation_manager import SimulationManager
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


def generate_full_report(simulation_id: str, query: str) -> dict:
    """Возвращает {verdict_struct, signals, custdev_count, report_markdown}."""
    answers = load_custdev_answers(simulation_id)
    signals = load_saved_signals(simulation_id)
    if signals is None:
        signals = SignalsService.scan(query or '', max_results=12)
        signals['evidence_source'] = 'live_scan'
    else:
        signals['evidence_source'] = 'attached_research'
    sources = signals.get('sources', [])

    result = {
        "signals": signals,
        "custdev_count": len(answers),
        "verdict": {},
        "report_markdown": "",
        "available": bool(Config.LLM_API_KEY and Config.LLM_BASE_URL),
    }
    if not result["available"]:
        return result

    prompt = (
        "Ты ведущий аналитик CustDev. Сведи ДВЕ независимые опоры в честный вердикт по продукту.\n"
        f"Продукт/гипотеза: {query}\n\n"
        f"ОПОРА 1 — РЕАЛЬНЫЕ СИГНАЛЫ РЫНКА (из сообществ):\n{_signals_digest(sources) or 'нет данных'}\n\n"
        f"ОПОРА 2 — ОТВЕТЫ ОБЩЕСТВА АГЕНТОВ (фокус-группа, CustDev-интервью):\n{_answers_digest(answers) or 'интервью не проводилось'}\n\n"
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
        "report_markdown должен быть развёрнутым (не короче 400 слов), на русском, по делу."
    )
    try:
        client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
        resp = client.chat.completions.create(
            model=Config.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=4000,
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
            result["verdict"] = parsed
    except Exception as e:
        logger.error(f"verdict synthesize error: {e}")
    return result
