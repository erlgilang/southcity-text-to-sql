from dataclasses import dataclass
from typing import Any

from psycopg.errors import InsufficientPrivilege, QueryCanceled
from sqlalchemy.exc import DataError, OperationalError, ProgrammingError

from app.sql.engines import readonly_engine

ROW_LIMIT = 200


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[tuple[Any, ...]]
    truncated: bool


class SqlExecutionError(Exception):
    """A database error the model can fix by rewriting the query. The message is safe to show it."""


def execute(sql: str) -> QueryResult:
    """Run one query and return at most ROW_LIMIT rows.

    Errors caused by the query itself raise SqlExecutionError. Connection problems and
    permission errors are not the model's fault, so they pass through unchanged.
    """
    try:
        with readonly_engine().connect() as connection:
            # exec_driver_sql skips SQLAlchemy's ':name' parsing. psycopg still reads '%' as a
            # placeholder because an empty parameter list is sent, so double it for LIKE patterns.
            cursor = connection.exec_driver_sql(sql.replace("%", "%%"))
            fetched = cursor.fetchmany(ROW_LIMIT + 1)
            columns = list(cursor.keys())
    except ProgrammingError as error:
        if isinstance(error.orig, InsufficientPrivilege):
            raise
        raise SqlExecutionError(_primary_message(error)) from error
    except DataError as error:
        raise SqlExecutionError(_primary_message(error)) from error
    except OperationalError as error:
        if isinstance(error.orig, QueryCanceled):
            raise SqlExecutionError(
                "The query ran too long and was cancelled. Filter more or simplify it."
            ) from error
        raise
    return QueryResult(
        columns, [tuple(row) for row in fetched[:ROW_LIMIT]], len(fetched) > ROW_LIMIT
    )


def _primary_message(error: ProgrammingError | DataError) -> str:
    # message_primary is Postgres' own sentence, without the SQL text SQLAlchemy appends.
    # Errors raised by the driver before reaching the server have none.
    return error.orig.diag.message_primary or str(error.orig)
