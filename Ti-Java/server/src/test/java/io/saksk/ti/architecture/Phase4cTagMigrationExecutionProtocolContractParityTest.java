package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity for the Phase 4C execution-protocol contract. */
class Phase4cTagMigrationExecutionProtocolContractParityTest {

    @Test
    void loadsFixedC2IdentityAndGitlessContract() throws Exception {
        JsonNode contract = contract();
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-tag-migration-execution-protocol-"
                        + "contract");
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(
                        Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                                .payloadSha256());
        assertThat(
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .physicalSha256()).hasSize(64);
        assertThat(
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .byteCount()).isPositive();

        JsonNode predecessor = contract.path("predecessor");
        assertThat(predecessor.path("sha256").asString()).isEqualTo(
                "0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936");
        assertThat(predecessor.path("document_payload_sha256").asString())
                .isEqualTo(
                        "fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64");
        assertThat(predecessor.path("byte_count").asLong())
                .isEqualTo(84_461L);
        assertThat(predecessor.path("fixed_commit_oid").asString())
                .isEqualTo("4c47d1ea220ae9e310338bbf23b74d87d477e20f");
        assertThat(predecessor.path("immutable").asBoolean()).isTrue();

        JsonNode authority = contract.path("source_authority");
        assertThat(authority.path("ordinary_build_and_load_are_gitless")
                .asBoolean()).isTrue();
        assertThat(authority.path("dynamic_source_discovery").asBoolean())
                .isFalse();
        assertThat(authority.path("live_head_main_or_origin_authority")
                .asBoolean()).isFalse();
        assertThat(authority.path("fixed_c2_commit_replay_is_explicit_only")
                .asBoolean()).isTrue();
    }

    @Test
    void fixesExactSevenControlElevenImplementationAndThirtySevenTransitions()
            throws Exception {
        JsonNode contract = contract();
        JsonNode authority = contract.path("source_authority");
        JsonNode successors = contract.path("historical_source_successors");
        assertThat(authority.path("control_source_count").asInt())
                .isEqualTo(7);
        assertThat(authority.path("implementation_source_count").asInt())
                .isEqualTo(11);
        assertThat(authority.path("transition_source_count").asInt())
                .isEqualTo(37);
        assertThat(authority.path("fixed_non_control_source_count").asInt())
                .isEqualTo(48);
        assertThat(authority.path("fixed_non_control_sources")).hasSize(48);
        assertThat(successors.path("override_count").asInt()).isEqualTo(37);
        assertThat(properties(successors.path("overrides")))
                .containsExactlyInAnyOrderElementsOf(
                        Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                                .successorPaths());
        assertThat(authority.path(
                "control_sources_excluded_from_self_authority").asBoolean())
                .isTrue();
        assertThat(authority.path(
                "current_control_sources_external_git_anchor_complete")
                .asBoolean()).isFalse();

        for (String relative
                : Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                .successorPaths()) {
            var transition =
                    Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                            .sourceTransition(root(), relative);
            assertThat(transition).as(relative).isNotNull();
            assertThat(transition.source()).isEqualTo(relative);
            assertThat(transition.acceptedSha256())
                    .isEqualTo(
                            Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                                    .acceptedSha256(relative));
            assertThat(transition.successorSha256())
                    .isEqualTo(
                            Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                                    .successorSha256(root(), relative));
            assertThat(transition.acceptedSha256()).hasSize(64);
            assertThat(transition.successorSha256()).hasSize(64);
            assertThat(transition.successorSha256())
                    .isNotEqualTo(transition.acceptedSha256());
        }
        assertThat(
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .sourceTransition(root(), "unknown")).isNull();
        assertThat(
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .acceptedSha256("unknown")).isNull();
        assertThat(
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .successorSha256(root(), "unknown")).isNull();
    }

    @Test
    void fixesRuntimeWormAndRouteWithoutProductionAuthority()
            throws Exception {
        JsonNode contract = contract();
        JsonNode runtime = contract.path("production_runtime_successor");
        assertThat(runtime.path("accepted_file_count").asInt()).isEqualTo(307);
        assertThat(runtime.path("current_file_count").asInt()).isEqualTo(311);
        assertThat(runtime.path("exact_delta").asString()).isEqualTo("4A0M0D");
        assertThat(runtime.path("added_files")).hasSize(4);
        assertThat(runtime.path("changed_files")).isEmpty();
        assertThat(runtime.path("deleted_files")).isEmpty();
        assertThat(runtime.path("learning_personalbank_main")
                .path("accepted_file_count").asInt()).isEqualTo(50);
        assertThat(runtime.path("learning_personalbank_main")
                .path("current_file_count").asInt()).isEqualTo(54);

        JsonNode worm = contract.path("worm_successor");
        assertThat(worm.path("accepted_chain_node_count").asInt())
                .isEqualTo(8);
        assertThat(worm.path("current_chain_node_count").asInt())
                .isEqualTo(9);
        assertThat(worm.path("appended_node_count").asInt()).isOne();
        assertThat(worm.path("historical_nodes_rewritten").asBoolean())
                .isFalse();
        var wormSuccessor =
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .validateWormSuccessor(
                                root(),
                                "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f",
                                "29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc");
        assertThat(wormSuccessor.acceptedChainNodeCount()).isEqualTo(8);
        assertThat(wormSuccessor.currentChainNodeCount()).isEqualTo(9);

        JsonNode route = contract.path("route_state");
        assertThat(route.path("migrated_operation_count").asInt())
                .isEqualTo(13);
        assertThat(route.path("pending_operation_count").asInt())
                .isEqualTo(598);
        assertThat(route.path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(route.path("legacy_flask_remains_production_owner")
                .asBoolean()).isTrue();
    }

    @Test
    void closesOnlyThreeAuthorizedGates() throws Exception {
        JsonNode authorization = contract().path("authorization");
        assertThat(strings(authorization.path("newly_closed_gates")))
                .containsExactlyInAnyOrder(
                        "migration_execution_protocol_implemented",
                        "cryptographic_evidence_verifier_implemented",
                        "local_test_backup_restore_execution_rehearsal_closed");
        assertThat(authorization.path(
                "migration_execution_protocol_implemented").asBoolean())
                .isTrue();
        assertThat(authorization.path(
                "cryptographic_evidence_verifier_implemented").asBoolean())
                .isTrue();
        assertThat(authorization.path(
                "local_test_backup_restore_execution_rehearsal_closed")
                .asBoolean()).isTrue();
        for (String field : Set.of(
                "migration_design_closed",
                "production_durable_ledger_or_tombstone",
                "production_source_write_freeze_evidence_closed",
                "production_target_write_freeze_evidence_closed",
                "production_membership_write_freeze_or_digest_recheck_evidence_closed",
                "production_connection_drain_evidence_closed",
                "production_schema_or_index",
                "flyway_baseline_or_migration",
                "backup_and_rollback_evidence_closed",
                "real_data_migration_execution",
                "production_trust_roots_or_key_rotation_audit",
                "durable_evidence_nonce_journal", "operator_runtime_wiring",
                "legacy_runtime_permanently_disabled",
                "route_or_openapi_delta", "client_gateway_or_proxy_change",
                "production_cutover")) {
            assertThat(authorization.path(field).asBoolean())
                    .as(field).isFalse();
        }
    }

    @Test
    void candidateCryptoProtocolAndRehearsalStayBounded() throws Exception {
        JsonNode contract = contract();
        JsonNode protocol = contract.path("execution_protocol");
        assertThat(protocol.path("explicit_callable_only").asBoolean())
                .isTrue();
        assertThat(protocol.path(
                "candidate_requires_fresh_complete_data_eligible_preflight")
                .asBoolean()).isTrue();
        assertThat(protocol.path(
                "preverification_before_jdbc_or_membership_access")
                .asBoolean()).isTrue();
        assertThat(protocol.path(
                "execute_all_force_reset_skip_or_rollback_entrypoint")
                .asBoolean()).isFalse();

        JsonNode crypto = contract.path("cryptographic_evidence_verifier");
        assertThat(crypto.path("algorithm").asString())
                .isEqualTo("pure-Ed25519");
        assertThat(crypto.path("raw_public_key_bytes").asInt()).isEqualTo(32);
        assertThat(crypto.path("signature_bytes").asInt()).isEqualTo(64);
        assertThat(crypto.path("dynamic_algorithm_dispatch").asBoolean())
                .isFalse();
        assertThat(crypto.path("durable_nonce_or_evidence_uuid_journal")
                .asBoolean()).isFalse();

        JsonNode rehearsal = contract.path("local_disposable_rehearsal");
        assertThat(rehearsal.path("writer_identity_count").asInt())
                .isEqualTo(6);
        assertThat(rehearsal.path("writer_domain_expectation_count").asInt())
                .isEqualTo(18);
        assertThat(rehearsal.path(
                "disposable_database_role_dump_and_connection_residue")
                .asInt()).isZero();
        assertThat(rehearsal.path(
                "production_backup_restore_or_rollback_evidence")
                .asBoolean()).isFalse();
    }

    @Test
    void minimalGitlessFixtureLoadsAndPhysicalTamperFailsClosed(
            @TempDir Path temporaryDirectory
    ) throws Exception {
        Path fixture = temporaryDirectory.resolve("fixture");
        copyFixture(fixture);
        assertThat(
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .load(fixture).path("contract_id").asString())
                .isEqualTo(
                        "ti.phase4c.personal-bank-tag-migration-"
                                + "execution-protocol-contract");

        String relative =
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .successorPaths().iterator().next();
        Files.writeString(
                fixture.resolve(relative),
                "\n# tampered\n",
                StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed source drifted");
    }

    @Test
    void fixedLoaderRejectsSymlinkedSource(@TempDir Path temporaryDirectory)
            throws Exception {
        Path fixture = temporaryDirectory.resolve("fixture");
        copyFixture(fixture);
        String relative =
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .successorPaths().iterator().next();
        Path target = fixture.resolve(relative);
        Path real = target.resolveSibling(target.getFileName() + ".real");
        Files.move(target, real);
        Files.createSymbolicLink(target, real.getFileName());
        assertThatThrownBy(() ->
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("symlink");
    }

    private static JsonNode contract() throws Exception {
        return Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                .load(root());
    }

    private static void copyFixture(Path targetRoot) throws Exception {
        for (String relative
                : Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                .minimalFixturePaths()) {
            Path target = targetRoot.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(
                    root().resolve(relative),
                    target,
                    StandardCopyOption.COPY_ATTRIBUTES);
        }
    }

    private static Set<String> properties(JsonNode object) {
        Set<String> result = new LinkedHashSet<>();
        object.properties().forEach(entry -> result.add(entry.getKey()));
        return Set.copyOf(result);
    }

    private static Set<String> strings(JsonNode array) {
        Set<String> result = new LinkedHashSet<>();
        array.forEach(value -> result.add(value.asString()));
        return Set.copyOf(result);
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
