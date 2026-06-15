"""Signals API Routes — pain-mining реальных сигналов рынка через Exa."""

from flask import request, jsonify

from . import signals_bp
from ..services.signals_service import SignalsService
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
