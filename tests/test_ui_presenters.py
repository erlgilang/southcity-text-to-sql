from presenters import STEP_LABELS, describe_step, format_seconds

from app.graph.builder import build_graph
from tests.fakes import FakeDatabase, FakeLLM, classification, generated, rows_result
from tests.test_graph import ask


def step(node, **info):
    return {"node": node, "ms": 1, "info": info}


def test_describe_each_kind_of_step():
    assert (
        describe_step(step("classify", intent="sql_query", relevant_tables=[])) == "pertanyaan data"
    )
    assert describe_step(step("generate_sql", attempt=2)) == "percobaan 2"
    assert describe_step(step("validate", status="ok")) == "lolos"
    assert describe_step(step("validate", status="rejected", retryable=False)) == "ditolak"
    assert "Use the literal date" in describe_step(
        step("validate", status="rejected", retryable=True, reason="Use the literal date")
    )
    assert describe_step(step("execute", rows=3, truncated=False, db_ms=5)) == "3 baris"
    assert describe_step(step("execute", status="error", reason="boom")) == "gagal, boom"
    assert describe_step(step("retry", attempt=1, error="boom")) == "percobaan 2, karena: boom"
    assert describe_step(step("load_context", role="Sales", today="2026-01-01")) == ""


def test_every_node_the_graph_produces_has_a_label():
    llm = FakeLLM(
        classifications=[classification("sql_query", "Q", ["units"])],
        sqls=[generated("SELECT unitnumber FROM units")],
        texts=["ok"],
    )
    result = ask("Q", llm, FakeDatabase(rows_result(["unitnumber"], [("A",)])))[0]
    for item in result.steps:
        assert item["node"] in STEP_LABELS
        describe_step(item)


def test_every_graph_node_name_is_labelled():
    graph = build_graph(FakeLLM(), FakeDatabase())
    assert set(graph.get_graph().nodes) - {"__start__", "__end__"} <= set(STEP_LABELS)


def test_seconds_use_a_decimal_comma():
    assert format_seconds(6940) == "6,9 detik"
    assert format_seconds(300) == "0,3 detik"
