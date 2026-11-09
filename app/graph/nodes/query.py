from collections.abc import Callable
from time import perf_counter

from app.graph.tracing import NodeResult
from app.sql.executor import QueryResult, SqlExecutionError
from app.sql.rbac import apply_rbac
from app.sql.validator import SqlRejected, validate_sql


def validate(state: dict) -> NodeResult:
    try:
        statement = validate_sql(state["sql"], state["role"])
    except SqlRejected as rejected:
        info = {"status": "rejected", "retryable": rejected.retryable}
        if rejected.retryable:
            info["reason"] = str(rejected)
            log = {}
        else:
            # The reason can name a protected table, so it stays out of the user-facing steps
            log = {"reason": str(rejected)}
        kind = "retry" if rejected.retryable else "security"
        return NodeResult({"error": str(rejected), "error_kind": kind}, info, log)
    return NodeResult({"statement": statement, "error_kind": "ok"}, {"status": "ok"})


def rbac_rewrite(state: dict) -> NodeResult:
    rewritten = apply_rbac(state["statement"], state["role"], state["agent_id"])
    sql = rewritten.sql(dialect="postgres")
    return NodeResult({"final_sql": sql}, info={"role": state["role"]}, log={"sql": sql})


def execute_query(state: dict, run_query: Callable[[str], QueryResult]) -> NodeResult:
    started = perf_counter()
    try:
        result = run_query(state["final_sql"])
    except SqlExecutionError as error:
        db_ms = round((perf_counter() - started) * 1000)
        info = {"status": "error", "retryable": True, "reason": str(error), "db_ms": db_ms}
        return NodeResult({"error": str(error), "error_kind": "retry", "db_ms": db_ms}, info)
    db_ms = round((perf_counter() - started) * 1000)
    info = {"rows": len(result.rows), "truncated": result.truncated, "db_ms": db_ms}
    return NodeResult({"result": result, "error_kind": "ok", "db_ms": db_ms}, info)


def prepare_retry(state: dict) -> NodeResult:
    attempt = state["attempt"] + 1
    return NodeResult({"attempt": attempt}, info={"attempt": attempt, "error": state["error"]})
