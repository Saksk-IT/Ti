#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
TI_JAVA_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
SERVER_DIR="$TI_JAVA_DIR/server"
MAVEN_IMAGE="maven:3.9.16-eclipse-temurin-25@sha256:7e461cec477077c1d9e50b13df8aef9018764410f4c4cd7c34803f10c4c99e4c"
MAVEN_CACHE_VOLUME=${TI_JAVA_MAVEN_CACHE_VOLUME:-ti-java-phase2-maven-cache}

case "$TI_JAVA_DIR" in
    /*) ;;
    *)
        echo "Ti-Java path must resolve to an absolute path" >&2
        exit 1
        ;;
esac

command -v docker >/dev/null 2>&1 || {
    echo "Docker CLI is required for the no-host-JDK verification" >&2
    exit 1
}
docker info >/dev/null 2>&1 || {
    echo "Docker daemon is unavailable" >&2
    exit 1
}
if [ ! -S /var/run/docker.sock ]; then
    echo "Expected Docker socket /var/run/docker.sock is unavailable" >&2
    exit 1
fi

verify_distribution=false
if [ "$#" -eq 0 ]; then
    set -- clean verify
fi
for maven_argument in "$@"; do
    if [ "$maven_argument" = "verify" ]; then
        verify_distribution=true
        break
    fi
done

echo "WARNING: this verification mounts /var/run/docker.sock into Maven." >&2
echo "WARNING: Docker-socket access is root-equivalent; run only trusted repository code." >&2
echo "The complete Ti-Java directory is mounted at the same absolute host/container path." >&2

host_override=${TESTCONTAINERS_HOST_OVERRIDE:-}
if [ -z "$host_override" ]; then
    case "$(docker info --format '{{.OperatingSystem}}' 2>/dev/null || true)" in
        *"Docker Desktop"*) host_override=host.docker.internal ;;
    esac
fi

if [ -n "$host_override" ]; then
    docker run --rm --init \
        --volume "$TI_JAVA_DIR:$TI_JAVA_DIR" \
        --workdir "$SERVER_DIR" \
        --volume /var/run/docker.sock:/var/run/docker.sock \
        --volume "$MAVEN_CACHE_VOLUME:/root/.m2" \
        --env TESTCONTAINERS_RYUK_DISABLED=false \
        --env TESTCONTAINERS_HOST_OVERRIDE="$host_override" \
        "$MAVEN_IMAGE" \
        ./mvnw --batch-mode --no-transfer-progress "$@"
else
    docker run --rm --init \
        --volume "$TI_JAVA_DIR:$TI_JAVA_DIR" \
        --workdir "$SERVER_DIR" \
        --volume /var/run/docker.sock:/var/run/docker.sock \
        --volume "$MAVEN_CACHE_VOLUME:/root/.m2" \
        --env TESTCONTAINERS_RYUK_DISABLED=false \
        "$MAVEN_IMAGE" \
        ./mvnw --batch-mode --no-transfer-progress "$@"
fi

if [ "$verify_distribution" = true ]; then
    jar_listing=$(docker run --rm --init \
        --volume "$TI_JAVA_DIR:$TI_JAVA_DIR:ro" \
        --workdir "$SERVER_DIR" \
        "$MAVEN_IMAGE" \
        jar tf target/ti-server-0.1.0-SNAPSHOT.jar)

    if printf '%s\n' "$jar_listing" | grep --extended-regexp --quiet '(^|/)ActorId\.class$'; then
        echo "Executable JAR contains forbidden stale ActorId.class" >&2
        exit 1
    fi
    if printf '%s\n' "$jar_listing" \
        | grep --extended-regexp '(^|/)events/.*\.class$' \
        | grep --invert-match --extended-regexp '/events/package-info\.class$' \
        | grep --quiet .; then
        echo "Executable JAR contains forbidden stale events classes" >&2
        exit 1
    fi
fi
