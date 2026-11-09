from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints

MAX_QUESTION_LENGTH = 500

Question = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_LENGTH)
]


class StrictRequest(BaseModel):
    # A field such as "role" in the body is an error, never silently ignored
    model_config = ConfigDict(extra="forbid")


class CreateSessionRequest(StrictRequest):
    username: str


class ChatRequest(StrictRequest):
    session_id: str
    question: Question


class UserOut(BaseModel):
    username: str
    full_name: str
    role: str


class SessionOut(BaseModel):
    session_id: str
    user: UserOut


class ChatResponse(BaseModel):
    request_id: str
    answer: str
    outcome: str
    intent: str
    table: dict[str, Any] | None
    steps: list[dict[str, Any]]
    sql: str | None
    total_ms: int
