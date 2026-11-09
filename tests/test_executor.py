"""Runs against the real Supabase database with the app_readonly and app_auth roles."""

import pytest
from sqlalchemy.exc import ProgrammingError

from app.sql.executor import ROW_LIMIT, SqlExecutionError, execute
from app.sql.rbac import apply_rbac
from app.sql.users import UnknownUserError, get_user, list_users
from app.sql.validator import validate_sql

pytestmark = pytest.mark.db

BAMBANG = 101


def run_rewritten(sql: str, role: str, agent_id: int | None = None):
    statement = apply_rbac(validate_sql(sql, role), role, agent_id)
    return execute(statement.sql(dialect="postgres"))


def test_returns_columns_and_rows():
    result = execute("SELECT unitnumber, floor FROM units WHERE unitnumber = 'A-1205'")
    assert result.columns == ["unitnumber", "floor"]
    assert result.rows == [("A-1205", 12)]
    assert result.truncated is False


def test_percent_and_colon_in_literals_are_not_interpreted():
    assert execute("SELECT count(*) FROM units WHERE unitnumber LIKE 'A-%'").rows == [(5,)]
    assert execute("SELECT 'note :abc 100%'").rows == [("note :abc 100%",)]


def test_rows_are_capped_and_marked_truncated():
    result = execute("SELECT a.unitid FROM units a, units b, units c")
    assert len(result.rows) == ROW_LIMIT
    assert result.truncated is True


def test_unknown_column_is_a_retryable_error():
    with pytest.raises(SqlExecutionError, match="phone"):
        execute("SELECT phone FROM sales_contracts")


def test_division_by_zero_is_a_retryable_error():
    with pytest.raises(SqlExecutionError, match="division by zero"):
        execute("SELECT 1 / (floor - floor) FROM units")


def test_statement_timeout_is_a_retryable_error():
    with pytest.raises(SqlExecutionError, match="too long"):
        execute("SELECT pg_sleep(15)")


def test_permission_error_is_not_hidden():
    with pytest.raises(ProgrammingError, match="permission denied"):
        execute("SELECT * FROM system_users")


# The same row counts as tests/test_rbac.py, now on real Postgres.
@pytest.mark.parametrize(
    ("table", "sales_rows", "finance_rows"),
    [
        ("units", 12, 12),
        ("sales_contracts", 2, 6),
        ("payment_schedules", 5, 16),
        ("payments_received", 4, 11),
        ("late_fee_penalties", 1, 5),
    ],
)
def test_rewritten_row_isolation_on_postgres(table, sales_rows, finance_rows):
    sql = f"SELECT COUNT(*) FROM {table}"
    assert run_rewritten(sql, "Sales", BAMBANG).rows == [(sales_rows,)]
    assert run_rewritten(sql, "Finance").rows == [(finance_rows,)]


def test_rewritten_select_star_hides_columns_on_postgres():
    result = run_rewritten("SELECT * FROM sales_contracts", "Sales", BAMBANG)
    assert "customernik" not in result.columns
    assert "customername" in result.columns
    assert len(result.rows) == 2


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        (
            "SELECT DISTINCT c.customername FROM sales_contracts c "
            "JOIN payment_schedules p ON p.contractid = c.contractid ORDER BY 1",
            [("Budi Santoso",), ("Robert Tan",)],
        ),
        (
            "WITH s AS (SELECT contractid FROM payment_schedules) SELECT COUNT(*) FROM s",
            [(5,)],
        ),
        (
            "SELECT COUNT(*) FROM sales_contracts a JOIN sales_contracts b "
            "ON a.contractid = b.contractid",
            [(2,)],
        ),
        (
            "SELECT customername FROM sales_contracts c WHERE "
            "(SELECT COUNT(*) FROM payment_schedules p WHERE p.contractid = c.contractid) > 2",
            [("Budi Santoso",)],
        ),
        ('SELECT COUNT(*) FROM "Sales_Contracts"', [(2,)]),
        ("SELECT COUNT(*) FROM public.sales_contracts", [(2,)]),
        ("SELECT sales_contracts.customername FROM sales_contracts ORDER BY 1", None),
    ],
)
def test_rewritten_queries_run_on_postgres(sql, expected):
    result = run_rewritten(sql, "Sales", BAMBANG)
    if expected is not None:
        assert result.rows == expected
    else:
        assert len(result.rows) == 2


def test_rewritten_outstanding_principal_matches_by_hand():
    sql = (
        "SELECT c.customername, s.billed - COALESCE(p.paid, 0) AS outstanding "
        "FROM sales_contracts c "
        "JOIN (SELECT contractid, SUM(billingamount) AS billed FROM payment_schedules "
        "GROUP BY contractid) s ON s.contractid = c.contractid "
        "LEFT JOIN (SELECT contractid, SUM(paidamount) AS paid FROM payments_received "
        "GROUP BY contractid) p ON p.contractid = c.contractid "
        "WHERE c.customername = 'Budi Santoso'"
    )
    result = run_rewritten(sql, "Sales", BAMBANG)
    assert [(name, int(amount)) for name, amount in result.rows] == [("Budi Santoso", 65_000_000)]


def test_list_users_returns_active_users_in_order():
    assert [u.username for u in list_users()] == [
        "sales_bambang",
        "sales_dewi",
        "sales_reza",
        "finance_hendra",
        "auditor_maya",
    ]


def test_get_user_returns_role_and_agent():
    user = get_user("sales_bambang")
    assert (user.role, user.agent_id, user.full_name) == ("Sales", 101, "Bambang Pamungkas")
    assert get_user("finance_hendra").agent_id is None


def test_get_unknown_user_raises():
    with pytest.raises(UnknownUserError):
        get_user("root")
