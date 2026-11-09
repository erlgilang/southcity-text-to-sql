import pytest

from app.sql.rbac import apply_rbac
from app.sql.validator import validate_sql
from tests.support import run_as, values

# Agent 101 (sales_bambang) owns contracts 101 (Budi Santoso) and 103 (Robert Tan).
BAMBANG = 101
DEWI = 102

ROW_COUNTS = [
    # table, rows for Sales agent 101, rows for Finance
    ("units", 12, 12),
    ("sales_contracts", 2, 6),
    ("payment_schedules", 5, 16),
    ("payments_received", 4, 11),
    ("late_fee_penalties", 1, 5),
]


@pytest.mark.parametrize(("table", "sales_rows", "finance_rows"), ROW_COUNTS)
def test_row_isolation_by_role(erp_db, table, sales_rows, finance_rows):
    sql = f"SELECT COUNT(*) FROM {table}"
    assert values(erp_db, sql, "Sales", BAMBANG) == [sales_rows]
    assert values(erp_db, sql, "Finance") == [finance_rows]


@pytest.mark.parametrize("role", ["Auditor", "SuperAdmin"])
def test_other_full_access_roles_see_everything(erp_db, role):
    assert values(erp_db, "SELECT COUNT(*) FROM sales_contracts", role) == [6]


def test_agent_id_comes_from_the_argument(erp_db):
    sql = "SELECT customername FROM sales_contracts ORDER BY customername"
    assert values(erp_db, sql, "Sales", BAMBANG) == ["Budi Santoso", "Robert Tan"]
    assert values(erp_db, sql, "Sales", DEWI) == ["Ahmad Farhan", "Siti Rahma"]


def test_select_star_hides_columns_for_sales(erp_db):
    contract_columns, _ = run_as(erp_db, "SELECT * FROM sales_contracts", "Sales", BAMBANG)
    payment_columns, _ = run_as(erp_db, "SELECT * FROM payments_received", "Sales", BAMBANG)
    assert "customername" in contract_columns
    assert "customernik" not in contract_columns
    assert "receiptnumber" in payment_columns
    assert not {"paymentmethod", "bankreferenceno"} & set(payment_columns)


def test_select_star_keeps_all_columns_for_finance(erp_db):
    columns, _ = run_as(erp_db, "SELECT * FROM sales_contracts", "Finance")
    assert "customernik" in columns


def test_alias_and_join_still_work(erp_db):
    sql = (
        "SELECT DISTINCT c.customername FROM sales_contracts c "
        "JOIN payment_schedules p ON p.contractid = c.contractid ORDER BY 1"
    )
    assert values(erp_db, sql, "Sales", BAMBANG) == ["Budi Santoso", "Robert Tan"]


def test_unaliased_table_name_still_resolves(erp_db):
    sql = "SELECT sales_contracts.customername FROM sales_contracts ORDER BY 1"
    assert values(erp_db, sql, "Sales", BAMBANG) == ["Budi Santoso", "Robert Tan"]


def test_schema_qualified_table_is_filtered(erp_db):
    assert values(erp_db, "SELECT COUNT(*) FROM public.sales_contracts", "Sales", BAMBANG) == [2]


def test_cte_over_restricted_table_is_filtered(erp_db):
    sql = "WITH s AS (SELECT contractid FROM payment_schedules) SELECT COUNT(*) FROM s"
    assert values(erp_db, sql, "Sales", BAMBANG) == [5]


def test_subquery_in_where_is_filtered(erp_db):
    sql = (
        "SELECT customername FROM sales_contracts "
        "WHERE contractid IN (SELECT contractid FROM late_fee_penalties)"
    )
    assert values(erp_db, sql, "Sales", BAMBANG) == ["Budi Santoso"]


def test_correlated_subquery_is_filtered(erp_db):
    sql = (
        "SELECT customername FROM sales_contracts c WHERE "
        "(SELECT COUNT(*) FROM payment_schedules p WHERE p.contractid = c.contractid) > 2"
    )
    assert values(erp_db, sql, "Sales", BAMBANG) == ["Budi Santoso"]


def test_self_join_is_filtered_on_both_sides(erp_db):
    sql = (
        "SELECT COUNT(*) FROM sales_contracts a "
        "JOIN sales_contracts b ON a.contractid = b.contractid"
    )
    assert values(erp_db, sql, "Sales", BAMBANG) == [2]


def test_union_is_filtered_on_both_sides(erp_db):
    sql = "SELECT contractid FROM sales_contracts UNION SELECT contractid FROM payment_schedules"
    assert sorted(values(erp_db, sql, "Sales", BAMBANG)) == [101, 103]


def test_user_filter_cannot_widen_access(erp_db):
    sql = "SELECT COUNT(*) FROM sales_contracts WHERE salesagentid = 102 OR 1 = 1"
    assert values(erp_db, sql, "Sales", BAMBANG) == [2]


def test_finance_query_is_not_rewritten(erp_db):
    statement = validate_sql(
        "SELECT * FROM sales_contracts c JOIN units u ON u.unitid = c.unitid", "Finance"
    )
    assert apply_rbac(statement, "Finance", None).sql() == statement.sql()


def test_input_tree_is_not_modified():
    statement = validate_sql("SELECT * FROM sales_contracts", "Sales")
    before = statement.sql()
    apply_rbac(statement, "Sales", BAMBANG)
    assert statement.sql() == before


def test_sales_without_agent_id_is_an_error():
    statement = validate_sql("SELECT * FROM sales_contracts", "Sales")
    with pytest.raises(ValueError, match="agent"):
        apply_rbac(statement, "Sales", None)
