"""
Configuration Management
Loads configuration from .env file in project root directory
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
# Path: Pitchy/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
    # Diagnostic log (will be visible in stdout)
    print(f"[CONFIG_DEBUG] Loaded .env from: {os.path.abspath(project_root_env)}")
else:
    # If no .env in root, try to load environment variables (for production)
    load_dotenv(override=True)
    print(f"[CONFIG_DEBUG] .env not found at {os.path.abspath(project_root_env)}, using system env")

# Check if secret key is present
app_secret = os.environ.get('APP_SECRET_KEY')
std_secret = os.environ.get('SECRET_KEY')
secret_key_check = app_secret or std_secret

if secret_key_check:
    preview = secret_key_check.strip()[:4]
    print(f"[CONFIG_DEBUG] SECRET_KEY is present (raw_len: {len(secret_key_check)}, preview: {preview}...)")
else:
    print("[CONFIG_DEBUG] WARNING: SECRET_KEY is missing from environment!")

# Check for emergency bypass
bypass_check = os.environ.get('ALLOW_UNVERIFIED_SESSION')
print(f"[CONFIG_DEBUG] ALLOW_UNVERIFIED_SESSION is set to: {bypass_check}")


class Config:
    """Flask configuration class"""

    # Flask configuration
    # Never ship a predictable signing key. Production startup now fails via
    # validate() until the shared main-site secret is configured.
    SECRET_KEY = os.environ.get('APP_SECRET_KEY', os.environ.get('SECRET_KEY', '')).strip()
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # Если True — при неудачной проверке подписи JWT доверяем непроверенному
    # payload (НЕБЕЗОПАСНО, только для переходного периода синхронизации секрета).
    # По умолчанию выкл: без валидной сессии главного сайта вход запрещён.
    ALLOW_UNVERIFIED_SESSION = os.environ.get('ALLOW_UNVERIFIED_SESSION', '').strip().lower() in ('1', 'true', 'yes')
    # Test-only local harness. It is disabled by default and only accepts
    # loopback requests; never enable it in a deployed environment.
    AUDIT_MODE = os.environ.get('CUSTDEV_AUDIT_MODE', '').strip().lower() in ('1', 'true', 'yes')

    # Куда редиректить, если сессии нет (логин основного сайта).
    MAIN_LOGIN_URL = os.environ.get('MAIN_LOGIN_URL', 'https://pitchy.pro/login')

    # Server-to-server SSO. The main Pitchy JWT is exchanged for a short-lived
    # CustDev grant; its signing key is never shared with this service.
    CUSTDEV_SSO_MODE = os.environ.get('CUSTDEV_SSO_MODE', 'dual').strip().lower()
    CUSTDEV_SSO_CLIENT_ID = os.environ.get('CUSTDEV_SSO_CLIENT_ID', 'custdev').strip()
    CUSTDEV_SSO_AUTHORIZE_URL = os.environ.get(
        'CUSTDEV_SSO_AUTHORIZE_URL',
        'https://pitchy.pro/auth/sso/custdev/authorize',
    ).strip()
    CUSTDEV_SSO_EXCHANGE_URL = os.environ.get(
        'CUSTDEV_SSO_EXCHANGE_URL',
        'https://pitchy.pro/internal/auth/custdev/exchange',
    ).strip()
    CUSTDEV_SSO_INTROSPECT_URL = os.environ.get(
        'CUSTDEV_SSO_INTROSPECT_URL',
        'https://pitchy.pro/internal/auth/custdev/introspect',
    ).strip()
    CUSTDEV_SSO_REVOKE_URL = os.environ.get(
        'CUSTDEV_SSO_REVOKE_URL',
        'https://pitchy.pro/internal/auth/custdev/revoke',
    ).strip()
    CUSTDEV_SSO_REDIRECT_URI = os.environ.get(
        'CUSTDEV_SSO_REDIRECT_URI',
        'https://custdev.pitchy.pro/api/auth/callback',
    ).strip()
    CUSTDEV_SSO_SERVICE_SECRET = os.environ.get('CUSTDEV_SSO_SERVICE_SECRET', '').strip()
    CUSTDEV_SSO_TIMEOUT = float(os.environ.get('CUSTDEV_SSO_TIMEOUT', '5'))
    CUSTDEV_SSO_RECHECK_SECONDS = float(os.environ.get('CUSTDEV_SSO_RECHECK_SECONDS', '60'))
    CUSTDEV_SESSION_SECRET = os.environ.get(
        'CUSTDEV_SESSION_SECRET',
        'custdev-dev-session-secret-change-me',
    ).strip()
    SESSION_COOKIE_NAME = '__Host-custdev_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('APP_ENV', 'dev').lower() == 'prod'
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_PATH = '/'
    # Основной Pitchy остаётся источником истины для общей HttpOnly-сессии.
    # Используется только после неуспешной локальной проверки JWT.
    MAIN_AUTH_URL = os.environ.get('MAIN_AUTH_URL', 'https://pitchy.pro/me').strip()
    MAIN_AUTH_TIMEOUT = float(os.environ.get('MAIN_AUTH_TIMEOUT', '3'))

    # ID администраторов (совпадают с user_id главного сайта, `sub` в JWT).
    # Список через запятую в env `ADMIN_USER_IDS`, напр. "1,42". По умолчанию пусто —
    # тогда кнопка «Админ» скрыта у всех, а история прогонов строго персональна.
    # Админ видит кнопку «Админ» и legacy-прогоны без владельца (созданные до
    # персональной истории). Чужие персональные прогоны админ не видит.
    ADMIN_USER_IDS = {
        x.strip() for x in os.environ.get('ADMIN_USER_IDS', '').split(',') if x.strip()
    }

    # JSON configuration - disable ASCII escaping to display Chinese directly (not as \uXXXX)
    JSON_AS_ASCII = False

    # LLM configuration (unified OpenAI format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'http://localhost:11434/v1')
    # Текстовая быстрая модель (дек больше не грузим — vision не нужен).
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'deepseek/deepseek-v4-flash')

    # Neo4j configuration
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'pitchy')
    NEO4J_CONNECTION_TIMEOUT = float(os.environ.get('NEO4J_CONNECTION_TIMEOUT', '5'))

    # Embedding configuration
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'nomic-embed-text')
    EMBEDDING_BASE_URL = os.environ.get('EMBEDDING_BASE_URL', 'http://localhost:11434')
    EMBEDDING_API_KEY = os.environ.get('EMBEDDING_API_KEY') or LLM_API_KEY

    # File upload configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    # Normalize the path once. Keeping ``app/../uploads`` in runtime paths
    # made storage diagnostics misleading and interacted badly with bind
    # mounts that were recreated by the deploy workspace.
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../uploads'))
    ALLOWED_EXTENSIONS = {'pdf', 'pptx', 'md', 'txt', 'markdown'}

    # Text processing configuration
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default overlap size

    # OASIS simulation configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(UPLOAD_FOLDER, 'simulations')

    # OASIS platform available actions configuration
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]

    # Report Agent configuration
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    # External RAG Service configuration
    MAIN_SERVER_RAG_URL = os.environ.get('MAIN_SERVER_RAG_URL', '')
    RAG_API_KEY = os.environ.get('RAG_API_KEY', '')

    # «Сигналы»: pain-mining реальных болей. Провайдер подключаемый.
    # SIGNAL_PROVIDER: ddg (бесплатно, без ключей) | searxng | exa | google_cse | brave
    SIGNAL_PROVIDER = os.environ.get('SIGNAL_PROVIDER', 'ddg').lower()
    SIGNAL_DOMAINS = [d.strip() for d in os.environ.get(
        'SIGNAL_DOMAINS', 'habr.com,vc.ru,pikabu.ru'
    ).split(',') if d.strip()]
    # Reddit как опережающий (западный) сигнал — бесплатный публичный поиск.
    ENABLE_REDDIT_SIGNALS = os.environ.get('ENABLE_REDDIT_SIGNALS', '1') not in ('0', 'false', 'False', '')
    REDDIT_USER_AGENT = os.environ.get('REDDIT_USER_AGENT', 'pitchy-custdev-signals/1.0')
    # Reddit OAuth (бесплатный script-app) — публичный .json блокирует серверные IP.
    REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID', '')
    REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET', '')
    # Ключи провайдеров (нужны только если выбран соответствующий SIGNAL_PROVIDER).
    EXA_API_KEY = os.environ.get('EXA_API_KEY', '')
    GOOGLE_CSE_KEY = os.environ.get('GOOGLE_CSE_KEY', '')
    GOOGLE_CSE_CX = os.environ.get('GOOGLE_CSE_CX', '')
    BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY', '')
    # SearXNG: self-hosted метапоиск (free, OSS). URL своего инстанса, напр. http://localhost:8080
    SEARXNG_URL = os.environ.get('SEARXNG_URL', '')

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not configured (set to any non-empty value, e.g. 'ollama')")
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            errors.append("APP_SECRET_KEY/SECRET_KEY must be configured with at least 32 characters")
        if not cls.NEO4J_URI:
            errors.append("NEO4J_URI not configured")
        if not cls.NEO4J_PASSWORD:
            errors.append("NEO4J_PASSWORD not configured")
        if cls.CUSTDEV_SSO_MODE not in ('legacy', 'dual', 'code_exchange'):
            errors.append("CUSTDEV_SSO_MODE must be legacy, dual, or code_exchange")
        if cls.CUSTDEV_SSO_MODE in ('dual', 'code_exchange') and os.environ.get('APP_ENV', 'dev').lower() == 'prod':
            if len(cls.CUSTDEV_SSO_SERVICE_SECRET) < 32:
                errors.append("CUSTDEV_SSO_SERVICE_SECRET must be at least 32 characters in production")
            if len(cls.CUSTDEV_SESSION_SECRET) < 32:
                errors.append("CUSTDEV_SESSION_SECRET must be at least 32 characters in production")
            for name, value in (
                ('CUSTDEV_SSO_AUTHORIZE_URL', cls.CUSTDEV_SSO_AUTHORIZE_URL),
                ('CUSTDEV_SSO_EXCHANGE_URL', cls.CUSTDEV_SSO_EXCHANGE_URL),
                ('CUSTDEV_SSO_INTROSPECT_URL', cls.CUSTDEV_SSO_INTROSPECT_URL),
                ('CUSTDEV_SSO_REVOKE_URL', cls.CUSTDEV_SSO_REVOKE_URL),
                ('CUSTDEV_SSO_REDIRECT_URI', cls.CUSTDEV_SSO_REDIRECT_URI),
            ):
                if not value.startswith('https://'):
                    errors.append(f"{name} must use HTTPS in production")
        return errors
# Synchronize with standard OpenAI environment variables for 3rd party tool compatibility
if Config.LLM_API_KEY and not os.environ.get('OPENAI_API_KEY'):
    os.environ['OPENAI_API_KEY'] = Config.LLM_API_KEY
if Config.LLM_BASE_URL and not os.environ.get('OPENAI_API_BASE_URL'):
    os.environ['OPENAI_API_BASE_URL'] = Config.LLM_BASE_URL
