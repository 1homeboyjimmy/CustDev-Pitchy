import jwt
import traceback
from functools import wraps
from flask import request, jsonify, current_app
from ..config import Config
from .logger import get_logger

logger = get_logger('pitchy.auth')

def verify_jwt(token):
    """
    Verify JWT token using the shared secret key.
    """
    try:
        # Get secret key from config
        secret_key = Config.SECRET_KEY
        
        # Decode token with support for common algorithms
        # Added RS256 just in case the main platform uses it
        payload = jwt.decode(token, secret_key, algorithms=['HS256', 'HS384', 'HS512', 'RS256'])
        logger.debug(f"[AUTH_DEBUG] JWT decoded successfully. Payload keys: {list(payload.keys())}")
        
        # Extract user information
        user_id = payload.get('userId') or payload.get('id') or payload.get('sub') or payload.get('user_id')
        
        if not user_id:
            logger.warning(f"[AUTH_DEBUG] JWT payload missing user identifier. Keys: {list(payload.keys())}")
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("[AUTH_DEBUG] JWT token expired")
        return None
    except Exception as e:
        logger.warning(f"[AUTH_DEBUG] JWT decode error ({type(e).__name__}): {str(e)}")
        # It's safe to log the first few chars of the token to see if it's actually a JWT
        token_preview = f"{token[:10]}..." if token else "None"
        logger.debug(f"[AUTH_DEBUG] Token starts with: {token_preview}, length: {len(token) if token else 0}")
        return None

def login_required(f):
    """
    Decorator to ensure user is logged in via shared JWT cookie.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Read from 'access_token' cookie (standard for the main app)
        token = request.cookies.get('access_token')
        
        # Also check Authorization header as fallback
        if not token:
            # TELEMETRY: Log all cookies to find the correct name or verify if they are sent at all
            cookie_names = list(request.cookies.keys())
            logger.debug(f"[AUTH_DEBUG] No 'access_token' cookie found. Total cookies: {len(cookie_names)}. Names: {cookie_names}")
            
            # Fallback to Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                logger.debug("[AUTH_DEBUG] Found token in Authorization header")
        
        if not token:
            return jsonify({
                "success": False,
                "error": "Authentication required",
                "code": "UNAUTHORIZED",
                "debug_info": {
                    "cookies_received": list(request.cookies.keys()),
                    "auth_header_present": bool(request.headers.get('Authorization'))
                }
            }), 401
            
        user_payload = verify_jwt(token)
        if not user_payload:
            logger.debug("[AUTH_DEBUG] JWT verification failed for the provided token")
            return jsonify({
                "success": False,
                "error": "Invalid or expired session",
                "code": "SESSION_EXPIRED",
                "debug_info": {
                    "token_received": True,
                    "token_length": len(token) if token else 0,
                    "secret_key_configured": bool(Config.SECRET_KEY)
                }
            }), 401
            
        # Store user info in request context if needed
        request.user = user_payload
        
        return f(*args, **kwargs)
        
    return decorated_function
