package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

class Phase4aPublicBankGoldenContractTest {

    private static final String LEGACY_COMMIT =
            "700006dfdfa063deb4387be572911e782bcea0d9";
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Map<String, SourceEvidence> KEY_SOURCES = Map.of(
            "app/__init__.py",
            new SourceEvidence(
                    "1f945e13969e2d4bebf8925e65f483f2a1d4cef3",
                    "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
                    43_489),
            "app/core/extensions.py",
            new SourceEvidence(
                    "963753e44321f8e884f8d4ea701aa61c5b0a3263",
                    "293c63c5ea2d548e1389f221909dced878a861d28f8073f305fb98d6ff334052",
                    2_150),
            "app/core/utils/api_response.py",
            new SourceEvidence(
                    "48a052d8c27eea94c396e9a9656f2e4d2d23bbbb",
                    "76fe1a04c1a9849264502054002f5b89e3a8a62a973df6c6c5ecc1ea7aead5b3",
                    1_072),
            "app/modules/user_bank/routes/public.py",
            new SourceEvidence(
                    "26044f0af2097b490e36a501894cb056aac654ae",
                    "6f3455e825b0316272d298d35782e73dd3230e9b2fc5271f1c078009b389a663",
                    12_723),
            "app/modules/user_bank/services/plaza_metrics_service.py",
            new SourceEvidence(
                    "147979ec1e0370d2d1cb946b4a8a6859f04478b0",
                    "a356ca751c30e50b5bb3d5fcab2742ce2ca6ac8a71dc6c82b974bdb63bb51d82",
                    13_375),
            "app/modules/user_bank/services/plaza_query_service.py",
            new SourceEvidence(
                    "4d1bd61921437fa9ec8b1463e68e3b6dffe8782f",
                    "4d26b12bc756a40a5c89cf9ee373753f73bd2d5eed6ee3b11c916192c58aa057",
                    42_772));

    @Test
    void goldenPinsACompleteReadOnlyLegacyAppArchive() throws Exception {
        JsonNode golden = JSON.readTree(Files.readString(
                goldenPath(),
                StandardCharsets.UTF_8));
        assertThat(golden.path("case_count").asInt()).isEqualTo(46);
        assertThat(golden.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);
        assertThat(golden.path("isolation").asString())
                .contains("fixed-commit Git archive")
                .contains("no working-tree imports");

        JsonNode attestation = golden.path("legacy_source_attestation");
        assertThat(attestation.path("archive_commit").asString()).isEqualTo(LEGACY_COMMIT);
        assertThat(attestation.path("archive_tree").asString())
                .isEqualTo("db528464896085fe14849baef3c5e686ad1bc253");
        assertThat(attestation.path("archive_sha256").asString())
                .isEqualTo("4f196047cefcb7c73984b0661a50cfec50f79926543593bdc32152ea1fc99034");
        assertThat(attestation.path("archive_scope").get(0).asString()).isEqualTo("app/");
        assertThat(attestation.path("git_object_format").asString()).isEqualTo("sha1");
        assertThat(attestation.path("commit_object_verified").asBoolean()).isTrue();
        assertThat(attestation.path("complete_app_tree_verified").asBoolean()).isTrue();
        assertThat(attestation.path("extracted_file_count").asInt()).isEqualTo(645);
        assertThat(attestation.path("member_count").asInt()).isEqualTo(792);

        JsonNode keySources = attestation.path("key_sources");
        Set<String> actualPaths = new java.util.HashSet<>();
        keySources.propertyNames().forEach(actualPaths::add);
        assertThat(actualPaths).isEqualTo(KEY_SOURCES.keySet());
        KEY_SOURCES.forEach((path, expected) -> {
            JsonNode actual = keySources.path(path);
            assertThat(actual.path("git_blob").asString()).as(path)
                    .isEqualTo(expected.gitBlob());
            assertThat(actual.path("sha256").asString()).as(path)
                    .isEqualTo(expected.sha256());
            assertThat(actual.path("size_bytes").asLong()).as(path)
                    .isEqualTo(expected.sizeBytes());
        });

        for (String caseId : Set.of(
                "detail-arbitrary-precision-id",
                "card-arbitrary-precision-id")) {
            JsonNode observed = caseById(golden, caseId);
            assertThat(observed.path("response").path("status").asInt()).isEqualTo(500);
            assertThat(observed.path("response").path("headers")
                    .path("Content-Type").asString()).isEqualTo("application/json");
            assertThat(observed.path("response").path("headers")
                    .path("X-RateLimit-Limit").asString()).isEqualTo("10");
            assertThat(observed.path("response").path("body").has("code")).isFalse();
            assertThat(observed.path("response").path("body").path("payload").isNull())
                    .isTrue();
        }

        assertUnicodeDecimalCaseMatchesAscii(
                golden, "detail-unicode-decimal-id", "detail-user-anonymous", 5401);
        assertUnicodeDecimalCaseMatchesAscii(
                golden, "card-unicode-decimal-id", "card-system-joined", 5301);
        assertThat(golden.path("warm_side_effect_free").asBoolean()).isTrue();
    }

    private static void assertUnicodeDecimalCaseMatchesAscii(
            JsonNode golden,
            String unicodeCaseId,
            String asciiCaseId,
            long expectedBankId
    ) {
        JsonNode unicode = caseById(golden, unicodeCaseId);
        JsonNode ascii = caseById(golden, asciiCaseId);
        assertThat(unicode.path("response").path("status").asInt()).isEqualTo(200);
        assertThat(unicode.path("response").path("headers")
                .path("X-RateLimit-Limit").asString()).isEqualTo("10");
        assertThat(unicode.path("response").path("body").path("data").path("id").asLong())
                .isEqualTo(expectedBankId);
        assertThat(unicode.path("response").path("body"))
                .isEqualTo(ascii.path("response").path("body"));
    }

    private static JsonNode caseById(JsonNode golden, String caseId) {
        return java.util.stream.StreamSupport.stream(
                        golden.path("cases").spliterator(), false)
                .filter(item -> item.path("case_id").asString().equals(caseId))
                .findFirst()
                .orElseThrow();
    }

    private static Path goldenPath() {
        return Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .getParent()
                .resolve("docs/refactor/phase4a/golden-public-bank-reads.json");
    }

    private record SourceEvidence(String gitBlob, String sha256, long sizeBytes) {}
}
