package io.saksk.ti.architecture;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/** Cross-language parity for the Phase 4C ordered learning route-scope entry. */
class Phase4cLearningRouteScopeContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String RELATIVE =
            "docs/refactor/phase4c/learning-route-scope-entry-contract.json";

    @Test
    void fixesPhysicalIdentityAndExternalNodeDPredecessor() throws Exception {
        byte[] payload = Files.readAllBytes(root().resolve(RELATIVE));
        JsonNode contract = JSON.readTree(payload);

        assertThat(sha256(payload)).isEqualTo(
                "73c235dac971a52b2bf620565f3e4070c663a9584a63b2cc0a668f121cb73684");
        assertThat(payload).hasSize(43_260);
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.learning-route-scope-entry-contract");
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(
                        "ca589656cbdf50aba9e4cb15b5e2cbb047f2b3f9e48eb4661e8e642c94124d49");
        assertThat(contract.path("predecessor").path("sha256").asString())
                .isEqualTo(
                        "a6dff0717d0da91091f50cb7a51d35ffc66db364e966c568fec40bdb3ca936cd");
        assertThat(contract.path("predecessor").path("fixed_d2_commit").asString())
                .isEqualTo(
                        "2579dfd344dbe318c9fb59d067c843356b98fece");
    }

    @Test
    void partitionsSeventyOneOperationsWithoutOverlap() throws Exception {
        JsonNode contract = contract();
        JsonNode partition = contract.path("phase4c_partition");
        JsonNode groups = contract.path("ordered_learning_groups");
        List<Integer> counts = List.of(
                groups.path("transaction_writes").size(),
                groups.path("progress_and_tags").size(),
                groups.path("selection_search_and_count").size(),
                groups.path("statistics_and_data_center").size());
        Set<String> keys = new HashSet<>();
        groups.properties().forEach(entry -> entry.getValue().forEach(item ->
                keys.add(item.path("route_id").asString()
                        + ":" + item.path("method").asString())));

        assertThat(partition.path("total_operation_count").asInt()).isEqualTo(71);
        assertThat(partition.path("phase6_page_shell_operation_count").asInt())
                .isEqualTo(21);
        assertThat(partition.path("cross_domain_transfer_operation_count").asInt())
                .isEqualTo(3);
        assertThat(partition.path("learning_backend_operation_count").asInt())
                .isEqualTo(47);
        assertThat(partition.path("already_migrated_learning_operation_count").asInt())
                .isEqualTo(2);
        assertThat(partition.path("remaining_learning_operation_count").asInt())
                .isEqualTo(45);
        assertThat(counts).containsExactly(9, 11, 9, 16);
        assertThat(keys).hasSize(45);
        assertThat(contract.path("already_migrated")).hasSize(2);
        assertThat(contract.path("page_shells")).hasSize(21);
        assertThat(contract.path("cross_domain_transfers")).hasSize(3);
        assertThat(partition.path("final_route_target").path("migrated").asInt())
                .isEqualTo(58);
        assertThat(partition.path("final_route_target").path("pending").asInt())
                .isEqualTo(553);
    }

    @Test
    void fixesNineTransactionWriteOperationsInOrder() throws Exception {
        JsonNode writes = contract().path("ordered_learning_groups")
                .path("transaction_writes");
        List<String> operations = new ArrayList<>();
        writes.forEach(item -> operations.add(
                item.path("method").asString() + " "
                        + item.path("path").asString()
                        + " [" + item.path("route_id").asString() + "]"));

        assertThat(operations).containsExactly(
                "POST /api/favorite [6d548bfd6830]",
                "POST /api/quiz/favorite [b52d3008d4d1]",
                "POST /api/record_result [87bb4fb340c8]",
                "POST /api/quiz/record_result [67dccafb3ea4]",
                "POST /api/quiz/study/learn/record [bf3cb0c4f9ab]",
                "POST /api/quiz/study/review/record [c797832c43db]",
                "POST /api/quiz/study/review/master [278e1eac5eb4]",
                "POST /api/user/checkin [59c9c7366ec3]",
                "PUT /api/quiz/questions/<int:question_id> [624b5ac217d0]");
    }

    @Test
    void bindsDurableAnswerIdempotencyAndCatalogOwnership() throws Exception {
        JsonNode contract = contract();
        JsonNode answer = contract.path("transaction_write_semantics")
                .path("answer_aliases");
        JsonNode idempotency = answer.path("target_optional_idempotency_key");
        JsonNode edit = contract.path("transaction_write_semantics")
                .path("question_edit");
        JsonNode boundary = contract.path("module_boundary");

        assertThat(idempotency.path("header").asString())
                .isEqualTo("Idempotency-Key");
        assertThat(idempotency.path("persistence").asString())
                .isEqualTo("PostgreSQL learning-owned durable receipt");
        assertThat(idempotency.path("same_actor_same_key_same_payload").asString())
                .isEqualTo("replay first committed response");
        assertThat(idempotency.path("same_actor_same_key_different_payload").asString())
                .isEqualTo("409 conflict");
        assertThat(idempotency.path("concurrent_same_key").asString())
                .contains("never double count");
        assertThat(edit.path("persistent_owner").asString()).isEqualTo("catalog");
        assertThat(edit.path("required_dependency").asString())
                .isEqualTo("learning -> catalog::api");
        assertThat(boundary.path("learning_direct_catalog_table_write_forbidden")
                .asBoolean()).isTrue();
        assertThat(boundary.path("cross_module_database_transaction_forbidden")
                .asBoolean()).isTrue();
    }

    @Test
    void authorizesOnlyFixedCommitGoldenCapture() throws Exception {
        JsonNode contract = contract();
        JsonNode authorization = contract.path("authorization");
        JsonNode route = contract.path("route_state");
        JsonNode control = contract.path("control_plane");

        assertThat(authorization.path("route_scope_partition_closed").asBoolean())
                .isTrue();
        assertThat(authorization.path("transaction_write_golden_capture_authorized")
                .asBoolean()).isTrue();
        for (String field : List.of(
                "transaction_write_implementation_authorized",
                "progress_and_tags_implementation_authorized",
                "selection_search_and_count_implementation_authorized",
                "statistics_and_data_center_implementation_authorized",
                "production_schema_or_index",
                "flyway_baseline_or_migration",
                "real_data_migration_execution",
                "legacy_runtime_permanently_disabled",
                "route_or_openapi_delta",
                "client_gateway_or_proxy_change",
                "production_cutover")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
        assertThat(route.path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(route.path("pending_operation_count").asInt()).isEqualTo(598);
        assertThat(route.path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(control.path("bootstrap").asBoolean()).isTrue();
        assertThat(control.path("current_control_sources_external_git_anchor_complete")
                .asBoolean()).isFalse();
        assertThat(control.path("self_signed").asBoolean()).isFalse();
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
