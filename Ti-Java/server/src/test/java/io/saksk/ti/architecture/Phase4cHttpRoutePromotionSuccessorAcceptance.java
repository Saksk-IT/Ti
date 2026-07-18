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

/** Gitless Java acceptance for the Phase 4C user-counts route successor. */
final class Phase4cHttpRoutePromotionSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/personal-bank-user-counts-route-promotion-contract.json";
    private static final String CONTRACT_SHA256 =
            "e5bc53bb8c011c5cf2f08447543aa3e5dd2a045b6226f064c6594a3639d7b5c9";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "1503c4dd5905abb70a77835e6602d8e51a7f042f5eed6b0a25a9a0de4b5f6e0f";
    private static final long CONTRACT_BYTES = 4_365L;
    private static final Map<String, Artifact> SOURCES = sources();

    private Phase4cHttpRoutePromotionSuccessorAcceptance() {
    }

    static JsonNode load(Path root) throws IOException {
        byte[] contractBytes = fixedBytes(
                root, CONTRACT_RELATIVE, CONTRACT_SHA256, CONTRACT_BYTES);
        for (Map.Entry<String, Artifact> entry : SOURCES.entrySet()) {
            fixedBytes(root, entry.getKey(), entry.getValue().sha256(), entry.getValue().bytes());
        }
        JsonNode contract = JSON.readTree(contractBytes);
        validate(contract);
        return contract;
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static Map<String, Artifact> sources() {
        Map<String, Artifact> sources = new LinkedHashMap<>();
        sources.put(
                "docs/refactor/02-route-parity-matrix.csv",
                new Artifact(
                        "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74",
                        416_225L));
        sources.put(
                "docs/refactor/phase4a/effective-route-parity-status.json",
                new Artifact(
                        "1c4645354be4d4a778ec7d68d2957130718e826648e420dd3d1fec7bea5339d4",
                        4_048L));
        sources.put(
                "docs/refactor/phase4c/route-parity-delta.csv",
                new Artifact(
                        "40ead5f703f1a589989fd524107f1fc31994662fb7d3e3be54fe22705025b52b",
                        2_230L));
        sources.put(
                "docs/refactor/phase4c/route-parity-successor-delta.csv",
                new Artifact(
                        "eef46dc120be7aff600f7f767120673451d21fa42389a777f24e7b4e4f011d07",
                        836L));
        sources.put(
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-http-full-parity-anchor-contract.json",
                new Artifact(
                        "77c15295db2addf223ac425dfbbde687c4be3685fd6c6a9b842db7a238b58836",
                        14_885L));
        sources.put(
                "docs/refactor/phase4c/effective-route-parity-successor-status.json",
                new Artifact(
                        "c0e96472533d0bbe7d67ac1416a91f3e9a3bfcef8c27e1170b0e9939c46b358a",
                        5_340L));
        return Map.copyOf(sources);
    }

    private static void validate(JsonNode contract) {
        require(contract.path("schema_version").asInt() == 1, "schema version");
        require("ti.phase4c.personal-bank-user-counts-route-promotion-contract".equals(
                contract.path("contract_id").asString()), "contract id");
        require(CONTRACT_PAYLOAD_SHA256.equals(
                contract.path("document_payload_sha256").asString()), "payload hash");
        JsonNode parity = contract.path("parity");
        require(parity.path("pg16_pg18_termination_fingerprints_complete").asBoolean(), "PG");
        require(parity.path("real_tomcat_complete_response_header_matrix_complete")
                .asBoolean(), "Tomcat");
        require(parity.path("same_service_redis_outage_and_recovery_complete")
                .asBoolean(), "Redis");
        require(parity.path("full_target_parity_closed").asBoolean(), "full parity");
        require(parity.path("route_migration_eligible").asBoolean(), "route eligibility");
        JsonNode authorization = contract.path("authorization");
        require(authorization.path("two_legacy_get_routes_migrated").asBoolean(), "routes");
        require(!authorization.path("derived_head_and_options_count_as_migrated")
                .asBoolean(), "derived operations");
        require(!authorization.path("production_cutover").asBoolean(), "production cutover");
        require(!authorization.path("operator_migration_implementation").asBoolean(), "operator");
        require(!authorization.path("production_schema_or_index").asBoolean(), "schema");
        require(!authorization.path("real_data_migration_execution").asBoolean(), "data migration");
        JsonNode route = contract.path("route_state");
        require(route.path("total_operation_count").asInt() == 611, "total count");
        require(route.path("migrated_operation_count").asInt() == 13, "migrated count");
        require(route.path("pending_operation_count").asInt() == 598, "pending count");
        require(route.path("production_cutover_operation_count").asInt() == 0, "cutover count");
        require(contract.path("route_authority").path("promoted_routes").size() == 2,
                "promoted routes");
        require(!contract.path("route_authority")
                .path("historical_matrix_and_deltas_overwritten").asBoolean(), "history");
        require(contract.path("source_authority").path("excluded_from_self_authority")
                .asBoolean(), "self authority");
    }

    private static byte[] fixedBytes(
            Path root, String relative, String sha256, long expectedBytes) throws IOException {
        Path normalizedRoot = root.toRealPath(LinkOption.NOFOLLOW_LINKS);
        Path candidate = normalizedRoot.resolve(relative).normalize();
        if (!candidate.startsWith(normalizedRoot) || Files.isSymbolicLink(candidate)
                || !Files.isRegularFile(candidate, LinkOption.NOFOLLOW_LINKS)) {
            throw new AssertionError("route promotion path is not fixed: " + relative);
        }
        byte[] payload = Files.readAllBytes(candidate);
        if (payload.length != expectedBytes || !sha256(payload).equals(sha256)) {
            throw new AssertionError("route promotion fixed bytes drifted: " + relative);
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
            throw new AssertionError("route promotion contract drifted: " + field);
        }
    }

    record Artifact(String sha256, long bytes) {
    }
}
