from time import perf_counter
from typing import Any

from langchain_core.messages import BaseMessage
from pydantic import BaseModel


def call_structured[T: BaseModel](
    llm: Any, schema: type[T], messages: list[BaseMessage]
) -> tuple[T, dict[str, int]]:
    """Call the model for a Pydantic result. Returns it with the usage counters for the state."""
    started = perf_counter()
    output = llm.with_structured_output(schema, include_raw=True).invoke(messages)
    if output["parsed"] is None:
        raise ValueError(f"Model output did not match {schema.__name__}: {output['parsing_error']}")
    return output["parsed"], _usage(started, output["raw"])


def call_text(llm: Any, messages: list[BaseMessage]) -> tuple[str, dict[str, int]]:
    started = perf_counter()
    reply = llm.invoke(messages)
    return reply.text, _usage(started, reply)


def _usage(started: float, reply: BaseMessage) -> dict[str, int]:
    tokens = reply.usage_metadata or {}
    return {
        "llm_calls": 1,
        "llm_ms": round((perf_counter() - started) * 1000),
        "input_tokens": tokens.get("input_tokens", 0),
        "output_tokens": tokens.get("output_tokens", 0),
    }
