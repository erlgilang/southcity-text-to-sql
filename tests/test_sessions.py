import pytest

from app.sessions import MessageLimitError, SessionNotFoundError, SessionStore
from app.sql.users import User

BAMBANG = User(1, "sales_bambang", "Bambang Pamungkas", "Sales", 101)
HENDRA = User(4, "finance_hendra", "Hendra Setiawan", "Finance", None)


def test_session_keeps_the_user_chosen_at_creation():
    store = SessionStore()
    session = store.create(BAMBANG)
    assert store.get(session.session_id).user == BAMBANG


def test_switching_user_gives_a_new_session_with_empty_history():
    store = SessionStore()
    first = store.create(BAMBANG)
    store.record_turn(first.session_id, "Berapa unit kosong?", "Ada 5 unit.")
    second = store.create(HENDRA)
    assert second.session_id != first.session_id
    assert list(second.history) == []


def test_history_keeps_only_the_last_six_turns():
    store = SessionStore()
    session = store.create(BAMBANG)
    for number in range(8):
        store.record_turn(session.session_id, f"q{number}", f"a{number}")
    assert [turn.question for turn in store.get(session.session_id).history] == [
        "q2",
        "q3",
        "q4",
        "q5",
        "q6",
        "q7",
    ]


def test_unknown_session_raises():
    with pytest.raises(SessionNotFoundError):
        SessionStore().get("not-a-session")


def test_oldest_unused_session_is_dropped_at_the_limit():
    store = SessionStore(max_sessions=2)
    first = store.create(BAMBANG)
    second = store.create(HENDRA)
    store.get(first.session_id)  # first was used more recently than second
    third = store.create(BAMBANG)
    store.get(first.session_id)
    store.get(third.session_id)
    with pytest.raises(SessionNotFoundError):
        store.get(second.session_id)


def test_message_limit_per_session():
    store = SessionStore(max_messages=2)
    session = store.create(BAMBANG)
    store.claim_message(session.session_id)
    store.claim_message(session.session_id)
    with pytest.raises(MessageLimitError):
        store.claim_message(session.session_id)


def test_message_limit_is_per_session():
    store = SessionStore(max_messages=1)
    first = store.create(BAMBANG)
    second = store.create(HENDRA)
    store.claim_message(first.session_id)
    store.claim_message(second.session_id)
