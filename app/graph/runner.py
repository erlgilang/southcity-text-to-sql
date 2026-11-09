import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.domain.formatting import strip_em_dash
from app.observability import log_event
from app.sessions import Session, SessionStore


@dataclass(frozen=True)
class ChatResult:
    request_id: str
    answer: str
    outcome: str  # answer, clarify, refuse or error
    intent: str
    table: dict[str, Any] | None
    steps: list[dict[str, Any]]  # node name, milliseconds and public info, never any SQL text
    sql: str | None  # the model's own SQL, only for outcomes where showing it is safe
    total_ms: int


def run_chat(
    graph: Any, store: SessionStore, session: Session, question: str, today: str | None = None
) -> ChatResult:
    """Run one question for a session and remember the turn.

    The role and agent id come from the session. The question text can never change them.
    """
    request_id = uuid4().hex[:12]
    ids = {"request_id": request_id, "session_id": session.session_id}
    started = perf_counter()
    initial = {
        **ids,
        "role": session.user.role,
        "agent_id": session.user.agent_id,
        "question": question,
        "history": [(turn.question, turn.answer) for turn in session.history],
    }
    if today:
        initial["today"] = today

    try:
        state = graph.invoke(initial)
    except Exception as error:
        total_ms = round((perf_counter() - started) * 1000)
        log_event(
            "request_summary",
            level=logging.ERROR,
            total_ms=total_ms,
            outcome="error",
            error_type=type(error).__name__,
            **ids,
        )
        raise

    total_ms = round((perf_counter() - started) * 1000)
    answer = strip_em_dash(state["answer"])
    log_event(
        "request_summary",
        total_ms=total_ms,
        llm_ms=state.get("llm_ms", 0),
        db_ms=state.get("db_ms", 0),
        llm_calls=state.get("llm_calls", 0),
        sql_attempts=state.get("sql_attempts", 0),
        input_tokens=state.get("input_tokens", 0),
        output_tokens=state.get("output_tokens", 0),
        intent=state["intent"],
        outcome=state["outcome"],
        **ids,
    )
    store.record_turn(session.session_id, question, answer)
    steps = [
        {**step, "info": {k: v for k, v in step["info"].items() if k != "sql"}}
        for step in state["steps"]
    ]
    # After a security refusal the SQL would only repeat what the attacker asked for
    shows_sql = state["outcome"] in ("answer", "error")
    return ChatResult(
        request_id=request_id,
        answer=answer,
        outcome=state["outcome"],
        intent=state["intent"],
        table=state["table"],
        steps=steps,
        sql=state.get("sql") if shows_sql else None,
        total_ms=total_ms,
    )
