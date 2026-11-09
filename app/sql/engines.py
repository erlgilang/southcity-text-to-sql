from functools import cache

from sqlalchemy import Engine, create_engine

from app.config import get_settings


@cache
def readonly_engine() -> Engine:
    """Engine for LLM-generated queries. Its role can read the business tables only."""
    return _build(get_settings().database_url.get_secret_value())


@cache
def auth_engine() -> Engine:
    """Engine for the user list and session lookup. Its role can read system_users only."""
    return _build(get_settings().auth_database_url.get_secret_value())


def _build(url: str) -> Engine:
    # Small pools: the Supabase session pooler limits clients per project
    return create_engine(url, pool_size=3, max_overflow=2, pool_pre_ping=True)
