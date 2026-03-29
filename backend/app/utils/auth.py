import jwt
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
        # Main server uses 'access_token' cookie and shared SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        
        # Extract user information
        # Adjust field names based on the main site's JWT structure (typically 'id' or 'sub')
        user_id = payload.get('userId') or payload.get('id') or payload.get('sub')
        
        if not user_id:
            logger.warning("JWT payload missing user identifier")
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT token invalid: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during JWT verification: {str(e)}")
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
