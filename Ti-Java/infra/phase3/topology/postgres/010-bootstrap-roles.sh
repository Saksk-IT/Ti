#!/bin/sh
set -eu

safe_identifier() {
    case "$1" in
        ''|*[!a-z0-9_]*|[0-9]*)
            echo "Phase 3 PostgreSQL role identifier is invalid" >&2
            exit 70
            ;;
    esac
}

read_secret() {
    line_count=$(wc -l < "$1" | tr -d '[:space:]')
    if [ "$line_count" != "1" ]; then
        echo "Phase 3 PostgreSQL role secret must contain exactly one line" >&2
        exit 70
    fi
    value=$(cat "$1")
    case "$value" in
        ''|*[!A-Za-z0-9_-]*)
            echo "Phase 3 PostgreSQL role secret is invalid" >&2
            exit 70
            ;;
    esac
    if [ "${#value}" -lt 32 ] || [ "${#value}" -gt 128 ]; then
        echo "Phase 3 PostgreSQL role secret length is invalid" >&2
        exit 70
    fi
    printf '%s' "$value"
}

app_user=${TI_PHASE3_DB_APP_USER:?application role is required}
audit_user=${TI_PHASE3_DB_AUDIT_USER:?audit role is required}
safe_identifier "$app_user"
safe_identifier "$audit_user"
test "$app_user" != "$audit_user"
test "$app_user" != "$POSTGRES_USER"
test "$audit_user" != "$POSTGRES_USER"

app_password=$(read_secret /run/secrets/db.app.password)
audit_password=$(read_secret /run/secrets/db.audit.password)

psql --set=ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set=app_user="$app_user" \
    --set=audit_user="$audit_user" \
    --set=app_password="$app_password" \
    --set=audit_password="$audit_password" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION',
              :'app_user', :'app_password') \gexec
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION',
              :'audit_user', :'audit_password') \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database()) \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'audit_user') \gexec
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL

unset app_password audit_password
