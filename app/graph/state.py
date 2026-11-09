import operator
from typing import Annotated, Any, TypedDict

from sqlglot import exp

from app.sql.executor import QueryResult


class GraphState(TypedDict, total=False):
    # Input, filled by the runner from the server-side session
    request_id: str
    session_id: str
    role: str
    agent_id: int | None
    question: str
    history: list[tuple[str, str]]

    # load_context
    today: str
    schema: str
    glossary: str

    # classify
    intent: str
    standalone_question: str
    relevant_tables: list[str]
    note: str

    # SQL loop
    attempt: int
    sql: str
    money_columns: list[str]
    error: str
    error_kind: str  # ok, retry or security
    statement: exp.Query
    final_sql: str  # after RBAC rewrite, only for the server log and the database
    result: QueryResult

    # Output
    answer: str
    outcome: str  # answer, clarify, refuse or error
    table: dict[str, Any] | None

    # Measurements. Nodes return deltas, the reducers add them up.
    steps: Annotated[list[dict[str, Any]], operator.add]
    llm_calls: Annotated[int, operator.add]
    llm_ms: Annotated[int, operator.add]
    db_ms: Annotated[int, operator.add]
    sql_attempts: Annotated[int, operator.add]
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]
