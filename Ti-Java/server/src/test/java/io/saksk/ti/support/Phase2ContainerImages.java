package io.saksk.ti.support;

import org.testcontainers.utility.DockerImageName;

/** Audited, multi-architecture OCI image indexes used by Phase 2. */
public final class Phase2ContainerImages {

    public static final String POSTGRES_18_REFERENCE =
            "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15";
    public static final String POSTGRES_16_COMPATIBILITY =
            "postgres:16.14-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777";
    public static final String REDIS_7 =
            "redis:7.4.7-alpine@sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf";

    private Phase2ContainerImages() {
    }

    public static DockerImageName postgres18() {
        return DockerImageName.parse(POSTGRES_18_REFERENCE)
                .asCompatibleSubstituteFor("postgres");
    }

    public static DockerImageName postgres16() {
        return DockerImageName.parse(POSTGRES_16_COMPATIBILITY)
                .asCompatibleSubstituteFor("postgres");
    }

    public static DockerImageName redis7() {
        return DockerImageName.parse(REDIS_7)
                .asCompatibleSubstituteFor("redis");
    }
}
