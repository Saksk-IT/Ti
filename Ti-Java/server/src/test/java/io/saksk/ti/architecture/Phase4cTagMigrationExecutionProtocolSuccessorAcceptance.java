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

/** Gitless Java bridge for the Phase 4C execution-protocol successor. */
final class Phase4cTagMigrationExecutionProtocolSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-execution-protocol-"
                    + "contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-tag-migration-execution-protocol-"
                    + "contract";
    private static final String CONTRACT_CAPTURED_AT =
            "2026-07-20T21:15:00+08:00";
    private static final String CONTRACT_SCOPE =
            "phase4c-learning-owned-personal-bank-tag-migration-"
                    + "execution-protocol";
    private static final String CONTRACT_STATUS =
            "execution_protocol_crypto_verifier_and_local_disposable_"
                    + "rehearsal_closed_production_freeze_backup_apply_"
                    + "runtime_disable_and_cutover_unauthorized";

    // Mechanically derived from the final deterministic builder payload.
    private static final String CONTRACT_SHA256 =
            "e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "42599261bc5632feed89fc41637ee1a98cff844dd9dc776f889d155a0567a7c4";
    private static final long CONTRACT_BYTE_COUNT = 44_336L;

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-operator-core-"
                    + "post-push-anchor-contract.json";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-tag-migration-operator-core-"
                    + "post-push-anchor-contract";
    private static final String PREDECESSOR_SHA256 =
            "0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64";
    private static final long PREDECESSOR_BYTE_COUNT = 84_461L;
    private static final String PREDECESSOR_COMMIT =
            "4c47d1ea220ae9e310338bbf23b74d87d477e20f";
    private static final String PREDECESSOR_INDEPENDENT_ACCEPTANCE_COMMIT =
            "4ec9966f836378a33058b574fd1812d4d19cac10";

    private static final String ACCEPTED_WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-operator-core-"
                    + "worm-evidence.json";
    private static final String ACCEPTED_WORM_SHA256 =
            "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f";
    private static final long ACCEPTED_WORM_BYTE_COUNT = 1_442L;
    private static final String ACCEPTED_BUILD_CONTEXT_SHA256 =
            "29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc";
    private static final String CURRENT_WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-execution-protocol-"
                    + "worm-evidence.json";
    private static final String HASHER_RELATIVE =
            "infra/phase2/hash-java-build-context.sh";
    private static final String DOCKERFILE_SHA256 =
            "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499";
    private static final String EXPECTED_CANONICAL_SCHEMA_DUMP_SHA256 =
            "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b";

    private static final String MIGRATION_MAIN_PREFIX =
            "server/src/main/java/io/saksk/ti/learning/"
                    + "infrastructure/migration/";
    private static final String MIGRATION_TEST_PREFIX =
            "server/src/test/java/io/saksk/ti/learning/"
                    + "infrastructure/migration/";

    private static final Set<String> CONTROL_SOURCE_PATHS = Set.of(
            CONTRACT_RELATIVE,
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-execution-protocol.md",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationExecutionProtocolContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java",
            "tools/build_phase4c_tag_migration_execution_protocol_contract.py",
            "tools/phase4c_tag_migration_execution_protocol_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_tag_migration_execution_protocol_contract.py");

    private static final Set<String> IMPLEMENTATION_SOURCE_PATHS = Set.of(
            MIGRATION_MAIN_PREFIX + "Ed25519TagMigrationEvidenceVerifier.java",
            MIGRATION_MAIN_PREFIX
                    + "LegacyPersonalBankTagMigrationExecutionProtocol.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationPlanCandidate.java",
            MIGRATION_MAIN_PREFIX + "TagMigrationPlanCandidateFactory.java",
            MIGRATION_TEST_PREFIX
                    + "Ed25519TagMigrationEvidenceVerifierTest.java",
            MIGRATION_TEST_PREFIX
                    + "LegacyPersonalBankTagMigrationExecutionProtocolStaticTest.java",
            MIGRATION_TEST_PREFIX
                    + "Phase4cLegacyPersonalBankTagMigrationExecutionProtocolIT.java",
            MIGRATION_TEST_PREFIX + "TagMigrationPlanCandidateFactoryTest.java",
            "server/src/test/resources/db/phase4c/"
                    + "078-legacy-personal-bank-tag-migration-"
                    + "execution-protocol-schema.sql",
            "server/src/test/resources/db/phase4c/"
                    + "079-legacy-personal-bank-tag-migration-"
                    + "execution-protocol-seed.sql",
            CURRENT_WORM_RELATIVE);

    private static final Set<String> SOURCE_TRANSITION_PATHS = Set.of(
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py",
            "tools/phase4c_tag_migration_operator_core_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_tag_migration_operator_core_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCoreContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCorePostPushAnchorContractParityTest.java",
            "tools/build_phase4c_tag_migration_global_preflight_contract.py",
            "tools/phase4c_tag_migration_global_preflight_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_tag_migration_global_preflight_contract.py",
            "tools/test_phase4c_tag_migration_operator_core_"
                    + "post_push_anchor_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightContractParityTest.java",
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
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java",
            "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
            "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
            "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
            "tools/test_phase4b_personal_bank_share_list_read_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
            "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "composition_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "http_entry_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_read_contract.py");

    // Accepted C2 hashes are generated from the fixed commit replay.
    private static final Map<String, String> ACCEPTED_TRANSITION_SHA256 =
            Map.ofEntries(
                    Map.entry(
                            "docs/refactor/05-progress.md",
                            "71fc8bf98bc4fb50645df473ee79b2bc33856ca928f49da7aecc96a7d1040f9d"),
                    Map.entry(
                            "docs/refactor/phase4c/README.md",
                            "f061ac5e2b240e3b8c367f9db817c84346a309e9872cfbdeeafe8d3ff8689230"),
                    Map.entry(
                            "infra/phase2/README.md",
                            "d5c8647397016f93c8ea2b5e83b41818ea00498fd7e699cc1119930f1995e21b"),
                    Map.entry(
                            "infra/phase2/verify-static.sh",
                            "2a1a5a5453a1090f6132971081d4ac2448803023acb50d474ced491bafe8efc3"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionSuccessorAcceptance.java",
                            "9f929532d8c31f96f4e3e5cd24ee199220c82ad2aac46f5944ee0d54cd22dbb6"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
                            "cb4cabfce2cded7cde291b54d2c2dd98cc397887d24141e5164250a8811fb369"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java",
                            "137f3a9911d886610300aecc95a13f05d5621d18c19acf491194f1b8b741efe3"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightContractParityTest.java",
                            "bdb3ee1169dfe164016a2afc6a46e6e3fff7abe9b8602988ab9d0c0ecff86158"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java",
                            "e5471121ea2fc52f9e36712b222578e24323d5785dddf27b27a86799867fc99f"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreContractParityTest.java",
                            "f7dad6c7d51769669fda0cb2c26a7c3991ad3bfae27178c9c8a470f6addff361"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCorePostPushAnchorContractParityTest.java",
                            "486bbc757e44408dc9237eade44ec3f4e2cd60bd2d3360c1cc54bdaf426eacb1"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java",
                            "83840dc07301be40828df8bd46f214bc2d50342bde6f8fb8412eca1ae3a7092c"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
                            "bd83bffe8851e2368f3d9280d213b7adac1b4073dbe2296bd1d6e1c6183a454e"),
                    Map.entry(
                            "server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java",
                            "ea9affd42829d4560c2b974e8d189bd6feac340112732cf15b89d797f7b4f7af"),
                    Map.entry(
                            "tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py",
                            "8d96674c8ea55f6050133945f0f58fe365ea9383d7660ba3c6d3423cf63bc7c5"),
                    Map.entry(
                            "tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py",
                            "c9d21809bd136ed131ee20ac6baabf0b6b67bcc85f03fab9fccedcd02c86f2c0"),
                    Map.entry(
                            "tools/build_phase4c_tag_migration_global_preflight_contract.py",
                            "604c550ceb144c0bdca1d92e915a166d84c582cd53084f934bac71e171154ddf"),
                    Map.entry(
                            "tools/phase2_wormhole_successor_acceptance.py",
                            "afd967894036289ad3587fc740c97931d1ca5492a9208829536bf6745a840ebc"),
                    Map.entry(
                            "tools/phase4c_http_target_execution_anchor_successor_acceptance.py",
                            "810efb88c88efeb35b7a1f182214dc8873ca7099d8f6dfb8ce6b1af651dd3ecd"),
                    Map.entry(
                            "tools/phase4c_http_target_execution_successor_acceptance.py",
                            "4048e962b5db2d332c0955099a77637c3542b77e58fd233b5460296c1f86abd9"),
                    Map.entry(
                            "tools/phase4c_tag_migration_global_preflight_successor_acceptance.py",
                            "6fe3bf23d53ccaccd33f3ccaf31466cf0fc44df0f71bcc6f798765519fe12f95"),
                    Map.entry(
                            "tools/phase4c_tag_migration_operator_core_successor_acceptance.py",
                            "c7e672f3a0d0ab959735de906c0e5131232c0dab17b698480f6a42cfb5871ee4"),
                    Map.entry(
                            "tools/test_phase2_wormhole_successor_acceptance.py",
                            "2c4881c5083c8e4ca2cf294ece486895e26d932d1f59d067f8da32ef544c63bc"),
                    Map.entry(
                            "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
                            "ab79ec3edc9f903a9917ae85450633982031f341aa219e75de08d69db0c63d26"),
                    Map.entry(
                            "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
                            "a308ba6b14bb9e960006378bdf165dc2dfece856bb09bf827d600a7a6f28e060"),
                    Map.entry(
                            "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
                            "3b59d4f9f4c3cafe84feb4bc0a902db1822455e73660f29461d2385370377122"),
                    Map.entry(
                            "tools/test_phase4b_personal_bank_share_list_read_contract.py",
                            "49441844f63e05ca57e0b89c751cca3b1b574c984223e588d40bac9e7613501f"),
                    Map.entry(
                            "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
                            "9625aad3553408ef631d055735af33b4b21847aaaf8a57d540dd582cba025ab9"),
                    Map.entry(
                            "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
                            "7c8a27ef4e97ed731dd4b0dd357942e32e75a45db3d9e482e7513b1e8c1820a4"),
                    Map.entry(
                            "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
                            "409a2663e26f559108e815a805f42f566f2a7dfea8d1da8f9aab966efa0a14cb"),
                    Map.entry(
                            "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
                            "18cdd0df59a7cfa6d052192ca85fe59cd50415fe263ae172133958d59df1f544"),
                    Map.entry(
                            "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py",
                            "17e77b5204bdec0b2deb43517354fada893802321a1cfa8f446151fcb5a2b0c9"),
                    Map.entry(
                            "tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py",
                            "7e6039fd7288cd16980149b385f71faa79659092f5bd187c14d060a19c08fe84"),
                    Map.entry(
                            "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
                            "3aacc3a54b0ecc6314f0f84d51057f657e8c188d1f673d931092c40c3f39106b"),
                    Map.entry(
                            "tools/test_phase4c_tag_migration_global_preflight_contract.py",
                            "28548d878900d0aeba6b983ba307af077b4ebdd01a6b27f4c496bf6ae472c313"),
                    Map.entry(
                            "tools/test_phase4c_tag_migration_operator_core_post_push_anchor_contract.py",
                            "2ddf897a07152d1a4a12f044ffe3d290591f86a3b21463aa1e25d74186345cb0"),
                    Map.entry(
                            "tools/test_phase4c_tag_migration_operator_core_contract.py",
                            "d3f89f0943d6aace6545f3f97ccc997d0c3aee9bc7175363bd47930281dfa42f"));

    private Phase4cTagMigrationExecutionProtocolSuccessorAcceptance() {
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
        require(successors.path("override_count").asInt() == 37
                        && propertyNames(overrides).equals(
                        SOURCE_TRANSITION_PATHS),
                "execution-protocol transition authority drifted");
        JsonNode descriptor = overrides.path(relative);
        require(propertyNames(descriptor).equals(Set.of(
                        "source", "accepted_sha256", "accepted_byte_count",
                        "successor_sha256", "successor_byte_count")),
                "execution-protocol transition descriptor drifted: "
                        + relative);
        SourceTransition transition = new SourceTransition(
                descriptor.path("source").asString(),
                descriptor.path("accepted_sha256").asString(),
                descriptor.path("accepted_byte_count").asLong(),
                descriptor.path("successor_sha256").asString(),
                descriptor.path("successor_byte_count").asLong());
        Path physical = fixedRegularFile(root, relative);
        require(relative.equals(transition.source())
                        && transition.acceptedSha256().equals(
                        ACCEPTED_TRANSITION_SHA256.get(relative)),
                "execution-protocol transition descriptor drifted: "
                        + relative);
        if (Files.size(physical) == transition.successorByteCount()
                && sha256(physical).equals(transition.successorSha256())) {
            return transition;
        }
        Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                .SourceTransition current =
                Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                        .transitionFromNodeD(
                                root,
                                relative,
                                transition.successorSha256(),
                                transition.successorByteCount());
        require(current != null
                        && relative.equals(current.source())
                        && Files.size(physical)
                        == current.successorByteCount()
                        && sha256(physical).equals(
                        current.successorSha256()),
                "execution-protocol transaction-write transition drifted: "
                        + relative);
        return new SourceTransition(
                relative,
                transition.acceptedSha256(),
                transition.acceptedByteCount(),
                current.successorSha256(),
                current.successorByteCount());
    }

    static String acceptedSha256(String relative) {
        return ACCEPTED_TRANSITION_SHA256.get(relative);
    }

    static String successorSha256(Path tiJavaRoot, String relative)
            throws IOException {
        SourceTransition transition = sourceTransition(tiJavaRoot, relative);
        return transition == null ? null : transition.successorSha256();
    }

    static ProductionRuntimeSuccessor validateProductionRuntimeSuccessor(
            Path tiJavaRoot,
            Map<String, String> acceptedFiles,
            Map<String, String> currentFiles,
            String view
    ) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode runtime = load(root).path("production_runtime_successor");
        JsonNode semantic;
        if ("full_runtime".equals(view)) {
            semantic = runtime;
        } else if ("learning_personalbank_main".equals(view)) {
            semantic = runtime.path("learning_personalbank_main");
        } else {
            throw new AssertionError(
                    "execution-protocol unknown production view: " + view);
        }
        TreeMap<String, String> accepted = new TreeMap<>(acceptedFiles);
        TreeMap<String, String> current = new TreeMap<>(currentFiles);
        require(accepted.size()
                        == semantic.path("accepted_file_count").asInt()
                        && canonicalSha256(JSON.valueToTree(accepted)).equals(
                        semantic.path("accepted_manifest_sha256").asString()),
                "execution-protocol rejected accepted production manifest");
        TreeMap<String, String> expectedCurrent = new TreeMap<>(accepted);
        expectedCurrent.putAll(textMap(semantic.path("added_files")));
        expectedCurrent.putAll(textMap(semantic.path("changed_files")));
        strings(semantic.path("deleted_files"))
                .forEach(expectedCurrent::remove);
        require("4A0M0D".equals(semantic.path("exact_delta").asString())
                        && textMap(semantic.path("added_files")).size() == 4
                        && textMap(semantic.path("changed_files")).isEmpty()
                        && strings(semantic.path("deleted_files")).isEmpty()
                        && current.equals(expectedCurrent)
                        && current.size()
                        == semantic.path("current_file_count").asInt()
                        && canonicalSha256(JSON.valueToTree(current)).equals(
                        semantic.path("current_manifest_sha256").asString()),
                "execution-protocol rejected current production manifest");
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
        require(acceptedReportSha256.equals(ACCEPTED_WORM_SHA256)
                        && acceptedReportSha256.equals(worm.path(
                        "accepted_report").path("sha256").asString())
                        && acceptedBuildContextSha256.equals(
                        ACCEPTED_BUILD_CONTEXT_SHA256)
                        && acceptedBuildContextSha256.equals(worm.path(
                        "accepted_build_context_sha256").asString())
                        && worm.path("accepted_chain_node_count").asInt() == 8,
                "execution-protocol rejected accepted WORM authority");
        String physicalBuildContext = javaBuildContextSha256(root);
        String nodeDCurrentBuildContext =
                worm.path("current_build_context_sha256").asString();
        if (!physicalBuildContext.equals(nodeDCurrentBuildContext)) {
            Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                    .validateCurrentBuildContext(root, physicalBuildContext);
        }
        return new WormSuccessor(
                acceptedReportSha256,
                acceptedBuildContextSha256,
                worm.path("accepted_chain_node_count").asInt(),
                worm.path("current_report").path("sha256").asString(),
                nodeDCurrentBuildContext,
                worm.path("current_chain_node_count").asInt());
    }

    static Set<String> minimalFixturePaths() {
        Set<String> paths = new LinkedHashSet<>();
        paths.add(CONTRACT_RELATIVE);
        paths.add(PREDECESSOR_RELATIVE);
        paths.add(ACCEPTED_WORM_RELATIVE);
        paths.add(HASHER_RELATIVE);
        paths.add("server/Dockerfile");
        paths.addAll(IMPLEMENTATION_SOURCE_PATHS);
        paths.addAll(SOURCE_TRANSITION_PATHS);
        paths.addAll(
                Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                        .minimalFixturePaths());
        return Set.copyOf(paths);
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadContractEnvelope(root);
        try {
            validate(contract, root);
            return contract;
        } catch (AssertionError predecessorError) {
            JsonNode successorPredecessor =
                    Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                            .loadNodeDPredecessor(root);
            require(successorPredecessor.equals(contract),
                    "execution-protocol successor returned a different predecessor");
            return contract;
        }
    }

    static void validate(JsonNode contract, Path tiJavaRoot)
            throws IOException {
        Path root = tiJavaRoot.toRealPath();
        require(propertyNames(contract).equals(Set.of(
                        "schema_version", "contract_id", "captured_at",
                        "scope", "status", "predecessor",
                        "execution_protocol",
                        "cryptographic_evidence_verifier",
                        "local_disposable_rehearsal",
                        "historical_source_successors",
                        "production_runtime_successor", "worm_successor",
                        "evidence", "authorization", "route_state",
                        "source_authority", "next_gate",
                        "document_payload_sha256")),
                "execution-protocol contract shape drifted");
        require(contract.path("schema_version").asInt() == 1
                        && CONTRACT_ID.equals(
                        contract.path("contract_id").asString())
                        && CONTRACT_CAPTURED_AT.equals(
                        contract.path("captured_at").asString())
                        && CONTRACT_SCOPE.equals(
                        contract.path("scope").asString())
                        && CONTRACT_STATUS.equals(
                        contract.path("status").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(contract.path(
                        "document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(contract)),
                "execution-protocol contract identity drifted");
        validatePredecessor(contract.path("predecessor"), root);
        validateSourceAuthority(contract.path("source_authority"), root);
        validateTransitions(contract.path("historical_source_successors"));
        validateRuntime(contract.path("production_runtime_successor"));
        validateWorm(contract.path("worm_successor"), root);
        validateProtocol(contract.path("execution_protocol"));
        validateCrypto(contract.path("cryptographic_evidence_verifier"));
        validateRehearsal(contract.path("local_disposable_rehearsal"));
        validateAuthorization(contract.path("authorization"));
        validateRoute(contract.path("route_state"));
    }

    private static JsonNode loadContractEnvelope(Path root)
            throws IOException {
        Path path = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(CONTRACT_BYTE_COUNT > 0
                        && CONTRACT_SHA256.matches("[0-9a-f]{64}")
                        && CONTRACT_PAYLOAD_SHA256.matches("[0-9a-f]{64}")
                        && Files.size(path) == CONTRACT_BYTE_COUNT
                        && CONTRACT_SHA256.equals(sha256(path)),
                "execution-protocol contract physical bytes drifted");
        JsonNode contract = readJson(path);
        require(contract.isObject()
                        && CONTRACT_PAYLOAD_SHA256.equals(contract.path(
                        "document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(contract)),
                "execution-protocol contract payload identity drifted");
        return contract;
    }

    private static void validatePredecessor(JsonNode descriptor, Path root)
            throws IOException {
        require(PREDECESSOR_RELATIVE.equals(
                        descriptor.path("source").asString())
                        && PREDECESSOR_ID.equals(
                        descriptor.path("contract_id").asString())
                        && PREDECESSOR_SHA256.equals(
                        descriptor.path("sha256").asString())
                        && descriptor.path("byte_count").asLong()
                        == PREDECESSOR_BYTE_COUNT
                        && PREDECESSOR_PAYLOAD_SHA256.equals(descriptor.path(
                        "document_payload_sha256").asString())
                        && PREDECESSOR_COMMIT.equals(
                        descriptor.path("fixed_commit_oid").asString())
                        && descriptor.path("immutable").asBoolean(),
                "execution-protocol predecessor descriptor drifted");
        Path path = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        require(Files.size(path) == PREDECESSOR_BYTE_COUNT
                        && PREDECESSOR_SHA256.equals(sha256(path)),
                "execution-protocol predecessor bytes drifted");
        JsonNode predecessor = readJson(path);
        require(PREDECESSOR_ID.equals(
                        predecessor.path("contract_id").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(predecessor.path(
                        "document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(predecessor))
                        && PREDECESSOR_INDEPENDENT_ACCEPTANCE_COMMIT.equals(
                        predecessor.path(
                        "independent_acceptance_checkpoint")
                        .path("commit_oid").asString()),
                "execution-protocol predecessor identity drifted");
    }

    private static void validateSourceAuthority(JsonNode authority, Path root)
            throws IOException {
        JsonNode sources = authority.path("fixed_non_control_sources");
        Set<String> expected = new LinkedHashSet<>(
                IMPLEMENTATION_SOURCE_PATHS);
        expected.addAll(SOURCE_TRANSITION_PATHS);
        require(expected.size() == 48
                        && authority.path(
                        "fixed_non_control_source_count").asInt() == 48
                        && authority.path(
                        "implementation_source_count").asInt() == 11
                        && authority.path(
                        "transition_source_count").asInt() == 37
                        && authority.path("control_source_count").asInt() == 7
                        && Set.copyOf(strings(authority.path(
                        "control_sources"))).equals(CONTROL_SOURCE_PATHS)
                        && propertyNames(sources).equals(expected)
                        && authority.path(
                        "control_sources_excluded_from_self_authority")
                        .asBoolean()
                        && !authority.path(
                        "current_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && authority.path(
                        "fixed_source_allowlist_exact").asBoolean()
                        && !authority.path("dynamic_source_discovery").asBoolean()
                        && authority.path(
                        "ordinary_build_and_load_are_gitless").asBoolean()
                        && !authority.path(
                        "live_head_main_or_origin_authority").asBoolean()
                        && authority.path(
                        "fixed_c2_commit_replay_is_explicit_only").asBoolean(),
                "execution-protocol source authority drifted");
        for (String relative : expected) {
            JsonNode descriptor = sources.path(relative);
            Path physical = fixedRegularFile(root, relative);
            require(relative.equals(descriptor.path("source").asString())
                            && Files.size(physical)
                            == descriptor.path("byte_count").asLong()
                            && sha256(physical).equals(
                            descriptor.path("sha256").asString()),
                    "execution-protocol fixed source drifted: " + relative);
        }
    }

    private static void validateTransitions(JsonNode successors) {
        JsonNode overrides = successors.path("overrides");
        require(PREDECESSOR_COMMIT.equals(successors.path(
                        "predecessor_checkpoint").asString())
                        && successors.path("override_count").asInt() == 37
                        && propertyNames(overrides).equals(
                        SOURCE_TRANSITION_PATHS)
                        && successors.path(
                        "accepted_bytes_replayable_only_by_explicit_fixed_commit")
                        .asBoolean()
                        && !successors.path(
                        "successor_external_git_anchor_complete").asBoolean()
                        && "reject".equals(
                        successors.path("unknown_path").asString())
                        && ACCEPTED_TRANSITION_SHA256.size() == 37,
                "execution-protocol source successor drifted");
        for (String relative : SOURCE_TRANSITION_PATHS) {
            JsonNode descriptor = overrides.path(relative);
            require(relative.equals(descriptor.path("source").asString())
                            && ACCEPTED_TRANSITION_SHA256.get(relative).equals(
                            descriptor.path("accepted_sha256").asString()),
                    "execution-protocol accepted transition drifted: "
                            + relative);
        }
    }

    private static void validateRuntime(JsonNode runtime) {
        require(runtime.path("accepted_file_count").asInt() == 307
                        && runtime.path("current_file_count").asInt() == 311
                        && "4A0M0D".equals(
                        runtime.path("exact_delta").asString())
                        && textMap(runtime.path("added_files")).size() == 4
                        && textMap(runtime.path("changed_files")).isEmpty()
                        && strings(runtime.path("deleted_files")).isEmpty(),
                "execution-protocol production runtime drifted");
        JsonNode main = runtime.path("learning_personalbank_main");
        require(main.path("accepted_file_count").asInt() == 50
                        && main.path("current_file_count").asInt() == 54
                        && "4A0M0D".equals(
                        main.path("exact_delta").asString()),
                "execution-protocol learning runtime drifted");
    }

    private static void validateWorm(JsonNode worm, Path root)
            throws IOException {
        require(ACCEPTED_WORM_RELATIVE.equals(worm.path("accepted_report")
                        .path("source").asString())
                        && ACCEPTED_WORM_SHA256.equals(worm.path(
                        "accepted_report").path("sha256").asString())
                        && worm.path("accepted_report").path(
                        "byte_count").asLong() == ACCEPTED_WORM_BYTE_COUNT
                        && ACCEPTED_BUILD_CONTEXT_SHA256.equals(worm.path(
                        "accepted_build_context_sha256").asString())
                        && worm.path("accepted_chain_node_count").asInt() == 8
                        && CURRENT_WORM_RELATIVE.equals(worm.path(
                        "current_report").path("source").asString())
                        && worm.path("current_chain_node_count").asInt() == 9
                        && worm.path("appended_node_count").asInt() == 1
                        && !worm.path(
                        "historical_nodes_rewritten").asBoolean()
                        && DOCKERFILE_SHA256.equals(
                        worm.path("dockerfile_sha256").asString()),
                "execution-protocol WORM successor drifted");
        Path acceptedPath = fixedRegularFile(root, ACCEPTED_WORM_RELATIVE);
        Path currentPath = fixedRegularFile(root, CURRENT_WORM_RELATIVE);
        require(Files.size(acceptedPath) == ACCEPTED_WORM_BYTE_COUNT
                        && ACCEPTED_WORM_SHA256.equals(sha256(acceptedPath))
                        && Files.size(currentPath) == worm.path(
                        "current_report").path("byte_count").asLong()
                        && sha256(currentPath).equals(worm.path(
                        "current_report").path("sha256").asString()),
                "execution-protocol WORM physical bytes drifted");
        JsonNode accepted = readJson(acceptedPath);
        JsonNode current = readJson(currentPath);
        require(current.path("source").equals(accepted.path("source"))
                        && current.path("restore").equals(
                        accepted.path("restore"))
                        && current.path("readRole").equals(
                        accepted.path("readRole"))
                        && EXPECTED_CANONICAL_SCHEMA_DUMP_SHA256.equals(
                        current.path("restore")
                                .path("canonicalSchemaDumpSha256").asString())
                        && DOCKERFILE_SHA256.equals(current.path("java")
                        .path("dockerfileSha256").asString())
                        && worm.path("current_build_context_sha256").asString()
                        .equals(current.path("java")
                                .path("buildContextSha256").asString())
                        && "unknown".equals(current.path(
                        "productionDatabaseVersion").asString())
                        && !current.path("flywayBaselineCreated").asBoolean(),
                "execution-protocol Node 9 WORM facts drifted");
    }

    private static void validateProtocol(JsonNode protocol) {
        require(protocol.path("explicit_callable_only").asBoolean()
                        && protocol.path(
                        "candidate_requires_fresh_complete_data_eligible_preflight")
                        .asBoolean()
                        && protocol.path(
                        "preverification_before_jdbc_or_membership_access")
                        .asBoolean()
                        && protocol.path(
                        "one_explicit_phase_per_invocation").asBoolean()
                        && !protocol.path(
                        "execute_all_force_reset_skip_or_rollback_entrypoint")
                        .asBoolean()
                        && !protocol.path(
                        "spring_bean_runner_scheduler_http_cli_registration")
                        .asBoolean(),
                "execution-protocol implementation boundary drifted");
    }

    private static void validateCrypto(JsonNode crypto) {
        require("pure-Ed25519".equals(
                        crypto.path("algorithm").asString())
                        && crypto.path("raw_public_key_bytes").asInt() == 32
                        && crypto.path("signature_bytes").asInt() == 64
                        && crypto.path("purpose_domain_separation").asBoolean()
                        && crypto.path(
                        "candidate_digest_recomputed_from_ids_and_binding")
                        .asBoolean()
                        && !crypto.path("dynamic_algorithm_dispatch").asBoolean()
                        && !crypto.path(
                        "durable_nonce_or_evidence_uuid_journal").asBoolean()
                        && !crypto.path("global_single_use_claimed").asBoolean(),
                "execution-protocol cryptographic boundary drifted");
    }

    private static void validateRehearsal(JsonNode rehearsal) {
        require(rehearsal.path("writer_identity_count").asInt() == 6
                        && rehearsal.path(
                        "writer_domain_expectation_count").asInt() == 18
                        && rehearsal.path(
                        "real_local_custom_dump_and_restore").asBoolean()
                        && rehearsal.path(
                        "wrong_binding_rejected_before_dml").asBoolean()
                        && rehearsal.path(
                        "disposable_database_role_dump_and_connection_residue")
                        .asInt() == 0
                        && !rehearsal.path(
                        "production_backup_restore_or_rollback_evidence")
                        .asBoolean()
                        && !rehearsal.path(
                        "production_writer_freeze_evidence").asBoolean(),
                "execution-protocol rehearsal boundary drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        Set<String> closed = Set.copyOf(
                strings(authorization.path("newly_closed_gates")));
        require(closed.equals(Set.of(
                        "migration_execution_protocol_implemented",
                        "cryptographic_evidence_verifier_implemented",
                        "local_test_backup_restore_execution_rehearsal_closed")),
                "execution-protocol newly closed gates drifted");
        for (String field : Set.of(
                "migration_execution_protocol_implemented",
                "cryptographic_evidence_verifier_implemented",
                "local_test_backup_restore_execution_rehearsal_closed")) {
            require(authorization.path(field).asBoolean(),
                    "execution-protocol required capability drifted: " + field);
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
                "production_trust_roots_or_key_rotation_audit",
                "durable_evidence_nonce_journal", "operator_runtime_wiring",
                "legacy_runtime_permanently_disabled",
                "route_or_openapi_delta", "client_gateway_or_proxy_change",
                "production_cutover")) {
            require(!authorization.path(field).asBoolean(),
                    "execution-protocol unauthorized gate opened: " + field);
        }
    }

    private static void validateRoute(JsonNode route) {
        require(route.path("total_operation_count").asInt() == 611
                        && route.path("migrated_operation_count").asInt() == 13
                        && route.path("pending_operation_count").asInt() == 598
                        && route.path(
                        "production_cutover_operation_count").asInt() == 0
                        && route.path(
                        "legacy_flask_remains_production_owner").asBoolean(),
                "execution-protocol route state drifted");
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path value = Path.of(relative);
        require(!value.isAbsolute() && value.getNameCount() > 0,
                "execution-protocol path escapes fixed root: " + relative);
        for (Path part : value) {
            require(!part.toString().isBlank()
                            && !part.toString().equals(".")
                            && !part.toString().equals(".."),
                    "execution-protocol path escapes fixed root: " + relative);
        }
        Path base = root.toRealPath();
        Path cursor = base;
        for (Path part : value) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "execution-protocol fixed source is a symlink: "
                            + relative);
        }
        Path resolved = base.resolve(value).normalize();
        require(resolved.startsWith(base)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "execution-protocol fixed source is absent or not regular: "
                        + relative);
        return resolved;
    }

    private static String javaBuildContextSha256(Path root)
            throws IOException {
        Path script = fixedRegularFile(root, HASHER_RELATIVE);
        Process process = new ProcessBuilder("/bin/sh", script.toString())
                .directory(root.toFile())
                .start();
        try {
            String stdout = new String(
                    process.getInputStream().readAllBytes(),
                    StandardCharsets.UTF_8).trim();
            String stderr = new String(
                    process.getErrorStream().readAllBytes(),
                    StandardCharsets.UTF_8).trim();
            int exitCode = process.waitFor();
            require(exitCode == 0,
                    "execution-protocol build-context hasher failed: "
                            + stderr);
            return stdout;
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IOException(
                    "execution-protocol build-context hasher interrupted",
                    error);
        }
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
