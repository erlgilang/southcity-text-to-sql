import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import InternalError, ProgrammingError

from app.config import get_settings

pytestmark = pytest.mark.db


@pytest.fixture
def readonly_conn():
    engine = create_engine(get_settings().database_url.get_secret_value())
    with engine.connect() as conn:
        yield conn
    engine.dispose()


@pytest.fixture
def auth_conn():
    engine = create_engine(get_settings().auth_database_url.get_secret_value())
    with engine.connect() as conn:
        yield conn
    engine.dispose()


def test_readonly_reads_units(readonly_conn):
    assert readonly_conn.execute(text("SELECT count(*) FROM units")).scalar_one() == 12


def test_readonly_is_denied_system_users(readonly_conn):
    with pytest.raises(ProgrammingError, match="permission denied"):
        readonly_conn.execute(text("SELECT count(*) FROM system_users"))


INSERT_UNIT = text(
    "INSERT INTO units (unitid, unitnumber, tower, unittype, floor, sga_area, nett_area, status)"
    " VALUES (99, 'X-0000', 'Tower X', 'Studio', 1, 1, 1, 'Vacant')"
)


def test_readonly_insert_is_blocked_by_read_only_transaction(readonly_conn):
    with pytest.raises(InternalError, match="read-only transaction"):
        readonly_conn.execute(INSERT_UNIT)


def test_readonly_insert_is_denied_even_in_read_write_transaction(readonly_conn):
    # A session can switch itself to read-write, so the missing INSERT grant must hold on its own
    readonly_conn.execute(text("SET TRANSACTION READ WRITE"))
    with pytest.raises(ProgrammingError, match="permission denied"):
        readonly_conn.execute(INSERT_UNIT)


def test_auth_is_denied_units(auth_conn):
    with pytest.raises(ProgrammingError, match="permission denied"):
        auth_conn.execute(text("SELECT count(*) FROM units"))


def test_auth_reads_system_users(auth_conn):
    assert auth_conn.execute(text("SELECT count(*) FROM system_users")).scalar_one() == 5
