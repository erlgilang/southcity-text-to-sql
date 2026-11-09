import logging

from app.sql.rbac import apply_rbac
from app.sql.validator import validate_sql


def run_as(db, sql: str, role: str, agent_id: int | None = None):
    """Validate, rewrite for the role and run on the test database. Returns (columns, rows)."""
    statement = apply_rbac(validate_sql(sql, role), role, agent_id)
    cursor = db.execute(statement.sql(dialect="sqlite"))
    # SQLite keeps the DDL casing for untouched tables, Postgres folds names to lowercase
    return [column[0].lower() for column in cursor.description], cursor.fetchall()


def values(db, sql: str, role: str, agent_id: int | None = None) -> list:
    """First column of every row."""
    return [row[0] for row in run_as(db, sql, role, agent_id)[1]]


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.events = []

    def emit(self, record):
        self.events.append({"event": record.getMessage(), **getattr(record, "fields", {})})
