"""Quota bridge to the main Pitchy API."""
import os
import requests
from flask import request


class BillingError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def consume_custdev_run(simulation_id: str, request_id: str) -> dict:
    base_url = os.getenv("PITCHY_MAIN_API_URL", "https://pitchy.pro").rstrip("/")
    headers = {"Content-Type": "application/json"}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    cookie_token = request.cookies.get("access_token")
    cookies = {"access_token": cookie_token} if cookie_token else None
    try:
        response = requests.post(
            f"{base_url}/billing/usage/consume",
            json={
                "resource": "custdev",
                "idempotency_key": f"custdev:{request_id}",
                "reference_id": simulation_id,
            },
            headers=headers,
            cookies=cookies,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise BillingError("Сервис лимитов временно недоступен") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail") or response.json().get("error")
        except Exception:
            detail = None
        raise BillingError(detail or "Не удалось проверить лимит CustDev", response.status_code)
    return response.json()
