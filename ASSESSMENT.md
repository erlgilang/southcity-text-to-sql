# Assessment map

This document lists each rule of [SOUTHCITY_BRIEF.md](SOUTHCITY_BRIEF.md) with the code and tests that meet it. Test names refer to files in `tests/`. Tests marked "live" use the real model and database and are selected with `pytest -m "llm or db"`. All other tests run without network access.

## Strict rules

| Rule | Where it is met | Tests |
| --- | --- | --- |
| Orchestrate with LangChain or LangGraph | `app/graph/builder.py` builds a LangGraph `StateGraph`. Nodes in `app/graph/nodes/` use LangChain `ChatAnthropic` (`app/llm/models.py`), message prompts (`app/graph/prompts.py`) and Pydantic structured output (`app/graph/llm_calls.py`, `app/graph/schemas.py`). | `test_graph.py` |
| No regex, keyword or template routing | The intent (`sql_query`, `chitchat`, `clarify`, `refuse`) is returned by the model in `app/graph/nodes/classify.py`. `INTENT_ROUTES` in `builder.py` only maps that value to a node name. | `test_graph.py::test_chitchat_never_touches_sql_or_database`, live `test_thank_you_does_not_run_sql` |
| Dynamic prompting with schema linking | `app/domain/schema_text.py` builds the schema text per role from the DDL and the policy. `classify` returns `relevant_tables`. Date, schema, glossary and history are template values in `app/prompts/*.md`. | `test_schema_text.py`, `test_prompts.py` |
| Query generation with a live LLM | `app/graph/nodes/generate_sql.py` with `app/prompts/generate_sql.md`. | live `test_questions.py` |
| Self-correction loop, at least 2 retries | `MAX_RETRIES = 2` in `builder.py` (3 attempts). Database errors and fixable validator errors go through `retry` to `generate_sql` with the failed SQL and the error. | `test_graph.py::test_database_error_goes_back_to_generate_sql_with_the_error`, `test_gives_up_after_three_attempts_with_fixed_text`, live `test_retry_loop_repairs_a_failed_execution_with_the_real_model` |
| Ambiguous question gets a clarifying question, no invented query | `clarify` intent, `ask_clarification` in `app/graph/nodes/reply.py`. | `test_graph.py::test_clarify_returns_the_question_and_stops`, live `test_ambiguous_question_asks_for_clarification` |
| Data that is not in the schema is reported as missing | Prompt rules in `classify.md`. | live `test_missing_data_is_reported_honestly` |
| Public URL, user switcher | Streamlit dropdown filled from `System_Users` (`ui/streamlit_app.py`, `app/sql/users.py`). Deployment package: `Dockerfile`, `docker-compose.yml`. | `test_ui_client.py`, `test_api.py` |
| Strictly read-only | `app/sql/validator.py` accepts exactly one SELECT and rejects every write node, including inside CTEs and subqueries, and `SELECT INTO`. The database role is read-only too (`db/roles_pg.sql`). | `test_validator.py`, `test_security.py`, `test_db_roles.py` (live) |
| AST parser, no regex or `contains` for SQL security | `sqlglot` with the `postgres` dialect, in `validator.py` and `rbac.py`. | `test_validator.py` |
| RBAC from the user in `System_Users` | `app/sql/rbac.py` rewrites each restricted table to a filtered subquery. Policy is in `app/domain/rbac_policy.yaml`. The agent id comes from the server session (`app/sessions.py`), never from the question. | `test_rbac.py`, `test_graph.py::test_sales_agent_id_comes_from_the_session_not_the_question`, `test_api.py::test_role_in_the_request_body_is_rejected_not_trusted` |
| Sales: own contracts only, no bank mutation data | Row filter by `salesagentid`; columns `bankreferenceno`, `paymentmethod`, `customernik` hidden. | `test_rbac.py`, `test_security.py::test_sales_agent_cannot_use_hidden_columns_even_on_own_data`, live `test_sales_never_sees_national_id_numbers`, `test_each_user_sees_only_their_contracts` |
| Finance: full transaction access | `rbac_policy.yaml` gives Finance, Auditor and SuperAdmin all five business tables with no row filter. | `test_rbac.py::test_other_full_access_roles_see_everything` |

## Sample business questions

The five samples are not hardcoded anywhere. Live tests ask them as plain questions and check the numbers against the database.

| Sample | Live test |
| --- | --- |
| 1. Vacant 2BR units in Tower A with floors | `test_sample_vacant_units_by_floor` |
| 2. Customers with overdue Unpaid or Partially Paid installments | `test_sample_overdue_unpaid_customers` |
| 3. Outstanding Principal for a named customer | `test_sample_outstanding_principal` |
| 4. Net Outstanding Penalty for Installment 24x | `test_sample_net_outstanding_penalty_by_scheme` |
| 5. Sales asks about a penalty of a customer | `test_sample_sales_asks_about_penalty_of_own_customer`, `test_sales_empty_result_is_exactly_the_fixed_sentence` |

Formulas and data rules (separate sums for Outstanding Principal, Net Outstanding Penalty, overdue means `DueDate` before the `<today>` date) are in `app/domain/glossary.md` and are shown to the model. `test_aggregation_across_tables_matches_the_database` checks a multi-table aggregate. `test_rewritten_outstanding_principal_matches_by_hand` checks the rewritten query on Postgres.

## Security tests

| Brief test | How it is handled | Tests |
| --- | --- | --- |
| 1. SQL injection with `DROP TABLE` | The validator rejects multiple statements and DROP. The database role could not run it either. | `test_security.py::test_sql_injection_with_drop_is_refused_and_nothing_runs`, `test_graph.py::test_security_rejection_refuses_without_retry`, live `test_security_sql_injection_is_harmless` |
| 2. Prompt injection, role escalation, read `System_Users` | The role comes from the session. `system_users` is never in a prompt and is blocked in the validator. The reply is fixed text. | `test_security.py::test_role_escalation_cannot_reach_user_table`, `test_role_is_never_taken_from_the_query`, live `test_security_prompt_injection_is_refused` |
| 3. Sales asks for another agent's customer and phone number | Row filter returns nothing for the other agent's customer. A phone number is not in the schema, so the answer says it is not available. | `test_security.py::test_other_sales_agent_gets_no_rows_for_the_customer`, live `test_security_other_agents_customer_is_not_visible`, `test_owner_can_see_the_same_customer` |

Known limit: an aggregate query by a Sales user over another agent's data can return `0` instead of no rows. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Deliverables

| Item | File |
| --- | --- |
| Public repository with LangGraph code | `app/graph/` |
| AST parser module | `app/sql/validator.py`, `app/sql/rbac.py` |
| Local config file | `requirements.txt`, `docker-compose.yml`, `Dockerfile` |
| Live application URL | https://southcity.gilang.cloud (also in [README.md](README.md)) |
| `ARCHITECTURE.md` with flow diagram, retry loop, injection and RBAC strategy | [ARCHITECTURE.md](ARCHITECTURE.md) |
