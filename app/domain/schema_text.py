from functools import cache
from pathlib import Path

import sqlglot
from sqlglot import exp

from app.domain.policy import load_policy

ROOT = Path(__file__).resolve().parents[2]
DDL_FILE = ROOT / "db" / "schema_pg.sql"
GLOSSARY_FILE = Path(__file__).with_name("glossary.md")


@cache
def column_types() -> dict[str, dict[str, str]]:
    """Table name to {column name: type}, read from the Postgres DDL."""
    types = {}
    for statement in sqlglot.parse(DDL_FILE.read_text(encoding="utf-8"), read="postgres"):
        if isinstance(statement, exp.Create) and statement.kind == "TABLE":
            schema = statement.this
            types[schema.this.name.lower()] = {
                column.name.lower(): column.args["kind"].sql(dialect="postgres")
                for column in schema.expressions
                if isinstance(column, exp.ColumnDef)
            }
    return types


def build_schema_text(role: str) -> str:
    """One line per table the role may query, with only the columns the role may see."""
    policy = load_policy()
    role_policy = policy.for_role(role)
    types = column_types()
    lines = []
    for table, columns in policy.columns.items():
        if table not in role_policy.tables:
            continue
        visible = [c for c in columns if c not in role_policy.hidden_columns]
        lines.append(f"{table}({', '.join(f'{c} {types[table][c]}' for c in visible)})")
    return "\n".join(lines)


def load_glossary() -> str:
    return GLOSSARY_FILE.read_text(encoding="utf-8")
