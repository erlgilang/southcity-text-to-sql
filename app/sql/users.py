from dataclasses import dataclass

from sqlalchemy import text

from app.sql.engines import auth_engine

COLUMNS = "userid, username, fullname, role, assignedagentid"


@dataclass(frozen=True)
class User:
    user_id: int
    username: str
    full_name: str
    role: str
    agent_id: int | None


class UnknownUserError(LookupError):
    pass


def list_users() -> list[User]:
    with auth_engine().connect() as connection:
        rows = connection.execute(
            text(f"SELECT {COLUMNS} FROM system_users WHERE isactive ORDER BY userid")
        )
        return [User(*row) for row in rows]


def get_user(username: str) -> User:
    with auth_engine().connect() as connection:
        row = connection.execute(
            text(f"SELECT {COLUMNS} FROM system_users WHERE isactive AND username = :username"),
            {"username": username},
        ).first()
    if row is None:
        raise UnknownUserError(f"No active user named {username!r}")
    return User(*row)
