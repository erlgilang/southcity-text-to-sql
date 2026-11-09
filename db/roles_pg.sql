-- Database roles for the app. Run after schema_pg.sql and seed_pg.sql, as the postgres owner.
-- Re-run the GRANT and REVOKE parts after every schema_pg.sql run, because DROP TABLE removes grants.
-- Replace both passwords before running. Never commit real passwords.

-- Used by the SQL executor for LLM-generated queries. It cannot see System_Users, so even a
-- validator bug cannot leak user data through chat.
CREATE ROLE app_readonly LOGIN PASSWORD 'CHANGE_ME_READONLY';
ALTER ROLE app_readonly SET default_transaction_read_only = on;
ALTER ROLE app_readonly SET statement_timeout = '10s';

GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON Units, Sales_Contracts, Payment_Schedules, Payments_Received, Late_Fee_Penalties
    TO app_readonly;

-- Used only by the API to list users for the dropdown and to resolve the session user.
CREATE ROLE app_auth LOGIN PASSWORD 'CHANGE_ME_AUTH';
ALTER ROLE app_auth SET default_transaction_read_only = on;
ALTER ROLE app_auth SET statement_timeout = '5s';

GRANT USAGE ON SCHEMA public TO app_auth;
GRANT SELECT ON System_Users TO app_auth;

-- Supabase only: new tables in public are open to the Data API roles by default.
-- Without this, anyone holding the project's anon key could read or write these tables.
REVOKE ALL ON Units, Sales_Contracts, Payment_Schedules, Payments_Received, Late_Fee_Penalties,
    System_Users FROM anon, authenticated;
