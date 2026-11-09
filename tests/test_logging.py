import json
import logging
from decimal import Decimal

import pytest

from app.observability import LOGGER, JsonFormatter, configure_logging, log_event
from app.sql.executor import SqlExecutionError
from tests.fakes import (
    BAMBANG,
    FakeDatabase,
    FakeLLM,
    classification,
    generated,
    rows_result,
)
from tests.support import ListHandler
from tests.test_graph import ask


@pytest.fixture
def logs():
    handler = ListHandler()
    old_level, old_propagate = LOGGER.level, LOGGER.propagate
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    yield handler.events
    LOGGER.removeHandler(handler)
    LOGGER.setLevel(old_level)
    LOGGER.propagate = old_propagate


def data_chat(user, rows, columns=("customername",)):
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["sales_contracts"])],
        sqls=[generated(f"SELECT {', '.join(columns)} FROM sales_contracts")],
        texts=["ok"],
    )
    db = FakeDatabase(rows_result(columns, rows))
    return ask("Q", llm, db, user=user)[0]


def by_event(logs, name):
    return [entry for entry in logs if entry["event"] == name]


def test_every_node_logs_one_line_with_ids_and_duration(logs):
    data_chat(BAMBANG, [("Budi",)])
    nodes = by_event(logs, "node")
    assert [entry["node"] for entry in nodes] == [
        "load_context",
        "classify",
        "generate_sql",
        "validate",
        "rbac_rewrite",
        "execute",
        "write_answer",
    ]
    assert len({entry["request_id"] for entry in nodes}) == 1
    assert all(entry["session_id"] and isinstance(entry["duration_ms"], int) for entry in nodes)


def test_node_lines_carry_their_specific_fields(logs):
    data_chat(BAMBANG, [("Budi",)])
    node = {entry["node"]: entry for entry in by_event(logs, "node")}
    assert node["classify"]["intent"] == "sql_query"
    assert node["classify"]["relevant_tables"] == ["sales_contracts"]
    assert node["generate_sql"]["sql"] == "SELECT customername FROM sales_contracts"
    assert node["validate"]["status"] == "ok"
    assert node["execute"]["rows"] == 1
    assert "db_ms" in node["execute"]
    assert node["classify"]["input_tokens"] == 10
    assert node["classify"]["output_tokens"] == 5


def test_rejection_reason_and_retry_are_logged(logs):
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT phone FROM units"), generated("SELECT unitnumber FROM units")],
        texts=["ok"],
    )
    db = FakeDatabase(
        SqlExecutionError('column "phone" does not exist'), rows_result(["unitnumber"], [("A",)])
    )
    ask("Q", llm, db)
    retry = by_event(logs, "node")
    retry = next(entry for entry in retry if entry["node"] == "retry")
    assert retry["attempt"] == 1
    assert 'column "phone" does not exist' in retry["error"]


def test_security_rejection_logs_the_reason_on_the_server(logs):
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT * FROM system_users")],
    )
    ask("Q", llm, FakeDatabase(), user=BAMBANG)
    validate = next(e for e in by_event(logs, "node") if e["node"] == "validate")
    assert validate["status"] == "rejected"
    assert validate["retryable"] is False
    assert "system_users" in validate["reason"]


def test_one_summary_line_per_request(logs):
    data_chat(BAMBANG, [("Budi",)])
    summary = by_event(logs, "request_summary")
    assert len(summary) == 1
    summary = summary[0]
    assert summary["intent"] == "sql_query"
    assert summary["outcome"] == "answer"
    assert summary["llm_calls"] == 3
    assert summary["sql_attempts"] == 1
    assert summary["input_tokens"] == 30
    assert summary["output_tokens"] == 15
    assert summary["total_ms"] >= summary["llm_ms"] + summary["db_ms"]
    assert summary["request_id"] == by_event(logs, "node")[0]["request_id"]


def test_rewritten_sql_is_logged_on_the_server_only(logs):
    result = data_chat(BAMBANG, [("Budi",)])
    rewrite = next(e for e in by_event(logs, "node") if e["node"] == "rbac_rewrite")
    assert "salesagentid = 101" in rewrite["sql"]
    assert "salesagentid" not in json.dumps(result.steps)


def test_result_rows_never_reach_the_log(logs):
    rows = [("RAHASIA-BARIS-123", Decimal("987654321"))]
    data_chat(BAMBANG, rows, columns=("customername", "totalprice"))
    exported = json.dumps(logs, default=str)
    assert "RAHASIA-BARIS-123" not in exported
    assert "987654321" not in exported
    assert next(e for e in by_event(logs, "node") if e["node"] == "execute")["rows"] == 1


def test_connection_strings_and_passwords_never_reach_the_log(logs):
    secret_error = RuntimeError(
        "could not connect: postgresql://app_readonly:s3cret@db.example.com/postgres"
    )
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT unitnumber FROM units")],
    )
    with pytest.raises(RuntimeError):
        ask("Q", llm, FakeDatabase(secret_error))
    summary = by_event(logs, "request_summary")[0]
    assert summary["outcome"] == "error"
    assert summary["error_type"] == "RuntimeError"
    exported = json.dumps(logs, default=str)
    assert "s3cret" not in exported
    assert "postgresql://" not in exported


def test_json_formatter_writes_one_valid_json_object():
    record = logging.LogRecord("southcity", logging.INFO, __file__, 1, "node", None, None)
    record.fields = {"node": "classify", "duration_ms": 12, "relevant_tables": ["units"]}
    line = JsonFormatter().format(record)
    parsed = json.loads(line)
    assert "\n" not in line
    assert (parsed["event"], parsed["node"], parsed["duration_ms"]) == ("node", "classify", 12)
    assert parsed["level"] == "INFO"
    assert parsed["time"]


def test_configure_logging_prints_json_to_stdout_and_honours_the_level(capsys):
    old_handlers, old_level, old_propagate = LOGGER.handlers[:], LOGGER.level, LOGGER.propagate
    try:
        configure_logging("WARNING")
        log_event("hidden", a=1)
        configure_logging("INFO")
        log_event("shown", a=2)
        lines = capsys.readouterr().out.strip().splitlines()
    finally:
        LOGGER.handlers, LOGGER.propagate = old_handlers, old_propagate
        LOGGER.setLevel(old_level)
    assert [json.loads(line)["event"] for line in lines] == ["shown"]
