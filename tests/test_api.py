import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.api.app import build_app
from app.graph.builder import build_graph
from app.observability import LOGGER
from app.sessions import SessionStore
from app.sql.users import UnknownUserError
from tests.fakes import (
    BAMBANG,
    HENDRA,
    FakeDatabase,
    FakeLLM,
    classification,
    generated,
    rows_result,
)


class FakeUsers:
    def __init__(self, *users):
        self._users = {user.username: user for user in users}

    def list_users(self):
        return list(self._users.values())

    def get_user(self, username):
        try:
            return self._users[username]
        except KeyError:
            raise UnknownUserError(username) from None


def make_client(llm=None, db=None, max_messages=50, app_env="production"):
    store = SessionStore(max_messages=max_messages)
    graph = build_graph(llm or FakeLLM(), db or FakeDatabase())
    app = build_app(graph, store, FakeUsers(BAMBANG, HENDRA), app_env)
    return TestClient(app, raise_server_exceptions=False), store


def open_session(client, username="finance_hendra"):
    response = client.post("/sessions", json={"username": username})
    assert response.status_code == 200
    return response.json()["session_id"]


def chitchat_llm(times=1):
    return FakeLLM(
        classifications=[classification("chitchat")] * times, texts=["Sama-sama!"] * times
    )


def test_health_does_not_need_the_database_or_the_model():
    client, _ = make_client()
    assert client.get("/health").json() == {"status": "ok"}


def test_users_lists_name_and_role_only():
    client, _ = make_client()
    body = client.get("/users").json()
    assert [u["username"] for u in body] == ["sales_bambang", "finance_hendra"]
    assert body[0] == {
        "username": "sales_bambang",
        "full_name": "Bambang Pamungkas",
        "role": "Sales",
    }


def test_session_is_created_for_a_known_user():
    client, store = make_client()
    body = client.post("/sessions", json={"username": "sales_bambang"}).json()
    assert body["user"] == {
        "username": "sales_bambang",
        "full_name": "Bambang Pamungkas",
        "role": "Sales",
    }
    assert store.get(body["session_id"]).user == BAMBANG


def test_unknown_user_gets_404_and_no_session():
    client, store = make_client()
    response = client.post("/sessions", json={"username": "root"})
    assert response.status_code == 404
    assert store._sessions == {}


def test_each_session_request_gives_a_new_id():
    client, _ = make_client()
    assert open_session(client) != open_session(client)


def test_chat_returns_answer_steps_and_total_time():
    client, _ = make_client(llm=chitchat_llm())
    session_id = open_session(client)
    response = client.post("/chat", json={"session_id": session_id, "question": "Makasih"})
    body = response.json()
    assert response.status_code == 200
    assert (body["answer"], body["outcome"], body["intent"]) == ("Sama-sama!", "answer", "chitchat")
    assert body["table"] is None
    assert [step["node"] for step in body["steps"]] == ["load_context", "classify", "write_answer"]
    assert isinstance(body["total_ms"], int)
    assert body["request_id"]


def test_chat_returns_table_and_the_models_sql():
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["sales_contracts"])],
        sqls=[generated("SELECT customername FROM sales_contracts")],
        texts=["Ada satu."],
    )
    client, _ = make_client(llm, FakeDatabase(rows_result(["customername"], [("Budi",)])))
    body = client.post("/chat", json={"session_id": open_session(client), "question": "Q"}).json()
    assert body["table"]["columns"] == ["customername"]
    assert body["table"]["rows"] == [["Budi"]]
    assert body["sql"] == "SELECT customername FROM sales_contracts"


def test_response_never_contains_the_rewritten_sql():
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["sales_contracts"])],
        sqls=[generated("SELECT customername FROM sales_contracts")],
        texts=["ok"],
    )
    client, _ = make_client(llm, FakeDatabase(rows_result(["customername"], [("Budi",)])))
    session_id = open_session(client, "sales_bambang")
    response = client.post("/chat", json={"session_id": session_id, "question": "Q"})
    assert "salesagentid" not in response.text.lower()
    assert "101" not in json.dumps(response.json()["steps"])


