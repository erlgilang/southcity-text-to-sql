import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from app.observability import log_event


@dataclass
class NodeResult:
    update: dict[str, Any]
    # Shown to the user in the "Proses" panel and also logged. Keep it free of secrets.
    info: dict[str, Any] = field(default_factory=dict)
    # Server log only, for example the SQL after the RBAC rewrite
    log: dict[str, Any] = field(default_factory=dict)


def traced(name: str, node: Callable[[dict], NodeResult]) -> Callable[[dict], dict]:
    """Time a node, write its log line and add a step to the state."""

    def run(state: dict) -> dict:
        ids = {"request_id": state["request_id"], "session_id": state["session_id"]}
        started = perf_counter()
        try:
            result = node(state)
        except Exception as error:
            # Only the type: the message of a driver error can contain the connection string
            log_event(
                "node_error", level=logging.ERROR, node=name, error_type=type(error).__name__, **ids
            )
            raise
        duration_ms = round((perf_counter() - started) * 1000)
        log_event("node", node=name, duration_ms=duration_ms, **ids, **result.info, **result.log)
        step = {"node": name, "ms": duration_ms, "info": result.info}
        return {**result.update, "steps": [step]}

    return run
