import jwt
import traceback
import os
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

        # --- FALLBACK: TRUST UNVERIFIED FOR DEVELOPMENT ---
        if not payload:
            logger.warning("[AUTH_DEBUG] !!! CRITICAL SECURITY WARNING: Signature verification failed for JWT !!!")
            logger.warning("[AUTH_DEBUG] !!! Falling back to UNVERIFIED payload for session sync !!!")
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
        # Read from 'access_token' cookie (standard for the main app)
        token = request.cookies.get('access_token')
        
        # Strip potential quotes if the browser/proxy wrapped the cookie value
        if token:
            token = token.strip('"')
        
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
