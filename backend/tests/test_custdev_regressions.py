"""Focused regressions for the CustDev evidence pipeline."""

import json

from app.config import Config
from app.utils import auth
from app.services.signals_service import _normalise_sources
from app.services.signals_research import _normalise_analysis
from app.services.ontology_generator import OntologyGenerator
from app.services import verdict_service


def test_search_hits_are_deduplicated_and_attributed():
    result = _normalise_sources([
        {"url": "https://example.test/post/#comments", "title": "Pain", "highlights": ["A"]},
        {"url": "https://example.test/post/", "title": "Same post", "highlights": ["A"]},
    ])
    assert len(result) == 1
    assert result[0]["retrieved_at"]


def test_llm_dashboard_counts_are_bounded_by_observed_sources():
    result = _normalise_analysis(
        {
            "willingness": {"complaining": 100, "seeking": -2, "paying": "9"},
            "segments": [{"pain_count": 100}],
            "top_pains": [{"count": 100}],
        },
        [{"url": "https://example.test/1"}, {"url": "https://example.test/2"}],
    )
    assert result["willingness"] == {"complaining": 2, "seeking": 0, "paying": 2}
    assert result["segments"][0]["pain_count"] == 2
    assert result["top_pains"][0]["count"] == 2


def test_verdict_uses_attached_evidence(tmp_path, monkeypatch):
    simulation_id = "sim_regression"
    simulation_dir = tmp_path / simulation_id
    simulation_dir.mkdir()
    attached = {"available": True, "sources": [{"title": "Attached"}], "context": "attached"}
    (simulation_dir / "signals.json").write_text(json.dumps(attached), encoding="utf-8")
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "LLM_API_KEY", "")
    monkeypatch.setattr(Config, "LLM_BASE_URL", "")
    monkeypatch.setattr(verdict_service.SignalsService, "scan", lambda *a, **k: (_ for _ in ()).throw(AssertionError("live scan must not run")))

    result = verdict_service.generate_full_report(simulation_id, "ignored")
    assert result["signals"]["evidence_source"] == "attached_research"
    assert result["signals"]["sources"][0]["title"] == "Attached"


def test_ontology_empty_llm_response_uses_safe_fallback():
    class EmptyResponseClient:
        def chat_json(self, **kwargs):
            raise ValueError("Invalid JSON format from LLM: ")

    result = OntologyGenerator(EmptyResponseClient()).generate(["A product pain"], "Validate demand")

    assert len(result["entity_types"]) == 10
    assert [item["name"] for item in result["entity_types"][-2:]] == ["Person", "Organization"]
    assert len(result["edge_types"]) == 9
    assert "базовая онтология" in result["analysis_summary"]


def test_remote_main_auth_fallback_maps_user(monkeypatch):
    class Response:
        status_code = 200
        content = b'{"id": 42, "email": "user@example.test"}'

        @staticmethod
        def json():
            return {"id": 42, "email": "user@example.test"}

    captured = {}

    def fake_get(url, **kwargs):
        captured.update(url=url, kwargs=kwargs)
        return Response()

    monkeypatch.setattr(auth.requests, "get", fake_get)
    result = auth.verify_remote_session("jwt-from-shared-cookie")

    assert result["sub"] == "42"
    assert result["main_auth"] is True
    assert captured["kwargs"]["headers"]["Cookie"] == "access_token=jwt-from-shared-cookie"
    assert captured["kwargs"]["allow_redirects"] is False
