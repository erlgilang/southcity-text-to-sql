import pytest

from app.domain.policy import load_policy
from app.domain.schema_text import GLOSSARY_FILE, build_schema_text, column_types

HIDDEN_FOR_SALES = ["customernik", "paymentmethod", "bankreferenceno"]


def test_sales_schema_leaves_out_hidden_columns_and_user_table():
    schema = build_schema_text("Sales")
    for name in [*HIDDEN_FOR_SALES, "system_users"]:
        assert name not in schema
    assert "customername" in schema
    assert "receiptnumber" in schema


@pytest.mark.parametrize("role", ["Finance", "Auditor", "SuperAdmin"])
def test_full_access_schema_has_every_business_column(role):
    schema = build_schema_text(role)
    for name in HIDDEN_FOR_SALES:
        assert name in schema
    assert "system_users" not in schema


def test_schema_lines_carry_column_types():
    schema = build_schema_text("Finance")
    assert "billingamount DECIMAL(15, 2)" in schema
    assert "duedate DATE" in schema
    assert "unitnumber VARCHAR(20)" in schema


def test_policy_columns_match_the_ddl():
    # Catches drift between rbac_policy.yaml and db/schema_pg.sql
    types = column_types()
    for table, columns in load_policy().columns.items():
        assert list(types[table]) == columns


def test_glossary_does_not_mention_hidden_columns_or_user_table():
    glossary = GLOSSARY_FILE.read_text(encoding="utf-8").lower()
    for name in [*HIDDEN_FOR_SALES, "system_users", "password"]:
        assert name not in glossary
