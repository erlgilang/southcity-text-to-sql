from typing import Any

from app.domain.formatting import format_table
from app.graph.llm_calls import call_text
from app.graph.messages import (
    CLARIFY_FALLBACK_MESSAGE,
    GIVE_UP_MESSAGE,
    SALES_EMPTY_MESSAGE,
    SECURITY_REFUSAL_MESSAGE,
)
from app.graph.prompts import build_messages, escape_tags, format_history
from app.graph.tracing import NodeResult
from app.sql.executor import ROW_LIMIT

ANSWER_ROWS = 30


def write_answer(state: dict, llm: Any) -> NodeResult:
    result = state.get("result")
    history = f"<history>\n{format_history(state['history'])}\n</history>"
    if result is None:
        human = f"{history}\n<question>{escape_tags(state['question'])}</question>"
        text, usage = _ask(state, llm, human)
        return NodeResult({**usage, "answer": text, "outcome": "answer", "table": None}, log=usage)

    # Python formats every amount first, so the model copies Rupiah text instead of raw numbers
    cells = format_table(result.columns, result.rows, state["money_columns"])
    money = {name.lower() for name in state["money_columns"]}
    table = {
        "columns": result.columns,
        "rows": cells,
        "money_columns": [name for name in result.columns if name.lower() in money],
        "truncated": result.truncated,
    }
    note = state.get("note", "")
    if not result.rows and state["role"] == "Sales":
        # The model's note is dropped: it can promise output that does not exist
        return NodeResult(
            {"answer": SALES_EMPTY_MESSAGE, "outcome": "answer", "table": table}, {"rows": 0}
        )

    human = (
        f"{history}\n<question>{escape_tags(state['standalone_question'])}</question>\n"
        f"{_query_result_block(result.columns, cells, result.truncated)}"
    )
    if note:
        human += f"\n<note>{escape_tags(note)}</note>"
    text, usage = _ask(state, llm, human)
    return NodeResult(
        {**usage, "answer": text, "outcome": "answer", "table": table},
        info={"rows": len(cells)},
        log=usage,
    )


def ask_clarification(state: dict) -> NodeResult:
    text = state.get("note") or CLARIFY_FALLBACK_MESSAGE
    return NodeResult({"answer": text, "outcome": "clarify", "table": None})


def refuse_request(state: dict) -> NodeResult:
    text = state.get("note") or SECURITY_REFUSAL_MESSAGE
    return NodeResult({"answer": text, "outcome": "refuse", "table": None})


def refuse_unsafe(state: dict) -> NodeResult:
    update = {"answer": SECURITY_REFUSAL_MESSAGE, "outcome": "refuse", "table": None}
    return NodeResult(update)


def give_up(state: dict) -> NodeResult:
    update = {"answer": GIVE_UP_MESSAGE, "outcome": "error", "table": None}
    return NodeResult(update, info={"attempts": state["attempt"] + 1})


def _ask(state: dict, llm: Any, human: str) -> tuple[str, dict[str, int]]:
    return call_text(llm, build_messages("answer", human, today=state["today"]))


def _query_result_block(columns: list[str], cells: list[list[str]], truncated: bool) -> str:
    shown = cells[:ANSWER_ROWS]
    total = f"more than {ROW_LIMIT}" if truncated else str(len(cells))
    lines = [
        "<query_result>",
        f"columns: {escape_tags(', '.join(columns))}",
        f"total_rows: {total}",
        f"shown_rows: {len(shown)}",
        "rows:",
        *(escape_tags(" | ".join(row)) for row in shown),
    ]
    if len(cells) > len(shown):
        lines.append(f"({len(cells) - len(shown)} more rows not shown)")
    lines.append("</query_result>")
    return "\n".join(lines)
