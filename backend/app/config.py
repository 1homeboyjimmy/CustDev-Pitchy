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


class Config:
    """Flask configuration class"""

    # Flask configuration
    SECRET_KEY = os.environ.get('APP_SECRET_KEY', os.environ.get('SECRET_KEY', 'pitchy-secret-key')).strip()
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # JSON configuration - disable ASCII escaping to display Chinese directly (not as \uXXXX)
    JSON_AS_ASCII = False

    # LLM configuration (unified OpenAI format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'http://localhost:11434/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'qwen/qwen2.5-vl-32b-instruct')

    # Neo4j configuration
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'pitchy')

    # Embedding configuration
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'nomic-embed-text')
    EMBEDDING_BASE_URL = os.environ.get('EMBEDDING_BASE_URL', 'http://localhost:11434')

    # File upload configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # Text processing configuration
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default overlap size

    # OASIS simulation configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

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

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not configured (set to any non-empty value, e.g. 'ollama')")
        if not cls.NEO4J_URI:
            errors.append("NEO4J_URI not configured")
        if not cls.NEO4J_PASSWORD:
            errors.append("NEO4J_PASSWORD not configured")
# Synchronize with standard OpenAI environment variables for 3rd party tool compatibility
if Config.LLM_API_KEY and not os.environ.get('OPENAI_API_KEY'):
    os.environ['OPENAI_API_KEY'] = Config.LLM_API_KEY
if Config.LLM_BASE_URL and not os.environ.get('OPENAI_API_BASE_URL'):
    os.environ['OPENAI_API_BASE_URL'] = Config.LLM_BASE_URL
