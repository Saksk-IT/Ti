package io.saksk.ti.identity.infrastructure.security;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

final class LegacyAuthVectors {
    private static final JsonNode ROOT = load();

    private LegacyAuthVectors() {
    }

    static JsonNode root() {
        return ROOT;
    }

    static byte[] publicTestSecret() {
        return ROOT.path("shared_secret").asString().getBytes(StandardCharsets.UTF_8);
    }

    static long fixedTime() {
        return ROOT.path("fixed_time_epoch_seconds").asLong();
    }

    private static JsonNode load() {
        try (InputStream stream = LegacyAuthVectors.class
                .getClassLoader()
                .getResourceAsStream("compat/legacy-auth-vectors.json")) {
            if (stream == null) {
                throw new IllegalStateException("legacy authentication vector manifest is missing");
            }
            String json = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
            JsonNode root = new ObjectMapper().readTree(json);
            if (root.path("schema_version").asInt() != 1
                    || !root.path("classification").asString().startsWith("PUBLIC TEST-ONLY")
                    || !root.path("formats").path("jwt").path("algorithm").asString().equals("HS256")
                    || !root.path("formats")
                            .path("flask_session")
                            .path("salt")
                            .asString()
                            .equals("cookie-session")
                    || root.path("formats")
                                    .path("password")
                                    .path("pbkdf2_iterations_maximum")
                                    .asInt()
                            != WerkzeugPasswordVerifier.MAXIMUM_PBKDF2_ITERATIONS
                    || !root.path("observed_legacy_inventory")
                            .path("production_inventory")
                            .asString()
                            .contains("never queried")
                    || root.path("observed_legacy_inventory").path("password_hash_rows").asInt()
                            != 8
                    || !root.path("observed_legacy_inventory")
                            .path("password_hash_formats")
                            .get(0)
                            .path("method")
                            .asString()
                            .equals("scrypt:32768:8:1")) {
                throw new IllegalStateException("legacy authentication vector manifest is unsafe");
            }
            return root;
        } catch (IOException exception) {
            throw new IllegalStateException("legacy authentication vector manifest is unreadable", exception);
        }
    }
}
