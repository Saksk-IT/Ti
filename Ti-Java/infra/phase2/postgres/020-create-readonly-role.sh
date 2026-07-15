#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${TI_JAVA_DB_APP_USER:?TI_JAVA_DB_APP_USER is required}"
: "${TI_JAVA_DB_APP_PASSWORD_FILE:?TI_JAVA_DB_APP_PASSWORD_FILE is required}"

if [ ! -r "$TI_JAVA_DB_APP_PASSWORD_FILE" ]; then
    echo "Phase 2 database application-password secret is unreadable" >&2
    exit 1
fi

app_password=$(tr -d '\r\n' < "$TI_JAVA_DB_APP_PASSWORD_FILE")
if [ -z "$app_password" ]; then
    echo "Phase 2 database application-password secret is blank" >&2
    exit 1
fi
export TI_PHASE2_APP_PASSWORD="$app_password"

psql \
    --set=ON_ERROR_STOP=1 \
    --set=db_name="$POSTGRES_DB" \
    --set=owner_user="$POSTGRES_USER" \
    --set=app_user="$TI_JAVA_DB_APP_USER" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" <<'SQL'
\getenv app_password TI_PHASE2_APP_PASSWORD

SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION',
    :'app_user',
    :'app_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec

ALTER ROLE :"app_user" SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE :"db_name" TO :"app_user";
REVOKE TEMPORARY ON DATABASE :"db_name" FROM PUBLIC;
REVOKE TEMPORARY ON DATABASE :"db_name" FROM :"app_user";
GRANT USAGE ON SCHEMA public TO :"app_user";
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM :"app_user";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM :"app_user";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :"app_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_user" IN SCHEMA public
    GRANT SELECT ON TABLES TO :"app_user";
SQL

unset TI_PHASE2_APP_PASSWORD app_password
