"""Импорт паспорта проекта с главного сервера Pitchy.

CustDev знает user_id из общего JWT (sub). Ходит на главный сервер
(cross-service, Bearer RAG_API_KEY) за списком проектов пользователя и
паспортом конкретного проекта. База берётся из MAIN_SERVER_RAG_URL.
"""

import requests
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('pitchy.passport_service')


def _base() -> str:
    # MAIN_SERVER_RAG_URL = https://pitchy.pro/api/rag/search → база https://pitchy.pro/api/rag
    url = (Config.MAIN_SERVER_RAG_URL or '').rstrip('/')
    return url.rsplit('/', 1)[0] if url else ''


def _headers() -> dict:
    h = {'Accept': 'application/json'}
    if Config.RAG_API_KEY:
        h['Authorization'] = f'Bearer {Config.RAG_API_KEY}'
    return h


def list_projects(user_id) -> list[dict]:
    base = _base()
    if not base or not Config.RAG_API_KEY:
        raise RuntimeError('MAIN_SERVER не настроен')
    r = requests.get(f'{base}/projects', params={'user_id': user_id}, headers=_headers(), timeout=20)
    r.raise_for_status()
    return r.json().get('projects', [])


def get_passport(user_id, project_id) -> dict:
    base = _base()
    if not base or not Config.RAG_API_KEY:
        raise RuntimeError('MAIN_SERVER не настроен')
    r = requests.get(f'{base}/projects/{project_id}/passport',
                     params={'user_id': user_id}, headers=_headers(), timeout=20)
    r.raise_for_status()
    return r.json()
