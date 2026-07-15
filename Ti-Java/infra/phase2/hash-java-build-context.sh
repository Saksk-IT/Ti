#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
SERVER_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../../server" && pwd -P)

sha256_stream() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    else
        echo "sha256sum or shasum is required" >&2
        return 1
    fi
}

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        echo "sha256sum or shasum is required" >&2
        return 1
    fi
}

(
    cd "$SERVER_DIR"
    find Dockerfile .dockerignore .mvn mvnw pom.xml build-versions.properties src/main \
        -type f -print \
        | LC_ALL=C sort \
        | while IFS= read -r file; do
            printf '%s  %s\n' "$(sha256_file "$file")" "$file"
        done
) | sha256_stream
