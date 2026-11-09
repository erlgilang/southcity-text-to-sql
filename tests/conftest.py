import sqlite3
from pathlib import Path

import pytest

from tests import timing

DB_DIR = Path(__file__).resolve().parent.parent / "db"


def pytest_terminal_summary(terminalreporter):
    lines = timing.summary_lines()
    if lines:
        terminalreporter.section("answer times per kind of question")
        for line in lines:
            terminalreporter.write_line(line)


@pytest.fixture(scope="session")
def erp_db():
    """In-memory SQLite loaded from the Postgres schema and seed.

    It checks which rows a rewritten query returns. It does not check Postgres behavior.
    """
    db = sqlite3.connect(":memory:")
    for name in ("schema_pg.sql", "seed_pg.sql"):
        db.executescript((DB_DIR / name).read_text(encoding="utf-8"))
    yield db
    db.close()
