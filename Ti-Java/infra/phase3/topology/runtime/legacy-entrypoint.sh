#!/bin/sh
set -eu

read_secret() {
    secret_file=$1
    line_count=$(wc -l < "$secret_file" | tr -d '[:space:]')
    if [ "$line_count" != "1" ]; then
        echo "Phase 3 legacy runtime secret must contain exactly one line" >&2
        exit 70
    fi
    value=$(cat "$secret_file")
    case "$value" in
        ''|*[!A-Za-z0-9_-]*)
            echo "Phase 3 legacy runtime secret is empty or outside the safe alphabet" >&2
            exit 70
            ;;
    esac
    if [ "${#value}" -lt 32 ] || [ "${#value}" -gt 128 ]; then
        echo "Phase 3 legacy runtime secret length is invalid" >&2
        exit 70
    fi
    printf '%s' "$value"
}

case "${TI_PHASE3_DB_HOST:-}:${TI_PHASE3_REDIS_HOST:-}" in
    legacy-postgres:legacy-redis) ;;
    *)
        echo "Phase 3 legacy runtime only accepts its isolated service names" >&2
        exit 70
        ;;
esac

db_password=$(read_secret "${TI_PHASE3_DB_PASSWORD_FILE:?database password file is required}")
redis_password=$(read_secret "${TI_PHASE3_REDIS_PASSWORD_FILE:?Redis password file is required}")
flask_secret=$(read_secret "${TI_PHASE3_FLASK_SECRET_FILE:?Flask secret file is required}")

export DATABASE_URL="postgresql://${TI_PHASE3_DB_USER:?database user is required}:${db_password}@legacy-postgres:5432/${TI_PHASE3_DB_NAME:?database name is required}"
export REDIS_URL="redis://:${redis_password}@legacy-redis:6379/0"
export RATELIMIT_STORAGE_URI="$REDIS_URL"
export SECRET_KEY="$flask_secret"

unset db_password redis_password flask_secret
exec "$@"
