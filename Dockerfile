FROM python:3.12.13-slim-bookworm

# HOME must be writable by the non-root user because Streamlit writes its own files there.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/appuser \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Dependencies first so code changes do not reinstall them.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Streamlit reads .streamlit/config.toml from the working directory.
COPY app ./app
COPY ui ./ui
# The API builds the schema text for the prompts from this DDL at startup.
COPY db/schema_pg.sql ./db/schema_pg.sql
COPY .streamlit ./.streamlit

RUN useradd --create-home --uid 10001 appuser
USER appuser

# The command is set per service in docker-compose.yml (one image runs both).
