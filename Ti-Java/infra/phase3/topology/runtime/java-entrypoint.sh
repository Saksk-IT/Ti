#!/bin/sh
set -eu

read_secret() {
    line_count=$(wc -l < "$1" | tr -d '[:space:]')
    if [ "$line_count" != "1" ]; then
        echo "Phase 3 Java runtime secret must contain exactly one line" >&2
        exit 70
    fi
    value=$(cat "$1")
    case "$value" in
        ''|*[!A-Za-z0-9_-]*)
            echo "Phase 3 Java runtime secret is empty or outside the safe alphabet" >&2
            exit 70
            ;;
    esac
    if [ "${#value}" -lt 32 ] || [ "${#value}" -gt 128 ]; then
        echo "Phase 3 Java runtime secret length is invalid" >&2
        exit 70
    fi
    printf '%s' "$value"
}

case "${TI_REDIS_HOST:-}" in
    java-redis) ;;
    *)
        echo "Phase 3 Java runtime only accepts its isolated Redis service" >&2
        exit 70
        ;;
esac
case "${TI_DB_URL:-}" in
    jdbc:postgresql://java-postgres:5432/*) ;;
    *)
        echo "Phase 3 Java runtime only accepts its isolated PostgreSQL service" >&2
        exit 70
        ;;
esac

export TI_DB_PASSWORD=$(read_secret "${TI_PHASE3_DB_PASSWORD_FILE:?database password file is required}")
export TI_REDIS_PASSWORD=$(read_secret "${TI_PHASE3_REDIS_PASSWORD_FILE:?Redis password file is required}")

exec "$@"
