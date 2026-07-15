-- Test-only credentials for an ephemeral Testcontainers database.
-- This role is not used by Compose or any deployed environment.
CREATE ROLE ti_phase2_read
    LOGIN
    PASSWORD 'phase2-ephemeral-readonly'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION;

ALTER ROLE ti_phase2_read SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE ti_phase2_fixture TO ti_phase2_read;
REVOKE TEMPORARY ON DATABASE ti_phase2_fixture FROM PUBLIC;
REVOKE TEMPORARY ON DATABASE ti_phase2_fixture FROM ti_phase2_read;
GRANT USAGE ON SCHEMA public TO ti_phase2_read;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM ti_phase2_read;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM ti_phase2_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ti_phase2_read;
