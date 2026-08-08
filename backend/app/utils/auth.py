import jwt
import traceback
import os
import requests
from functools import wraps
from flask import request, jsonify, current_app
from ..config import Config
from .logger import get_logger
from .sso import bridge_user

logger = get_logger('pitchy.auth')


def verify_remote_session(token):
    """Validate the shared HttpOnly cookie through the main Pitchy service."""
    if not token or not Config.MAIN_AUTH_URL:
        return None

    try:
        response = requests.get(
            Config.MAIN_AUTH_URL,
            headers={
                'Cookie': f'access_token={token}',
                'x-pitchy-api': '1',
                'Accept': 'application/json',
            },
            timeout=Config.MAIN_AUTH_TIMEOUT,
            allow_redirects=False,
        )
        if response.status_code != 200:
            return None

        data = response.json() if response.content else {}
        user_id = data.get('id') or data.get('user_id') or data.get('userId') or data.get('sub')
        if user_id is None:
            return None

        return {
            **data,
            'sub': str(user_id),
            'userId': str(user_id),
            'main_auth': True,
        }
    except (requests.RequestException, ValueError, TypeError) as exc:
        # Never include the cookie or its value in logs.
        logger.debug('[AUTH_DEBUG] Main auth fallback unavailable: %s', type(exc).__name__)
        return None

def verify_jwt(token):
    """
    Verify JWT token using the shared secret key.
    """
    try:
        # Get secret key from config
        secret_key = Config.SECRET_KEY
        
        # Support for all possible key transformations
        import hashlib, base64
        key_variants = [
            secret_key,                               # Plain string
            secret_key.encode('utf-8'),               # UTF-8 bytes
        ]
        
        # 1. Hex bytes
        try:
            if len(secret_key) >= 64:
                key_variants.append(bytes.fromhex(secret_key[:64]))
        except: pass
            
        # 2. Base64 decoded (standard for some platforms)
        try:
            key_variants.append(base64.b64decode(secret_key))
        except: pass

        # 3. SHA256 of the key
        key_variants.append(hashlib.sha256(secret_key.encode('utf-8')).digest())

        # Log Header
        header = jwt.get_unverified_header(token)
        logger.debug(f"[AUTH_DEBUG] JWT Header: {header}")

        payload = None
        
        # Try all variants
        for variant in key_variants:
            try:
                payload = jwt.decode(token, variant, algorithms=['HS256', 'HS384', 'HS512', 'RS256'])
                if payload:
                    logger.debug(f"[AUTH_DEBUG] JWT verified successfully using a key variant")
                    break
            except: continue

        # --- FALLBACK: только если ЯВНО разрешено (переходный период) ---
        if not payload:
            if not Config.ALLOW_UNVERIFIED_SESSION:
                # Строгий режim: нет валидной подписи главного сайта → нет доступа.
                logger.warning("[AUTH_DEBUG] Подпись JWT не прошла — доступ запрещён (strict).")
                return None
            logger.warning("[AUTH_DEBUG] !!! UNVERIFIED payload разрешён (ALLOW_UNVERIFIED_SESSION) !!!")
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
            except Exception as e:
                logger.error(f"[AUTH_DEBUG] Could not even decode unverified token: {e}")
                return None

        # Extract user information
        user_id = payload.get('userId') or payload.get('id') or payload.get('sub') or payload.get('user_id')
        
        if not user_id:
            logger.warning(f"[AUTH_DEBUG] JWT payload missing user identifier. Keys: {list(payload.keys())}")
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("[AUTH_DEBUG] JWT token expired")
        return None
    except jwt.InvalidSignatureError as e:
        logger.warning(f"[AUTH_DEBUG] JWT Signature verification failed: {e}")
        # Log unverified payload to see what's inside (issuer, etc)
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            logger.debug(f"[AUTH_DEBUG] Unverified payload: {unverified}")
        except:
            pass
        return None
    except Exception as e:
        logger.warning(f"[AUTH_DEBUG] JWT decode error ({type(e).__name__}): {str(e)}")
        # It's safe to log the first few chars of the token to see if it's actually a JWT
        token_preview = f"{token[:10]}..." if token else "None"
        logger.debug(f"[AUTH_DEBUG] Token preview: {token_preview}, length: {len(token)}")
        return None

def login_required(f):
    """
    Decorator to ensure user is logged in via shared JWT cookie.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if getattr(request, 'user', None):
            return f(*args, **kwargs)

        user_payload = authenticate_request()
        if not user_payload:
            return jsonify({
                "success": False,
                "error": "Authentication required",
                "code": "UNAUTHORIZED",
            }), 401

        request.user = user_payload
        return f(*args, **kwargs)

    return decorated_function


def authenticate_request():
    """Decode the request token without rejecting public/health endpoints."""
    if Config.AUDIT_MODE and request.remote_addr in ('127.0.0.1', '::1'):
        return {'sub': 'audit-user', 'userId': 'audit-user', 'audit_mode': True}

    # Prefer the dedicated SSO grant. In code_exchange mode the main JWT is
    # never accepted or forwarded by CustDev; dual mode is a rollout bridge.
    if Config.CUSTDEV_SSO_MODE in ('dual', 'code_exchange'):
        bridge_payload = bridge_user()
        if bridge_payload:
            return bridge_payload
        if Config.CUSTDEV_SSO_MODE == 'code_exchange':
            return None

    # Read from 'access_token' cookie (standard for the main app)
    cookie_token = request.cookies.get('access_token')

    # Strip potential quotes if the browser/proxy wrapped the cookie value.
    token = cookie_token.strip('"') if cookie_token else None

    # Also check Authorization header as fallback.
    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]

    if not token:
        return None
    local_payload = verify_jwt(token)
    # Only forward the browser's shared HttpOnly cookie to the main service.
    # Authorization headers may contain unrelated bearer credentials.
    return local_payload or (verify_remote_session(token) if cookie_token else None)


def current_user_id():
    """ID текущего пользователя из JWT (sub) — единый способ по всему бэку."""
    u = getattr(request, 'user', None) or {}
    return u.get('sub') or u.get('userId') or u.get('id') or u.get('user_id')


def is_admin_user() -> bool:
    """Является ли текущий пользователь администратором (Config.ADMIN_USER_IDS)."""
    uid = current_user_id()
    return bool(uid) and str(uid) in Config.ADMIN_USER_IDS
