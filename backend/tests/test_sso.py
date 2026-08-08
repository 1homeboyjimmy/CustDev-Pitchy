import base64
import hashlib
import json

from flask import Flask

from app.utils import sso


def _app():
    app = Flask(__name__)
    app.secret_key = "custdev-test-session-secret-" + "x" * 32
    app.config.update(
        CUSTDEV_SSO_CLIENT_ID="custdev",
        CUSTDEV_SSO_REDIRECT_URI="https://custdev.pitchy.pro/api/auth/callback",
        CUSTDEV_SSO_AUTHORIZE_URL="https://pitchy.pro/auth/sso/custdev/authorize",
        CUSTDEV_SSO_EXCHANGE_URL="https://pitchy.pro/internal/auth/custdev/exchange",
        CUSTDEV_SSO_INTROSPECT_URL="https://pitchy.pro/internal/auth/custdev/introspect",
        CUSTDEV_SSO_REVOKE_URL="https://pitchy.pro/internal/auth/custdev/revoke",
        CUSTDEV_SSO_SERVICE_SECRET="service-secret-" + "x" * 32,
        CUSTDEV_SSO_TIMEOUT=1,
        CUSTDEV_SSO_RECHECK_SECONDS=60,
    )
    return app


def test_pkce_pair_has_s256_shape():
    with _app().app_context():
        verifier, challenge = sso._pkce_pair()
    assert 43 <= len(verifier) <= 128
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected


def test_exchange_request_is_signed_without_cookie_or_jwt(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"active": True, "sub": "42", "grant_id": "g" * 43, "expires_at": 9999999999}

    def fake_post(url, **kwargs):
        captured.update(url=url, kwargs=kwargs)
        return Response()

    monkeypatch.setattr(sso.requests, "post", fake_post)
    with _app().app_context():
        result = sso.exchange_code("c" * 32, "v" * 64)

    assert result["sub"] == "42"
    assert captured["kwargs"]["headers"]["X-Custdev-Client"] == "custdev"
    assert "Cookie" not in captured["kwargs"]["headers"]
    assert b"code_verifier" in captured["kwargs"]["data"]


def test_start_url_stores_state_and_pkce_verifier():
    with _app().test_request_context("/"):
        url = sso.start_url("/process/7")
        assert url.startswith("https://pitchy.pro/auth/sso/custdev/authorize?")
        assert sso.session.get("sso_state")
        assert sso.session.get("sso_verifier")
        assert sso.session.get("sso_next") == "/process/7"
