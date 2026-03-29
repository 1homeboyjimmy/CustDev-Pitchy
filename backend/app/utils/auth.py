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
        
        # Decode token
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        logger.debug(f"JWT decoded successfully. Payload keys: {list(payload.keys())}")
        
        # Extract user information - added 'user_id' as common variant
        user_id = payload.get('userId') or payload.get('id') or payload.get('sub') or payload.get('user_id')
        
        if not user_id:
            logger.warning(f"JWT payload missing user identifier. Full payload keys: {list(payload.keys())}")
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT token invalid: {str(e)}")
        # Log a small piece of the key to verify we're using the right one (first 4 chars)
        logger.debug(f"Verify failed. Using SECRET_KEY starting with: {secret_key[:4] if secret_key else 'None'}...")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during JWT verification: {str(e)}")
        logger.error(traceback.format_exc())
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
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            logger.debug(f"No 'access_token' cookie found. Total cookies received: {len(request.cookies)}. Names: {list(request.cookies.keys())}")
            return jsonify({
                "success": False,
                "error": "Authentication required",
                "code": "UNAUTHORIZED"
            }), 401
            
        user_payload = verify_jwt(token)
        if not user_payload:
            return jsonify({
                "success": False,
                "error": "Invalid or expired session",
                "code": "SESSION_EXPIRED"
            }), 401
            
        # Store user info in request context if needed
        request.user = user_payload
        
        return f(*args, **kwargs)
        
    return decorated_function
