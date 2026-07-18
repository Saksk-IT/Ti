package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;

/** Gitless Java acceptance for the Phase 4C full-parity bootstrap. */
final class Phase4cHttpFullParitySuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-full-parity-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-full-parity-contract";
    private static final String CONTRACT_SHA256 =
            "13df3a1f81ca909d62e89495564215e92a757e41889aa91658db55e33717b787";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "7eecb6279b2e2b5532dab21c171b9fca3a7bb6129ff2f4dff3bfcf7941196da2";
    private static final long CONTRACT_BYTES = 7_477L;
    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-typed-normalization-anchor-contract.json";
    private static final String PREDECESSOR_SHA256 =
            "c713aa04a82f340ea04fdd5ae870bd5cfae82f099101431c664f047c2d5218ca";
    private static final long PREDECESSOR_BYTES = 43_737L;

    private static final Map<String, Artifact> ARTIFACTS = artifacts();

    private Phase4cHttpFullParitySuccessorAcceptance() {
    }

    static JsonNode load(Path root) throws IOException {
        byte[] contractBytes = fixedBytes(
                root, CONTRACT_RELATIVE, CONTRACT_SHA256, CONTRACT_BYTES);
        fixedBytes(root, PREDECESSOR_RELATIVE, PREDECESSOR_SHA256, PREDECESSOR_BYTES);
        for (Map.Entry<String, Artifact> entry : ARTIFACTS.entrySet()) {
            Artifact artifact = entry.getValue();
            fixedBytes(root, entry.getKey(), artifact.sha256(), artifact.bytes());
        }
        JsonNode contract = JSON.readTree(contractBytes);
        validate(contract);
        return contract;
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static String contractSha256() {
        return CONTRACT_SHA256;
    }

    static String contractPayloadSha256() {
        return CONTRACT_PAYLOAD_SHA256;
    }

    static long contractBytes() {
        return CONTRACT_BYTES;
    }

    static Map<String, Artifact> artifacts() {
        Map<String, Artifact> artifacts = new LinkedHashMap<>();
        artifacts.put(
                "server/src/test/java/io/saksk/ti/integration/"
                        + "LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT.java",
                new Artifact(
                        "cd9a45f6cfc52342d235202519ace13883e37354a901a790304739b7507501c9",
                        40_107L));
        artifacts.put(
                "server/src/test/java/io/saksk/ti/integration/"
                        + "Phase4cUserCountsTerminationFingerprintIT.java",
                new Artifact(
                        "aa55869a57233a34ceae59773456cbb759670db1624b844cae75e664f8c0701a",
                        26_069L));
        artifacts.put(
                "server/src/test/java/io/saksk/ti/support/"
                        + "Phase4cUserCountsTerminationFingerprintSupport.java",
                new Artifact(
                        "e4c4fc6f73b5ee9eebc3ab2e9904a51d6c593ed711b4aaaa39a79971e887ce42",
                        25_907L));
        artifacts.put(
                "server/src/test/java/io/saksk/ti/web/security/"
                        + "Phase4cUserCountsRedisOutageRecoveryIT.java",
                new Artifact(
                        "b07ec534e41a74c1fddc3d9c2b63a6ae26f57ab8918112dc7799f10b479239c4",
                        39_719L));
        artifacts.put(
                "server/src/test/java/io/saksk/ti/web/security/support/"
                        + "Phase4cRedisNetworkGate.java",
                new Artifact(
                        "ac3bab1cd092dcce640954c167baf4f7de5e53dee8579e77fb36d632c410b5ab",
                        7_245L));
        artifacts.put(
                "server/src/test/resources/db/phase4c/"
                        + "073-personal-bank-user-counts-termination-fingerprint-seed.sql",
                new Artifact(
                        "33a6a4ce9845fe8b51ae6d5006af9a394bdc51d8427183d2775b2ef1cb4e6b40",
                        843L));
        return Map.copyOf(artifacts);
    }

    private static void validate(JsonNode contract) {
        require(contract.path("schema_version").asInt() == 1, "schema version");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString()), "contract id");
        require(
                CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString()),
                "payload hash declaration");
        JsonNode parity = contract.path("parity");
        for (String field : new String[] {
            "pg16_pg18_termination_fingerprints_complete",
            "real_tomcat_complete_response_header_matrix_complete",
            "same_service_redis_outage_and_recovery_complete",
            "full_target_parity_closed",
            "all_required_parity_prerequisites_true",
            "typed_parity_review_complete"
        }) {
            require(parity.path(field).asBoolean(), field);
        }
        JsonNode verification = contract.path("verification");
        require(verification.path("targeted_failsafe_tests").asInt() == 13, "targeted tests");
        require(verification.path("full_surefire_tests").asInt() == 709, "surefire tests");
        require(verification.path("full_failsafe_tests").asInt() == 167, "failsafe tests");
        require(verification.path("full_failures_errors_skipped").asInt() == 0, "failures");
        JsonNode authorization = contract.path("authorization");
        require(
                !authorization.path("current_bootstrap_sources_external_git_anchor_complete")
                        .asBoolean(),
                "bootstrap external anchor");
        require(!authorization.path("route_migration_eligible").asBoolean(), "route eligibility");
        require(!authorization.path("production_cutover").asBoolean(), "production cutover");
        JsonNode route = contract.path("route_state");
        require(route.path("migrated_operation_count").asInt() == 11, "migrated count");
        require(route.path("pending_operation_count").asInt() == 600, "pending count");
        require(route.path("production_cutover_operation_count").asInt() == 0, "cutover count");
        require(contract.path("worker_integration").path("lane_count").asInt() == 3, "lane count");
        require(contract.path("worker_integration").path("artifact_count").asInt() == 6, "artifact count");
        require(contract.path("source_authority").path("excluded_from_self_authority")
                .asBoolean(), "self authority exclusion");
    }

    private static byte[] fixedBytes(
            Path root, String relative, String sha256, long expectedBytes) throws IOException {
        Path normalizedRoot = root.toRealPath(LinkOption.NOFOLLOW_LINKS);
        Path candidate = normalizedRoot.resolve(relative).normalize();
        if (!candidate.startsWith(normalizedRoot) || Files.isSymbolicLink(candidate)
                || !Files.isRegularFile(candidate, LinkOption.NOFOLLOW_LINKS)) {
            throw new AssertionError("full parity path is not a fixed regular file: " + relative);
        }
        byte[] payload = Files.readAllBytes(candidate);
        if (payload.length != expectedBytes || !sha256(payload).equals(sha256)) {
            throw new AssertionError("full parity fixed bytes drifted: " + relative);
        }
        return payload;
    }

    private static String sha256(byte[] payload) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(payload));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException(error);
        }
    }

    private static void require(boolean condition, String field) {
        if (!condition) {
            throw new AssertionError("full parity contract drifted: " + field);
        }
    }

    record Artifact(String sha256, long bytes) {
    }
}
