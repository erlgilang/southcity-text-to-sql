# SouthCity Text-to-SQL

A chat assistant for a property ERP. A user asks a question in Indonesian. The system turns it into one read-only SQL SELECT, runs it on Postgres, and answers in Indonesian with Rupiah amounts and a supporting table.

Live demo: https://southcity.gilang.cloud

The project is the take-home assessment for the AI & Automation Engineer role at SouthCity. The original brief is in [SOUTHCITY_BRIEF.md](SOUTHCITY_BRIEF.md).

## What the application does

- Classifies each message with an LLM as a data question, small talk, an ambiguous question that needs clarification, or a request to refuse.
- Generates one SELECT for data questions, checks it with an AST parser (`sqlglot`), applies row and column rules for the user's role, and runs it with a read-only database account.
- Sends database errors and fixable validation errors back to the LLM, up to two retries.
- Answers in Indonesian. Python formats the amounts (for example `Rp 1.554.000.000`) and builds the table. The LLM does not compute numbers.
- Supports five users from the `System_Users` table through a dropdown. Sales users see only their own contracts. Finance, Auditor and SuperAdmin see all transaction tables.

[ARCHITECTURE.md](ARCHITECTURE.md) describes the design, the security layers and the known limits. [ASSESSMENT.md](ASSESSMENT.md) maps each rule of the brief to the code and tests.

## Project layout

- `app/`: FastAPI backend, LangGraph flow, prompts, SQL validator and RBAC rewrite.
- `ui/`: Streamlit chat interface. It talks to the API over HTTP only.
- `db/`: Postgres schema, seed data and database roles.
- `tests/`: fast unit tests and live tests that use the real model and database.

## Running locally

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), a Postgres database and an Anthropic API key.

The database is created from `db/schema_pg.sql`, `db/seed_pg.sql` and `db/roles_pg.sql`, in that order. The roles script contains placeholder passwords that are replaced before use.

Configuration is read from environment variables. For local runs they can be placed in a `.env` file, and `.env.example` lists the names.

```
uv sync
uv run uvicorn app.api.main:create_app --factory --reload --port 8000
uv run streamlit run ui/streamlit_app.py
```

The Streamlit address is printed on start (port 8501 by default). The UI reaches the API at the address in `API_BASE_URL`.

With `APP_ENV=development` the API serves `/docs` and writes full tracebacks to its log. The default is `production`, where both are off.

## Running with Docker

One image runs both services, `api` and `ui`, as defined in `docker-compose.yml`.

```
docker compose up --build
```

Compose reads the variables from the environment or from a `.env` file next to it, and nothing from `.env` is copied into the image. The compose file publishes no ports. The `api` service is reachable only inside the compose network, and the `ui` service calls it at `http://api:8000`. Compose refuses to start when a required secret is missing.

Sessions are kept in process memory, so the API runs as a single process.

## Environment variables

Values are set in the environment of each deployment and are not stored in the repository.

| Name | Purpose | Required | Used by |
| --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes | api |
| `DATABASE_URL` | Connection string for the `app_readonly` role, used for generated queries | Yes | api |
| `AUTH_DATABASE_URL` | Connection string for the `app_auth` role, used only to list users | Yes | api |
| `LLM_MODEL` | Model name. Default `claude-sonnet-4-6` | No | api |
| `LOG_LEVEL` | Log level. Default `INFO` | No | api |
| `APP_ENV` | `development` enables `/docs` and tracebacks in the log. Default `production` | No | api |
| `API_BASE_URL` | Address of the API. In compose it defaults to `http://api:8000` | Yes for the UI | ui |

## Tests and lint

```
uv run pytest                    # fast tests, no network
uv run pytest -m "llm or db"     # live tests with the real model and database
uv run ruff check . && uv run ruff format .
```

`requirements.txt` is exported from `uv.lock` with `uv export --no-dev --no-hashes -o requirements.txt`. A test compares the two files.
