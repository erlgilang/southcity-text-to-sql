"""The user endpoints against the real database, with a graph that is never called."""

import pytest
from fastapi.testclient import TestClient

from app.api.app import build_app
from app.sessions import SessionStore
from app.sql import users

pytestmark = pytest.mark.db


@pytest.fixture
def client():
    return TestClient(
        build_app(graph=None, store=SessionStore(), users=users, app_env="production")
    )


def test_users_come_from_system_users(client):
    body = client.get("/users").json()
    assert [u["username"] for u in body] == [
        "sales_bambang",
        "sales_dewi",
        "sales_reza",
        "finance_hendra",
        "auditor_maya",
    ]
    assert {u["role"] for u in body} == {"Sales", "Finance", "Auditor"}
    assert all(set(u) == {"username", "full_name", "role"} for u in body)


def test_session_for_a_real_user_and_a_missing_one(client):
    ok = client.post("/sessions", json={"username": "sales_dewi"})
    assert ok.status_code == 200
    assert ok.json()["user"]["full_name"] == "Dewi Lestari"
    assert client.post("/sessions", json={"username": "root"}).status_code == 404
