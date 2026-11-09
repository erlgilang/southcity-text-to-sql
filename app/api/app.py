import logging
import traceback
from typing import Any

from fastapi import FastAPI, HTTPException

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    SessionOut,
    UserOut,
)
from app.graph.runner import run_chat
from app.observability import log_event
from app.sessions import MessageLimitError, SessionNotFoundError, SessionStore
from app.sql.users import UnknownUserError, User


def build_app(graph: Any, store: SessionStore, users: Any, app_env: str) -> FastAPI:
    """Create the API. graph, store and users are passed in so tests can replace them."""
    development = app_env == "development"
    app = FastAPI(
        title="SouthCity Text-to-SQL",
        docs_url="/docs" if development else None,
        redoc_url="/redoc" if development else None,
        openapi_url="/openapi.json" if development else None,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/users")
    def list_users() -> list[UserOut]:
        return [_user_out(user) for user in users.list_users()]

    @app.post("/sessions")
    def create_session(request: CreateSessionRequest) -> SessionOut:
        try:
            user = users.get_user(request.username)
        except UnknownUserError:
            raise HTTPException(404, f"User {request.username!r} tidak ditemukan.") from None
        session = store.create(user)
        return SessionOut(session_id=session.session_id, user=_user_out(user))

    @app.post("/chat")
    def chat(request: ChatRequest) -> ChatResponse:
        try:
            session = store.claim_message(request.session_id)
        except SessionNotFoundError:
            raise HTTPException(404, "Sesi tidak ditemukan atau sudah berakhir.") from None
        except MessageLimitError:
            raise HTTPException(
                429, "Sesi ini sudah mencapai batas pesan. Pilih user lagi untuk memulai sesi baru."
            ) from None
        try:
            result = run_chat(graph, store, session, request.question)
        except Exception as error:  # noqa: BLE001  # turn any failure into a generic 500, log the type only
            fields = {"error_type": type(error).__name__}
            if development:
                # Driver messages can hold the connection string, so only development logs them.
                fields["traceback"] = traceback.format_exc()
            log_event("chat_error", level=logging.ERROR, **fields)
            raise HTTPException(
                500, "Terjadi kesalahan di server. Coba kirim ulang pertanyaan beberapa saat lagi."
            ) from None
        return ChatResponse(**vars(result))

    return app


def _user_out(user: User) -> UserOut:
    return UserOut(username=user.username, full_name=user.full_name, role=user.role)
