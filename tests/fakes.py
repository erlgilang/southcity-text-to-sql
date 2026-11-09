"""Test doubles for the graph: a scripted LLM and a scripted database."""

from langchain_core.messages import AIMessage

from app.graph.schemas import Classification, GeneratedSql
from app.sessions import SessionStore
from app.sql.executor import QueryResult
from app.sql.users import User

BAMBANG = User(1, "sales_bambang", "Bambang Pamungkas", "Sales", 101)
HENDRA = User(4, "finance_hendra", "Hendra Setiawan", "Finance", None)
TOKENS = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}


def classification(intent, standalone="", tables=(), message=""):
    return Classification(
        intent=intent,
        standalone_question=standalone,
        relevant_tables=list(tables),
        message=message,
    )


def generated(sql, money=()):
    return GeneratedSql(sql=sql, money_columns=list(money))


class FakeLLM:
    """Returns scripted answers in order and records every prompt it receives."""

    def __init__(self, classifications=(), sqls=(), texts=()):
        self._queues = {
            Classification: list(classifications),
            GeneratedSql: list(sqls),
            "text": list(texts),
        }
        self.calls = []  # (kind, system prompt, human message)

    def with_structured_output(self, schema, include_raw=False):
        return _StructuredCall(self, schema)

    def invoke(self, messages):
        text = self._next("text", messages)
        return AIMessage(content=text, usage_metadata=TOKENS)

    def calls_of(self, kind):
        return [call for call in self.calls if call[0] == kind]

    def _next(self, kind, messages):
        self.calls.append((kind, messages[0].content, messages[-1].content))
        queue = self._queues[kind]
        if not queue:
            raise AssertionError(f"Unexpected LLM call of kind {kind!r}")
        return queue.pop(0)


class _StructuredCall:
    def __init__(self, llm, schema):
        self._llm = llm
        self._schema = schema

    def invoke(self, messages):
        parsed = self._llm._next(self._schema, messages)
        return {
            "raw": AIMessage(content="", usage_metadata=TOKENS),
            "parsed": parsed,
            "parsing_error": None,
        }


class FakeDatabase:
    """Plays back results or raises errors in order, and records the SQL it was given."""

    def __init__(self, *outcomes):
        self._outcomes = list(outcomes)
        self.queries = []

    def __call__(self, sql):
        self.queries.append(sql)
        if not self._outcomes:
            raise AssertionError("Unexpected database call")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def rows_result(columns, rows, truncated=False):
    return QueryResult(list(columns), list(rows), truncated)


def new_session(user=HENDRA, turns=()):
    store = SessionStore()
    session = store.create(user)
    for question, answer in turns:
        store.record_turn(session.session_id, question, answer)
    return store, session
