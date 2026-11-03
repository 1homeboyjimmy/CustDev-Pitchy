"""Small live checks of the approved Polza models, without starting a study.

Run from backend: python scripts/check_polza.py
--key-stdin accepts {"POLZA_API_KEY": "..."} over a private pipe for rollout.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from llm_settings import polza_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key-stdin', action='store_true')
    args = parser.parse_args()
    if args.key_stdin:
        os.environ['POLZA_API_KEY'] = json.load(sys.stdin)['POLZA_API_KEY']
    settings = polza_settings()
    if not settings['api_key']:
        raise SystemExit('POLZA_API_KEY not configured')
    headers = {'Authorization': f"Bearer {settings['api_key']}"}

    def check_chat(model):
        response = requests.post(settings['base_url'] + '/chat/completions', headers=headers, timeout=90,
            json={'model': model, 'messages': [{'role': 'user', 'content': 'Return only this JSON: {"ok": true}'}],
                  'temperature': 0.2, 'max_tokens': 1024, 'response_format': {'type': 'json_object'}})
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        if json.loads(content).get('ok') is not True:
            raise ValueError(f'{model}: incorrect structured response')
        print(json.dumps({'model': model, 'json': True}), flush=True)

    def check_embeddings():
        response = requests.post(settings['base_url'] + '/embeddings', headers=headers, timeout=90,
            json={'model': settings['embedding_model'], 'input': ['Проверка рынка', 'Ресторанные заказы'],
                  'dimensions': 768, 'encoding_format': 'float'})
        response.raise_for_status()
        data = response.json()['data']
        if len(data) != 2 or any(len(item['embedding']) != 768 for item in data):
            raise ValueError('Polza embedding dimensions differ from the Neo4j schema')
        print(json.dumps({'model': settings['embedding_model'], 'dimensions': 768, 'batch': True}), flush=True)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(check_chat, model) for model in sorted(set(settings['models'].values()))]
        futures.append(pool.submit(check_embeddings))
        failed = False
        for future in futures:
            try:
                future.result()
            except Exception as exc:
                failed = True
                print(f'FAILED: {type(exc).__name__}: {exc}', flush=True)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
