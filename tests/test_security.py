"""The three security tests from the SouthCity README, at SQL level.

The LLM is not involved here. Each test feeds the SQL a model could produce when it is
tricked, and checks that the code refuses it or returns nothing the user may not see.
"""

import pytest

from app.sql.validator import SqlRejected, validate_sql
from tests.support import run_as, values

ALL_ROLES = ["Sales", "Finance", "Auditor", "SuperAdmin"]
BAMBANG = 101
DEWI = 102

SITI_OUTSTANDING = """
SELECT c.customername, s.total_billed - COALESCE(p.total_paid, 0) AS outstanding
FROM sales_contracts c
JOIN (SELECT contractid, SUM(billingamount) AS total_billed
      FROM payment_schedules GROUP BY contractid) s ON s.contractid = c.contractid
LEFT JOIN (SELECT contractid, SUM(paidamount) AS total_paid
           FROM payments_received GROUP BY contractid) p ON p.contractid = c.contractid
WHERE c.customername = 'Siti Rahma'
"""


@pytest.mark.parametrize("role", ALL_ROLES)
def test_sql_injection_with_drop_is_refused_and_nothing_runs(erp_db, role):
    sql = (
        "SELECT customername FROM sales_contracts "
        "WHERE EXTRACT(MONTH FROM bookingdate) = 1; DROP TABLE Units; --"
    )
    with pytest.raises(SqlRejected) as rejected:
        run_as(erp_db, sql, role, BAMBANG)
    assert rejected.value.retryable is False
    assert values(erp_db, "SELECT COUNT(*) FROM units", "Finance") == [12]


@pytest.mark.parametrize("role", ALL_ROLES)
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM system_users",
        "SELECT username, role, password_hash FROM system_users",
        "SELECT * FROM public.system_users",
        "SELECT table_name FROM information_schema.tables",
        "SELECT * FROM pg_catalog.pg_roles",
    ],
)
def test_role_escalation_cannot_reach_user_table(erp_db, role, sql):
    with pytest.raises(SqlRejected) as rejected:
        run_as(erp_db, sql, role, BAMBANG)
    assert rejected.value.retryable is False


def test_role_is_never_taken_from_the_query():
    # An unknown role means a bug or a forged session, so it fails instead of defaulting
    with pytest.raises(ValueError, match="Unknown role"):
        validate_sql("SELECT * FROM units", "root")


def test_owner_can_read_the_customer_balance(erp_db):
    _, rows = run_as(erp_db, SITI_OUTSTANDING, "Sales", DEWI)
    assert rows == [("Siti Rahma", 1454000000)]


def test_finance_can_read_the_customer_balance(erp_db):
    _, rows = run_as(erp_db, SITI_OUTSTANDING, "Finance")
    assert rows == [("Siti Rahma", 1454000000)]


def test_other_sales_agent_gets_no_rows_for_the_customer(erp_db):
    _, rows = run_as(erp_db, SITI_OUTSTANDING, "Sales", BAMBANG)
    assert rows == []


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM sales_contracts WHERE customername = 'Siti Rahma'",
        "SELECT COUNT(*) FROM sales_contracts WHERE salesagentid = 102",
        "SELECT COUNT(*) FROM payment_schedules WHERE contractid = 102",
        "SELECT COUNT(*) FROM payments_received WHERE contractid = 102",
        "SELECT COUNT(*) FROM late_fee_penalties WHERE contractid = 104",
        'SELECT COUNT(*) FROM "Sales_Contracts" WHERE contractid = 102',
        "SELECT COUNT(*) FROM sales_contracts WHERE contractid IN "
        "(SELECT contractid FROM payment_schedules WHERE contractid = 102)",
    ],
)
def test_sales_agent_cannot_count_rows_of_another_agent(erp_db, sql):
    assert values(erp_db, sql, "Sales", BAMBANG) == [0]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT customernik FROM sales_contracts",
        "SELECT paymentmethod, bankreferenceno FROM payments_received",
        "SELECT customername FROM sales_contracts WHERE customernik LIKE '3171%'",
    ],
)
def test_sales_agent_cannot_use_hidden_columns_even_on_own_data(erp_db, sql):
    with pytest.raises(SqlRejected) as rejected:
        run_as(erp_db, sql, "Sales", BAMBANG)
    assert rejected.value.retryable is False
