"""Interview readiness is independent from simulation execution health."""

from types import SimpleNamespace

from flask import Flask
import pytest

from app.api import simulation as api
from app.services import pitchy_billing


@pytest.mark.parametrize('runner,alive,expected', [
    ('starting', False, 'preparing'), ('running', False, 'preparing'),
    ('completed', True, 'ready'), ('failed', False, 'closed'),
])
def test_env_status_does_not_call_a_running_simulation_closed(monkeypatch, runner, alive, expected):
    monkeypatch.setattr(api.SimulationRunner, 'check_env_alive', lambda sid: alive)
    monkeypatch.setattr(api.SimulationRunner, 'get_run_state', lambda sid: SimpleNamespace(runner_status=SimpleNamespace(value=runner)))
    monkeypatch.setattr(api.SimulationRunner, 'get_env_status_detail', lambda sid: {'status': 'alive' if alive else 'stopped', 'reddit_available': alive})
    with Flask(__name__).test_request_context(json={'simulation_id': 'sim_test'}):
        data = api.get_env_status.__wrapped__().get_json()['data']
    assert data['interview_state'] == expected
    assert data['runner_status'] == runner
    assert data['env_alive'] is alive


@pytest.mark.parametrize('storage_available', [True, False])
def test_graph_memory_storage_is_checked_before_billing_and_passed_to_runner(monkeypatch, storage_available):
    state = SimpleNamespace(status=api.SimulationStatus.READY, graph_id='graph', project_id='project')
    manager = SimpleNamespace(get_simulation=lambda sid: state, _save_simulation_state=lambda state: None)
    monkeypatch.setattr(api, 'SimulationManager', lambda: manager)
    calls = []
    monkeypatch.setattr(pitchy_billing, 'consume_custdev_run', lambda *a: calls.append('billed'))
    def start(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(to_dict=lambda: {'runner_status': 'running'})
    monkeypatch.setattr(api.SimulationRunner, 'start_simulation', start)
    app = Flask(__name__)
    storage = object()
    if storage_available:
        app.extensions['neo4j_storage'] = storage
    with app.test_request_context(json={'simulation_id': 'sim_test', 'request_id': 'test', 'enable_graph_memory_update': True}):
        response = api.start_simulation.__wrapped__()
    if storage_available:
        assert response.get_json()['success'] is True
        assert calls[0] == 'billed'
        assert calls[1]['storage'] is storage
    else:
        assert response[1] == 503
        assert calls == []
