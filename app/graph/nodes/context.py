from datetime import datetime
from zoneinfo import ZoneInfo

from app.domain.schema_text import build_schema_text, load_glossary
from app.graph.tracing import NodeResult

JAKARTA = ZoneInfo("Asia/Jakarta")


def load_context(state: dict) -> NodeResult:
    # state["today"] is only set by tests that need a fixed date
    today = state.get("today") or datetime.now(JAKARTA).date().isoformat()
    return NodeResult(
        update={
            "today": today,
            "schema": build_schema_text(state["role"]),
            "glossary": load_glossary(),
            "attempt": 0,
            "error": "",
            "error_kind": "ok",
        },
        info={"role": state["role"], "today": today},
    )
