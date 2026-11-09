from typing import Any

from app.graph.llm_calls import call_structured
from app.graph.prompts import build_messages, escape_tags
from app.graph.schemas import GeneratedSql
from app.graph.tracing import NodeResult


def generate_sql(state: dict, llm: Any) -> NodeResult:
    parts = [
        f"<standalone_question>{escape_tags(state['standalone_question'])}</standalone_question>",
        f"<relevant_tables>{', '.join(state['relevant_tables'])}</relevant_tables>",
    ]
    if state["attempt"] > 0:
        parts.append(
            f"<previous_attempt>\n<sql>{state['sql']}</sql>\n"
            f"<error>{state['error']}</error>\n</previous_attempt>"
        )
    messages = build_messages(
        "generate_sql",
        "\n".join(parts),
        today=state["today"],
        schema=state["schema"],
        glossary=state["glossary"],
    )
    generated, usage = call_structured(llm, GeneratedSql, messages)
    return NodeResult(
        update={
            **usage,
            "sql": generated.sql,
            "money_columns": generated.money_columns,
            "error": "",
            "error_kind": "ok",
            "sql_attempts": 1,
        },
        info={"attempt": state["attempt"] + 1, "sql": generated.sql},
        log=usage,
    )
