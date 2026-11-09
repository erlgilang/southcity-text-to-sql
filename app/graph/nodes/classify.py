from typing import Any

from app.domain.policy import load_policy
from app.graph.llm_calls import call_structured
from app.graph.prompts import build_messages, escape_tags, format_history
from app.graph.schemas import Classification
from app.graph.tracing import NodeResult


def classify(state: dict, llm: Any) -> NodeResult:
    human = (
        f"<history>\n{format_history(state['history'])}\n</history>\n"
        f"<question>{escape_tags(state['question'])}</question>"
    )
    messages = build_messages(
        "classify",
        human,
        today=state["today"],
        role=state["role"],
        schema=state["schema"],
        glossary=state["glossary"],
    )
    classification, usage = call_structured(llm, Classification, messages)
    # The model may name a table the role cannot use. Drop it before it reaches the next prompt.
    allowed = load_policy().for_role(state["role"]).tables
    tables = [name for name in classification.relevant_tables if name in allowed]
    return NodeResult(
        update={
            **usage,
            "intent": classification.intent,
            "standalone_question": classification.standalone_question,
            "relevant_tables": tables,
            "note": classification.message,
        },
        info={"intent": classification.intent, "relevant_tables": tables},
        log=usage,
    )
