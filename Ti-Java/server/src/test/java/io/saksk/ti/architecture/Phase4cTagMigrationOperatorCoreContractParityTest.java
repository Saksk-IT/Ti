package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity for the Phase 4C tag-migration operator core. */
class Phase4cTagMigrationOperatorCoreContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final Map<String, String> NODE_A_RUNTIME_ADDITIONS =
            Map.of(
                    "server/src/main/java/io/saksk/ti/learning/"
                            + "infrastructure/migration/"
                            + "LegacyPersonalBankTagGlobalPreflight.java",
                    "cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76",
                    "server/src/main/java/io/saksk/ti/learning/"
                            + "infrastructure/migration/"
                            + "LegacyPersonalBankTagPreflightParser.java",
                    "c3311e28f33c8bc447fd72191af696ceca333162747e94eb91681dd75c0f5bf3",
                    "server/src/main/java/io/saksk/ti/learning/"
                            + "infrastructure/migration/"
                            + "LegacyPersonalBankTagPreflightReport.java",
                    "d7d988f5bfe7c86e30a5410e8eac0032a24ad5c85011b6c03de159c97d3ff750");

    @Test
    void loadsFixedIdentityPredecessorAndNodeBGitAuthority() throws Exception {
        JsonNode contract = contract();

        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-tag-migration-operator-core-contract");
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(
                        Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                                .payloadSha256());
        assertThat(Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .physicalSha256()).hasSize(64);
        assertThat(Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .byteCount()).isPositive();

        JsonNode predecessor = contract.path("predecessor");
        assertThat(predecessor.path("sha256").asString()).isEqualTo(
                "2d65af0c4fd725dceef5d99d2b2dd06804f78f0250f0136a662ca6fb184ccaa6");
        assertThat(predecessor.path("document_payload_sha256").asString())
                .isEqualTo(
                        "840d8e06a755fc6c01f5357411023fd875ec5dd87e322608252782b1bbc39542");
        assertThat(predecessor.path("byte_count").asLong()).isEqualTo(15_550L);
        assertThat(predecessor.path("immutable").asBoolean()).isTrue();

        JsonNode git = contract.path("node_b_git_authority");
        assertThat(git.path("implementation_checkpoint_commit_oid").asString())
                .isEqualTo("ea894b3a02787a91b688d7295cace37139f7f486");
        assertThat(git.path("external_anchor_checkpoint")
                .path("commit_oid").asString()).isEqualTo(
                "bbeb08efcccb0b9974dfefa2044aab43e0675f6f");
        assertThat(git.path("external_anchor_artifact_count").asInt())
                .isEqualTo(6);
        assertThat(git.path("ordinary_build_and_load_require_git").asBoolean())
                .isFalse();
        assertThat(git.path("live_head_main_or_origin_authority").asBoolean())
                .isFalse();
    }

    @Test
    void fixesExactThirtyFourTransitionsAndFortyNinePhysicalSources()
            throws Exception {
        JsonNode contract = contract();
        JsonNode successors = contract.path("historical_source_successors");
        JsonNode authority = contract.path("source_authority");

        assertThat(authority.path("historical_authority_source_count").asInt())
                .isEqualTo(3);
        assertThat(properties(authority.path("historical_authority_sources")))
                .containsExactlyInAnyOrder(
                        "docs/refactor/phase4c/"
                                + "personal-bank-tag-migration-durable-ledger-"
                                + "freeze-design-post-push-anchor-contract.json",
                        "docs/refactor/phase4c/"
                                + "personal-bank-tag-migration-global-"
                                + "preflight-contract.json",
                        "docs/refactor/phase4c/"
                                + "personal-bank-user-counts-http-target-"
                                + "execution-contract.json");
        assertThat(successors.path("override_count").asInt()).isEqualTo(34);
        assertThat(properties(successors.path("overrides")))
                .containsExactlyInAnyOrderElementsOf(
                        Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                                .successorPaths());
        assertThat(authority.path("fixed_non_control_source_count").asInt())
                .isEqualTo(49);
        assertThat(authority.path("fixed_non_control_sources")).hasSize(49);
        assertThat(authority.path("control_source_count").asInt()).isEqualTo(7);
        assertThat(authority.path(
                "control_sources_excluded_from_self_authority").asBoolean())
                .isTrue();
        assertThat(authority.path(
                "current_control_sources_external_git_anchor_complete")
                .asBoolean()).isFalse();

        successors.path("overrides").properties().forEach(entry -> {
            try {
                var transition =
                        Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                                .sourceTransition(root(), entry.getKey());
                assertThat(transition).as(entry.getKey()).isNotNull();
                assertThat(transition.source()).isEqualTo(entry.getKey());
                assertThat(transition.acceptedSha256()).hasSize(64);
                assertThat(transition.successorSha256()).hasSize(64);
                assertThat(transition.successorSha256())
                        .isNotEqualTo(transition.acceptedSha256());
            } catch (Exception error) {
                throw new AssertionError(error);
            }
        });
        assertThat(Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .sourceTransition(root(), "tools/unknown.py")).isNull();
        assertThat(Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .sourceTransition(root(), "../outside")).isNull();
    }

    @Test
    void composesExactRuntimeViewsFromNodeAToNodeC() throws Exception {
        JsonNode contract = contract();
        Map<String, String> accepted = acceptedRuntime();
        Map<String, String> current = currentRuntime(contract, accepted);

        var full = Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .validateProductionRuntimeSuccessor(
                        root(), accepted, current, "full_runtime");
        assertThat(full.acceptedFileCount()).isEqualTo(300);
        assertThat(full.acceptedManifestSha256()).isEqualTo(
                "8d28a382447c8756b2ec4cfc4107bc55fd744587d81a8835b71eee1f1942fbb3");
        assertThat(full.currentFileCount()).isEqualTo(307);
        assertThat(full.currentManifestSha256()).isEqualTo(contract.path(
                "production_runtime_successor")
                .path("current_manifest_sha256").asString());
        assertThat(full.addedFiles()).hasSize(7);
        assertThat(full.changedFiles()).containsOnlyKeys(
                "server/src/main/java/io/saksk/ti/learning/"
                        + "infrastructure/migration/"
                        + "LegacyPersonalBankTagGlobalPreflight.java");
        assertThat(full.deletedFiles()).isEmpty();

        Map<String, String> acceptedMain = learningPersonalBank(accepted);
        Map<String, String> currentMain = learningPersonalBank(current);
        var main = Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .validateProductionRuntimeSuccessor(
                        root(), acceptedMain, currentMain,
                        "learning_personalbank_main");
        assertThat(main.acceptedFileCount()).isEqualTo(43);
        assertThat(main.currentFileCount()).isEqualTo(50);
        assertThat(main.currentManifestSha256()).isEqualTo(contract.path(
                "production_runtime_successor")
                .path("learning_personalbank_main")
                .path("current_manifest_sha256").asString());

        Map<String, String> changed = new TreeMap<>(current);
        changed.put(changed.keySet().iterator().next(), "f".repeat(64));
        assertThatThrownBy(() ->
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(), accepted, changed, "full_runtime"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("current production manifest");
        Map<String, String> wrongAccepted = new TreeMap<>(accepted);
        wrongAccepted.put(
                wrongAccepted.keySet().iterator().next(), "f".repeat(64));
        assertThatThrownBy(() ->
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(), wrongAccepted, current,
                                "full_runtime"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("accepted production manifest");
        assertThatThrownBy(() ->
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(), accepted, current, "unknown"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("unknown production view");
    }

    @Test
    void appendsExactlyOneWormNodeWithoutProductionAuthority()
            throws Exception {
        JsonNode contract = contract();
        JsonNode worm = contract.path("worm_successor");

        var successor = Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .validateWormSuccessor(
                        root(),
                        "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344",
                        "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17");
        assertThat(successor.acceptedChainNodeCount()).isEqualTo(7);
        assertThat(successor.currentChainNodeCount()).isEqualTo(8);
        assertThat(successor.currentReportSha256()).isEqualTo(
                worm.path("current_report").path("sha256").asString());
        assertThat(successor.currentBuildContextSha256()).isEqualTo(
                worm.path("current_build_context_sha256").asString());
        assertThat(worm.path("appended_node_count").asInt()).isEqualTo(1);
        assertThat(worm.path("historical_nodes_rewritten").asBoolean()).isFalse();
        assertThat(worm.path("production_database_version").asString())
                .isEqualTo("unknown");
        assertThat(worm.path("flyway_baseline_created").asBoolean()).isFalse();

        assertThatThrownBy(() ->
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .validateWormSuccessor(
                                root(), "f".repeat(64),
                                "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("accepted WORM authority");
    }

    @Test
    void closesOnlyOperatorEvidenceAndKeepsRouteAndProductionClosed()
            throws Exception {
        JsonNode contract = contract();
        JsonNode authorization = contract.path("authorization");

        JsonNode operator = contract.path("operator_core_implementation");
        assertThat(operator.path("explicit_callable_only").asBoolean()).isTrue();
        assertThat(operator.path(
                "spring_component_or_bean_registration").asBoolean()).isFalse();
        assertThat(operator.path(
                "command_line_runner_scheduler_or_http_registration")
                .asBoolean()).isFalse();
        assertThat(operator.path(
                "production_data_source_wiring").asBoolean()).isFalse();
        JsonNode writerReceipts = operator.path("writer_stop_receipts");
        assertThat(properties(writerReceipts)).containsExactlyInAnyOrder(
                "source_writer_stop_receipt_sha256",
                "target_writer_stop_receipt_sha256",
                "membership_writer_stop_receipt_sha256",
                "pairwise_distinct_required",
                "single_collapsed_receipt_allowed",
                "all_three_bound_to_ledger_receipts_and_recovery");
        for (String field : Set.of(
                "source_writer_stop_receipt_sha256",
                "target_writer_stop_receipt_sha256",
                "membership_writer_stop_receipt_sha256")) {
            assertThat(writerReceipts.path(field).asString()).as(field)
                    .isEqualTo("required_separate_digest");
        }
        assertThat(writerReceipts.path(
                "single_collapsed_receipt_allowed").asBoolean()).isFalse();
        assertThat(writerReceipts.path(
                "pairwise_distinct_required").asBoolean()).isTrue();
        assertThat(writerReceipts.path(
                "all_three_bound_to_ledger_receipts_and_recovery")
                .asBoolean()).isTrue();

        JsonNode schema = contract.path("schema_and_acl_verification");
        assertThat(schema.path("expected_catalog_sha256").asString())
                .isEqualTo(
                        "f4361024a36e4e509f1ca4203c2dca5ecfd5bf1eded036e462bbbb20f395f99c");
        JsonNode retry = contract.path(
                "bounded_retry_and_ambiguity_recovery");
        assertThat(retry.path("commit_ack_discard_evidence").asString())
                .isEqualTo("deterministic_test_fixture");
        assertThat(retry.path(
                "real_network_commit_ack_loss_evidenced").asBoolean())
                .isFalse();
        JsonNode invariants = contract.path(
                "source_target_receipt_invariants");
        assertThat(invariants.path(
                "partial_receipts_must_be_strict_manifest_prefix")
                .asBoolean()).isTrue();
        assertThat(invariants.path(
                "sparse_or_out_of_order_partial_receipts_block")
                .asBoolean()).isTrue();
        JsonNode evidence = contract.path("evidence");
        assertThat(evidence.path("targeted_unit_test_count").asInt())
                .isEqualTo(83);
        assertThat(evidence.path(
                "sparse_partial_receipt_business_facts_and_existing_receipts_unchanged")
                .asBoolean()).isTrue();
        assertThat(evidence.path(
                "sparse_partial_receipt_durable_block_run_and_single_audit_only")
                .asBoolean()).isTrue();

        assertThat(strings(authorization.path("newly_closed_gates")))
                .containsExactlyInAnyOrder(
                        "operator_core_evidence_closed",
                        "bounded_40001_40P01_retry_implemented",
                        "operator_migration_implementation");
        for (String field : Set.of(
                "migration_global_preflight_evidence_closed",
                "migration_durable_ledger_freeze_design_evidence_closed",
                "operator_core_evidence_closed",
                "bounded_40001_40P01_retry_implemented",
                "operator_migration_implementation")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isTrue();
        }
        for (String field : Set.of(
                "migration_design_closed",
                "production_durable_ledger_or_tombstone",
                "production_source_write_freeze_evidence_closed",
                "production_target_write_freeze_evidence_closed",
                "production_membership_write_freeze_or_digest_recheck_evidence_closed",
                "production_connection_drain_evidence_closed",
                "production_schema_or_index", "flyway_baseline_or_migration",
                "backup_and_rollback_evidence_closed",
                "real_data_migration_execution",
                "legacy_runtime_permanently_disabled",
                "route_or_openapi_delta", "client_gateway_or_proxy_change",
                "production_cutover",
                "current_node_control_sources_external_git_anchor_complete")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
        JsonNode route = contract.path("route_state");
        assertThat(route.path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(route.path("pending_operation_count").asInt()).isEqualTo(598);
        assertThat(route.path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(route.path("legacy_flask_remains_production_owner")
                .asBoolean()).isTrue();
        assertThat(Files.readString(root().resolve(
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .contractRelative()), StandardCharsets.UTF_8))
                .doesNotContain("NODEC_CANARY_RAW_TAG_7F21");
    }

    @Test
    void minimalGitlessFixtureLoadsAndPhysicalTamperFails(
            @TempDir Path temporary
    ) throws Exception {
        Path valid = temporary.resolve("valid");
        copyFixture(valid, false);
        assertThat(valid.resolve(".git")).doesNotExist();
        assertThat(Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .load(valid).path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-tag-migration-operator-core-contract");

        Path sourceTamper = temporary.resolve("source-tamper");
        copyFixture(sourceTamper, false);
        Files.writeString(sourceTamper.resolve(
                        "server/src/main/java/io/saksk/ti/learning/"
                                + "infrastructure/migration/BoundedSqlRetry.java"),
                "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .load(sourceTamper))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed source physical bytes");

        Path predecessorTamper = temporary.resolve("predecessor-tamper");
        copyFixture(predecessorTamper, false);
        Files.writeString(predecessorTamper.resolve(
                        "docs/refactor/phase4c/"
                                + "personal-bank-tag-migration-durable-ledger-"
                                + "freeze-design-post-push-anchor-contract.json"),
                " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .load(predecessorTamper))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("predecessor physical bytes");

        Path symlink = temporary.resolve("symlink");
        copyFixture(symlink, false);
        Path report = symlink.resolve(
                "docs/refactor/phase4c/"
                        + "personal-bank-tag-migration-operator-core-"
                        + "worm-evidence.json");
        Path outside = symlink.resolve("outside.json");
        Files.move(report, outside);
        Files.createSymbolicLink(report, outside);
        assertThatThrownBy(() ->
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .load(symlink))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("symlink");
    }

    @Test
    void semanticGitlessFixtureExecutesRuntimeAndWormBridges(
            @TempDir Path temporary
    ) throws Exception {
        Path fixture = temporary.resolve("semantic");
        copyFixture(fixture, true);
        assertThat(fixture.resolve(".git")).doesNotExist();
        JsonNode contract =
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .load(fixture);
        Map<String, String> accepted = acceptedRuntime(fixture);
        Map<String, String> current = currentRuntime(contract, accepted);

        assertThat(Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .validateProductionRuntimeSuccessor(
                        fixture, accepted, current, "full_runtime")
                .currentFileCount()).isEqualTo(307);
        assertThat(Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .validateWormSuccessor(
                        fixture,
                        "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344",
                        "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17")
                .currentChainNodeCount()).isEqualTo(8);
    }

    @Test
    void inMemoryOverclaimsAndControlPlaneRuntimeEscapesFailClosed()
            throws Exception {
        JsonNode fixed = contract();
        for (Mutation mutation : Set.of(
                new Mutation("route", value -> ((ObjectNode) value
                        .path("route_state")).put(
                        "migrated_operation_count", 14)),
                new Mutation("cutover", value -> ((ObjectNode) value
                        .path("authorization")).put(
                        "production_cutover", true)),
                new Mutation("transition", value -> ((ObjectNode) value
                        .path("historical_source_successors")
                        .path("overrides")
                        .path("infra/phase2/README.md")).put(
                        "successor_sha256", "f".repeat(64))),
                new Mutation("WORM", value -> ((ObjectNode) value
                        .path("worm_successor")).put(
                        "current_chain_node_count", 9)))) {
            JsonNode changed = fixed.deepCopy();
            mutation.action().apply(changed);
            assertThatThrownBy(() ->
                    Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                            .validate(changed, root()))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }

        String source = Files.readString(root().resolve(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cTagMigrationOperatorCore"
                        + "SuccessorAcceptance.java"),
                StandardCharsets.UTF_8).toLowerCase();
        assertThat(source).doesNotContain(
                "python3", "/usr/bin/python", "org.eclipse.jgit",
                "rev-parse", "origin/main", "runtime.getruntime().exec");
    }

    private static JsonNode contract() throws Exception {
        return Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .load(root());
    }

    private static Map<String, String> acceptedRuntime() throws Exception {
        return acceptedRuntime(root());
    }

    private static Map<String, String> acceptedRuntime(Path fixtureRoot)
            throws Exception {
        JsonNode historical = JSON.readTree(Files.readAllBytes(
                fixtureRoot.resolve(
                        "docs/refactor/phase4c/"
                                + "personal-bank-user-counts-http-target-"
                                + "execution-contract.json")));
        TreeMap<String, String> accepted = new TreeMap<>();
        historical.path("production_surface").path("files").properties()
                .forEach(entry -> accepted.put(
                        entry.getKey(), entry.getValue().asString()));
        accepted.putAll(NODE_A_RUNTIME_ADDITIONS);
        return Map.copyOf(accepted);
    }

    private static Map<String, String> currentRuntime(
            JsonNode contract,
            Map<String, String> accepted
    ) {
        JsonNode runtime = contract.path("production_runtime_successor");
        TreeMap<String, String> current = new TreeMap<>(accepted);
        runtime.path("added_files").properties().forEach(entry ->
                current.put(entry.getKey(), entry.getValue().asString()));
        runtime.path("changed_files").properties().forEach(entry ->
                current.put(entry.getKey(), entry.getValue().asString()));
        return Map.copyOf(current);
    }

    private static Map<String, String> learningPersonalBank(
            Map<String, String> files
    ) {
        TreeMap<String, String> result = new TreeMap<>();
        files.forEach((relative, digest) -> {
            if (relative.startsWith(
                    "server/src/main/java/io/saksk/ti/learning/")
                    || relative.startsWith(
                    "server/src/main/java/io/saksk/ti/personalbank/")) {
                result.put(relative, digest);
            }
        });
        return Map.copyOf(result);
    }

    private static void copyFixture(Path targetRoot, boolean semantic)
            throws Exception {
        Set<String> paths = new LinkedHashSet<>(semantic
                ? Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .semanticFixturePaths(root())
                : Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .minimalFixturePaths());
        for (String relative : paths) {
            Path target = targetRoot.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(root().resolve(relative), target,
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

    @SuppressWarnings("unused")
    private static String sha256(Path path) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(Files.readAllBytes(path)));
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }

    private record Mutation(String label, MutationAction action) {
    }

    @FunctionalInterface
    private interface MutationAction {
        void apply(JsonNode value);
    }
}
