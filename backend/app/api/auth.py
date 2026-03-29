from flask import Blueprint, jsonify, request
from ..utils.auth import login_required
from . import auth_bp

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    """
    Get current user information from session cookie.
    Already validated by @login_required decorator.
    """
    return jsonify({
        "success": True,
        "data": request.user
    })
