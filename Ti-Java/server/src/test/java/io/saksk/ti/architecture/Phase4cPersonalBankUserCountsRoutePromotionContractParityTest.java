package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.Map;
import java.util.Objects;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity gate for the Phase 4C route-promotion successor. */
class Phase4cPersonalBankUserCountsRoutePromotionContractParityTest {

    @Test
    void promotesExactlyTwoGetOperationsToThirteenMigrated() throws Exception {
        JsonNode contract = Phase4cHttpRoutePromotionSuccessorAcceptance.load(root());
        JsonNode routes = contract.path("route_authority").path("promoted_routes");
        assertThat(routes).hasSize(2);
        assertThat(routes.get(0).path("route_id").asString()).isEqualTo("6858f6fa506f");
        assertThat(routes.get(1).path("route_id").asString()).isEqualTo("006913d0d956");
        assertThat(routes.get(0).path("method").asString()).isEqualTo("GET");
        assertThat(routes.get(1).path("method").asString()).isEqualTo("GET");
        JsonNode route = contract.path("route_state");
        assertThat(route.path("total_operation_count").asInt()).isEqualTo(611);
        assertThat(route.path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(route.path("pending_operation_count").asInt()).isEqualTo(598);
        assertThat(route.path("production_cutover_operation_count").asInt()).isZero();
    }

    @Test
    void bindsEligibilityAndEveryRouteAuthoritySource() throws Exception {
        JsonNode contract = Phase4cHttpRoutePromotionSuccessorAcceptance.load(root());
        JsonNode parity = contract.path("parity");
        assertThat(parity.path("pg16_pg18_termination_fingerprints_complete").asBoolean())
                .isTrue();
        assertThat(parity.path("real_tomcat_complete_response_header_matrix_complete")
                .asBoolean()).isTrue();
        assertThat(parity.path("same_service_redis_outage_and_recovery_complete")
                .asBoolean()).isTrue();
        assertThat(parity.path("full_target_parity_closed").asBoolean()).isTrue();
        assertThat(parity.path("route_migration_eligible").asBoolean()).isTrue();
        assertThat(Phase4cHttpRoutePromotionSuccessorAcceptance.sources()).hasSize(6);
        for (Map.Entry<String, Phase4cHttpRoutePromotionSuccessorAcceptance.Artifact> entry
                : Phase4cHttpRoutePromotionSuccessorAcceptance.sources().entrySet()) {
            assertThat(Files.readAllBytes(root().resolve(entry.getKey()))).hasSize(
                    Math.toIntExact(entry.getValue().bytes()));
        }
    }

    @Test
    void leavesCutoverOperatorSchemaAndDataMigrationForbidden() throws Exception {
        JsonNode contract = Phase4cHttpRoutePromotionSuccessorAcceptance.load(root());
        JsonNode authorization = contract.path("authorization");
        assertThat(authorization.path("two_legacy_get_routes_migrated").asBoolean())
                .isTrue();
        assertThat(authorization.path("derived_head_and_options_count_as_migrated")
                .asBoolean()).isFalse();
        assertThat(authorization.path("production_cutover").asBoolean()).isFalse();
        assertThat(authorization.path("operator_migration_implementation").asBoolean())
                .isFalse();
        assertThat(authorization.path("production_schema_or_index").asBoolean()).isFalse();
        assertThat(authorization.path("real_data_migration_execution").asBoolean()).isFalse();
        assertThat(contract.path("route_authority")
                .path("historical_matrix_and_deltas_overwritten").asBoolean()).isFalse();
    }

    @Test
    void loadsFromAGitlessMinimalFixture(@TempDir Path temporary) throws Exception {
        copyFixture(temporary);
        assertThat(temporary.resolve(".git")).doesNotExist();
        assertThat(Phase4cHttpRoutePromotionSuccessorAcceptance.load(temporary)
                .path("route_state").path("migrated_operation_count").asInt())
                .isEqualTo(13);
    }

    @Test
    void rejectsContractAndSuccessorDeltaTampering(@TempDir Path temporary) throws Exception {
        copyFixture(temporary);
        Path contract = temporary.resolve(
                Phase4cHttpRoutePromotionSuccessorAcceptance.contractRelative());
        Files.writeString(contract, " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cHttpRoutePromotionSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes drifted");

        copyFixture(temporary);
        Path delta = temporary.resolve(
                "docs/refactor/phase4c/route-parity-successor-delta.csv");
        Files.writeString(delta, " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cHttpRoutePromotionSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes drifted");
    }

    private static void copyFixture(Path targetRoot) throws Exception {
        copy(Phase4cHttpRoutePromotionSuccessorAcceptance.contractRelative(), targetRoot);
        for (String relative : Phase4cHttpRoutePromotionSuccessorAcceptance.sources().keySet()) {
            copy(relative, targetRoot);
        }
    }

    private static void copy(String relative, Path targetRoot) throws Exception {
        Path target = targetRoot.resolve(relative);
        Files.createDirectories(target.getParent());
        Files.copy(root().resolve(relative), target, StandardCopyOption.REPLACE_EXISTING);
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
