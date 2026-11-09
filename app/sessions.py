import threading
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from uuid import uuid4

from app.sql.users import User

MAX_SESSIONS = 500
MAX_MESSAGES = 50
MAX_TURNS = 6


@dataclass(frozen=True)
class Turn:
    question: str
    answer: str


@dataclass
class Session:
    session_id: str
    user: User
    history: deque[Turn] = field(default_factory=lambda: deque(maxlen=MAX_TURNS))
    messages_used: int = 0


class SessionNotFoundError(LookupError):
    pass


class MessageLimitError(Exception):
    pass


class SessionStore:
    """In-memory sessions. Lost on restart, so callers must handle SessionNotFoundError.

    The user is fixed when the session is created. Switching user means creating a new
    session, so history from one role never reaches another.
    """

    def __init__(self, max_sessions: int = MAX_SESSIONS, max_messages: int = MAX_MESSAGES):
        self._sessions: OrderedDict[str, Session] = OrderedDict()
        self._max_sessions = max_sessions
        self._max_messages = max_messages
        # FastAPI runs sync endpoints in a thread pool
        self._lock = threading.Lock()

    def create(self, user: User) -> Session:
        session = Session(session_id=str(uuid4()), user=user)
        with self._lock:
            self._sessions[session.session_id] = session
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)
        return session

    def get(self, session_id: str) -> Session:
        with self._lock:
            return self._touch(session_id)

    def claim_message(self, session_id: str) -> Session:
        """Count one message against the session limit and return the session."""
        with self._lock:
            session = self._touch(session_id)
            if session.messages_used >= self._max_messages:
                raise MessageLimitError(f"Session reached {self._max_messages} messages")
            session.messages_used += 1
            return session

    def record_turn(self, session_id: str, question: str, answer: str) -> None:
        with self._lock:
            self._touch(session_id).history.append(Turn(question, answer))

    def _touch(self, session_id: str) -> Session:
        try:
            session = self._sessions[session_id]
        except KeyError:
            raise SessionNotFoundError(f"Unknown session {session_id}") from None
        self._sessions.move_to_end(session_id)
        return session
