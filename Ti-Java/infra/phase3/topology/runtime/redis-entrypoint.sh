#!/bin/sh
set -eu

secret_file=/run/secrets/redis.password
line_count=$(wc -l < "$secret_file" | tr -d '[:space:]')
if [ "$line_count" != "1" ]; then
    echo "Phase 3 Redis secret must contain exactly one line" >&2
    exit 70
fi
password=$(cat "$secret_file")
case "$password" in
    ''|*[!A-Za-z0-9_-]*)
        echo "Phase 3 Redis secret is outside the safe alphabet" >&2
        exit 70
        ;;
esac
if [ "${#password}" -lt 32 ] || [ "${#password}" -gt 128 ]; then
    echo "Phase 3 Redis secret length is invalid" >&2
    exit 70
fi

escaped=$(printf '%s' "$password" | sed 's/\\/\\\\/g; s/"/\\"/g')
umask 077
printf 'requirepass "%s"\nappendonly yes\nappendfsync everysec\nmaxmemory 128mb\nmaxmemory-policy noeviction\n' \
    "$escaped" > /tmp/redis.conf
unset password escaped
exec redis-server /tmp/redis.conf
