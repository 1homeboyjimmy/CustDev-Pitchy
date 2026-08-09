"""Signals API Routes — pain-mining реальных сигналов рынка (рой агентов)."""

import os
import re
import json
import tempfile
from pathlib import Path

from flask import request, jsonify

from . import signals_bp
from ..config import Config
from ..services.signals_service import SignalsService
from ..services.signals_research import start_research
from ..services.simulation_manager import SimulationManager
from ..models.task import TaskManager
from ..utils.logger import get_logger
from ..utils.auth import login_required, current_user_id, is_admin_user
from ..utils.file_parser import FileParser
from ..services.text_processor import TextProcessor

logger = get_logger('pitchy.api.signals')

# Разрешённый формат id симуляции — защита от path traversal при сборке пути.
_SIM_ID_RE = re.compile(r'^[A-Za-z0-9_\-]+$')


def _signals_path(simulation_id: str):
    """Путь к сохранённым сигналам прогона. None — если id небезопасен."""
    if not simulation_id or not _SIM_ID_RE.match(simulation_id):
        return None
    sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
    return os.path.join(sim_dir, 'signals.json')


def signals_saved(simulation_id: str) -> bool:
    """Есть ли сохранённые сигналы для прогона (для payload истории)."""
    path = _signals_path(simulation_id)
    return bool(path and os.path.exists(path))


def _check_simulation_access(simulation_id: str):
    """Return a response on access failure, otherwise None."""
    state = SimulationManager().get_simulation(simulation_id)
    if not state:
        return jsonify({"success": False, "error": "Simulation not found"}), 404
    uid = current_user_id()
    if state.user_id is None:
        if not is_admin_user():
            return jsonify({"success": False, "error": "Simulation access denied"}), 403
    elif str(state.user_id) != str(uid) and not is_admin_user():
        return jsonify({"success": False, "error": "Simulation access denied"}), 403
    return None


@signals_bp.route('/presentation-context', methods=['POST'])
@login_required
def extract_presentation_context():
    """Extract a bounded deck excerpt before real-market signal research."""
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or all(not item.filename for item in uploaded_files):
        return jsonify({'success': False, 'error': 'Прикрепите PDF или PPTX'}), 400

    parts = []
    errors = []
    with tempfile.TemporaryDirectory(prefix='custdev-deck-') as directory:
        for index, item in enumerate(uploaded_files[:5]):
            filename = item.filename or ''
            suffix = Path(filename).suffix.lower()
            if suffix not in {'.pdf', '.pptx'}:
                errors.append(f'{filename}: поддерживаются только PDF и PPTX')
                continue
            path = os.path.join(directory, f'deck-{index}{suffix}')
            item.save(path)
            if os.path.getsize(path) > 25 * 1024 * 1024:
                errors.append(f'{filename}: файл превышает 25 МБ')
                continue
            try:
                text = TextProcessor.preprocess_text(FileParser.extract_text(path))
                if text.strip():
                    parts.append(f'=== {filename} ===\n{text.strip()}')
            except Exception as exc:
                errors.append(f'{filename}: {exc}')

    if not parts:
        return jsonify({
            'success': False,
            'error': '; '.join(errors) or 'В презентации не найден текст для анализа',
        }), 400
    requirement = (request.form.get('requirement') or '').strip()
    extracted_text = '\n\n'.join(parts)[:60000]
    context = extracted_text[:8000]
    return jsonify({'success': True, 'data': {
        'research_context': f'Проверяемая гипотеза: {requirement}\n\nКонтекст презентации:\n{context}',
        'extracted_text': extracted_text,
        'extracted_characters': len(context),
        'files_processed': len(parts),
        'warnings': errors,
    }})


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
        task_id = start_research(query, segments, owner_id=current_user_id())
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
    owner_id = (task.metadata or {}).get('owner_id')
    if owner_id and str(owner_id) != str(current_user_id()) and not is_admin_user():
        return jsonify({"success": False, "error": "Task access denied"}), 403
    return jsonify({"success": True, "data": task.to_dict()})


@signals_bp.route('/attach', methods=['POST'])
@login_required
def attach_signals():
    """Сохраняет результат разведки сигналов к прогону (для просмотра из истории).

    Вызывается фоном после создания симуляции. Идемпотентно: перезаписывает файл.
    Request (JSON): { "simulation_id": str, "result": {...} }
    """
    try:
        data = request.get_json() or {}
        simulation_id = (data.get('simulation_id') or '').strip()
        result = data.get('result')
        path = _signals_path(simulation_id)
        if not path:
            return jsonify({"success": False, "error": "Invalid simulation_id"}), 400
        access_error = _check_simulation_access(simulation_id)
        if access_error:
            return access_error
        if not isinstance(result, dict):
            return jsonify({"success": False, "error": "Please provide result object"}), 400
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Signals attach failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@signals_bp.route('/saved', methods=['GET'])
@login_required
def get_saved_signals():
    """Отдаёт сохранённые сигналы прогона по simulation_id (read-only из истории)."""
    simulation_id = (request.args.get('simulation_id') or '').strip()
    path = _signals_path(simulation_id)
    if not path:
        return jsonify({"success": False, "error": "Invalid simulation_id"}), 400
    access_error = _check_simulation_access(simulation_id)
    if access_error:
        return access_error
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "Signals not found"}), 404
    try:
        with open(path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"Read saved signals failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
