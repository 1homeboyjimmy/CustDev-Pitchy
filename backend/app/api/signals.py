"""Signals API Routes — pain-mining реальных сигналов рынка (рой агентов)."""

from flask import request, jsonify

from . import signals_bp
from ..services.signals_service import SignalsService
from ..services.signals_research import start_research
from ..models.task import TaskManager
from ..utils.logger import get_logger
from ..utils.auth import login_required

logger = get_logger('pitchy.api.signals')


@signals_bp.route('/scan', methods=['POST'])
@login_required
def scan_signals():
    """Ищет реальные сигналы (боли/спрос) по гипотезе в RU-сообществах.

    Request (JSON): { "query": "...", "max_results"?: 8 }
    Returns: { success, data: { available, sources:[{title,url,domain,highlights}], context, query } }
    """
    try:
        data = request.get_json() or {}
        query = (data.get('query') or '').strip()
        if not query:
            return jsonify({"success": False, "error": "Please provide query"}), 400

        max_results = int(data.get('max_results', 8) or 8)
        max_results = max(1, min(max_results, 20))

        result = SignalsService.scan(query, max_results=max_results)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"Signals scan failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@signals_bp.route('/research', methods=['POST'])
@login_required
def start_signals_research():
    """Запускает рой research-агентов (фон). Возвращает task_id для опроса.

    Request (JSON): { "query": str, "segments"?: [str] }
    """
    try:
        data = request.get_json() or {}
        query = (data.get('query') or '').strip()
        if not query:
            return jsonify({"success": False, "error": "Please provide query"}), 400
        segments = data.get('segments') or []
        if not isinstance(segments, list):
            segments = []
        task_id = start_research(query, segments)
        return jsonify({"success": True, "data": {"task_id": task_id}})
    except Exception as e:
        logger.error(f"Signals research start failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@signals_bp.route('/research/status', methods=['GET'])
@login_required
def signals_research_status():
    """Статус задачи разведки: прогресс агентов + итоговый результат."""
    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({"success": False, "error": "Please provide task_id"}), 400
    task = TaskManager().get_task(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404
    return jsonify({"success": True, "data": task.to_dict()})
