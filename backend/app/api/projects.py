"""Projects API — импорт паспорта проекта пользователя с главного сервера."""

from flask import request, jsonify

from . import projects_bp
from ..services.passport_service import list_projects, get_passport
from ..utils.logger import get_logger
from ..utils.auth import login_required

logger = get_logger('pitchy.api.projects')


def _user_id():
    u = getattr(request, 'user', None) or {}
    return u.get('sub') or u.get('userId') or u.get('id') or u.get('user_id')


@projects_bp.route('/list', methods=['GET'])
@login_required
def list_my_projects():
    """Список проектов текущего пользователя с главного Pitchy (по JWT sub)."""
    uid = _user_id()
    if not uid:
        return jsonify({"success": False, "error": "Нет идентификатора пользователя"}), 400
    try:
        return jsonify({"success": True, "data": {"projects": list_projects(uid)}})
    except Exception as e:
        logger.error(f"list projects failed: {e}")
        return jsonify({"success": False, "error": f"Паспорт-сервис недоступен: {e}"}), 502


@projects_bp.route('/<project_id>/passport', methods=['GET'])
@login_required
def get_project_passport(project_id):
    """Паспорт выбранного проекта (для заполнения гипотезы)."""
    uid = _user_id()
    if not uid:
        return jsonify({"success": False, "error": "Нет идентификатора пользователя"}), 400
    try:
        return jsonify({"success": True, "data": get_passport(uid, project_id)})
    except Exception as e:
        logger.error(f"get passport failed: {e}")
        return jsonify({"success": False, "error": f"Паспорт-сервис недоступен: {e}"}), 502
