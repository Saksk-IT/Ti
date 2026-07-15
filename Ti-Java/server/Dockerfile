# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

ARG MAVEN_IMAGE=maven:3.9.16-eclipse-temurin-25@sha256:7e461cec477077c1d9e50b13df8aef9018764410f4c4cd7c34803f10c4c99e4c
ARG RUNTIME_IMAGE=eclipse-temurin:25.0.3_9-jre-noble@sha256:2f1da100788559b397bcf48c736169ea5b070bde84e55f203bbee8e83d87a175

FROM ${MAVEN_IMAGE} AS build

# The official Maven image uses MAVEN_CONFIG for its entrypoint, while Maven
# Wrapper treats that variable as extra CLI arguments. Clear it for wrapper runs.
ENV MAVEN_CONFIG=""

WORKDIR /workspace

COPY .mvn/ .mvn/
COPY mvnw pom.xml build-versions.properties ./

# Resolve only build dependencies here. The image build never starts Docker-backed
# Testcontainers; integration tests run in the separate verification workflow.
RUN --mount=type=cache,target=/root/.m2 \
    ./mvnw --batch-mode --no-transfer-progress -Dmaven.test.skip=true dependency:go-offline

COPY src/main/ src/main/

RUN --mount=type=cache,target=/root/.m2 \
    ./mvnw --batch-mode --no-transfer-progress -Dmaven.test.skip=true clean package && \
    test -f target/ti-server-0.1.0-SNAPSHOT.jar

FROM ${RUNTIME_IMAGE} AS runtime

LABEL org.opencontainers.image.title="Ti Java Server" \
      org.opencontainers.image.description="Ti Phase 2 modular-monolith server skeleton" \
      org.opencontainers.image.vendor="Saksk-IT"

RUN groupadd --system --gid 10001 ti && \
    useradd --system --uid 10001 --gid 10001 --home-dir /app --shell /usr/sbin/nologin ti && \
    install --directory --owner=10001 --group=10001 --mode=0750 /app

WORKDIR /app

COPY --from=build --chown=10001:10001 \
    /workspace/target/ti-server-0.1.0-SNAPSHOT.jar /app/application.jar

USER 10001:10001

EXPOSE 8080

ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-Djava.io.tmpdir=/tmp", "-jar", "/app/application.jar"]