def test_steps_do_not_carry_sql_text():
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT unitnumber FROM units")],
        texts=["ok"],
    )
    client, _ = make_client(llm, FakeDatabase(rows_result(["unitnumber"], [("A-0101",)])))
    body = client.post("/chat", json={"session_id": open_session(client), "question": "Q"}).json()
    assert "SELECT" not in json.dumps(body["steps"])


def test_security_refusal_returns_neither_sql_nor_the_reason():
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT * FROM system_users")],
    )
    client, _ = make_client(llm)
    response = client.post(
        "/chat", json={"session_id": open_session(client, "sales_bambang"), "question": "Q"}
    )
    body = response.json()
    assert body["outcome"] == "refuse"
    assert body["sql"] is None
    assert "system_users" not in response.text


def test_unknown_session_gets_404():
    client, _ = make_client()
    response = client.post("/chat", json={"session_id": "missing", "question": "Halo"})
    assert response.status_code == 404


def test_session_is_lost_when_the_store_is_empty_again():
    client, store = make_client(llm=chitchat_llm())
    session_id = open_session(client)
    store._sessions.clear()
    assert client.post("/chat", json={"session_id": session_id, "question": "x"}).status_code == 404


@pytest.mark.parametrize("question", ["", "   ", "x" * 501])
def test_bad_question_length_gets_422(question):
    client, _ = make_client()
    response = client.post("/chat", json={"session_id": open_session(client), "question": question})
    assert response.status_code == 422


def test_question_of_exactly_500_characters_is_accepted():
    client, _ = make_client(llm=chitchat_llm())
    response = client.post(
        "/chat", json={"session_id": open_session(client), "question": "x" * 500}
    )
    assert response.status_code == 200


def test_message_limit_gets_429():
    client, _ = make_client(llm=chitchat_llm(2), max_messages=2)
    session_id = open_session(client)
    for _ in range(2):
        assert (
            client.post("/chat", json={"session_id": session_id, "question": "x"}).status_code
            == 200
        )
    assert client.post("/chat", json={"session_id": session_id, "question": "x"}).status_code == 429


def test_role_in_the_request_body_is_rejected_not_trusted():
    client, _ = make_client()
    response = client.post(
        "/chat",
        json={
            "session_id": open_session(client, "sales_bambang"),
            "question": "x",
            "role": "Finance",
        },
    )
    assert response.status_code == 422


def test_unexpected_failure_returns_a_generic_500_without_details():
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT unitnumber FROM units")],
    )
    db = FakeDatabase(RuntimeError("could not connect: postgresql://app_readonly:s3cret@db/x"))
    client, _ = make_client(llm, db)
    response = client.post("/chat", json={"session_id": open_session(client), "question": "Q"})
    assert response.status_code == 500
    assert "s3cret" not in response.text
    assert "postgresql" not in response.text
    assert response.json()["detail"]


def failed_chat_log(app_env):
    """Run a /chat that fails and return the chat_error log fields."""
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT unitnumber FROM units")],
    )
    db = FakeDatabase(RuntimeError("could not connect: postgresql://app_readonly:s3cret@db/x"))
    client, _ = make_client(llm, db, app_env=app_env)
    records = []
    handler = logging.Handler()
    handler.emit = records.append
    LOGGER.addHandler(handler)
    try:
        client.post("/chat", json={"session_id": open_session(client), "question": "Q"})
    finally:
        LOGGER.removeHandler(handler)
    return next(r.fields for r in records if r.getMessage() == "chat_error")


def test_production_logs_the_error_type_only():
    fields = failed_chat_log("production")
    assert fields == {"error_type": "RuntimeError"}


def test_development_logs_the_traceback_but_the_client_never_gets_it():
    fields = failed_chat_log("development")
    assert "Traceback" in fields["traceback"]
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT unitnumber FROM units")],
    )
    db = FakeDatabase(RuntimeError("boom"))
    client, _ = make_client(llm, db, app_env="development")
    response = client.post("/chat", json={"session_id": open_session(client), "question": "Q"})
    assert response.status_code == 500
    assert "Traceback" not in response.text
    assert "boom" not in response.text


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_off_by_default(path):
    client, _ = make_client()
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_on_only_in_development(path):
    client, _ = make_client(app_env="development")
    assert client.get(path).status_code == 200
