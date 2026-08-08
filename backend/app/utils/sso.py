"""CustDev-side server-to-server SSO bridge.

The bridge stores only a CustDev-scoped opaque grant in Flask's own
host-only session cookie.  The main Pitchy JWT is never decoded or persisted
by this service.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import requests
from flask import current_app, session


def _safe_next(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith(("//", "/\\")):
        return "/"
    return value


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def start_url(next_path: str | None = None) -> str:
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    session.clear()
    session["sso_state"] = state
    session["sso_verifier"] = verifier
    session["sso_next"] = _safe_next(next_path)
    query = urlencode(
        {
            "client_id": current_app.config["CUSTDEV_SSO_CLIENT_ID"],
            "redirect_uri": current_app.config["CUSTDEV_SSO_REDIRECT_URI"],
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{current_app.config['CUSTDEV_SSO_AUTHORIZE_URL']}?{query}"


def _signed_headers(url: str, method: str, body: bytes) -> dict[str, str]:
    secret = current_app.config["CUSTDEV_SSO_SERVICE_SECRET"]
    if len(secret) < 32:
        raise RuntimeError("CUSTDEV_SSO_SERVICE_SECRET is not configured")
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(24)
    path = "/" + url.split("/", 3)[-1].split("?", 1)[0]
    canonical = "\n".join(
        (
            current_app.config["CUSTDEV_SSO_CLIENT_ID"],
            timestamp,
            nonce,
            method.upper(),
            path,
            hashlib.sha256(body).hexdigest(),
        )
    )
    signature = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Custdev-Client": current_app.config["CUSTDEV_SSO_CLIENT_ID"],
        "X-Custdev-Timestamp": timestamp,
        "X-Custdev-Nonce": nonce,
        "X-Custdev-Signature": signature,
    }


def exchange_code(code: str, verifier: str) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "client_id": current_app.config["CUSTDEV_SSO_CLIENT_ID"],
        "code": code,
        "redirect_uri": current_app.config["CUSTDEV_SSO_REDIRECT_URI"],
        "code_verifier": verifier,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    url = current_app.config["CUSTDEV_SSO_EXCHANGE_URL"]
    response = requests.post(
        url,
        data=body,
        headers=_signed_headers(url, "POST", body),
        timeout=current_app.config["CUSTDEV_SSO_TIMEOUT"],
        allow_redirects=False,
    )
    if response.status_code != 200:
        raise RuntimeError("SSO exchange rejected")
    data = response.json()
    if not data.get("active") or not data.get("grant_id") or not data.get("sub"):
        raise RuntimeError("SSO exchange returned an invalid grant")
    return data


def establish_session(grant: dict) -> None:
    session.clear()
    session["sso_grant_id"] = str(grant["grant_id"])
    session["sso_user_id"] = str(grant["sub"])
    session["sso_scope"] = list(grant.get("scope", []))
    session["sso_expires_at"] = int(grant["expires_at"])
    session["sso_checked_at"] = int(time.time())


def _introspect(grant_id: str) -> dict | None:
    payload = {"grant_id": grant_id}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    url = current_app.config["CUSTDEV_SSO_INTROSPECT_URL"]
    response = requests.post(
        url,
        data=body,
        headers=_signed_headers(url, "POST", body),
        timeout=current_app.config["CUSTDEV_SSO_TIMEOUT"],
        allow_redirects=False,
    )
    if response.status_code != 200:
        raise RuntimeError("SSO introspection unavailable")
    data = response.json()
    return data if data.get("active") else {}


def bridge_user() -> dict | None:
    grant_id = session.get("sso_grant_id")
    user_id = session.get("sso_user_id")
    expires_at = int(session.get("sso_expires_at", 0) or 0)
    if not grant_id or not user_id or expires_at <= int(time.time()):
        return None
    checked_at = int(session.get("sso_checked_at", 0) or 0)
    data = None
    if int(time.time()) - checked_at >= current_app.config["CUSTDEV_SSO_RECHECK_SECONDS"]:
        try:
            data = _introspect(str(grant_id))
        except (requests.RequestException, ValueError, RuntimeError, TypeError):
            # Keep a short availability grace period; after that fail closed.
            if int(time.time()) - checked_at > max(300, current_app.config["CUSTDEV_SSO_RECHECK_SECONDS"] * 5):
                session.clear()
                return None
        if data == {}:
            session.clear()
            return None
        if data is None and checked_at and int(time.time()) - checked_at > max(300, current_app.config["CUSTDEV_SSO_RECHECK_SECONDS"] * 5):
            session.clear()
            return None
        if data:
            if str(data.get("sub")) != str(user_id):
                session.clear()
                return None
            session["sso_checked_at"] = int(time.time())
            session["sso_expires_at"] = int(data.get("expires_at", expires_at))
    return {
        "sub": str(user_id),
        "userId": str(user_id),
        "main_auth": True,
        "sso_grant": True,
        "scope": session.get("sso_scope", []),
    }


def revoke_session() -> None:
    grant_id = session.get("sso_grant_id")
    if grant_id:
        try:
            payload = {"grant_id": str(grant_id)}
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            url = current_app.config["CUSTDEV_SSO_REVOKE_URL"]
            requests.post(
                url,
                data=body,
                headers=_signed_headers(url, "POST", body),
                timeout=current_app.config["CUSTDEV_SSO_TIMEOUT"],
                allow_redirects=False,
            )
        except (requests.RequestException, RuntimeError):
            pass
    session.clear()
