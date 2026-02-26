from __future__ import annotations

import os
import json
import uuid
import time
from typing import Optional, Generator

import pytest
from fastapi.testclient import TestClient

from main import app


def _env(key: str) -> Optional[str]:
    value = os.getenv(key)
    return value.strip() if value else None


def _required_env_ready() -> tuple[bool, str]:
    missing = []
    for key in [
        "BLSC_API_KEY",
        "BLSC_BASE_URL",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "REDIS_URL",
    ]:
        if not _env(key):
            missing.append(key)
    if missing:
        return False, f"Missing env: {', '.join(missing)}"
    return True, ""


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def _register_or_login(client: TestClient) -> dict:
    username = f"itest_{uuid.uuid4().hex[:8]}"
    password = "test1234"

    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "name": "ITest",
            "email": f"{username}@example.com",
        },
    )
    if register_resp.status_code not in (200, 400):
        raise AssertionError(register_resp.text)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert login_resp.status_code == 200
    payload = login_resp.json()
    assert payload.get("code") == 0
    return payload["data"]


def _create_session(client: TestClient) -> int:
    resp = client.post(
        "/api/v1/sessions",
        json={"title": "itest", "biz_type": "ai_chat"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("code") == 0
    return payload["data"]["id"]


def _wait_stream_done(resp, timeout_s: float = 60.0) -> list[dict]:
    start = time.time()
    events = []
    for line in resp.iter_lines():
        if time.time() - start > timeout_s:
            break
        if not line or not line.startswith("data: "):
            continue
        events.append(json.loads(line.replace("data: ", "", 1)))
        if events[-1].get("done") is True:
            break
    return events


@pytest.mark.integration
def test_chat_messages_stream_and_history(client: TestClient):
    ready, reason = _required_env_ready()
    if not ready:
        pytest.skip(reason)

    _register_or_login(client)
    session_id = _create_session(client)

    with client.stream(
        "POST",
        f"/api/v1/sessions/{session_id}/messages/stream",
        json={"content": "你好，简单自我介绍", "role": "user"},
    ) as resp:
        assert resp.status_code == 200
        events = _wait_stream_done(resp)

    contents = [event.get("content") for event in events if "content" in event]
    assert any(contents), "Stream returned no content chunks"
    assert any(event.get("done") is True for event in events)

    history_resp = client.get(f"/api/v1/sessions/{session_id}/messages?page=1&size=20")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history.get("code") == 0
    assert history["data"]["total"] >= 2
