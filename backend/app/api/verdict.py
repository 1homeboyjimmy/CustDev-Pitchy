"""Verdict API — финальный отчёт «Сигналы × Симуляция»."""

from flask import request, jsonify

from . import verdict_bp
from ..services.verdict_service import generate_full_report
from ..utils.logger import get_logger
from ..utils.auth import login_required

logger = get_logger('pitchy.api.verdict')


@verdict_bp.route('/generate', methods=['POST'])
@login_required
def generate_verdict():
    """Сводит сигналы + ответы фокус-группы в вердикт и масштабный отчёт.

    Request (JSON): { "simulation_id": str, "query": str }
    """
    try:
        data = request.get_json() or {}
        simulation_id = (data.get('simulation_id') or '').strip()
        query = (data.get('query') or '').strip()
        if not simulation_id:
            return jsonify({"success": False, "error": "Please provide simulation_id"}), 400
        result = generate_full_report(simulation_id, query)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"Verdict generate failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
