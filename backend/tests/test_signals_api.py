"""Request validation and safe persistence without any remote service."""
import json
from flask import Flask
import pytest

from app.api import signals


@pytest.mark.parametrize('payload', [[], {'query': []}, {'query': 'q', 'segments': [None]},
    {'query': 'q', 'segments': {}}, {'query': 'q', 'request_id': '../invalid'}, {'query': 'q' * 16001}])
def test_invalid_research_requests_return_400(payload):
    with Flask(__name__).test_request_context(json=payload):
        _, status = signals.start_signals_research.__wrapped__()
    assert status == 400


def test_research_request_passes_idempotency_key_and_owner(monkeypatch):
    captured = {}
    monkeypatch.setattr(signals, 'current_user_id', lambda: '42')
    def start(query, segments, **kwargs):
        captured.update(query=query, segments=segments, **kwargs)
        return 'task-1'
    monkeypatch.setattr(signals, 'start_research', start)
    with Flask(__name__).test_request_context(json={'query': ' Pain ', 'segments': ['Founders'], 'request_id': 'test-request-1'}):
        result = signals.start_signals_research.__wrapped__()
        assert result.get_json()['data']['task_id'] == 'task-1'
    assert captured == {'query': 'Pain', 'segments': ['Founders'], 'owner_id': '42', 'request_id': 'test-request-1'}


def test_failed_attachment_write_keeps_previous_history_and_cleans_temp_file(tmp_path, monkeypatch):
    path = tmp_path / 'signals.json'
    original = {'sources': [{'title': 'Previous evidence'}]}
    path.write_text(json.dumps(original))
    monkeypatch.setattr(signals, '_signals_path', lambda *args: str(path))
    monkeypatch.setattr(signals, '_check_simulation_access', lambda *args: None)
    def interrupted(*args, **kwargs):
        raise OSError('simulated interrupted write')
    monkeypatch.setattr(signals.json, 'dump', interrupted)
    with Flask(__name__).test_request_context(json={'simulation_id': 'sim_test', 'result': {'sources': []}}):
        _, status = signals.attach_signals.__wrapped__()
    assert status == 500
    assert json.loads(path.read_text()) == original
    assert list(tmp_path.iterdir()) == [path]
