package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * Gitless Java acceptance for the Phase 4C tag-migration operator core.
 *
 * <p>The implementation mirrors the fixed cross-language acceptance without
 * invoking another runtime, discovering directories, or consulting a live Git
 * ref. Git replay of the fixed Node B checkpoint remains an explicit external
 * diagnostic; ordinary Java load is bound to immutable predecessor bytes.</p>
 */
final class Phase4cTagMigrationOperatorCoreSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-operator-core-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-tag-migration-operator-core-contract";
    private static final String CONTRACT_CAPTURED_AT =
            "2026-07-19T15:30:00+08:00";
    private static final String CONTRACT_SCOPE =
            "phase4c-learning-owned-personal-bank-tag-migration-operator-core";
    private static final String CONTRACT_STATUS =
            "operator_core_and_bounded_retry_evidence_closed_"
                    + "production_schema_freeze_backup_apply_and_cutover_"
                    + "unauthorized";

    private static final String CONTRACT_SHA256 =
            "2124d1b042f2df201ad3d8ca87fd19fa121b8d47cbaf51a60eb5271fe55b7fe8";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "28f0fa1a5ec1c2e795c60d472b47d0ccb16d1b838a30dd0e7ac69fe738f53778";
    private static final long CONTRACT_BYTE_COUNT = 50_467L;

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-durable-ledger-freeze-design-"
                    + "post-push-anchor-contract.json";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-tag-migration-durable-ledger-freeze-design-"
                    + "post-push-anchor-contract";
    private static final String PREDECESSOR_SHA256 =
            "2d65af0c4fd725dceef5d99d2b2dd06804f78f0250f0136a662ca6fb184ccaa6";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "840d8e06a755fc6c01f5357411023fd875ec5dd87e322608252782b1bbc39542";
    private static final long PREDECESSOR_BYTE_COUNT = 15_550L;

    private static final String NODE_B_ANCHOR_COMMIT =
            "bbeb08efcccb0b9974dfefa2044aab43e0675f6f";
    private static final String NODE_B_IMPLEMENTATION_COMMIT =
            "ea894b3a02787a91b688d7295cace37139f7f486";

    private static final String ACCEPTED_RUNTIME_MANIFEST_SHA256 =
            "8d28a382447c8756b2ec4cfc4107bc55fd744587d81a8835b71eee1f1942fbb3";
    private static final String ACCEPTED_MAIN_MANIFEST_SHA256 =
            "2cc855057a4b3b6b5693ad717404ea6b9828de3aa73ef9be8a9a1a62b177f751";
    private static final String CURRENT_RUNTIME_MANIFEST_SHA256 =
            "b1228337b60b752ff088c4e5b67ae21092ca75a07c437bae35cc67b39b1c8c25";
    private static final String CURRENT_MAIN_MANIFEST_SHA256 =
            "3abdc97486bbb9ec62a2d426063157e0ef3a990a34ca4862fc9e18580b4f60e9";

    private static final String ACCEPTED_WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-global-preflight-hardening-"
                    + "worm-evidence.json";
    private static final String ACCEPTED_WORM_SHA256 =
            "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344";
    private static final long ACCEPTED_WORM_BYTE_COUNT = 1_442L;
    private static final String ACCEPTED_BUILD_CONTEXT_SHA256 =
            "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17";
    private static final String CURRENT_WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-operator-core-"
                    + "worm-evidence.json";
    private static final String CURRENT_WORM_SHA256 =
            "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f";
    private static final long CURRENT_WORM_BYTE_COUNT = 1_442L;
    private static final String CURRENT_WORM_CAPTURED_AT =
            "2026-07-19T17:10:23Z";
    private static final String CURRENT_BUILD_CONTEXT_SHA256 =
            "29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc";
    private static final String DOCKERFILE_SHA256 =
            "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499";

    private static final String HASHER_RELATIVE =
            "infra/phase2/hash-java-build-context.sh";
    private static final String HISTORICAL_RUNTIME_CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-contract.json";
    private static final String HISTORICAL_RUNTIME_CONTRACT_SHA256 =
            "9f6c37c4217da83199403da8207ed4f89a3999fafd149f069afb520dee4d2460";
    private static final String HISTORICAL_RUNTIME_CONTRACT_PAYLOAD_SHA256 =
            "331c82ad941f4eeb3e07d1701271310f2b1dea91132794e4e5d1eb1b466fc458";
    private static final long HISTORICAL_RUNTIME_CONTRACT_BYTE_COUNT =
            74_597L;
    private static final String GLOBAL_PREFLIGHT_CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-global-preflight-contract.json";
    private static final String GLOBAL_PREFLIGHT_CONTRACT_SHA256 =
            "65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e";
    private static final String GLOBAL_PREFLIGHT_CONTRACT_PAYLOAD_SHA256 =
            "c7a94e88772a2453743f9821b165ae10f52650a41bf6dab78006d7058951159e";
    private static final long GLOBAL_PREFLIGHT_CONTRACT_BYTE_COUNT =
            102_931L;

    private static final String MIGRATION_MAIN_PREFIX =
            "server/src/main/java/io/saksk/ti/learning/"
                    + "infrastructure/migration/";
    private static final String GLOBAL_PREFLIGHT_MAIN_RELATIVE =
            MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagGlobalPreflight.java";

    private static final Set<String> PRODUCTION_ADDITION_PATHS = Set.of(
            MIGRATION_MAIN_PREFIX + "BoundedSqlRetry.java",
            MIGRATION_MAIN_PREFIX + "JdbcTagMigrationStore.java",
            MIGRATION_MAIN_PREFIX
                    + "LegacyPersonalBankTagMigrationOperatorCore.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationCommand.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationDigests.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationResult.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationSchemaVerifier.java");

    private static final Set<String> NODE_A_PRODUCTION_ADDITION_PATHS = Set.of(
            GLOBAL_PREFLIGHT_MAIN_RELATIVE,
            MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagPreflightParser.java",
            MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagPreflightReport.java");

    private static final Set<String> CONTROL_SOURCE_PATHS = Set.of(
            CONTRACT_RELATIVE,
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-operator-core.md",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCoreContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java",
            "tools/build_phase4c_tag_migration_operator_core_contract.py",
            "tools/phase4c_tag_migration_operator_core_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_tag_migration_operator_core_contract.py");

    private static final Set<String> SOURCE_TRANSITION_PATHS = Set.of(
            GLOBAL_PREFLIGHT_MAIN_RELATIVE,
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagGlobalPreflightTest.java",
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "tools/build_phase4c_tag_migration_global_preflight_contract.py",
            "tools/phase4c_tag_migration_global_preflight_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_tag_migration_global_preflight_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "ModuleContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "composition_contract.py",
            "tools/test_phase4b_personal_bank_all_shares_"
                    + "entry_contract.py",
            "tools/test_phase4b_personal_bank_all_shares_"
                    + "read_contract.py",
            "tools/test_phase4b_personal_bank_share_list_"
                    + "entry_contract.py",
            "tools/test_phase4b_personal_bank_share_list_"
                    + "read_contract.py",
            "tools/test_phase4b_personal_bank_user_counts_"
                    + "entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_"
                    + "entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_"
                    + "read_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "read_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "http_entry_contract.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/phase4c_http_target_execution_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_anchor_contract.py",
            "tools/phase4c_http_target_execution_anchor_"
                    + "successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java");

    private static final Set<String> FIXED_SOURCE_PATHS = Set.of(
            MIGRATION_MAIN_PREFIX + "BoundedSqlRetry.java",
            MIGRATION_MAIN_PREFIX + "JdbcTagMigrationStore.java",
            MIGRATION_MAIN_PREFIX
                    + "LegacyPersonalBankTagMigrationOperatorCore.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationCommand.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationDigests.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationResult.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationSchemaVerifier.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/BoundedSqlRetryTest.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagMigrationOperatorCoreStaticTest.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/Phase4cBoundedSqlRetryPostgresIT.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/Phase4cLegacyPersonalBankTagOperatorCoreIT.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/TagMigrationValueTypesTest.java",
            "server/src/test/resources/db/phase4c/"
                    + "076-legacy-personal-bank-tag-operator-core-schema.sql",
            "server/src/test/resources/db/phase4c/"
                    + "077-legacy-personal-bank-tag-operator-core-seed.sql",
            CURRENT_WORM_RELATIVE,
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "tools/build_phase4c_tag_migration_global_preflight_contract.py",
            "tools/phase4c_tag_migration_global_preflight_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_tag_migration_global_preflight_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "ModuleContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java",
            GLOBAL_PREFLIGHT_MAIN_RELATIVE,
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagGlobalPreflightTest.java",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "composition_contract.py",
            "tools/test_phase4b_personal_bank_all_shares_"
                    + "entry_contract.py",
            "tools/test_phase4b_personal_bank_all_shares_"
                    + "read_contract.py",
            "tools/test_phase4b_personal_bank_share_list_"
                    + "entry_contract.py",
            "tools/test_phase4b_personal_bank_share_list_"
                    + "read_contract.py",
            "tools/test_phase4b_personal_bank_user_counts_"
                    + "entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_"
                    + "entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_"
                    + "read_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "read_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "http_entry_contract.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/phase4c_http_target_execution_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_anchor_contract.py",
            "tools/phase4c_http_target_execution_anchor_"
                    + "successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java");

    private Phase4cTagMigrationOperatorCoreSuccessorAcceptance() {
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static String physicalSha256() {
        return CONTRACT_SHA256;
    }

    static String payloadSha256() {
        return CONTRACT_PAYLOAD_SHA256;
    }

    static long byteCount() {
        return CONTRACT_BYTE_COUNT;
    }

    static Set<String> successorPaths() {
        return SOURCE_TRANSITION_PATHS;
    }

    static SourceTransition sourceTransition(Path tiJavaRoot, String relative)
            throws IOException {
        if (!SOURCE_TRANSITION_PATHS.contains(relative)) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadContractEnvelope(root);
        JsonNode successors = contract.path("historical_source_successors");
        JsonNode overrides = successors.path("overrides");
        require(propertyNames(successors).equals(Set.of(
                        "predecessor_checkpoint", "override_count",
                        "overrides",
                        "accepted_bytes_replayable_from_fixed_predecessor",
                        "successor_external_git_anchor_complete",
                        "unknown_path"))
                        && successors.path("override_count").asInt()
                        == SOURCE_TRANSITION_PATHS.size()
                        && propertyNames(overrides).equals(
                        SOURCE_TRANSITION_PATHS),
                "operator-core source transition authority drifted");
        JsonNode descriptor = overrides.path(relative);
        require(propertyNames(descriptor).equals(Set.of(
                        "source", "accepted_sha256",
                        "accepted_byte_count", "successor_sha256",
                        "successor_byte_count")),
                "operator-core source transition descriptor drifted: "
                        + relative);
        SourceTransition transition = new SourceTransition(
                descriptor.path("source").asString(),
                descriptor.path("accepted_sha256").asString(),
                descriptor.path("accepted_byte_count").asLong(),
                descriptor.path("successor_sha256").asString(),
                descriptor.path("successor_byte_count").asLong());
        Path physical = fixedRegularFile(root, relative);
        String physicalSha256 = sha256(physical);
        long physicalByteCount = Files.size(physical);
        require(relative.equals(transition.source()),
                "operator-core source transition path drifted: " + relative);
        if (physicalByteCount == transition.successorByteCount()
                && physicalSha256.equals(transition.successorSha256())) {
            return transition;
        }
        Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                .SourceTransition nodeD;
        try {
            nodeD = Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                    .sourceTransition(root, relative);
        } catch (AssertionError error) {
            throw new AssertionError(
                    "operator-core source transition physical bytes drifted: "
                            + relative,
                    error);
        }
        require(nodeD != null
                        && relative.equals(nodeD.source())
                        && transition.successorSha256().equals(
                        nodeD.acceptedSha256())
                        && transition.successorByteCount()
                        == nodeD.acceptedByteCount()
                        && physicalSha256.equals(nodeD.successorSha256())
                        && physicalByteCount == nodeD.successorByteCount(),
                "operator-core Node D source transition drifted: "
                        + relative);
        return new SourceTransition(
                relative,
                transition.acceptedSha256(),
                transition.acceptedByteCount(),
                physicalSha256,
                physicalByteCount);
    }

    static ProductionRuntimeSuccessor validateProductionRuntimeSuccessor(
            Path tiJavaRoot,
            Map<String, String> acceptedFiles,
            Map<String, String> currentFiles,
            String view
    ) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode production = load(root).path("production_runtime_successor");
        JsonNode semantic;
        if ("full_runtime".equals(view)) {
            semantic = production;
        } else if ("learning_personalbank_main".equals(view)) {
            semantic = production.path("learning_personalbank_main");
        } else {
            throw new AssertionError(
                    "operator-core unknown production view: " + view);
        }

        TreeMap<String, String> normalizedAccepted =
                new TreeMap<>(acceptedFiles);
        TreeMap<String, String> normalizedCurrent =
                new TreeMap<>(currentFiles);
        require(normalizedAccepted.size()
                        == semantic.path("accepted_file_count").asInt()
                        && canonicalSha256(JSON.valueToTree(normalizedAccepted))
                        .equals(semantic.path(
                                "accepted_manifest_sha256").asString()),
                "operator-core rejected accepted production manifest");
        TreeMap<String, String> expectedCurrent =
                new TreeMap<>(normalizedAccepted);
        expectedCurrent.putAll(textMap(semantic.path("added_files")));
        expectedCurrent.putAll(textMap(semantic.path("changed_files")));
        strings(semantic.path("deleted_files"))
                .forEach(expectedCurrent::remove);
        boolean currentMatchesNodeC = normalizedCurrent.equals(expectedCurrent)
                && normalizedCurrent.size()
                == semantic.path("current_file_count").asInt()
                && canonicalSha256(JSON.valueToTree(normalizedCurrent))
                .equals(semantic.path(
                        "current_manifest_sha256").asString());
        if (!currentMatchesNodeC) {
            var nodeD = Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                    .validateProductionRuntimeSuccessor(
                            root, expectedCurrent, normalizedCurrent, view);
            require(nodeD.acceptedFileCount()
                            == semantic.path("current_file_count").asInt()
                            && nodeD.acceptedManifestSha256().equals(
                            semantic.path("current_manifest_sha256")
                                    .asString()),
                    "operator-core Node D production runtime drifted");
            TreeMap<String, String> additions = new TreeMap<>(
                    textMap(semantic.path("added_files")));
            TreeMap<String, String> changes = new TreeMap<>(
                    textMap(semantic.path("changed_files")));
            nodeD.addedFiles().forEach((relative, digest) -> {
                if (normalizedAccepted.containsKey(relative)) {
                    changes.put(relative, digest);
                } else {
                    additions.put(relative, digest);
                }
            });
            nodeD.changedFiles().forEach((relative, digest) -> {
                if (additions.containsKey(relative)) {
                    additions.put(relative, digest);
                } else {
                    changes.put(relative, digest);
                }
            });
            return new ProductionRuntimeSuccessor(
                    view,
                    semantic.path("accepted_file_count").asInt(),
                    semantic.path("accepted_manifest_sha256").asString(),
                    nodeD.currentFileCount(),
                    nodeD.currentManifestSha256(),
                    Map.copyOf(additions),
                    Map.copyOf(changes),
                    Set.copyOf(nodeD.deletedFiles()));
        }
        return new ProductionRuntimeSuccessor(
                view,
                semantic.path("accepted_file_count").asInt(),
                semantic.path("accepted_manifest_sha256").asString(),
                semantic.path("current_file_count").asInt(),
                semantic.path("current_manifest_sha256").asString(),
                Map.copyOf(textMap(semantic.path("added_files"))),
                Map.copyOf(textMap(semantic.path("changed_files"))),
                Set.copyOf(strings(semantic.path("deleted_files"))));
    }

    static WormSuccessor validateWormSuccessor(
            Path tiJavaRoot,
            String acceptedReportSha256,
            String acceptedBuildContextSha256
    ) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode worm = load(root).path("worm_successor");
        require(acceptedReportSha256.equals(
                        worm.path("accepted_report").path("sha256").asString())
                        && acceptedBuildContextSha256.equals(
                        worm.path("accepted_build_context_sha256").asString())
                        && worm.path("accepted_chain_node_count").asInt() == 7,
                "operator-core rejected accepted WORM authority");
        String physicalBuildContext = javaBuildContextSha256(root);
        String nodeCBuildContext = worm.path(
                "current_build_context_sha256").asString();
        if (!physicalBuildContext.equals(nodeCBuildContext)) {
            var nodeD = Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                    .validateWormSuccessor(
                            root,
                            worm.path("current_report").path("sha256")
                                    .asString(),
                            nodeCBuildContext);
            require(nodeD.acceptedReportSha256().equals(
                            worm.path("current_report").path("sha256")
                                    .asString())
                            && nodeD.acceptedBuildContextSha256().equals(
                            nodeCBuildContext)
                            && nodeD.acceptedChainNodeCount() == 8
                            && nodeD.currentChainNodeCount() == 9
                            && nodeD.currentBuildContextSha256().equals(
                            physicalBuildContext),
                    "operator-core Node D WORM bridge drifted");
            return new WormSuccessor(
                    acceptedReportSha256,
                    acceptedBuildContextSha256,
                    worm.path("accepted_chain_node_count").asInt(),
                    nodeD.currentReportSha256(),
                    physicalBuildContext,
                    nodeD.currentChainNodeCount());
        }
        return new WormSuccessor(
                acceptedReportSha256,
                acceptedBuildContextSha256,
                worm.path("accepted_chain_node_count").asInt(),
                worm.path("current_report").path("sha256").asString(),
                physicalBuildContext,
                worm.path("current_chain_node_count").asInt());
    }

    static Set<String> minimalFixturePaths() {
        Set<String> paths = new LinkedHashSet<>();
        paths.add(CONTRACT_RELATIVE);
        paths.add(PREDECESSOR_RELATIVE);
        paths.add(GLOBAL_PREFLIGHT_CONTRACT_RELATIVE);
        paths.add(HISTORICAL_RUNTIME_CONTRACT_RELATIVE);
        paths.add(ACCEPTED_WORM_RELATIVE);
        paths.add(HASHER_RELATIVE);
        paths.add("server/Dockerfile");
        paths.addAll(FIXED_SOURCE_PATHS);
        paths.addAll(
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .minimalFixturePaths());
        return Set.copyOf(paths);
    }

    static Set<String> semanticFixturePaths(Path tiJavaRoot)
            throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Set<String> paths = new LinkedHashSet<>(minimalFixturePaths());
        JsonNode historical = readJson(fixedRegularFile(
                root, HISTORICAL_RUNTIME_CONTRACT_RELATIVE));
        historical.path("production_surface").path("files").properties()
                .forEach(entry -> {
                    String relative = entry.getKey();
                    if (relative.equals("server/Dockerfile")
                            || relative.equals("server/.dockerignore")
                            || relative.equals("server/mvnw")
                            || relative.equals("server/pom.xml")
                            || relative.equals(
                            "server/build-versions.properties")
                            || relative.startsWith("server/.mvn/")
                            || relative.startsWith("server/src/main/")) {
                        paths.add(relative);
                    }
                });
        paths.addAll(PRODUCTION_ADDITION_PATHS);
        paths.addAll(NODE_A_PRODUCTION_ADDITION_PATHS);
        return Set.copyOf(paths);
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadContractEnvelope(root);
        validate(contract, root);
        return contract;
    }

    static void validate(JsonNode contract, Path tiJavaRoot)
            throws IOException {
        Path root = tiJavaRoot.toRealPath();
        require(propertyNames(contract).equals(Set.of(
                        "schema_version", "contract_id", "captured_at",
                        "scope", "status", "predecessor",
                        "node_b_git_authority", "operator_core_implementation",
                        "schema_and_acl_verification",
                        "bounded_retry_and_ambiguity_recovery",
                        "source_target_receipt_invariants",
                        "historical_source_successors",
                        "production_runtime_successor", "worm_successor",
                        "evidence", "authorization", "route_state",
                        "source_authority", "next_gate",
                        "document_payload_sha256")),
                "operator-core contract shape drifted");
        require(contract.path("schema_version").asInt() == 1
                        && CONTRACT_ID.equals(
                        contract.path("contract_id").asString())
                        && CONTRACT_CAPTURED_AT.equals(
                        contract.path("captured_at").asString())
                        && CONTRACT_SCOPE.equals(
                        contract.path("scope").asString())
                        && CONTRACT_STATUS.equals(
                        contract.path("status").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(contract)),
                "operator-core contract identity drifted");

        validatePredecessor(contract.path("predecessor"), root);
        validateHistoricalRuntimeAuthorities(root);
        validateNodeBGitAuthority(contract.path("node_b_git_authority"));
        validateOperatorCore(contract.path("operator_core_implementation"));
        validateSchemaAndAcl(contract.path("schema_and_acl_verification"));
        validateRetryAndRecovery(
                contract.path("bounded_retry_and_ambiguity_recovery"));
        validateReceiptInvariants(
                contract.path("source_target_receipt_invariants"));
        Map<String, JsonNode> sources = validateSourceAuthority(
                contract.path("source_authority"), root);
        validateTransitions(
                contract.path("historical_source_successors"), sources);
        validateProductionRuntime(
                contract.path("production_runtime_successor"), sources);
        validateWorm(contract.path("worm_successor"), sources, root);
        validateEvidence(contract.path("evidence"));
        validateAuthorization(contract.path("authorization"));
        validateRoute(contract.path("route_state"));
        validateNextGate(contract.path("next_gate"));
    }

    private static JsonNode loadContractEnvelope(Path root) throws IOException {
        Path path = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(CONTRACT_BYTE_COUNT > 0
                        && Files.size(path) == CONTRACT_BYTE_COUNT
                        && CONTRACT_SHA256.equals(sha256(path)),
                "operator-core contract physical bytes drifted");
        JsonNode contract = readJson(path);
        require(contract.isObject()
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(contract)),
                "operator-core contract payload identity drifted");
        return contract;
    }

    private static void validatePredecessor(JsonNode descriptor, Path root)
            throws IOException {
        require(propertyNames(descriptor).equals(Set.of(
                        "source", "contract_id", "captured_at", "scope",
                        "status", "sha256", "byte_count",
                        "document_payload_sha256", "immutable"))
                        && PREDECESSOR_RELATIVE.equals(
                        descriptor.path("source").asString())
                        && PREDECESSOR_ID.equals(
                        descriptor.path("contract_id").asString())
                        && PREDECESSOR_SHA256.equals(
                        descriptor.path("sha256").asString())
                        && descriptor.path("byte_count").asLong()
                        == PREDECESSOR_BYTE_COUNT
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        descriptor.path("document_payload_sha256").asString())
                        && descriptor.path("immutable").asBoolean(),
                "operator-core predecessor descriptor drifted");
        Path path = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        require(Files.size(path) == PREDECESSOR_BYTE_COUNT
                        && PREDECESSOR_SHA256.equals(sha256(path)),
                "operator-core predecessor physical bytes drifted");
        JsonNode predecessor = readJson(path);
        require(PREDECESSOR_ID.equals(
                        predecessor.path("contract_id").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(predecessor))
                        && NODE_B_IMPLEMENTATION_COMMIT.equals(predecessor
                        .path("git_checkpoint").path("commit_oid").asString())
                        && predecessor.path("route_state")
                        .path("migrated_operation_count").asInt() == 13
                        && predecessor.path("route_state")
                        .path("pending_operation_count").asInt() == 598,
                "operator-core predecessor identity drifted");
    }

    private static void validateNodeBGitAuthority(JsonNode authority) {
        require(propertyNames(authority).equals(Set.of(
                        "implementation_checkpoint_commit_oid",
                        "external_anchor_checkpoint",
                        "external_anchor_artifacts",
                        "external_anchor_artifact_count",
                        "explicit_fixed_checkpoint_replay_available",
                        "ordinary_build_and_load_require_git",
                        "live_head_main_or_origin_authority")),
                "operator-core Node B Git authority shape drifted");
        JsonNode checkpoint = authority.path("external_anchor_checkpoint");
        require(NODE_B_IMPLEMENTATION_COMMIT.equals(authority.path(
                        "implementation_checkpoint_commit_oid").asString())
                        && NODE_B_ANCHOR_COMMIT.equals(
                        checkpoint.path("commit_oid").asString())
                        && NODE_B_IMPLEMENTATION_COMMIT.equals(
                        checkpoint.path("parent_oid").asString())
                        && "sha1".equals(
                        checkpoint.path("object_format").asString())
                        && "2df48a21e622d0e5e3731fe2617ddaedbf466866"
                        .equals(checkpoint.path("root_tree_oid").asString())
                        && "ce2c2035763ac4512fa2bcaaa73cacb255212756"
                        .equals(checkpoint.path("ti_java_tree_oid").asString())
                        && "931e1268a43465023e23b31d903d5d7b3219981d"
                        .equals(checkpoint.path("server_tree_oid").asString())
                        && checkpoint.path("server_src_main_tree_oid")
                        .equals(checkpoint.path(
                                "parent_server_src_main_tree_oid"))
                        && checkpoint.path("web_tree_oid").equals(
                        checkpoint.path("parent_web_tree_oid"))
                        && checkpoint.path("changed_path_count").asInt() == 6
                        && checkpoint.path("added_count").asInt() == 6
                        && checkpoint.path("modified_count").asInt() == 0
                        && checkpoint.path("deleted_count").asInt() == 0
                        && authority.path(
                        "external_anchor_artifact_count").asInt() == 6
                        && authority.path("external_anchor_artifacts").size()
                        == 6
                        && authority.path(
                        "explicit_fixed_checkpoint_replay_available")
                        .asBoolean()
                        && !authority.path(
                        "ordinary_build_and_load_require_git").asBoolean()
                        && !authority.path(
                        "live_head_main_or_origin_authority").asBoolean(),
                "operator-core Node B Git authority drifted");
    }

    private static void validateHistoricalRuntimeAuthorities(Path root)
            throws IOException {
        Path globalPath = fixedRegularFile(
                root, GLOBAL_PREFLIGHT_CONTRACT_RELATIVE);
        require(Files.size(globalPath) == GLOBAL_PREFLIGHT_CONTRACT_BYTE_COUNT
                        && GLOBAL_PREFLIGHT_CONTRACT_SHA256.equals(
                        sha256(globalPath)),
                "operator-core fixed Node A contract physical bytes drifted");
        JsonNode global = readJson(globalPath);
        JsonNode nodeARuntime = global.path("historical_semantic_successors")
                .path("production_runtime_manifest");
        JsonNode nodeAWorm = global.path("historical_semantic_successors")
                .path("java_build_context_and_worm_chain");
        require(GLOBAL_PREFLIGHT_CONTRACT_PAYLOAD_SHA256.equals(global.path(
                        "document_payload_sha256").asString())
                        && GLOBAL_PREFLIGHT_CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(global))
                        && nodeARuntime.path("successor_file_count").asInt()
                        == 300
                        && ACCEPTED_RUNTIME_MANIFEST_SHA256.equals(nodeARuntime
                        .path("successor_manifest_sha256").asString())
                        && nodeARuntime.path("learning_personalbank_main")
                        .path("successor_file_count").asInt() == 43
                        && ACCEPTED_MAIN_MANIFEST_SHA256.equals(nodeARuntime
                        .path("learning_personalbank_main")
                        .path("successor_manifest_sha256").asString())
                        && nodeAWorm.path(
                        "terminal_successor_chain_node_count").asInt() == 7
                        && ACCEPTED_WORM_SHA256.equals(nodeAWorm
                        .path("terminal_successor_worm")
                        .path("sha256").asString())
                        && ACCEPTED_BUILD_CONTEXT_SHA256.equals(nodeAWorm
                        .path("terminal_successor_build_context_sha256")
                        .asString()),
                "operator-core fixed Node A semantic authority drifted");

        Path historicalPath = fixedRegularFile(
                root, HISTORICAL_RUNTIME_CONTRACT_RELATIVE);
        require(Files.size(historicalPath)
                        == HISTORICAL_RUNTIME_CONTRACT_BYTE_COUNT
                        && HISTORICAL_RUNTIME_CONTRACT_SHA256.equals(
                        sha256(historicalPath)),
                "operator-core historical runtime contract bytes drifted");
        JsonNode historical = readJson(historicalPath);
        require(HISTORICAL_RUNTIME_CONTRACT_PAYLOAD_SHA256.equals(
                        historical.path("document_payload_sha256").asString())
                        && HISTORICAL_RUNTIME_CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(historical))
                        && historical.path("production_surface")
                        .path("file_count").asInt() == 297
                        && "d327a5ef85fa47abc6417527d7bfd99a01f29de6ea3c2f08205cbf30a6e38f79"
                        .equals(historical.path("production_surface")
                                .path("manifest_sha256").asString())
                        && historical.path("production_surface")
                        .path("files").size() == 297
                        && canonicalSha256(historical.path("production_surface")
                        .path("files")).equals(historical
                        .path("production_surface")
                        .path("manifest_sha256").asString()),
                "operator-core historical production authority drifted");
    }

    private static void validateOperatorCore(JsonNode value) {
        require(propertyNames(value).equals(Set.of(
                        "owner", "entrypoint", "explicit_callable_only",
                        "spring_component_or_bean_registration",
                        "command_line_runner_scheduler_or_http_registration",
                        "environment_file_redis_or_local_marker_input",
                        "production_data_source_wiring", "transaction_owner",
                        "nonblocking_advisory_try_lock",
                        "lock_busy_fails_without_business_dml",
                        "statement_timeout_milliseconds",
                        "lock_timeout_milliseconds",
                        "idle_in_transaction_timeout_milliseconds",
                        "setup_schema_identity_and_recovery_queries_bounded",
                        "setup_and_recovery_metadata_lock_wait_bounded_by_lock_timeout",
                        "maximum_payload_bytes", "maximum_source_rows",
                        "maximum_tag_utf8_bytes", "maximum_target_facts",
                        "raw_sensitive_material_persisted_or_returned",
                        "writer_stop_receipts"))
                        && "learning".equals(value.path("owner").asString())
                        && value.path("entrypoint").asString().endsWith(
                        ".LegacyPersonalBankTagMigrationOperatorCore")
                        && value.path("explicit_callable_only").asBoolean()
                        && !value.path(
                        "spring_component_or_bean_registration").asBoolean()
                        && !value.path(
                        "command_line_runner_scheduler_or_http_registration")
                        .asBoolean()
                        && !value.path(
                        "environment_file_redis_or_local_marker_input")
                        .asBoolean()
                        && !value.path(
                        "production_data_source_wiring").asBoolean()
                        && "JdbcTagMigrationStore".equals(
                        value.path("transaction_owner").asString())
                        && value.path(
                        "nonblocking_advisory_try_lock").asBoolean()
                        && value.path(
                        "lock_busy_fails_without_business_dml").asBoolean()
                        && value.path(
                        "statement_timeout_milliseconds").asInt() == 30_000
                        && value.path("lock_timeout_milliseconds").asInt()
                        == 5_000
                        && value.path(
                        "idle_in_transaction_timeout_milliseconds").asInt()
                        == 60_000
                        && value.path(
                        "setup_schema_identity_and_recovery_queries_bounded")
                        .asBoolean()
                        && value.path(
                        "setup_and_recovery_metadata_lock_wait_bounded_by_lock_timeout")
                        .asBoolean()
                        && value.path("maximum_payload_bytes").asInt()
                        == 1_048_576
                        && value.path("maximum_source_rows").asInt() == 100_001
                        && value.path("maximum_tag_utf8_bytes").asInt() == 84
                        && value.path("maximum_target_facts").asInt() == 200_001
                        && !value.path(
                        "raw_sensitive_material_persisted_or_returned")
                        .asBoolean()
                        && writerStopReceiptsAreExact(
                        value.path("writer_stop_receipts")),
                "operator-core implementation boundary drifted");
    }

    private static boolean writerStopReceiptsAreExact(JsonNode receipts) {
        Set<String> digestFields = Set.of(
                "source_writer_stop_receipt_sha256",
                "target_writer_stop_receipt_sha256",
                "membership_writer_stop_receipt_sha256");
        Set<String> expectedFields = new LinkedHashSet<>(digestFields);
        expectedFields.add("single_collapsed_receipt_allowed");
        expectedFields.add("pairwise_distinct_required");
        expectedFields.add(
                "all_three_bound_to_ledger_receipts_and_recovery");
        return propertyNames(receipts).equals(expectedFields)
                && digestFields.stream().allMatch(field ->
                "required_separate_digest".equals(
                        receipts.path(field).asString()))
                && !receipts.path(
                "single_collapsed_receipt_allowed").asBoolean()
                && receipts.path("pairwise_distinct_required").asBoolean()
                && receipts.path(
                "all_three_bound_to_ledger_receipts_and_recovery")
                .asBoolean();
    }

    private static void validateSchemaAndAcl(JsonNode value) {
        require(propertyNames(value).equals(Set.of(
                        "fixture_only_schema_scripts",
                        "production_flyway_or_schema_change",
                        "postgresql_versions",
                        "exact_relation_column_type_nullability_default_identity_checks",
                        "primary_unique_foreign_check_and_trigger_closure",
                        "owner_role_membership_and_effective_acl_closure",
                        "function_identity_language_volatility_security_and_acl_closure",
                        "hostile_search_path_safe",
                        "schema_fingerprint_before_business_dml",
                        "schema_or_acl_mismatch_business_dml",
                        "schema_verifier_uses_catalog_only",
                        "expected_catalog_sha256"))
                        && strings(value.path("fixture_only_schema_scripts"))
                        .equals(List.of(
                                "server/src/test/resources/db/phase4c/"
                                        + "076-legacy-personal-bank-tag-"
                                        + "operator-core-schema.sql",
                                "server/src/test/resources/db/phase4c/"
                                        + "077-legacy-personal-bank-tag-"
                                        + "operator-core-seed.sql"))
                        && strings(value.path("postgresql_versions"))
                        .equals(List.of("16.14", "18.4"))
                        && !value.path(
                        "production_flyway_or_schema_change").asBoolean()
                        && value.path(
                        "exact_relation_column_type_nullability_default_identity_checks")
                        .asBoolean()
                        && value.path(
                        "primary_unique_foreign_check_and_trigger_closure")
                        .asBoolean()
                        && value.path(
                        "owner_role_membership_and_effective_acl_closure")
                        .asBoolean()
                        && value.path(
                        "function_identity_language_volatility_security_and_acl_closure")
                        .asBoolean()
                        && value.path("hostile_search_path_safe").asBoolean()
                        && value.path(
                        "schema_fingerprint_before_business_dml").asBoolean()
                        && value.path(
                        "schema_or_acl_mismatch_business_dml").asInt() == 0
                        && value.path(
                        "schema_verifier_uses_catalog_only").asBoolean()
                        && "f4361024a36e4e509f1ca4203c2dca5ecfd5bf1eded036e462bbbb20f395f99c"
                        .equals(value.path(
                                "expected_catalog_sha256").asString()),
                "operator-core schema/ACL evidence drifted");
    }

    private static void validateRetryAndRecovery(JsonNode value) {
        require(propertyNames(value).equals(Set.of(
                        "retryable_root_sqlstates", "maximum_attempts",
                        "maximum_retries",
                        "fresh_connection_pid_and_txid_per_retry",
                        "root_sqlstate_only",
                        "cause_or_next_exception_sqlstate_smuggling_rejected",
                        "connection_acquisition_setup_rollback_close_and_commit_failures_terminal",
                        "real_40001_success_and_exhaustion_on_both_postgresql_versions",
                        "real_40P01_success_and_exhaustion_on_both_postgresql_versions",
                        "deferred_commit_23503_nonretryable",
                        "commit_outcome_unknown_never_reapplies_business_dml",
                        "commit_ack_discard_evidence",
                        "real_network_commit_ack_loss_evidenced",
                        "recovery_uses_fresh_connection",
                        "recovery_is_receipt_first"))
                        && strings(value.path("retryable_root_sqlstates"))
                        .equals(List.of("40001", "40P01"))
                        && value.path("maximum_attempts").asInt() == 3
                        && value.path("maximum_retries").asInt() == 2
                        && value.path(
                        "fresh_connection_pid_and_txid_per_retry").asBoolean()
                        && value.path("root_sqlstate_only").asBoolean()
                        && value.path(
                        "cause_or_next_exception_sqlstate_smuggling_rejected")
                        .asBoolean()
                        && value.path(
                        "connection_acquisition_setup_rollback_close_and_commit_failures_terminal")
                        .asBoolean()
                        && value.path(
                        "real_40001_success_and_exhaustion_on_both_postgresql_versions")
                        .asBoolean()
                        && value.path(
                        "real_40P01_success_and_exhaustion_on_both_postgresql_versions")
                        .asBoolean()
                        && value.path(
                        "deferred_commit_23503_nonretryable").asBoolean()
                        && value.path(
                        "commit_outcome_unknown_never_reapplies_business_dml")
                        .asBoolean()
                        && "deterministic_test_fixture".equals(value.path(
                        "commit_ack_discard_evidence").asString())
                        && !value.path(
                        "real_network_commit_ack_loss_evidenced").asBoolean()
                        && value.path(
                        "recovery_uses_fresh_connection").asBoolean()
                        && value.path("recovery_is_receipt_first").asBoolean(),
                "operator-core bounded retry/recovery evidence drifted");
    }

    private static void validateReceiptInvariants(JsonNode value) {
        require(propertyNames(value).equals(Set.of(
                        "frozen_source_manifest_rechecked_before_apply",
                        "source_target_membership_and_plan_digests_rechecked",
                        "partial_receipts_must_be_strict_manifest_prefix",
                        "sparse_or_out_of_order_partial_receipts_block",
                        "exact_receipt_replay_business_dml",
                        "receipt_precedes_target_insert",
                        "receipt_target_and_applied_state_commit_together",
                        "target_digest_recomputed_from_canonical_facts",
                        "all_empty_noop_requires_explicit_receipts",
                        "ambiguous_recovery_mismatch_blocks",
                        "schema_identity_or_digest_failure_fingerprint_unchanged",
                        "users_last_active_dml"))
                        && value.path(
                        "frozen_source_manifest_rechecked_before_apply")
                        .asBoolean()
                        && value.path(
                        "source_target_membership_and_plan_digests_rechecked")
                        .asBoolean()
                        && value.path(
                        "partial_receipts_must_be_strict_manifest_prefix")
                        .asBoolean()
                        && value.path(
                        "sparse_or_out_of_order_partial_receipts_block")
                        .asBoolean()
                        && value.path(
                        "exact_receipt_replay_business_dml").asInt() == 0
                        && value.path(
                        "receipt_precedes_target_insert").asBoolean()
                        && value.path(
                        "receipt_target_and_applied_state_commit_together")
                        .asBoolean()
                        && value.path(
                        "target_digest_recomputed_from_canonical_facts")
                        .asBoolean()
                        && value.path(
                        "all_empty_noop_requires_explicit_receipts")
                        .asBoolean()
                        && value.path(
                        "ambiguous_recovery_mismatch_blocks").asBoolean()
                        && value.path(
                        "schema_identity_or_digest_failure_fingerprint_unchanged")
                        .asBoolean()
                        && value.path("users_last_active_dml").asInt() == 0,
                "operator-core receipt invariants drifted");
    }

    private static Map<String, JsonNode> validateSourceAuthority(
            JsonNode authority,
            Path root
    ) throws IOException {
        require(propertyNames(authority).equals(Set.of(
                        "historical_authority_source_count",
                        "historical_authority_sources",
                        "fixed_non_control_source_count",
                        "fixed_non_control_sources", "control_source_count",
                        "control_sources",
                        "control_sources_excluded_from_self_authority",
                        "current_control_sources_external_git_anchor_complete",
                        "fixed_source_allowlist_exact",
                        "dynamic_source_discovery",
                        "ordinary_build_and_load_are_gitless",
                        "live_head_main_or_origin_authority", "unknown_source",
                        "absolute_parent_escape_or_symlink",
                        "historical_contract_or_worm_overwrite"))
                        && authority.path(
                        "historical_authority_source_count").asInt() == 3
                        && authority.path(
                        "fixed_non_control_source_count").asInt() == 49
                        && authority.path("control_source_count").asInt() == 7
                        && Set.copyOf(strings(authority.path("control_sources")))
                        .equals(CONTROL_SOURCE_PATHS)
                        && authority.path(
                        "control_sources_excluded_from_self_authority")
                        .asBoolean()
                        && !authority.path(
                        "current_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && authority.path(
                        "fixed_source_allowlist_exact").asBoolean()
                        && !authority.path(
                        "dynamic_source_discovery").asBoolean()
                        && authority.path(
                        "ordinary_build_and_load_are_gitless").asBoolean()
                        && !authority.path(
                        "live_head_main_or_origin_authority").asBoolean()
                        && "reject".equals(
                        authority.path("unknown_source").asString())
                        && "reject".equals(authority.path(
                        "absolute_parent_escape_or_symlink").asString())
                        && !authority.path(
                        "historical_contract_or_worm_overwrite").asBoolean(),
                "operator-core source authority boundary drifted");

        JsonNode historical = authority.path("historical_authority_sources");
        require(propertyNames(historical).equals(Set.of(
                        PREDECESSOR_RELATIVE,
                        GLOBAL_PREFLIGHT_CONTRACT_RELATIVE,
                        HISTORICAL_RUNTIME_CONTRACT_RELATIVE)),
                "operator-core historical source authority set drifted");
        validateHistoricalAuthorityDescriptor(
                historical.path(PREDECESSOR_RELATIVE),
                PREDECESSOR_RELATIVE,
                PREDECESSOR_SHA256,
                PREDECESSOR_BYTE_COUNT,
                PREDECESSOR_PAYLOAD_SHA256);
        validateHistoricalAuthorityDescriptor(
                historical.path(GLOBAL_PREFLIGHT_CONTRACT_RELATIVE),
                GLOBAL_PREFLIGHT_CONTRACT_RELATIVE,
                GLOBAL_PREFLIGHT_CONTRACT_SHA256,
                GLOBAL_PREFLIGHT_CONTRACT_BYTE_COUNT,
                GLOBAL_PREFLIGHT_CONTRACT_PAYLOAD_SHA256);
        validateHistoricalAuthorityDescriptor(
                historical.path(HISTORICAL_RUNTIME_CONTRACT_RELATIVE),
                HISTORICAL_RUNTIME_CONTRACT_RELATIVE,
                HISTORICAL_RUNTIME_CONTRACT_SHA256,
                HISTORICAL_RUNTIME_CONTRACT_BYTE_COUNT,
                HISTORICAL_RUNTIME_CONTRACT_PAYLOAD_SHA256);

        JsonNode descriptors = authority.path("fixed_non_control_sources");
        require(propertyNames(descriptors).equals(FIXED_SOURCE_PATHS),
                "operator-core fixed source allowlist drifted");
        Map<String, JsonNode> byPath = new TreeMap<>();
        for (Map.Entry<String, JsonNode> entry : descriptors.properties()) {
            String relative = entry.getKey();
            JsonNode descriptor = entry.getValue();
            require(propertyNames(descriptor).equals(
                            Set.of("source", "sha256", "byte_count"))
                            && relative.equals(
                            descriptor.path("source").asString()),
                    "operator-core fixed source descriptor drifted: "
                            + relative);
            Path path = fixedRegularFile(root, relative);
            long physicalByteCount = Files.size(path);
            String physicalSha256 = sha256(path);
            boolean nodeCBytes = physicalByteCount == descriptor.path(
                    "byte_count").asLong()
                    && physicalSha256.equals(
                    descriptor.path("sha256").asString());
            if (!nodeCBytes) {
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .SourceTransition nodeD;
                try {
                    nodeD =
                            Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                                    .sourceTransition(root, relative);
                } catch (AssertionError error) {
                    throw new AssertionError(
                            "operator-core fixed source physical bytes drifted: "
                                    + relative,
                            error);
                }
                require(SOURCE_TRANSITION_PATHS.contains(relative)
                                && nodeD != null
                                && relative.equals(nodeD.source())
                                && descriptor.path("sha256").asString().equals(
                                nodeD.acceptedSha256())
                                && descriptor.path("byte_count").asLong()
                                == nodeD.acceptedByteCount()
                                && physicalSha256.equals(
                                nodeD.successorSha256())
                                && physicalByteCount
                                == nodeD.successorByteCount(),
                        "operator-core fixed source physical bytes drifted "
                                + "outside Node D: " + relative);
            }
            require(byPath.put(relative, descriptor) == null,
                    "operator-core duplicate fixed source: " + relative);
        }
        require(byPath.keySet().equals(FIXED_SOURCE_PATHS),
                "operator-core fixed source path set drifted");
        return Map.copyOf(byPath);
    }

    private static void validateHistoricalAuthorityDescriptor(
            JsonNode descriptor,
            String relative,
            String expectedSha256,
            long expectedByteCount,
            String expectedPayloadSha256
    ) {
        require(propertyNames(descriptor).equals(Set.of(
                        "source", "sha256", "byte_count",
                        "document_payload_sha256"))
                        && relative.equals(descriptor.path("source").asString())
                        && expectedSha256.equals(
                        descriptor.path("sha256").asString())
                        && expectedByteCount
                        == descriptor.path("byte_count").asLong()
                        && expectedPayloadSha256.equals(descriptor.path(
                        "document_payload_sha256").asString()),
                "operator-core historical source descriptor drifted: "
                        + relative);
    }

    private static void validateTransitions(
            JsonNode successors,
            Map<String, JsonNode> sources
    ) {
        require(propertyNames(successors).equals(Set.of(
                        "predecessor_checkpoint", "override_count",
                        "overrides",
                        "accepted_bytes_replayable_from_fixed_predecessor",
                        "successor_external_git_anchor_complete",
                        "unknown_path"))
                        && NODE_B_ANCHOR_COMMIT.equals(successors.path(
                        "predecessor_checkpoint").asString())
                        && successors.path("override_count").asInt() == 34
                        && successors.path(
                        "accepted_bytes_replayable_from_fixed_predecessor")
                        .asBoolean()
                        && !successors.path(
                        "successor_external_git_anchor_complete").asBoolean()
                        && "reject".equals(
                        successors.path("unknown_path").asString()),
                "operator-core historical successor boundary drifted");
        JsonNode overrides = successors.path("overrides");
        require(propertyNames(overrides).equals(SOURCE_TRANSITION_PATHS),
                "operator-core source transition allowlist drifted");
        for (String relative : SOURCE_TRANSITION_PATHS) {
            JsonNode transition = overrides.path(relative);
            JsonNode source = sources.get(relative);
            require(propertyNames(transition).equals(Set.of(
                            "source", "accepted_sha256",
                            "accepted_byte_count", "successor_sha256",
                            "successor_byte_count"))
                            && relative.equals(
                            transition.path("source").asString())
                            && transition.path("successor_sha256").asString()
                            .equals(source.path("sha256").asString())
                            && transition.path("successor_byte_count").asLong()
                            == source.path("byte_count").asLong()
                            && (!transition.path("accepted_sha256").asString()
                            .equals(transition.path(
                                    "successor_sha256").asString())
                            || transition.path("accepted_byte_count").asLong()
                            != transition.path(
                                    "successor_byte_count").asLong()),
                    "operator-core source transition drifted: " + relative);
        }
    }

    private static void validateProductionRuntime(
            JsonNode runtime,
            Map<String, JsonNode> sources
    ) {
        validateRuntimeView(
                runtime, 300, ACCEPTED_RUNTIME_MANIFEST_SHA256,
                307, CURRENT_RUNTIME_MANIFEST_SHA256, 299, true, sources);
        validateRuntimeView(
                runtime.path("learning_personalbank_main"),
                43, ACCEPTED_MAIN_MANIFEST_SHA256,
                50, CURRENT_MAIN_MANIFEST_SHA256, 42, false, sources);
        require("reject".equals(
                        runtime.path("unknown_or_extra_files").asString())
                        && "reject".equals(
                        runtime.path("symlink_or_root_escape").asString()),
                "operator-core runtime rejection policy drifted");
    }

    private static void validateRuntimeView(
            JsonNode view,
            int acceptedCount,
            String acceptedManifest,
            int currentCount,
            String currentManifest,
            int unchangedCount,
            boolean full,
            Map<String, JsonNode> sources
    ) {
        Set<String> expectedFields = new LinkedHashSet<>(Set.of(
                "accepted_file_count", "accepted_manifest_sha256",
                "current_file_count", "current_manifest_sha256",
                "unchanged_file_count", "added_files", "changed_files",
                "deleted_files", "exact_additions_and_changes_only"));
        if (full) {
            expectedFields.add("unknown_or_extra_files");
            expectedFields.add("symlink_or_root_escape");
            expectedFields.add("learning_personalbank_main");
        }
        Map<String, String> additions = textMap(view.path("added_files"));
        Map<String, String> changes = textMap(view.path("changed_files"));
        require(propertyNames(view).equals(expectedFields)
                        && view.path("accepted_file_count").asInt()
                        == acceptedCount
                        && acceptedManifest.equals(view.path(
                        "accepted_manifest_sha256").asString())
                        && view.path("current_file_count").asInt()
                        == currentCount
                        && currentManifest.equals(view.path(
                        "current_manifest_sha256").asString())
                        && view.path("unchanged_file_count").asInt()
                        == unchangedCount
                        && additions.keySet().equals(PRODUCTION_ADDITION_PATHS)
                        && changes.keySet().equals(
                        Set.of(GLOBAL_PREFLIGHT_MAIN_RELATIVE))
                        && strings(view.path("deleted_files")).isEmpty()
                        && view.path(
                        "exact_additions_and_changes_only").asBoolean(),
                "operator-core production runtime view drifted");
        additions.forEach((relative, digest) -> require(
                digest.equals(sources.get(relative).path("sha256").asString()),
                "operator-core production addition source drifted: "
                        + relative));
        changes.forEach((relative, digest) -> require(
                digest.equals(sources.get(relative).path("sha256").asString()),
                "operator-core production change source drifted: "
                        + relative));
    }

    private static void validateWorm(
            JsonNode worm,
            Map<String, JsonNode> sources,
            Path root
    ) throws IOException {
        require(propertyNames(worm).equals(Set.of(
                        "accepted_report", "accepted_build_context_sha256",
                        "accepted_chain_node_count", "current_report",
                        "current_build_context_sha256", "dockerfile_sha256",
                        "current_chain_node_count", "appended_node_count",
                        "historical_nodes_rewritten",
                        "production_database_version",
                        "flyway_baseline_created")),
                "operator-core WORM successor shape drifted");
        JsonNode accepted = worm.path("accepted_report");
        JsonNode current = worm.path("current_report");
        require(propertyNames(accepted).equals(Set.of("source", "sha256"))
                        && ACCEPTED_WORM_RELATIVE.equals(
                        accepted.path("source").asString())
                        && ACCEPTED_WORM_SHA256.equals(
                        accepted.path("sha256").asString())
                        && ACCEPTED_BUILD_CONTEXT_SHA256.equals(worm.path(
                        "accepted_build_context_sha256").asString())
                        && worm.path("accepted_chain_node_count").asInt() == 7
                        && propertyNames(current).equals(Set.of(
                        "source", "sha256", "byte_count", "captured_at"))
                        && CURRENT_WORM_RELATIVE.equals(
                        current.path("source").asString())
                        && CURRENT_WORM_SHA256.equals(
                        current.path("sha256").asString())
                        && current.path("byte_count").asLong()
                        == CURRENT_WORM_BYTE_COUNT
                        && CURRENT_WORM_CAPTURED_AT.equals(
                        current.path("captured_at").asString())
                        && CURRENT_BUILD_CONTEXT_SHA256.equals(worm.path(
                        "current_build_context_sha256").asString())
                        && DOCKERFILE_SHA256.equals(
                        worm.path("dockerfile_sha256").asString())
                        && worm.path("current_chain_node_count").asInt() == 8
                        && worm.path("appended_node_count").asInt() == 1
                        && !worm.path("historical_nodes_rewritten").asBoolean()
                        && "unknown".equals(worm.path(
                        "production_database_version").asString())
                        && !worm.path("flyway_baseline_created").asBoolean()
                        && current.path("sha256").asString().equals(
                        sources.get(CURRENT_WORM_RELATIVE)
                                .path("sha256").asString())
                        && current.path("byte_count").asLong()
                        == sources.get(CURRENT_WORM_RELATIVE)
                                .path("byte_count").asLong(),
                "operator-core WORM successor drifted");

        Path acceptedPath = fixedRegularFile(root, ACCEPTED_WORM_RELATIVE);
        require(Files.size(acceptedPath) == ACCEPTED_WORM_BYTE_COUNT
                        && ACCEPTED_WORM_SHA256.equals(sha256(acceptedPath)),
                "operator-core accepted WORM physical bytes drifted");
        JsonNode acceptedReport = readJson(acceptedPath);
        require(ACCEPTED_BUILD_CONTEXT_SHA256.equals(acceptedReport
                        .path("java").path("buildContextSha256").asString())
                        && DOCKERFILE_SHA256.equals(acceptedReport
                        .path("java").path("dockerfileSha256").asString())
                        && acceptedReport.path("java")
                        .path("startupPassed").asBoolean()
                        && acceptedReport.path("java")
                        .path("readinessPassed").asBoolean(),
                "operator-core accepted WORM report drifted");
        JsonNode report = readJson(fixedRegularFile(root, CURRENT_WORM_RELATIVE));
        require(report.path("schemaVersion").asInt() == 1
                        && CURRENT_WORM_CAPTURED_AT.equals(
                        report.path("capturedAt").asString())
                        && "18.4".equals(report.path("source")
                        .path("serverVersion").asString())
                        && "18.4".equals(report.path("restore")
                        .path("serverVersion").asString())
                        && report.path("readRole").path(
                        "selectPassed").asBoolean()
                        && report.path("readRole").path(
                        "insertRejected").asBoolean()
                        && report.path("readRole").path(
                        "updateRejected").asBoolean()
                        && report.path("readRole").path(
                        "deleteRejected").asBoolean()
                        && DOCKERFILE_SHA256.equals(report.path("java")
                        .path("dockerfileSha256").asString())
                        && CURRENT_BUILD_CONTEXT_SHA256.equals(report.path("java")
                        .path("buildContextSha256").asString())
                        && report.path("java").path(
                        "startupPassed").asBoolean()
                        && report.path("java").path(
                        "readinessPassed").asBoolean()
                        && "unknown".equals(report.path(
                        "productionDatabaseVersion").asString())
                        && !report.path("flywayBaselineCreated").asBoolean(),
                "operator-core WORM report payload drifted");
    }

    private static void validateEvidence(JsonNode evidence) {
        require(propertyNames(evidence).equals(Set.of(
                        "classification", "targeted_unit_test_count",
                        "operator_postgresql_integration_test_count",
                        "bounded_retry_postgresql_integration_test_count",
                        "postgresql_versions",
                        "canonical_cross_version_catalog_parity",
                        "real_lock_wait_timeout_and_recovery_after_unlock",
                        "sparse_partial_receipt_business_facts_and_existing_receipts_unchanged",
                        "sparse_partial_receipt_durable_block_run_and_single_audit_only",
                        "raw_sensitive_canary_excluded",
                        "production_database_connected",
                        "production_credentials_read",
                        "production_data_read_or_mutated",
                        "production_operator_executed",
                        "user_compose_or_production_docker_mutated"))
                        && evidence.path("classification").asString().startsWith(
                        "test-only explicit operator core")
                        && evidence.path(
                        "targeted_unit_test_count").asInt() == 83
                        && evidence.path(
                        "operator_postgresql_integration_test_count")
                        .asInt() == 3
                        && evidence.path(
                        "bounded_retry_postgresql_integration_test_count")
                        .asInt() == 2
                        && strings(evidence.path("postgresql_versions"))
                        .equals(List.of("16.14", "18.4"))
                        && evidence.path(
                        "canonical_cross_version_catalog_parity").asBoolean()
                        && evidence.path(
                        "real_lock_wait_timeout_and_recovery_after_unlock")
                        .asBoolean()
                        && evidence.path(
                        "sparse_partial_receipt_business_facts_and_existing_receipts_unchanged")
                        .asBoolean()
                        && evidence.path(
                        "sparse_partial_receipt_durable_block_run_and_single_audit_only")
                        .asBoolean()
                        && evidence.path(
                        "raw_sensitive_canary_excluded").asBoolean()
                        && !evidence.path(
                        "production_database_connected").asBoolean()
                        && !evidence.path(
                        "production_credentials_read").asBoolean()
                        && !evidence.path(
                        "production_data_read_or_mutated").asBoolean()
                        && !evidence.path(
                        "production_operator_executed").asBoolean()
                        && !evidence.path(
                        "user_compose_or_production_docker_mutated").asBoolean(),
                "operator-core evidence boundary drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        Set<String> trueFields = Set.of(
                "migration_global_preflight_evidence_closed",
                "migration_durable_ledger_freeze_design_evidence_closed",
                "operator_core_evidence_closed",
                "bounded_40001_40P01_retry_implemented",
                "operator_migration_implementation");
        Set<String> falseFields = Set.of(
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
                "legacy_runtime_permanently_disabled",
                "route_or_openapi_delta", "client_gateway_or_proxy_change",
                "production_cutover",
                "source_successor_external_git_anchor_complete",
                "semantic_successor_external_git_anchor_complete",
                "bootstrap_control_sources_external_git_anchor_complete",
                "current_node_control_sources_external_git_anchor_complete");
        Set<String> expectedFields = new LinkedHashSet<>(trueFields);
        expectedFields.addAll(falseFields);
        expectedFields.add("newly_closed_gates");
        require(Set.copyOf(strings(authorization.path("newly_closed_gates")))
                        .equals(Set.of(
                                "operator_core_evidence_closed",
                                "bounded_40001_40P01_retry_implemented",
                                "operator_migration_implementation"))
                        && propertyNames(authorization).equals(expectedFields),
                "operator-core newly closed gates drifted");
        for (String field : trueFields) {
            require(authorization.path(field).asBoolean(),
                    "operator-core required authorization drifted: " + field);
        }
        for (String field : falseFields) {
            require(!authorization.path(field).asBoolean(),
                    "operator-core unauthorized gate opened: " + field);
        }
    }

    private static void validateRoute(JsonNode route) {
        require(propertyNames(route).equals(Set.of(
                        "migrated_operation_count", "pending_operation_count",
                        "production_cutover_operation_count",
                        "total_operation_count",
                        "legacy_flask_remains_production_owner"))
                        && route.path("total_operation_count").asInt() == 611
                        && route.path("migrated_operation_count").asInt() == 13
                        && route.path("pending_operation_count").asInt() == 598
                        && route.path(
                        "production_cutover_operation_count").asInt() == 0
                        && route.path(
                        "legacy_flask_remains_production_owner").asBoolean(),
                "operator-core route authority drifted");
    }

    private static void validateNextGate(JsonNode nextGate) {
        require(propertyNames(nextGate).equals(Set.of(
                        "required_next",
                        "node_c_operator_core_is_production_apply_authorization",
                        "production_execution_requires_explicit_user_authorization"))
                        && nextGate.path("required_next").asString().startsWith(
                        "externally anchor this Node C control plane")
                        && !nextGate.path(
                        "node_c_operator_core_is_production_apply_authorization")
                        .asBoolean()
                        && nextGate.path(
                        "production_execution_requires_explicit_user_authorization")
                        .asBoolean(),
                "operator-core next gate drifted");
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path value = Path.of(relative);
        require(!value.isAbsolute()
                        && value.getNameCount() > 0,
                "operator-core path escapes fixed root: " + relative);
        for (Path part : value) {
            require(!part.toString().isBlank()
                            && !part.toString().equals(".")
                            && !part.toString().equals(".."),
                    "operator-core path escapes fixed root: " + relative);
        }
        Path base = root.toRealPath();
        Path cursor = base;
        for (Path part : value) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "operator-core fixed source is a symlink: " + relative);
        }
        Path resolved = base.resolve(value).normalize();
        require(resolved.startsWith(base)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "operator-core fixed source is absent or not regular: "
                        + relative);
        return resolved;
    }

    private static String javaBuildContextSha256(Path root)
            throws IOException {
        Path script = fixedRegularFile(root, HASHER_RELATIVE);
        Process process = new ProcessBuilder("/bin/sh", script.toString())
                .directory(root.toFile())
                .start();
        String stdout;
        String stderr;
        try {
            stdout = new String(
                    process.getInputStream().readAllBytes(),
                    StandardCharsets.UTF_8).trim();
            stderr = new String(
                    process.getErrorStream().readAllBytes(),
                    StandardCharsets.UTF_8).trim();
            int exitCode = process.waitFor();
            require(exitCode == 0,
                    "operator-core Java build-context hasher failed: "
                            + stderr);
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IOException(
                    "operator-core Java build-context hasher interrupted",
                    error);
        }
        return stdout;
    }

    private static JsonNode readJson(Path path) throws IOException {
        return JSON.readTree(Files.readAllBytes(path));
    }

    private static Set<String> propertyNames(JsonNode object) {
        Set<String> result = new LinkedHashSet<>();
        object.properties().forEach(entry -> result.add(entry.getKey()));
        return Set.copyOf(result);
    }

    private static List<String> strings(JsonNode values) {
        List<String> result = new ArrayList<>();
        values.forEach(value -> result.add(value.asString()));
        return List.copyOf(result);
    }

    private static Map<String, String> textMap(JsonNode object) {
        TreeMap<String, String> result = new TreeMap<>();
        object.properties().forEach(entry ->
                result.put(entry.getKey(), entry.getValue().asString()));
        return Map.copyOf(result);
    }

    private static String canonicalSha256(JsonNode value) {
        return sha256(JSON.writeValueAsBytes(canonicalNode(value)));
    }

    private static String documentPayloadSha256(JsonNode value) {
        ObjectNode copy = (ObjectNode) value.deepCopy();
        copy.remove("document_payload_sha256");
        return canonicalSha256(copy);
    }

    private static JsonNode canonicalNode(JsonNode value) {
        if (value.isObject()) {
            ObjectNode result = JSON.createObjectNode();
            TreeMap<String, JsonNode> sorted = new TreeMap<>();
            value.properties().forEach(entry -> sorted.put(
                    entry.getKey(), canonicalNode(entry.getValue())));
            sorted.forEach(result::set);
            return result;
        }
        if (value.isArray()) {
            ArrayNode result = JSON.createArrayNode();
            value.forEach(item -> result.add(canonicalNode(item)));
            return result;
        }
        return value;
    }

    private static String sha256(Path path) throws IOException {
        return sha256(Files.readAllBytes(path));
    }

    private static String sha256(byte[] payload) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(payload));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    record SourceTransition(
            String source,
            String acceptedSha256,
            long acceptedByteCount,
            String successorSha256,
            long successorByteCount) {
    }

    record ProductionRuntimeSuccessor(
            String view,
            int acceptedFileCount,
            String acceptedManifestSha256,
            int currentFileCount,
            String currentManifestSha256,
            Map<String, String> addedFiles,
            Map<String, String> changedFiles,
            Set<String> deletedFiles) {
    }

    record WormSuccessor(
            String acceptedReportSha256,
            String acceptedBuildContextSha256,
            int acceptedChainNodeCount,
            String currentReportSha256,
            String currentBuildContextSha256,
            int currentChainNodeCount) {
    }
}
