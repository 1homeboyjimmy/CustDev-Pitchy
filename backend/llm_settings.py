"""Shared Polza settings for Flask and standalone OASIS workers.

Use the same variable names and defaults as the main Pitchy repository.
Legacy LLM/OPENAI/BOOST settings must never select a different provider.
"""

import os
from urllib.parse import urlparse

DEFAULT_MODELS = {
    'search': 'deepseek/deepseek-v4-flash',
    'signals': 'openai/gpt-6-luna-pro',
    'ontology': 'openai/gpt-6-luna-pro',
    'extraction': 'deepseek/deepseek-v4-flash',
    'profiles': 'openai/gpt-6-luna',
    'simulation_config': 'deepseek/deepseek-v4-flash',
    'simulation': 'openai/gpt-6-luna',
    'graph_analysis': 'openai/gpt-6-luna-pro',
    'report': 'openai/gpt-6-luna-pro',
    'verdict': 'openai/gpt-6-luna-pro',
    'report_chat': 'openai/gpt-6-luna',
}


def polza_settings(environ=None):
    env = os.environ if environ is None else environ
    base = (env.get('POLZA_API_BASE') or 'https://polza.ai/api/v1').strip().rstrip('/')
    parsed = urlparse(base)
    if parsed.scheme != 'https' or parsed.hostname != 'polza.ai' or parsed.path != '/api/v1' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('POLZA_API_BASE must be https://polza.ai/api/v1')
    return {
        'api_key': (env.get('POLZA_API_KEY') or '').strip(),
        'base_url': base,
        'model': (env.get('POLZA_MODEL') or 'openai/gpt-6-luna-pro').strip(),
        'embedding_model': (env.get('POLZA_EMBEDDING_MODEL') or 'qwen/qwen3-embedding-8b').strip(),
        'models': {task: (env.get(f'CUSTDEV_MODEL_{task.upper()}') or model).strip()
                   for task, model in DEFAULT_MODELS.items()},
    }


def sync_polza_environment(environ=None):
    env = os.environ if environ is None else environ
    settings = polza_settings(env)
    for prefix in ('LLM', 'LLM_BOOST'):
        env[f'{prefix}_API_KEY'] = settings['api_key']
        env[f'{prefix}_BASE_URL'] = settings['base_url']
        env[f'{prefix}_MODEL_NAME'] = settings['models']['simulation']
    env['OPENAI_API_KEY'] = settings['api_key']
    env['OPENAI_API_BASE_URL'] = settings['base_url']
    env['OPENAI_BASE_URL'] = settings['base_url']
    env['EMBEDDING_BASE_URL'] = settings['base_url']
    env['EMBEDDING_MODEL'] = settings['embedding_model']
    env['EMBEDDING_API_KEY'] = settings['api_key']
    return settings
