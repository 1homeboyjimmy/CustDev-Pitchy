"""Импорт паспорта проекта с главного сервера Pitchy.

CustDev знает user_id из общего JWT (sub). Ходит на главный сервер
(cross-service, Bearer RAG_API_KEY) за списком проектов пользователя и
паспортом конкретного проекта. База берётся из MAIN_SERVER_RAG_URL.
"""

import requests
from urllib.parse import quote, urlsplit, urlunsplit
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('pitchy.passport_service')


def _base() -> str:
    # Accept both the search endpoint and its /api/rag base. The production
    # env has used both forms over time.
    url = (Config.MAIN_SERVER_RAG_URL or '').rstrip('/')
    if not url:
        return ''

    parsed = urlsplit(url)
    path = parsed.path.rstrip('/')
    if path.endswith('/search'):
        path = path[:-len('/search')]
    return urlunsplit((parsed.scheme, parsed.netloc, path, '', '')).rstrip('/')


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
    payload = r.json()
    if isinstance(payload, dict):
        projects = payload.get('projects')
        if projects is None and isinstance(payload.get('data'), dict):
            projects = payload['data'].get('projects')
        return projects if isinstance(projects, list) else []
    return payload if isinstance(payload, list) else []


def get_passport(user_id, project_id) -> dict:
    base = _base()
    if not base or not Config.RAG_API_KEY:
        raise RuntimeError('MAIN_SERVER не настроен')
    encoded_project_id = quote(str(project_id), safe='')
    r = requests.get(f'{base}/projects/{encoded_project_id}/passport',
                     params={'user_id': user_id}, headers=_headers(), timeout=20)
    r.raise_for_status()
    payload = r.json()
    if isinstance(payload, dict) and isinstance(payload.get('data'), dict):
        nested = payload['data']
        if 'passport' in nested or 'name' in nested:
            return nested
    return payload if isinstance(payload, dict) else {}
