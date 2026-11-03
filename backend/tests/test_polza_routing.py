"""Provider isolation and approved model routing across the CustDev pipeline."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from llm_settings import DEFAULT_MODELS, polza_settings, sync_polza_environment
from app.config import Config
from app.storage.embedding_service import EmbeddingService, EmbeddingError


def test_flash_json_requests_disable_reasoning_without_changing_analysis_models(monkeypatch):
    from app.utils import llm_client
    monkeypatch.setattr(Config, 'LLM_API_KEY', 'polza-test')
    captured = []
    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))])
    monkeypatch.setattr(llm_client, 'OpenAI', lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    llm_client.LLMClient(task='extraction').chat_json(messages=[])
    llm_client.LLMClient(task='ontology').chat_json(messages=[])
    assert captured[0]['extra_body'] == {'reasoning': {'enabled': False}}
    assert 'extra_body' not in captured[1]


def test_old_provider_settings_cannot_escape_to_workers():
    env = {'POLZA_API_KEY': 'polza-test'}
    for prefix in ('LLM', 'LLM_BOOST', 'OPENAI', 'EMBEDDING'):
        env[f'{prefix}_API_KEY'] = 'old-key'
        env[f'{prefix}_BASE_URL'] = 'https://routerai.ru/api/v1'
        env[f'{prefix}_MODEL_NAME'] = 'old-model'
    settings = sync_polza_environment(env)
    assert settings['models'] == DEFAULT_MODELS
    assert settings['embedding_model'] == 'qwen/qwen3-embedding-8b'
    for prefix in ('LLM', 'LLM_BOOST'):
        assert env[f'{prefix}_API_KEY'] == 'polza-test'
        assert env[f'{prefix}_BASE_URL'] == 'https://polza.ai/api/v1'
        assert env[f'{prefix}_MODEL_NAME'] == 'openai/gpt-6-luna'
    assert env['OPENAI_API_KEY'] == 'polza-test'
    assert env['OPENAI_API_BASE_URL'] == env['OPENAI_BASE_URL'] == settings['base_url']


def test_missing_polza_key_does_not_reuse_router_key():
    assert not polza_settings({'LLM_API_KEY': 'old-key'})['api_key']


def test_other_provider_base_is_rejected():
    with pytest.raises(ValueError, match='POLZA_API_BASE'):
        polza_settings({'POLZA_API_BASE': 'https://routerai.ru/api/v1'})


def test_service_constructors_use_approved_task_models(monkeypatch):
    from app.services.graph_tools import GraphToolsService
    from app.services.oasis_profile_generator import OasisProfileGenerator
    from app.services.ontology_generator import OntologyGenerator
    from app.services.report_agent import ReportAgent
    from app.services.simulation_config_generator import SimulationConfigGenerator
    from app.storage.ner_extractor import NERExtractor

    monkeypatch.setattr(Config, 'LLM_API_KEY', 'polza-test')
    monkeypatch.setattr('app.utils.llm_client.OpenAI', lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr('app.services.oasis_profile_generator.OpenAI', lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr('app.services.simulation_config_generator.OpenAI', lambda **kwargs: SimpleNamespace(**kwargs))
    tools = GraphToolsService(storage=object())
    report = ReportAgent('graph', 'sim', 'hypothesis', graph_tools=tools)
    assert OntologyGenerator().llm_client.model == 'openai/gpt-6-luna-pro'
    assert NERExtractor().llm.model == 'deepseek/deepseek-v4-flash'
    assert OasisProfileGenerator().model_name == 'openai/gpt-6-luna'
    assert SimulationConfigGenerator().model_name == 'deepseek/deepseek-v4-flash'
    assert tools.llm.model == report.llm.model == 'openai/gpt-6-luna-pro'
    assert report.chat_llm.model == 'openai/gpt-6-luna'


@pytest.mark.parametrize('script', ['run_reddit_simulation.py', 'run_twitter_simulation.py', 'run_parallel_simulation.py'])
def test_workers_pass_polza_credentials_explicitly(monkeypatch, script):
    """Execute real worker factory bodies without starting OASIS or a paid run."""
    monkeypatch.setenv('POLZA_API_KEY', 'polza-test')
    monkeypatch.setenv('LLM_BOOST_API_KEY', 'old-key')
    monkeypatch.setenv('LLM_BOOST_BASE_URL', 'https://routerai.ru/api/v1')
    tree = ast.parse((Path(__file__).parents[1] / 'scripts' / script).read_text(encoding='utf-8'))
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in ('create_model', '_create_model'))
    captured = {}
    def create(**kwargs):
        captured.update(kwargs)
        return kwargs
    namespace = {'ModelFactory': SimpleNamespace(create=create), 'ModelPlatformType': SimpleNamespace(OPENAI='openai'), 'Dict': dict, 'Any': object}
    exec(compile(ast.Module(body=[function], type_ignores=[]), script, 'exec'), namespace)
    if function.name == 'create_model':
        namespace[function.name]({'llm_model': 'old-model'}, use_boost=True)
    else:
        namespace[function.name](SimpleNamespace(config={'llm_model': 'old-model'}))
    assert captured == {'model_platform': 'openai', 'model_type': 'openai/gpt-6-luna', 'api_key': 'polza-test', 'url': 'https://polza.ai/api/v1'}


def test_embeddings_auth_dimensions_and_response_order(monkeypatch):
    monkeypatch.setattr(Config, 'EMBEDDING_API_KEY', 'polza-test')
    monkeypatch.setattr(Config, 'EMBEDDING_MODEL', 'qwen/qwen3-embedding-8b')
    monkeypatch.setattr(Config, 'EMBEDDING_BASE_URL', 'https://polza.ai/api/v1')
    captured = {}
    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'data': [
            {'index': 1, 'embedding': [2.0] * 768}, {'index': 0, 'embedding': [1.0] * 768}]})
    monkeypatch.setattr('app.storage.embedding_service.requests.post', post)
    assert EmbeddingService().embed_batch(['first', 'second']) == [[1.0] * 768, [2.0] * 768]
    assert captured['url'] == 'https://polza.ai/api/v1/embeddings'
    assert captured['headers']['Authorization'] == 'Bearer polza-test'
    assert captured['json']['dimensions'] == 768
    assert captured['json']['encoding_format'] == 'float'


def test_embedding_dimension_mismatch_is_not_stored(monkeypatch):
    monkeypatch.setattr('app.storage.embedding_service.requests.post', lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {'data': [{'index': 0, 'embedding': [1.0] * 4096}]}))
    with pytest.raises(EmbeddingError, match='768 dimensions'):
        EmbeddingService().embed('test')
