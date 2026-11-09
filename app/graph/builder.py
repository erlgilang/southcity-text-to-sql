from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.classify import classify
from app.graph.nodes.context import load_context
from app.graph.nodes.generate_sql import generate_sql
from app.graph.nodes.query import execute_query, prepare_retry, rbac_rewrite, validate
from app.graph.nodes.reply import (
    ask_clarification,
    give_up,
    refuse_request,
    refuse_unsafe,
    write_answer,
)
from app.graph.state import GraphState
from app.graph.tracing import traced
from app.llm.models import get_llm
from app.sql.executor import QueryResult, execute

MAX_RETRIES = 2

# The intent is chosen by the LLM. This only maps its answer to the next node.
INTENT_ROUTES = {
    "sql_query": "generate_sql",
    "chitchat": "write_answer",
    "clarify": "ask_clarification",
    "refuse": "refuse_request",
}


def build_graph(llm: Any = None, run_query: Callable[[str], QueryResult] = execute):
    """Compile the graph. llm and run_query can be replaced in tests."""
    llm = llm or get_llm()
    graph = StateGraph(GraphState)

    graph.add_node("load_context", traced("load_context", load_context))
    graph.add_node("classify", traced("classify", lambda state: classify(state, llm)))
    graph.add_node("generate_sql", traced("generate_sql", lambda state: generate_sql(state, llm)))
    graph.add_node("validate", traced("validate", validate))
    graph.add_node("rbac_rewrite", traced("rbac_rewrite", rbac_rewrite))
    graph.add_node("execute", traced("execute", lambda state: execute_query(state, run_query)))
    graph.add_node("retry", traced("retry", prepare_retry))
    graph.add_node("write_answer", traced("write_answer", lambda state: write_answer(state, llm)))
    graph.add_node("ask_clarification", traced("ask_clarification", ask_clarification))
    graph.add_node("refuse_request", traced("refuse_request", refuse_request))
    graph.add_node("refuse_unsafe", traced("refuse_unsafe", refuse_unsafe))
    graph.add_node("give_up", traced("give_up", give_up))

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "classify")
    graph.add_conditional_edges("classify", _route_after_classify, list(INTENT_ROUTES.values()))
    graph.add_edge("generate_sql", "validate")
    graph.add_conditional_edges(
        "validate", _route_after_validate, ["rbac_rewrite", "refuse_unsafe", "retry", "give_up"]
    )
    graph.add_edge("rbac_rewrite", "execute")
    graph.add_conditional_edges(
        "execute", _route_after_execute, ["write_answer", "retry", "give_up"]
    )
    graph.add_edge("retry", "generate_sql")
    for terminal in (
        "write_answer",
        "ask_clarification",
        "refuse_request",
        "refuse_unsafe",
        "give_up",
    ):
        graph.add_edge(terminal, END)
    return graph.compile()


def _route_after_classify(state: dict) -> str:
    return INTENT_ROUTES[state["intent"]]


def _route_after_validate(state: dict) -> str:
    if state["error_kind"] == "ok":
        return "rbac_rewrite"
    if state["error_kind"] == "security":
        return "refuse_unsafe"
    return _retry_or_give_up(state)


def _route_after_execute(state: dict) -> str:
    if state["error_kind"] == "ok":
        return "write_answer"
    return _retry_or_give_up(state)


def _retry_or_give_up(state: dict) -> str:
    return "retry" if state["attempt"] < MAX_RETRIES else "give_up"
