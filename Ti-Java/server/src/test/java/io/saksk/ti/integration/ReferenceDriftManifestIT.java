package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.InputStream;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Properties;
import org.junit.jupiter.api.Test;

class ReferenceDriftManifestIT {

    private static final String MANIFEST = "db/phase2/reference-drift-manifest.properties";

    @Test
    void manifestPreservesObservedDriftWithoutClaimingProductionVersion() throws Exception {
        Properties manifest = loadProperties(MANIFEST);

        assertThat(manifest.getProperty("production.postgresql.version.status")).isEqualTo("unknown");
        assertThat(manifest.getProperty("repository.declared.postgresql.image"))
                .isEqualTo("postgres:16-alpine");
        assertThat(manifest.getProperty("reference.observed.postgresql.version")).isEqualTo("18.4");
        assertThat(manifest.getProperty("reference.observed.postgresql.version_num")).isEqualTo("180004");
        assertThat(manifest.getProperty("reference.physical.table_count")).isEqualTo("70");
        assertThat(manifest.getProperty("reference.physical.column_count")).isEqualTo("617");
        assertThat(manifest.getProperty("reference.alembic.head")).isEqualTo("f5b6c7d8e9f0");
        assertThat(manifest.getProperty("reference.legacy.commit"))
                .matches("[0-9a-f]{40}");
        assertThat(manifest.getProperty("fixture.not_flyway_baseline")).isEqualTo("true");
        assertThat(manifest.getProperty("compatibility.pg18_dump_to_pg16_supported"))
                .isEqualTo("false");

        String schemaResource = manifest.getProperty("fixture.schema.resource");
        assertThat(sha256(schemaResource)).isEqualTo(manifest.getProperty("fixture.schema.sha256"));
    }

    private Properties loadProperties(String resource) throws Exception {
        Properties properties = new Properties();
        try (InputStream input = requiredResource(resource)) {
            properties.load(input);
        }
        return properties;
    }

    private String sha256(String resource) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = requiredResource(resource)) {
            input.transferTo(new java.security.DigestOutputStream(OutputStreamSink.INSTANCE, digest));
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private InputStream requiredResource(String resource) {
        InputStream input = Thread.currentThread().getContextClassLoader().getResourceAsStream(resource);
        assertThat(input).as("classpath resource %s", resource).isNotNull();
        return input;
    }

    private static final class OutputStreamSink extends java.io.OutputStream {
        private static final OutputStreamSink INSTANCE = new OutputStreamSink();

        @Override
        public void write(int value) {
            // Discard bytes after the DigestOutputStream observes them.
        }

        @Override
        public void write(byte[] bytes, int offset, int length) {
            // Discard bytes after the DigestOutputStream observes them.
        }
    }
}
