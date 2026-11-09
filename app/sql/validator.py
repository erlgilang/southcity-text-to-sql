import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, SqlglotError

from app.domain.policy import load_policy

FORBIDDEN_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Merge,
    exp.Command,
    exp.Copy,
    exp.Into,
    exp.Lock,
)

# sqlglot models these as functions, but they are plain SQL syntax
SYNTAX_NODES = (exp.Cast, exp.Case, exp.If, exp.Extract, exp.Exists, exp.And, exp.Or)

# The server runs on UTC, but "today" must be the Asia/Jakarta date from the prompt
CLOCK_FUNCTIONS = frozenset(
    {
        "now",
        "current_date",
        "current_time",
        "current_timestamp",
        "localtime",
        "localtimestamp",
        "clock_timestamp",
        "statement_timestamp",
        "transaction_timestamp",
        "timeofday",
    }
)

# Names are the ones sqlglot reports, which differ from Postgres for some functions:
# string_agg=group_concat, bool_and/or=logical_and/or, position/strpos=str_position,
# date_trunc=timestamp_trunc, to_date=str_to_date, to_char=time_to_str.
# ltrim/rtrim map to trim, substr to substring, char_length to length, ceiling to ceil.
ALLOWED_FUNCTIONS = frozenset(
    {
        # aggregates
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "group_concat",
        "logical_and",
        "logical_or",
        "stddev",
        "variance",
        "percentile_cont",
        "percentile_disc",
        # window
        "row_number",
        "rank",
        "dense_rank",
        "ntile",
        "lag",
        "lead",
        "first_value",
        "last_value",
        "nth_value",
        "percent_rank",
        "cume_dist",
        # numbers
        "abs",
        "round",
        "ceil",
        "floor",
        "trunc",
        "power",
        "sqrt",
        "sign",
        "greatest",
        "least",
        # null handling
        "coalesce",
        "nullif",
        # text
        "lower",
        "upper",
        "initcap",
        "trim",
        "length",
        "substring",
        "left",
        "right",
        "replace",
        "concat",
        "concat_ws",
        "str_position",
        "split_part",
        "reverse",
        # dates and conversion
        "timestamp_trunc",
        "make_date",
        "str_to_date",
        "time_to_str",
        "to_number",
    }
)


class SqlRejected(Exception):
    """Raised when a query is refused. retryable tells the caller if the model can fix it."""

    def __init__(self, message: str, *, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


def validate_sql(sql: str, role: str) -> exp.Query:
    """Return the parsed query if it is one safe SELECT for this role, otherwise raise SqlRejected.

    Security problems (writes, blocked tables, hidden columns) are never retryable.
    Problems the model can fix (syntax, unknown table, function outside the allowlist) are.
    """
    policy = load_policy()
    role_policy = policy.for_role(role)

    statement = _parse_single_statement(sql)
    if not isinstance(statement, exp.Query):
        raise SqlRejected("Only a SELECT statement is allowed.", retryable=False)
    if statement.find(*FORBIDDEN_NODES):
        raise SqlRejected(
            "Writes, DDL and locking clauses are not allowed. Use read-only SELECT.",
            retryable=False,
        )

    real_tables = policy.columns.keys() | policy.blocked_tables
    cte_names = {cte.alias.lower() for cte in statement.find_all(exp.CTE)}
    if cte_names & real_tables:
        raise SqlRejected("A CTE must not reuse the name of a real table.", retryable=False)

    unknown_tables = []
    for table in statement.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            continue  # a function used as a table, checked with the other functions
        name = table.name.lower()
        if table.db and table.db.lower() != "public":
            raise SqlRejected("Only tables in the public schema are allowed.", retryable=False)
        if name in cte_names:
            continue
        if name in policy.blocked_tables or (name in real_tables - role_policy.tables):
            raise SqlRejected(f"Table {name} is not accessible for this role.", retryable=False)
        if name not in role_policy.tables:
            unknown_tables.append(name)

    for column in statement.find_all(exp.Column):
        if column.name.lower() in role_policy.hidden_columns:
            raise SqlRejected(
                f"Column {column.name.lower()} is not accessible for this role.", retryable=False
            )

    if unknown_tables:
        raise SqlRejected(
            f"Table {unknown_tables[0]} does not exist in the schema. "
            "Use only the tables listed in <schema>.",
            retryable=True,
        )

    for function in statement.find_all(exp.Func):
        if isinstance(function, SYNTAX_NODES):
            continue
        name = _function_name(function)
        if name in CLOCK_FUNCTIONS:
            raise SqlRejected(
                "Server clock functions (now, current_date, current_timestamp) are not allowed "
                "because the server clock is not Asia/Jakarta. "
                "Use the literal date from <today> instead.",
                retryable=True,
            )
        if name not in ALLOWED_FUNCTIONS:
            raise SqlRejected(
                f"Function {name} is not allowed. "
                "Use standard aggregate, window, math, text and date functions.",
                retryable=True,
            )

    return statement


def _parse_single_statement(sql: str) -> exp.Expression:
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except SqlglotError as error:
        detail = error.errors[0]["description"] if isinstance(error, ParseError) else str(error)
        raise SqlRejected(f"SQL syntax error: {detail}", retryable=True) from error
    if not statements:
        raise SqlRejected("The query is empty. Write exactly one SELECT statement.", retryable=True)
    if len(statements) > 1:
        raise SqlRejected("Only one statement is allowed.", retryable=False)
    return statements[0]


def _function_name(function: exp.Func) -> str:
    if isinstance(function, exp.Anonymous):
        return function.name.lower()
    return function.sql_name().lower()
