from fastapi import FastAPI

from app.api.app import build_app
from app.config import get_settings
from app.graph.builder import build_graph
from app.observability import configure_logging
from app.sessions import SessionStore
from app.sql import users


def create_app() -> FastAPI:
    """Entry point for uvicorn --factory. Reads the settings from the environment."""
    settings = get_settings()
    configure_logging(settings.log_level)
    return build_app(build_graph(), SessionStore(), users, settings.app_env)
