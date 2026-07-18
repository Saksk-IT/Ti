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

/** Gitless Java acceptance for the fixed Phase 4C full-parity Git anchor. */
final class Phase4cHttpFullParityAnchorSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-full-parity-anchor-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-full-parity-anchor-contract";
    private static final String CONTRACT_SHA256 =
            "77c15295db2addf223ac425dfbbde687c4be3685fd6c6a9b842db7a238b58836";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "eb76c6bf825b4efe0ad6d1ed0a1d2fa02eb1025226c9168c6fe42108dc4ff816";
    private static final long CONTRACT_BYTES = 14_885L;
    private static final Map<String, Artifact> BOOTSTRAP_SOURCES = bootstrapSources();

    private Phase4cHttpFullParityAnchorSuccessorAcceptance() {
    }

    static JsonNode load(Path root) throws IOException {
        byte[] contractBytes = fixedBytes(
                root, CONTRACT_RELATIVE, CONTRACT_SHA256, CONTRACT_BYTES);
        for (Map.Entry<String, Artifact> entry : BOOTSTRAP_SOURCES.entrySet()) {
            fixedBytes(root, entry.getKey(), entry.getValue().sha256(), entry.getValue().bytes());
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

    static Map<String, Artifact> bootstrapSources() {
        Map<String, Artifact> sources = new LinkedHashMap<>();
        sources.put(
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-http-full-parity-contract.json",
                new Artifact(
                        "13df3a1f81ca909d62e89495564215e92a757e41889aa91658db55e33717b787",
                        7_477L));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpFullParitySuccessorAcceptance.java",
                new Artifact(
                        "703eeaff656912bd67eb553fe6e1accf8cf6c4e9bc99a59bf71d13423f33baf7",
                        8_577L));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cPersonalBankUserCountsHttpFullParityContractParityTest.java",
                new Artifact(
                        "45ad052dfe392bf614f8af03f40bf77a954fb82648c2a1e97cb715f7818dace4",
                        6_586L));
        sources.put(
                "tools/build_phase4c_personal_bank_user_counts_http_full_parity_contract.py",
                new Artifact(
                        "6ae98b23ca5d475f266608ae0ee443800d004004062a30f60b1895d1551ea585",
                        11_271L));
        sources.put(
                "tools/phase4c_http_full_parity_successor_acceptance.py",
                new Artifact(
                        "a28c01c637cf61acc6dc476abe540d13a247c9298086d660c899f2af17c23cf0",
                        7_171L));
        sources.put(
                "tools/test_phase4c_personal_bank_user_counts_http_full_parity_contract.py",
                new Artifact(
                        "c9ba6025c127c92f1f20d2eefe753f02256d9aa3ed7e37c04e94093ed1044d14",
                        6_313L));
        return Map.copyOf(sources);
    }

    private static void validate(JsonNode contract) {
        require(contract.path("schema_version").asInt() == 1, "schema version");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString()), "contract id");
        require(CONTRACT_PAYLOAD_SHA256.equals(
                contract.path("document_payload_sha256").asString()), "payload hash");
        JsonNode checkpoint = contract.path("git_checkpoint");
        require("848af89cb99ae0330ec1f0955cf23749a044d40e".equals(
                checkpoint.path("commit_oid").asString()), "commit oid");
        require("765e4470f1ddb60f0ce6f23227d6303961f47fcf".equals(
                checkpoint.path("parent_oid").asString()), "parent oid");
        require(checkpoint.path("changed_path_count").asInt() == 15, "changed path count");
        require(checkpoint.path("added_path_count").asInt() == 12, "added path count");
        require(checkpoint.path("modified_path_count").asInt() == 3, "modified path count");
        require(checkpoint.path("artifacts").size() == 15, "checkpoint artifacts");
        JsonNode anchor = contract.path("full_parity_source_anchor");
        require(anchor.path("source_count").asInt() == 6, "source count");
        require(anchor.path("artifacts").size() == 6, "source artifacts");
        require(anchor.path("predecessor_bootstrap_sources_external_git_anchor_complete")
                .asBoolean(), "bootstrap external anchor");
        require(anchor.path("current_anchor_sources_excluded_from_self_authority")
                .asBoolean(), "current source exclusion");
        require(!anchor.path("current_anchor_source_bytes_external_git_anchor_complete")
                .asBoolean(), "current source external anchor");
        JsonNode parity = contract.path("parity");
        require(parity.path("pg16_pg18_termination_fingerprints_complete").asBoolean(), "PG");
        require(parity.path("real_tomcat_complete_response_header_matrix_complete")
                .asBoolean(), "Tomcat");
        require(parity.path("same_service_redis_outage_and_recovery_complete")
                .asBoolean(), "Redis");
        require(parity.path("full_target_parity_closed").asBoolean(), "full parity");
        JsonNode authorization = contract.path("authorization");
        require(authorization.path(
                "full_parity_checkpoint_and_six_excluded_sources_external_git_anchor_complete")
                .asBoolean(), "full parity source anchor");
        require(authorization.path("route_migration_eligible").asBoolean(), "route eligibility");
        require(!authorization.path("two_legacy_get_routes_migrated").asBoolean(), "route promoted");
        require(!authorization.path("production_cutover").asBoolean(), "production cutover");
        require(contract.path("route_state").path("migrated_operation_count").asInt() == 11,
                "migrated count");
        require(contract.path("route_state").path("pending_operation_count").asInt() == 600,
                "pending count");
    }

    private static byte[] fixedBytes(
            Path root, String relative, String sha256, long expectedBytes) throws IOException {
        Path normalizedRoot = root.toRealPath(LinkOption.NOFOLLOW_LINKS);
        Path candidate = normalizedRoot.resolve(relative).normalize();
        if (!candidate.startsWith(normalizedRoot) || Files.isSymbolicLink(candidate)
                || !Files.isRegularFile(candidate, LinkOption.NOFOLLOW_LINKS)) {
            throw new AssertionError("full parity anchor path is not fixed: " + relative);
        }
        byte[] payload = Files.readAllBytes(candidate);
        if (payload.length != expectedBytes || !sha256(payload).equals(sha256)) {
            throw new AssertionError("full parity anchor fixed bytes drifted: " + relative);
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
            throw new AssertionError("full parity anchor contract drifted: " + field);
        }
    }

    record Artifact(String sha256, long bytes) {
    }
}
