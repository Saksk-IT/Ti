package io.saksk.ti.architecture;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/** Cross-language parity for the Phase 4C transaction-write implementation gate. */
class Phase4cLearningTransactionWriteImplementationContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String RELATIVE =
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-implementation-contract.json";

    @Test
    void fixesPhysicalIdentityAndCommittedGoldenPredecessor() throws Exception {
        byte[] payload = Files.readAllBytes(root().resolve(RELATIVE));
        JsonNode contract = JSON.readTree(payload);

        assertThat(sha256(payload)).isEqualTo(
                "c4f4b2aed1836ffb2515ca6f13d0e5d822557e57be1a8befc7b696959a814cd3");
        assertThat(payload).hasSize(15_652);
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.learning-transaction-write-implementation-contract");
        assertThat(contract.path("document_payload_sha256").asString()).isEqualTo(
                "56eca630a339aae9d19c232573d722d64de67a2e3e53068a5a6346e4a2d0b6f6");
        assertThat(contract.path("predecessor").path("commit_oid").asString())
                .isEqualTo("22a1d81b14be61129427ca614a68ea12befde919");
        assertThat(contract.path("predecessor").path("golden_evidence")
                .path("sha256").asString()).isEqualTo(
                        "0d64e42b1d73c031151e76bb29c3d6a2e1f445c93bafcecb16e9d56fc3c12057");
    }

    @Test
    void authorizesExactlyNineRoutesAndThreeApprovedDifferences() throws Exception {
        JsonNode contract = contract();
        JsonNode scope = contract.path("scope");
        Set<String> routeIds = new HashSet<>();
        scope.path("routes").forEach(route ->
                routeIds.add(route.path("route_id").asString()));

        assertThat(scope.path("operation_count").asInt()).isEqualTo(9);
        assertThat(scope.path("semantic_group_count").asInt()).isEqualTo(7);
        assertThat(routeIds).containsExactlyInAnyOrder(
                "6d548bfd6830",
                "b52d3008d4d1",
                "87bb4fb340c8",
                "67dccafb3ea4",
                "bf3cb0c4f9ab",
                "c797832c43db",
                "278e1eac5eb4",
                "59c9c7366ec3",
                "624b5ac217d0");
        assertThat(contract.path("approved_differences")).hasSize(3);
        contract.path("approved_differences").forEach(difference ->
                assertThat(difference.path("approved").asBoolean())
                        .as(difference.path("difference_id").asString())
                        .isTrue());
    }

    @Test
    void bindsDurableIdempotencyAndOwnerLocalTransactions() throws Exception {
        JsonNode contract = contract();
        JsonNode idempotency = contract.path("idempotency_contract");
        JsonNode schema = contract.path("schema_authorization");
        JsonNode boundary = contract.path("module_boundary");

        assertThat(idempotency.path("header").asString())
                .isEqualTo("Idempotency-Key");
        assertThat(idempotency.path("same_actor_key_different_payload").asString())
                .isEqualTo("HTTP 409");
        assertThat(idempotency.path("concurrent_same_key").asString())
                .contains("one business commit");
        assertThat(idempotency.path("failed_transaction").asString())
                .contains("roll back together");
        assertThat(schema.path("authorized").asBoolean()).isTrue();
        assertThat(schema.path("production_execution_authorized").asBoolean())
                .isFalse();
        assertThat(schema.path("tables")).hasSize(2);
        assertThat(boundary.path("learning_direct_sql_to_catalog_tables_forbidden")
                .asBoolean()).isTrue();
        assertThat(boundary.path("question_edit_call_direction").asString())
                .isEqualTo("learning HTTP -> catalog::api");
        assertThat(boundary.path("question_edit_idempotency_owner").asString())
                .isEqualTo("catalog");
    }

    @Test
    void keepsRouteStatePendingUntilImplementationEvidenceCloses() throws Exception {
        JsonNode contract = contract();
        JsonNode authorization = contract.path("authorization");
        JsonNode route = contract.path("route_state");
        JsonNode status = contract.path("status");

        for (String field : List.of(
                "transaction_write_implementation",
                "scoped_flyway_migrations",
                "approved_difference_implementation",
                "unit_and_integration_tests",
                "openapi_draft")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isTrue();
        }
        for (String field : List.of(
                "route_matrix_delta",
                "production_schema_execution",
                "production_cutover",
                "legacy_runtime_disable",
                "progress_and_tags_group",
                "selection_search_and_count_group",
                "statistics_and_data_center_group")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
        assertThat(route.path("migrated_operation_count_after_contract").asInt())
                .isEqualTo(13);
        assertThat(route.path("pending_operation_count_after_contract").asInt())
                .isEqualTo(598);
        assertThat(status.path("implementation_authorized").asBoolean()).isTrue();
        assertThat(status.path("implementation_complete").asBoolean()).isFalse();
        assertThat(status.path("route_migration_complete").asBoolean()).isFalse();
        assertThat(status.path("production_cutover").asBoolean()).isFalse();
    }

    private static JsonNode contract() throws Exception {
        return JSON.readTree(Files.readAllBytes(root().resolve(RELATIVE)));
    }

    private static String sha256(byte[] payload) throws Exception {
        return java.util.HexFormat.of().formatHex(
                MessageDigest.getInstance("SHA-256").digest(payload));
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }
}
