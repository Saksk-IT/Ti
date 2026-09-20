package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.stream.Stream;

/**
 * Gitless Java bridge for the transaction-write source/runtime successor.
 *
 * <p>This bootstrap externally fixes the full-parity predecessor, but its own
 * control sources remain self-excluded.  Consequently this class composes
 * source, runtime and WORM facts without granting route migration.
 */
final class Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-http-"
                    + "source-successor-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.learning-transaction-write-http-"
                    + "source-successor-contract";
    private static final String CONTRACT_SHA256 =
            "0c1a46eea25404167cd740f679029c87ec224e7643159eb757dff782c5fc2f5d";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "890f2b90c10fcf55f30f426e287b69016af766b17c3c4c9cc86a9f84660bb6af";
    private static final long CONTRACT_BYTE_COUNT = 19_381L;
    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-http-"
                    + "full-parity-contract.json";
    private static final String PREDECESSOR_SHA256 =
            "40b38a443d7f7d754cc42ce43fa854b0c3c18dc66f4920a2f07d451601d6d1db";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "83ca7d51d768540ed744830c74f07eb1fd1f63db88c293ea4ec83e41d6a6c1e1";
    private static final long PREDECESSOR_BYTE_COUNT = 15_604L;
    private static final String NODE_D_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-"
                    + "execution-protocol-contract.json";
    private static final String NODE_D_SHA256 =
            "e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14";
    private static final long NODE_D_BYTE_COUNT = 44_336L;
    private static final String ACCEPTED_WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-"
                    + "execution-protocol-worm-evidence.json";
    private static final String ACCEPTED_WORM_SHA256 =
            "5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c";
    private static final String ACCEPTED_BUILD_CONTEXT_SHA256 =
            "36978a808a327abfb3c7b3dfe138f5622000213a25bad762b59128c78894d7c7";
    private static final String CURRENT_WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-http-worm-evidence.json";
    private static final String CURRENT_WORM_SHA256 =
            "dd165106d7b3a73512acdbf89924b352e3f1ad027132b8a8519af957a47de599";
    private static final long CURRENT_WORM_BYTE_COUNT = 1_442L;
    private static final String CURRENT_BUILD_CONTEXT_SHA256 =
            "5e4247d0a43405661cef27b91b4169273e8ad096bfa750b4ba4488ca6c247224";
    private static final String BOOTSTRAP_COMMIT =
            "6ed81347467a4155887300b7e4ae36589204af79";
    private static final String ACCEPTED_CHECKPOINT =
            "2579dfd344dbe318c9fb59d067c843356b98fece";
    private static final String SUCCESSOR_CHECKPOINT =
            "b635d1db3b9d71698d9a40cc729a215d67a6906f";
    private static final String FULL_RUNTIME_ACCEPTED_SHA256 =
            "053ffc0a6a6ecc02ffb7cd2a8545af339bef35ffd502dcdbfbc0de8b11977d4a";
    private static final String FULL_RUNTIME_CURRENT_SHA256 =
            "d90cdbfe0da59544f44e859488c1a3df602857c53d7f082fe5bc9166464b3045";
    private static final String SCOPED_RUNTIME_ACCEPTED_SHA256 =
            "66e7874b40dcbfc46fa349e7d4d8cd36025a82a03df009f985a6fc30d2edead6";
    private static final String SCOPED_RUNTIME_CURRENT_SHA256 =
            "b5821442ec7066e807d16c0d9a5a0cf30d96479b49df96cba64f1d8863cbb738";

    private static final Set<String> TRANSITION_PATHS = Set.of(
            "docs/refactor/05-progress.md",
            "infra/phase2/README.md",
            "infra/phase2/verify-local-reference-wormhole.sh",
            "infra/phase2/verify-static.sh",
            "server/pom.xml",
            "server/src/main/java/io/saksk/ti/catalog/api/"
                    + "SubjectMetadataApplicationApi.java",
            "server/src/main/java/io/saksk/ti/catalog/application/"
                    + "SubjectMetadataQueryService.java",
            "server/src/main/java/io/saksk/ti/catalog/application/port/"
                    + "SubjectContextQueryPort.java",
            "server/src/main/java/io/saksk/ti/catalog/infrastructure/"
                    + "persistence/JdbcSubjectContextQueryAdapter.java",
            "server/src/main/java/io/saksk/ti/web/config/"
                    + "ProductionSecretsConfiguration.java",
            "server/src/main/java/io/saksk/ti/web/config/"
                    + "SecurityConfiguration.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "LoginRateLimitConfiguration.java",
            "server/src/main/resources/application-prod.yml",
            "server/src/main/resources/application.yml",
            "server/src/test/java/io/saksk/ti/catalog/application/"
                    + "SubjectMetadataQueryServiceTest.java",
            "server/src/test/java/io/saksk/ti/learning/"
                    + "LearningModuleContextTest.java",
            "server/src/test/java/io/saksk/ti/web/config/"
                    + "ProductionSecretsConfigurationTest.java");

    private static final Set<String> CONTROL_SOURCE_PATHS = Set.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cLearningTransactionWriteHttp"
                    + "SourceSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cLearningTransactionWriteHttp"
                    + "SourceSuccessorContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cLearningTransactionWriteHttp"
                    + "FullParitySuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cLearningTransactionWriteHttp"
                    + "FullParityContractParityTest.java",
            "tools/build_phase4c_learning_transaction_write_http_"
                    + "source_successor_contract.py",
            "tools/phase4c_learning_transaction_write_http_"
                    + "source_successor_acceptance.py",
            "tools/test_phase4c_learning_transaction_write_http_"
                    + "source_successor_contract.py",
            "tools/build_phase4c_tag_migration_execution_protocol_contract.py",
            "tools/phase4c_tag_migration_execution_protocol_"
                    + "successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationExecutionProtocol"
                    + "SuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationExecutionProtocol"
                    + "ContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationExecutionProtocol"
                    + "PostPushAnchorSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationExecutionProtocol"
                    + "PostPushAnchorContractParityTest.java",
            "tools/phase4c_http_implementation_successor_acceptance.py",
            "tools/phase4c_http_target_execution_successor_acceptance.py",
            "tools/phase4c_http_target_execution_post_push_"
                    + "successor_acceptance.py",
            "tools/phase4c_http_target_execution_post_push_anchor_"
                    + "successor_acceptance.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_anchor_contract.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_contract.py",
            "tools/phase4c_http_typed_normalization_"
                    + "successor_acceptance.py",
            "tools/phase4c_http_target_execution_anchor_"
                    + "successor_acceptance.py",
            "tools/test_capture_phase4c_learning_transaction_write_goldens.py",
            "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
            "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
            "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
            "tools/test_phase4b_personal_bank_share_list_read_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
            "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
            "tools/phase4c_tag_migration_operator_core_"
                    + "successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCore"
                    + "SuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCore"
                    + "ContractParityTest.java",
            "tools/build_phase4c_tag_migration_global_preflight_contract.py",
            "tools/phase4c_tag_migration_global_preflight_"
                    + "successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflight"
                    + "SuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflight"
                    + "ContractParityTest.java",
            "tools/phase4c_tag_migration_execution_protocol_"
                    + "post_push_anchor_successor_acceptance.py",
            "tools/test_phase4c_tag_migration_execution_protocol_contract.py",
            "tools/test_phase4c_tag_migration_operator_core_contract.py",
            "tools/test_phase4c_tag_migration_global_preflight_contract.py",
            "tools/capture_phase4c_learning_transaction_write_goldens.py",
            "tools/build_phase4c_learning_transaction_write_http_"
                    + "full_parity_contract.py");

    private static final List<String> RUNTIME_ROOTS = List.of(
            "server/src/main",
            "server/pom.xml",
            "server/Dockerfile",
            "server/.dockerignore",
            "server/.mvn",
            "server/mvnw",
            "server/mvnw.cmd",
            "server/build-versions.properties",
            "compose.dev.yml",
            ".env.example",
            "contracts",
            "openapi");

    private Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance() {
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = readFixedJson(
                root,
                CONTRACT_RELATIVE,
                CONTRACT_SHA256,
                CONTRACT_BYTE_COUNT);
        require(CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && contract.path("schema_version").asInt() == 1
                        && CONTRACT_PAYLOAD_SHA256.equals(contract.path(
                        "document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(contract)),
                "transaction-write source successor identity drifted");
        validatePredecessor(contract, root);
        validateTransitions(contract, root);
        validateRuntimeAndWorm(contract, root);
        validateAuthorization(contract);
        return contract;
    }

    static JsonNode loadNodeDPredecessor(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadSourceBridge(root);
        JsonNode nodeD = readFixedJson(
                root, NODE_D_RELATIVE, NODE_D_SHA256, NODE_D_BYTE_COUNT);
        validateNodeDSourcesForBridge(contract, nodeD, root);
        return nodeD;
    }

    static SourceTransition sourceTransition(
            Path tiJavaRoot, String relative
    ) throws IOException {
        if (!TRANSITION_PATHS.contains(relative)) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        JsonNode descriptor = loadSourceBridge(root).path("source_successors")
                .path("transitions").path(relative);
        SourceTransition transition = transition(descriptor);
        Path physical = fixedRegularFile(root, relative);
        require(relative.equals(transition.source())
                        && Files.size(physical)
                        == transition.successorByteCount()
                        && sha256(physical).equals(
                        transition.successorSha256()),
                "transaction-write source transition drifted: " + relative);
        return transition;
    }

    static SourceTransition transitionFromNodeD(
            Path tiJavaRoot,
            String relative,
            String acceptedSha256,
        long acceptedByteCount
    ) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        SourceTransition predecessor = sourceTransition(root, relative);
        if (predecessor != null) {
            require(acceptedSha256.equals(
                            predecessor.acceptedSha256())
                            && acceptedByteCount
                            == predecessor.acceptedByteCount(),
                    "transaction-write source Node D origin drifted: "
                            + relative);
            return predecessor;
        }
        if (!CONTROL_SOURCE_PATHS.contains(relative)) {
            return null;
        }
        loadSourceBridge(root);
        JsonNode nodeD = readFixedJson(
                root, NODE_D_RELATIVE, NODE_D_SHA256, NODE_D_BYTE_COUNT);
        JsonNode nodeDTransition = nodeD.path(
                "historical_source_successors").path("overrides")
                .path(relative);
        if (nodeDTransition.isMissingNode()) {
            return null;
        }
        require(acceptedSha256.equals(nodeDTransition.path(
                        "successor_sha256").asString())
                        && acceptedByteCount
                        == nodeDTransition.path(
                        "successor_byte_count").asLong(),
                "transaction-write source Node D control origin drifted: "
                        + relative);
        Path physical = fixedRegularFile(root, relative);
        return new SourceTransition(
                relative,
                acceptedSha256,
                acceptedByteCount,
                sha256(physical),
                Files.size(physical));
    }

    static boolean isCurrentControlSource(String relative) {
        return CONTROL_SOURCE_PATHS.contains(relative);
    }

    static String currentControlSha256(
            Path tiJavaRoot, String relative
    ) throws IOException {
        require(CONTROL_SOURCE_PATHS.contains(relative),
                "transaction-write source unknown current control: "
                        + relative);
        Path root = tiJavaRoot.toRealPath();
        loadSourceBridge(root);
        return sha256(fixedRegularFile(root, relative));
    }

    static ProductionRuntimeSuccessor validateProductionRuntimeSuccessor(
            Path tiJavaRoot,
            Map<String, String> acceptedFiles,
            Map<String, String> currentFiles,
            String view
    ) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode semantic = load(root).path("semantic_successors");
        JsonNode descriptor;
        if ("full_runtime".equals(view)) {
            descriptor = semantic.path("full_runtime");
        } else if ("learning_personalbank_main".equals(view)) {
            descriptor = semantic.path("learning_personalbank_main");
        } else {
            throw new AssertionError(
                    "transaction-write source unknown production view: "
                            + view);
        }

        TreeMap<String, String> accepted = new TreeMap<>(acceptedFiles);
        TreeMap<String, String> current = new TreeMap<>(currentFiles);
        require(accepted.size()
                        == descriptor.path("accepted_file_count").asInt()
                        && canonicalSha256(JSON.valueToTree(accepted)).equals(
                        descriptor.path(
                                "accepted_manifest_sha256").asString()),
                "transaction-write source rejected accepted runtime");
        require(current.size()
                        == descriptor.path("current_file_count").asInt()
                        && canonicalSha256(JSON.valueToTree(current)).equals(
                        descriptor.path(
                                "current_manifest_sha256").asString()),
                "transaction-write source rejected current production manifest");

        TreeMap<String, String> additions = new TreeMap<>();
        TreeMap<String, String> changes = new TreeMap<>();
        current.forEach((relative, digest) -> {
            String acceptedDigest = accepted.get(relative);
            if (acceptedDigest == null) {
                additions.put(relative, digest);
            } else if (!acceptedDigest.equals(digest)) {
                changes.put(relative, digest);
            }
        });
        Set<String> deletions = new LinkedHashSet<>(accepted.keySet());
        deletions.removeAll(current.keySet());
        require(additions.size()
                        == descriptor.path("added_file_count").asInt()
                        && changes.size()
                        == descriptor.path("changed_file_count").asInt()
                        && deletions.size()
                        == descriptor.path("deleted_file_count").asInt(),
                "transaction-write source runtime delta drifted");
        return new ProductionRuntimeSuccessor(
                view,
                accepted.size(),
                canonicalSha256(JSON.valueToTree(accepted)),
                current.size(),
                canonicalSha256(JSON.valueToTree(current)),
                Map.copyOf(additions),
                Map.copyOf(changes),
                Set.copyOf(deletions));
    }

    static WormSuccessor validateWormSuccessor(
            Path tiJavaRoot,
            String acceptedReportSha256,
            String acceptedBuildContextSha256,
            String physicalBuildContextSha256
    ) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode descriptor = loadWormBridge(root);
        require(ACCEPTED_WORM_SHA256.equals(acceptedReportSha256)
                        && ACCEPTED_BUILD_CONTEXT_SHA256.equals(
                        acceptedBuildContextSha256)
                        && acceptedReportSha256.equals(descriptor.path(
                        "accepted_report_sha256").asString())
                        && acceptedBuildContextSha256.equals(descriptor.path(
                        "accepted_build_context_sha256").asString())
                        && descriptor.path(
                        "accepted_chain_node_count").asInt() == 9,
                "transaction-write source rejected WORM predecessor");
        validateCurrentBuildContext(root, physicalBuildContextSha256);
        return new WormSuccessor(
                acceptedReportSha256,
                acceptedBuildContextSha256,
                9,
                CURRENT_WORM_SHA256,
                physicalBuildContextSha256,
                10);
    }

    static void validateCurrentBuildContext(
            Path tiJavaRoot, String physicalBuildContextSha256
    ) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        loadWormBridge(root);
        require(CURRENT_BUILD_CONTEXT_SHA256.equals(
                        physicalBuildContextSha256),
                "transaction-write source build-context drifted");
    }

    static Map<String, String> productionRuntimeManifest(Path tiJavaRoot)
            throws IOException {
        Path root = tiJavaRoot.toRealPath();
        TreeMap<String, String> manifest = new TreeMap<>();
        for (String relative : RUNTIME_ROOTS) {
            Path surface = root.resolve(relative).normalize();
            require(surface.startsWith(root) && Files.exists(surface),
                    "transaction-write source runtime root is absent: "
                            + relative);
            if (Files.isRegularFile(surface, LinkOption.NOFOLLOW_LINKS)) {
                require(!Files.isSymbolicLink(surface),
                        "transaction-write source runtime contains a symlink: "
                                + relative);
                manifest.put(relative, sha256(surface));
                continue;
            }
            try (Stream<Path> walked = Files.walk(surface)) {
                for (Path candidate : walked.sorted().toList()) {
                    require(!Files.isSymbolicLink(candidate),
                            "transaction-write source runtime contains a symlink: "
                                    + root.relativize(candidate));
                    if (Files.isRegularFile(
                            candidate, LinkOption.NOFOLLOW_LINKS)) {
                        manifest.put(
                                root.relativize(candidate)
                                        .toString().replace('\\', '/'),
                                sha256(candidate));
                    }
                }
            }
        }
        return Map.copyOf(manifest);
    }

    static Map<String, String> nodeDCurrentRuntimeManifest(Path tiJavaRoot)
            throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.load(root);
        TreeMap<String, String> manifest = new TreeMap<>(textMap(readJson(
                fixedRegularFile(
                        root,
                        "docs/refactor/phase4c/"
                                + "personal-bank-user-counts-http-"
                                + "target-execution-contract.json"))
                .path("production_surface").path("files")));
        applyRuntimeSuccessor(
                manifest,
                readJson(fixedRegularFile(
                        root,
                        "docs/refactor/phase4c/"
                                + "personal-bank-tag-migration-"
                                + "global-preflight-contract.json"))
                        .path("historical_semantic_successors")
                        .path("production_runtime_manifest"));
        applyRuntimeSuccessor(
                manifest,
                readJson(fixedRegularFile(
                        root,
                        "docs/refactor/phase4c/"
                                + "personal-bank-tag-migration-"
                                + "operator-core-contract.json"))
                        .path("production_runtime_successor"));
        applyRuntimeSuccessor(
                manifest,
                readJson(fixedRegularFile(root, NODE_D_RELATIVE))
                        .path("production_runtime_successor"));
        require(manifest.size() == 311
                        && FULL_RUNTIME_ACCEPTED_SHA256.equals(
                        canonicalSha256(JSON.valueToTree(manifest))),
                "transaction-write source Node D runtime drifted");
        return Map.copyOf(manifest);
    }

    static Set<String> minimalFixturePaths(Path tiJavaRoot)
            throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Set<String> paths = new LinkedHashSet<>(
                Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                        .minimalFixturePaths());
        paths.add(CONTRACT_RELATIVE);
        paths.add(ACCEPTED_WORM_RELATIVE);
        paths.add(CURRENT_WORM_RELATIVE);
        paths.add(NODE_D_RELATIVE);
        paths.addAll(productionRuntimeManifest(root).keySet());
        return Set.copyOf(paths);
    }

    private static void validatePredecessor(JsonNode contract, Path root)
            throws IOException {
        JsonNode predecessor = contract.path("predecessor");
        JsonNode anchor = contract.path("bootstrap_external_anchor");
        require(PREDECESSOR_RELATIVE.equals(
                        predecessor.path("source").asString())
                        && PREDECESSOR_SHA256.equals(
                        predecessor.path("sha256").asString())
                        && PREDECESSOR_BYTE_COUNT
                        == predecessor.path("byte_count").asLong()
                        && predecessor.path("immutable").asBoolean()
                        && BOOTSTRAP_COMMIT.equals(anchor.path(
                        "fixed_checkpoint").path("commit_oid").asString())
                        && anchor.path(
                        "anchored_control_source_count").asInt() == 8
                        && anchor.path(
                        "predecessor_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && !anchor.path("live_ref_authority").asBoolean(),
                "transaction-write source predecessor drifted");
        JsonNode fixedPredecessor = readFixedJson(
                root,
                PREDECESSOR_RELATIVE,
                PREDECESSOR_SHA256,
                PREDECESSOR_BYTE_COUNT);
        require("ti.phase4c.learning-transaction-write-http-"
                        .concat("full-parity-contract")
                        .equals(fixedPredecessor.path(
                        "contract_id").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        fixedPredecessor.path(
                        "document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(fixedPredecessor)),
                "transaction-write source fixed predecessor drifted");
    }

    private static JsonNode loadSourceBridge(Path root) throws IOException {
        JsonNode contract = readFixedJson(
                root,
                CONTRACT_RELATIVE,
                CONTRACT_SHA256,
                CONTRACT_BYTE_COUNT);
        require(CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && contract.path("schema_version").asInt() == 1
                        && CONTRACT_PAYLOAD_SHA256.equals(contract.path(
                        "document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(contract)),
                "transaction-write source bridge identity drifted");
        validatePredecessor(contract, root);
        validateTransitions(contract, root);
        validateAuthorization(contract);
        return contract;
    }

    private static JsonNode loadWormBridge(Path root) throws IOException {
        JsonNode descriptor = loadSourceBridge(root)
                .path("semantic_successors")
                .path("java_build_context_and_worm");
        Path currentWorm = fixedRegularFile(root, CURRENT_WORM_RELATIVE);
        require(ACCEPTED_WORM_RELATIVE.equals(descriptor.path(
                        "accepted_report_source").asString())
                        && ACCEPTED_WORM_SHA256.equals(descriptor.path(
                        "accepted_report_sha256").asString())
                        && ACCEPTED_BUILD_CONTEXT_SHA256.equals(descriptor.path(
                        "accepted_build_context_sha256").asString())
                        && descriptor.path(
                        "accepted_chain_node_count").asInt() == 9
                        && CURRENT_WORM_RELATIVE.equals(descriptor.path(
                        "current_report_source").asString())
                        && CURRENT_WORM_SHA256.equals(descriptor.path(
                        "current_report_sha256").asString())
                        && CURRENT_WORM_BYTE_COUNT
                        == descriptor.path(
                        "current_report_byte_count").asLong()
                        && CURRENT_BUILD_CONTEXT_SHA256.equals(descriptor.path(
                        "current_build_context_sha256").asString())
                        && descriptor.path(
                        "current_chain_node_count").asInt() == 10
                        && Files.size(currentWorm) == CURRENT_WORM_BYTE_COUNT
                        && CURRENT_WORM_SHA256.equals(sha256(currentWorm)),
                "transaction-write source WORM bridge drifted");
        return descriptor;
    }

    private static void validateTransitions(JsonNode contract, Path root)
            throws IOException {
        JsonNode successors = contract.path("source_successors");
        JsonNode transitions = successors.path("transitions");
        JsonNode predecessorTransitions = readFixedJson(
                root,
                PREDECESSOR_RELATIVE,
                PREDECESSOR_SHA256,
                PREDECESSOR_BYTE_COUNT)
                .path("historical_source_successors")
                .path("transitions");
        require(ACCEPTED_CHECKPOINT.equals(
                        successors.path("accepted_checkpoint").asString())
                        && SUCCESSOR_CHECKPOINT.equals(
                        successors.path("successor_checkpoint").asString())
                        && successors.path("transition_count").asInt() == 17
                        && propertyNames(transitions).equals(TRANSITION_PATHS)
                        && transitions.equals(predecessorTransitions)
                        && !successors.path(
                        "dynamic_source_discovery").asBoolean()
                        && "reject".equals(
                        successors.path("unknown_path").asString()),
                "transaction-write source transition authority drifted");
        for (String relative : TRANSITION_PATHS) {
            SourceTransition current = transition(
                    transitions.path(relative));
            Path physical = fixedRegularFile(root, relative);
            require(relative.equals(current.source())
                            && Files.size(physical)
                            == current.successorByteCount()
                            && sha256(physical).equals(
                            current.successorSha256()),
                    "transaction-write source transition drifted: "
                            + relative);
        }
    }

    private static void validateRuntimeAndWorm(
            JsonNode contract, Path root
    ) throws IOException {
        JsonNode semantic = contract.path("semantic_successors");
        JsonNode full = semantic.path("full_runtime");
        JsonNode scoped = semantic.path("learning_personalbank_main");
        Map<String, String> runtime = productionRuntimeManifest(root);
        Map<String, String> scopedRuntime =
                learningPersonalbankMain(runtime);
        require(full.path("accepted_file_count").asInt() == 311
                        && FULL_RUNTIME_ACCEPTED_SHA256.equals(full.path(
                        "accepted_manifest_sha256").asString())
                        && full.path("current_file_count").asInt() == 395
                        && FULL_RUNTIME_CURRENT_SHA256.equals(full.path(
                        "current_manifest_sha256").asString())
                        && full.path("added_file_count").asInt() == 84
                        && full.path("changed_file_count").asInt() == 10
                        && full.path("deleted_file_count").asInt() == 0
                        && runtime.size() == 395
                        && FULL_RUNTIME_CURRENT_SHA256.equals(
                        canonicalSha256(JSON.valueToTree(runtime)))
                        && scoped.path(
                        "accepted_file_count").asInt() == 54
                        && SCOPED_RUNTIME_ACCEPTED_SHA256.equals(scoped.path(
                        "accepted_manifest_sha256").asString())
                        && scoped.path("current_file_count").asInt() == 105
                        && SCOPED_RUNTIME_CURRENT_SHA256.equals(scoped.path(
                        "current_manifest_sha256").asString())
                        && scoped.path("added_file_count").asInt() == 51
                        && scoped.path("changed_file_count").asInt() == 0
                        && scoped.path("deleted_file_count").asInt() == 0
                        && scopedRuntime.size() == 105
                        && SCOPED_RUNTIME_CURRENT_SHA256.equals(
                        canonicalSha256(JSON.valueToTree(scopedRuntime))),
                "transaction-write source runtime successor drifted");
        JsonNode worm = semantic.path("java_build_context_and_worm");
        Path currentWorm = fixedRegularFile(root, CURRENT_WORM_RELATIVE);
        require(ACCEPTED_WORM_RELATIVE.equals(worm.path(
                        "accepted_report_source").asString())
                        && ACCEPTED_WORM_SHA256.equals(worm.path(
                        "accepted_report_sha256").asString())
                        && ACCEPTED_BUILD_CONTEXT_SHA256.equals(worm.path(
                        "accepted_build_context_sha256").asString())
                        && worm.path(
                        "accepted_chain_node_count").asInt() == 9
                        && CURRENT_WORM_RELATIVE.equals(worm.path(
                        "current_report_source").asString())
                        && CURRENT_WORM_SHA256.equals(worm.path(
                        "current_report_sha256").asString())
                        && CURRENT_WORM_BYTE_COUNT
                        == worm.path("current_report_byte_count").asLong()
                        && CURRENT_BUILD_CONTEXT_SHA256.equals(worm.path(
                        "current_build_context_sha256").asString())
                        && worm.path(
                        "current_chain_node_count").asInt() == 10
                        && Files.size(currentWorm) == CURRENT_WORM_BYTE_COUNT
                        && CURRENT_WORM_SHA256.equals(sha256(currentWorm)),
                "transaction-write source WORM successor drifted");
    }

    private static void validateNodeDSourcesForBridge(
            JsonNode contract, JsonNode nodeD, Path root
    ) throws IOException {
        JsonNode sources = nodeD.path("source_authority")
                .path("fixed_non_control_sources");
        JsonNode transitions = contract.path("source_successors")
                .path("transitions");
        for (String relative : propertyNames(sources)) {
            if (CONTROL_SOURCE_PATHS.contains(relative)) {
                continue;
            }
            JsonNode descriptor = sources.path(relative);
            Path physical = fixedRegularFile(root, relative);
            String physicalSha256 = sha256(physical);
            long physicalBytes = Files.size(physical);
            if (physicalBytes == descriptor.path("byte_count").asLong()
                    && physicalSha256.equals(
                    descriptor.path("sha256").asString())) {
                continue;
            }
            JsonNode transition = transitions.path(relative);
            require(!transition.isMissingNode()
                            && descriptor.path("sha256").asString().equals(
                            transition.path(
                                    "accepted_sha256").asString())
                            && descriptor.path("byte_count").asLong()
                            == transition.path(
                            "accepted_byte_count").asLong()
                            && physicalSha256.equals(transition.path(
                            "successor_sha256").asString())
                            && physicalBytes == transition.path(
                            "successor_byte_count").asLong(),
                    "transaction-write source Node D fixed source drifted: "
                            + relative);
        }
    }

    private static void validateAuthorization(JsonNode contract) {
        JsonNode authorization = contract.path("authorization");
        require(authorization.path(
                        "predecessor_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && authorization.path(
                        "full_target_parity_closed").asBoolean()
                        && !authorization.path(
                        "current_bridge_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && !authorization.path(
                        "route_migration_eligible").asBoolean()
                        && !authorization.path(
                        "nine_transaction_write_operations_migrated")
                        .asBoolean()
                        && !authorization.path("route_delta").asBoolean()
                        && !authorization.path(
                        "production_cutover").asBoolean(),
                "transaction-write source authorization drifted");
        JsonNode route = contract.path("route_state");
        require(route.path("total_operation_count").asInt() == 611
                        && route.path(
                        "migrated_operation_count").asInt() == 13
                        && route.path(
                        "pending_operation_count").asInt() == 598
                        && route.path(
                        "production_cutover_operation_count").asInt() == 0
                        && route.path(
                        "implemented_pending_operation_count").asInt() == 9,
                "transaction-write source route state drifted");
        JsonNode sourceAuthority = contract.path("source_authority");
        require(sourceAuthority.path(
                        "control_source_count").asInt() == 48
                        && Set.copyOf(strings(sourceAuthority.path(
                        "control_sources"))).equals(CONTROL_SOURCE_PATHS)
                        && sourceAuthority.path(
                        "control_sources_excluded_from_self_authority")
                        .asBoolean()
                        && sourceAuthority.path(
                        "ordinary_build_is_gitless").asBoolean()
                        && !sourceAuthority.path(
                        "live_head_main_or_origin_authority").asBoolean()
                        && !sourceAuthority.path(
                        "historical_contracts_or_worm_overwritten")
                        .asBoolean(),
                "transaction-write source authority drifted");
    }

    private static Map<String, String> learningPersonalbankMain(
            Map<String, String> manifest
    ) {
        TreeMap<String, String> scoped = new TreeMap<>();
        manifest.forEach((relative, digest) -> {
            if (relative.startsWith(
                    "server/src/main/java/io/saksk/ti/learning/")
                    || relative.startsWith(
                    "server/src/main/java/io/saksk/ti/personalbank/")) {
                scoped.put(relative, digest);
            }
        });
        return Map.copyOf(scoped);
    }

    private static void applyRuntimeSuccessor(
            Map<String, String> manifest, JsonNode successor
    ) {
        manifest.putAll(textMap(successor.path("added_files")));
        manifest.putAll(textMap(successor.path("changed_files")));
        strings(successor.path("deleted_files")).forEach(manifest::remove);
    }

    private static SourceTransition transition(JsonNode descriptor) {
        return new SourceTransition(
                descriptor.path("source").asString(),
                descriptor.path("accepted_sha256").asString(),
                descriptor.path("accepted_byte_count").asLong(),
                descriptor.path("successor_sha256").asString(),
                descriptor.path("successor_byte_count").asLong());
    }

    private static JsonNode readFixedJson(
            Path root, String relative, String expectedSha256, long byteCount
    ) throws IOException {
        Path path = fixedRegularFile(root, relative);
        require(Files.size(path) == byteCount
                        && expectedSha256.equals(sha256(path)),
                "transaction-write source fixed JSON drifted: " + relative);
        JsonNode document = readJson(path);
        require(document.isObject(),
                "transaction-write source JSON is not an object: "
                        + relative);
        return document;
    }

    private static JsonNode readJson(Path path) throws IOException {
        return JSON.readTree(Files.readAllBytes(path));
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path value = Path.of(relative);
        require(!value.isAbsolute() && value.getNameCount() > 0,
                "transaction-write source path escapes root: " + relative);
        Path base = root.toRealPath();
        Path cursor = base;
        for (Path part : value) {
            require(!part.toString().isBlank()
                            && !part.toString().equals(".")
                            && !part.toString().equals(".."),
                    "transaction-write source path escapes root: "
                            + relative);
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "transaction-write source path is a symlink: "
                            + relative);
        }
        Path resolved = base.resolve(value).normalize();
        require(resolved.startsWith(base)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "transaction-write source path is absent: " + relative);
        return resolved;
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
        Map<String, String> result = new LinkedHashMap<>();
        object.properties().forEach(entry -> result.put(
                entry.getKey(), entry.getValue().asString()));
        return Map.copyOf(result);
    }

    private static String documentPayloadSha256(JsonNode value) {
        ObjectNode copy = (ObjectNode) value.deepCopy();
        copy.remove("document_payload_sha256");
        return sha256(JSON.writeValueAsBytes(canonicalNode(copy)));
    }

    private static String canonicalSha256(JsonNode value) {
        return sha256(JSON.writeValueAsBytes(canonicalNode(value)));
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
