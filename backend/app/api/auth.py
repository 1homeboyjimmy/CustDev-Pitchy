import hmac

from flask import Blueprint, current_app, jsonify, redirect, request, session
from ..utils.auth import login_required, current_user_id, is_admin_user
from ..utils import sso
from . import auth_bp


@auth_bp.route('/start', methods=['GET'])
def start_sso():
    """Redirect an unauthenticated browser to the main Pitchy SSO endpoint."""
    target = sso.start_url(request.args.get('next'))
    response = redirect(target, code=302)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@auth_bp.route('/callback', methods=['GET'])
def finish_sso():
    expected_state = str(session.get('sso_state', ''))
    received_state = str(request.args.get('state', ''))
    code = request.args.get('code', '')
    verifier = str(session.get('sso_verifier', ''))
    if not expected_state or not received_state or not hmac.compare_digest(expected_state, received_state):
        session.clear()
        return jsonify({'success': False, 'error': 'Invalid SSO state'}), 400
    if not code or not verifier:
        session.clear()
        return jsonify({'success': False, 'error': 'Missing SSO code'}), 400
    next_path = session.get('sso_next', '/')
    try:
        grant = sso.exchange_code(code, verifier)
        sso.establish_session(grant)
    except Exception:
        session.clear()
        return jsonify({'success': False, 'error': 'SSO exchange failed'}), 401
    response = redirect(next_path if isinstance(next_path, str) else '/', code=302)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@auth_bp.route('/logout', methods=['POST'])
def logout():
    sso.revoke_session()
    response = jsonify({'success': True})
    response.delete_cookie(
        current_app.config['SESSION_COOKIE_NAME'],
        path='/',
    )
    return response

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
