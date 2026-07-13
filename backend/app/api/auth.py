from flask import Blueprint, jsonify, request
from ..utils.auth import login_required, current_user_id, is_admin_user
from . import auth_bp

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    """
    Get current user information from session cookie.
    Already validated by @login_required decorator.
    """
    data = dict(request.user) if isinstance(request.user, dict) else {}
    data["user_id"] = current_user_id()
    data["is_admin"] = is_admin_user()
    return jsonify({
        "success": True,
        "data": data
    })
