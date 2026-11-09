import pytest
from sqlglot import exp

from app.sql.validator import SqlRejected, validate_sql

# SELECT * is valid here: rbac.py limits the columns, the validator does not.
VALID = [
    "SELECT COUNT(*) FROM units WHERE status = 'Vacant' AND tower = 'Tower A'",
    "SELECT * FROM units",
    "SELECT * FROM public.units",
    "SELECT c.customername, SUM(s.billingamount) FROM sales_contracts c "
    "JOIN payment_schedules s ON s.contractid = c.contractid GROUP BY c.customername",
    "WITH due AS (SELECT contractid FROM payment_schedules WHERE duedate < DATE '2026-11-08') "
    "SELECT customername FROM sales_contracts WHERE contractid IN (SELECT contractid FROM due)",
    "SELECT tower FROM units UNION SELECT tower FROM units",
    "SELECT COALESCE(SUM(paidamount), 0) FROM payments_received",
    "SELECT DATE_TRUNC('month', bookingdate), COUNT(*) FROM sales_contracts GROUP BY 1",
    "SELECT * FROM units WHERE floor BETWEEN 5 AND 15 OR unittype IN ('Studio', '2BR')",
    "SELECT * FROM units WHERE unitnumber LIKE 'A-%' AND NOT status = 'Sold'",
    "SELECT CASE WHEN status = 'Sold' THEN 1 ELSE 0 END AS sold, floor::numeric FROM units",
    "SELECT contractid, SUM(billingamount) OVER (PARTITION BY contractid ORDER BY duedate) "
    "FROM payment_schedules",
    "SELECT contractid FROM payment_schedules GROUP BY contractid HAVING SUM(billingamount) > 1",
    "SELECT customername FROM sales_contracts c WHERE EXISTS "
    "(SELECT 1 FROM payment_schedules p WHERE p.contractid = c.contractid AND p.status = 'Unpaid')",
    "SELECT duedate + INTERVAL '30 days', DATE '2026-11-08' - duedate "
    "FROM payment_schedules LIMIT 5",
]

# Cannot be fixed by rewriting the query, so the caller refuses without retrying.
SECURITY = [
    "SELECT customername FROM sales_contracts; DROP TABLE units; --",
    "SELECT 1 /* ; */; DROP TABLE units",
    "SELECT 1; SELECT 2",
    "DROP TABLE units",
    "dRoP tAbLe units",
    "DELETE FROM units",
    "UPDATE units SET status = 'Sold'",
    "INSERT INTO units (unitid) VALUES (1)",
    "ALTER TABLE units ADD COLUMN x INT",
    "TRUNCATE TABLE units",
    "CREATE TABLE x (a INT)",
    "COPY units TO '/tmp/x'",
    "SET ROLE postgres",
    "SELECT * INTO backup FROM units",
    "SELECT * FROM units FOR UPDATE",
    "WITH x AS (INSERT INTO units (unitid) VALUES (99) RETURNING unitid) SELECT * FROM x",
    "SELECT * FROM system_users",
    "SELECT * FROM public.system_users",
    'SELECT * FROM "System_Users"',
    "SELECT * FROM units u JOIN system_users s ON s.userid = u.unitid",
    "SELECT (SELECT COUNT(*) FROM system_users)",
    "WITH units AS (SELECT 1 AS unitid) SELECT * FROM units",
    "SELECT * FROM pg_catalog.pg_tables",
]

HIDDEN_FOR_SALES = [
    "SELECT customernik FROM sales_contracts",
    "SELECT c.customernik FROM sales_contracts c",
    "SELECT customername FROM sales_contracts WHERE customernik = '3171012345670001'",
    "SELECT COUNT(customernik) FROM sales_contracts",
    "SELECT paymentmethod FROM payments_received",
    "SELECT bankreferenceno FROM payments_received",
]

# The model can fix these, so the caller retries with the message.
RETRYABLE = [
    ("SELEC * FROM units", "syntax"),
    ("", "empty"),
    ("SELECT * FROM customers", "customers"),
    ("SELECT pg_sleep(5)", "pg_sleep"),
    ("SELECT pg_read_file('/etc/passwd')", "pg_read_file"),
    ("SELECT version()", "version"),
    ("SELECT CURRENT_DATE", "current_date"),
    ("SELECT NOW()", "now"),
    ("SELECT repeat('a', 1000000)", "repeat"),
    ("SELECT * FROM units WHERE unitnumber ~ 'A'", "regexp_like"),
    ("SELECT * FROM generate_series(1, 3) AS g", "generate_series"),
]


@pytest.mark.parametrize("role", ["Sales", "Finance"])
@pytest.mark.parametrize("sql", VALID)
def test_valid_select_passes(sql, role):
    assert isinstance(validate_sql(sql, role), exp.Query)


@pytest.mark.parametrize("sql", SECURITY)
def test_security_violation_is_not_retryable(sql):
    with pytest.raises(SqlRejected) as rejected:
        validate_sql(sql, "Finance")
    assert rejected.value.retryable is False


@pytest.mark.parametrize("sql", HIDDEN_FOR_SALES)
def test_sales_cannot_reference_hidden_column(sql):
    with pytest.raises(SqlRejected) as rejected:
        validate_sql(sql, "Sales")
    assert rejected.value.retryable is False


@pytest.mark.parametrize("sql", HIDDEN_FOR_SALES)
def test_finance_can_reference_hidden_column(sql):
    validate_sql(sql, "Finance")


@pytest.mark.parametrize(("sql", "word"), RETRYABLE)
def test_fixable_problem_is_retryable_with_clear_message(sql, word):
    with pytest.raises(SqlRejected) as rejected:
        validate_sql(sql, "Finance")
    assert rejected.value.retryable is True
    assert word in str(rejected.value).lower()
