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
 * Gitless Java acceptance for the fixed Phase 4C tag global-preflight
 * successor. It mirrors the Python bridge without consulting Git, directory
 * discovery, or any live branch ref.
 */
final class Phase4cTagMigrationGlobalPreflightSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-global-preflight-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-tag-migration-global-preflight-contract";
    private static final String CONTRACT_SHA256 =
            "65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "c7a94e88772a2453743f9821b165ae10f52650a41bf6dab78006d7058951159e";
    private static final long CONTRACT_BYTES = 102_931L;

    private static final String TYPED_ANCHOR_CONTRACT =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-typed-normalization-"
                    + "anchor-contract.json";
    private static final String PHASE6_ANCHOR_CONTRACT =
            "docs/refactor/phase6/"
                    + "web-foundation-source-successor-anchor-contract.json";
    private static final String HISTORICAL_TARGET_EXECUTION_CONTRACT =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-contract.json";
    private static final String HISTORICAL_READ_CONTRACT =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-read-contract.json";
    private static final String HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-contract.json";
    private static final String HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-"
                    + "contract.json";
    private static final String HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-"
                    + "anchor-contract.json";
    private static final int HISTORICAL_PRODUCTION_FILE_COUNT = 297;
    private static final String HISTORICAL_PRODUCTION_MANIFEST_SHA256 =
            "d327a5ef85fa47abc6417527d7bfd99a01f29de6ea3c2f08205cbf30a6e38f79";
    private static final int SUCCESSOR_PRODUCTION_FILE_COUNT = 300;
    private static final String SUCCESSOR_PRODUCTION_MANIFEST_SHA256 =
            "8d28a382447c8756b2ec4cfc4107bc55fd744587d81a8835b71eee1f1942fbb3";
    private static final String HISTORICAL_BUILD_CONTEXT_SHA256 =
            "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3";
    private static final String TERMINAL_BUILD_CONTEXT_SHA256 =
            "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17";
    private static final Map<String, String> PRODUCTION_MANIFEST_ADDITIONS = Map.of(
            "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
                    + "LegacyPersonalBankTagGlobalPreflight.java",
            "cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76",
            "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
                    + "LegacyPersonalBankTagPreflightParser.java",
            "c3311e28f33c8bc447fd72191af696ceca333162747e94eb91681dd75c0f5bf3",
            "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
                    + "LegacyPersonalBankTagPreflightReport.java",
            "d7d988f5bfe7c86e30a5410e8eac0032a24ad5c85011b6c03de159c97d3ff750");
    private static final String DOCKERFILE_SHA256 =
            "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499";

    private static final Set<String> TYPED_PHASE2_PATHS = Set.of(
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py");
    private static final Set<String> PHASE6_TYPED_BRIDGE_PATHS = Set.of(
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchor"
                    + "ContractParityTest.java",
            "tools/phase4c_http_typed_normalization_anchor_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_typed_"
                    + "normalization_anchor_contract.py");
    private static final Set<String> PHASE6_DOCUMENT_PATHS = Set.of(
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md");
    private static final Set<String> PHASE6_BOOTSTRAP_PATHS = Set.of(
            "tools/test_phase6_web_foundation_source_successor_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java");
    private static final Set<String> SEMANTIC_CONSUMER_PATHS = Set.of(
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "implementation_contract.py",
            "tools/phase4c_http_implementation_successor_acceptance.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/phase4c_http_target_execution_successor_acceptance.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_anchor_contract.py",
            "tools/phase4c_http_target_execution_anchor_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "composition_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "ModuleContractParityTest.java",
            "tools/phase4c_read_successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cReadSuccessorAcceptance.java",
            "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
            "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
            "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
            "tools/test_phase4b_personal_bank_share_list_read_contract.py",
            "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpImplementationSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_anchor_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "implementation_contract.py");
    private static final Set<String> POST_PUSH_BRIDGE_PATHS = Set.of(
            "tools/phase4c_http_target_execution_post_push_"
                    + "successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java");
    private static final Set<String> TYPED_NORMALIZATION_BRIDGE_PATHS = Set.of(
            "tools/phase4c_http_typed_normalization_successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java");

    /**
     * The only historical Node A inputs that Node C is allowed to replace.
     * Node A's six control-source transitions are intentionally absent here:
     * they are fixed directly by Node C and were never self-authority inputs
     * of this contract.
     */
    private static final Set<String> NODE_C_SOURCE_SUCCESSOR_PATHS = Set.of(
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagGlobalPreflight.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagGlobalPreflightTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "ModuleContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
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
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py");

    private static final Set<String> CONTROL_SOURCE_PATHS = Set.of(
            CONTRACT_RELATIVE,
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-global-preflight.md",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightContractParityTest.java",
            "tools/build_phase4c_tag_migration_global_preflight_contract.py",
            "tools/phase4c_tag_migration_global_preflight_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_tag_migration_global_preflight_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorContractParityTest.java",
            "tools/phase6_web_foundation_source_successor_anchor_acceptance.py",
            "tools/test_phase6_web_foundation_source_successor_anchor_contract.py");

    private static final Set<String> FIXED_SOURCE_PATHS = Set.of(
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-composition-contract.json",
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-route-promotion-contract.json",
            "docs/refactor/phase4c/approved-differences.md",
            "docs/refactor/phase4c/effective-data-ownership-status.json",
            "docs/refactor/phase4c/data-ownership-delta.csv",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "persistence/LegacyPersonalBankTagMigrationEvidence.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "persistence/LegacyPersonalBankTagMigrationEvidenceTest.java",
            "server/src/test/java/io/saksk/ti/integration/"
                    + "Phase4cLegacyPersonalBankTagMigrationEvidenceIT.java",
            "server/src/test/resources/db/phase4c/"
                    + "069-legacy-personal-bank-tag-migration-schema.sql",
            "server/src/test/resources/db/phase4c/"
                    + "070-legacy-personal-bank-tag-migration-seed.sql",
            "server/src/main/java/io/saksk/ti/personalbank/api/"
                    + "PersonalBankQuestionFactsApi.java",
            "server/src/main/java/io/saksk/ti/personalbank/api/"
                    + "PersonalBankQuestionMembershipView.java",
            TYPED_ANCHOR_CONTRACT,
            PHASE6_ANCHOR_CONTRACT,
            HISTORICAL_TARGET_EXECUTION_CONTRACT,
            HISTORICAL_READ_CONTRACT,
            HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT,
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT,
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT,
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py",
            "tools/phase4c_http_typed_normalization_anchor_"
                    + "successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchor"
                    + "ContractParityTest.java",
            "tools/test_phase4c_personal_bank_user_counts_http_typed_"
                    + "normalization_anchor_contract.py",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "tools/test_phase6_web_foundation_source_successor_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "implementation_contract.py",
            "tools/phase4c_http_implementation_successor_acceptance.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/phase4c_http_target_execution_successor_acceptance.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_anchor_contract.py",
            "tools/phase4c_http_target_execution_anchor_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "composition_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "ModuleContractParityTest.java",
            "tools/phase4c_read_successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cReadSuccessorAcceptance.java",
            "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
            "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
            "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
            "tools/test_phase4b_personal_bank_share_list_read_contract.py",
            "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
            "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpImplementationSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_anchor_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "implementation_contract.py",
            "tools/phase4c_http_target_execution_post_push_"
                    + "successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
            "tools/phase4c_http_typed_normalization_successor_acceptance.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-"
                    + "worm-evidence.json",
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-global-preflight-worm-evidence.json",
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-global-preflight-hardening-"
                    + "worm-evidence.json",
            "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagPreflightParser.java",
            "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagPreflightReport.java",
            "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagGlobalPreflight.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagPreflightParserTest.java",
            "server/src/test/java/io/saksk/ti/learning/infrastructure/"
                    + "migration/LegacyPersonalBankTagGlobalPreflightTest.java",
            "server/src/test/java/io/saksk/ti/integration/"
                    + "Phase4cLegacyPersonalBankTagGlobalPreflightIT.java",
            "server/src/test/resources/db/phase4c/"
                    + "071-legacy-personal-bank-tag-global-preflight-schema.sql",
            "server/src/test/resources/db/phase4c/"
                    + "072-legacy-personal-bank-tag-global-preflight-seed.sql");

    private static final Map<String, Transition> TRANSITIONS = Map.ofEntries(
            transition(
                    "infra/phase2/README.md",
                    "414901d53174c7875ea000c323652a1ddf046a2e97018bbbd1dc4c9a4b3bf988",
                    6_959L,
                    "a0c467bfc8aa0f0b64b4d520f9cda60ff081a340f016647e1da934c73b7b99d5",
                    7_474L,
                    TYPED_ANCHOR_CONTRACT),
            transition(
                    "infra/phase2/verify-static.sh",
                    "410108998f03e4d857d230c75687e854bd3bad99ba85d18c2fb090978ffa46d7",
                    14_719L,
                    "893ca920d0ed1bd62e16509893fa30bbfc72b88368d66d96c2ebc5c2fbae38dc",
                    16_417L,
                    TYPED_ANCHOR_CONTRACT),
            transition(
                    "tools/phase2_wormhole_successor_acceptance.py",
                    "1164b6c584f4905a8011c5320eac62591e039ad0526b5a0657908f7b82688480",
                    25_791L,
                    "5c93b9aa00d3faec19ebc8d6472bd9e8ab1903a7116d487ff8a711fc60fd8d20",
                    28_590L,
                    TYPED_ANCHOR_CONTRACT),
            transition(
                    "tools/test_phase2_wormhole_successor_acceptance.py",
                    "ff3250a88eb6e16102fc91930beec627f79ed57720140a32e7ad4410d7856e9f",
                    44_809L,
                    "e61ed72335bba631cf34ebfe06fae8d391e7828622eba17d0240f59efed379a3",
                    52_825L,
                    TYPED_ANCHOR_CONTRACT),
            transition(
                    "tools/phase4c_http_typed_normalization_anchor_"
                            + "successor_acceptance.py",
                    "cf434c2dc8e33c0b60d09646292fc358bc2df678bfe2f83d04edae79c7bd4aee",
                    41_725L,
                    "c54843d2c759882e4d5e7553e9b76598a1ecd31038ace27ac265275887a414d2",
                    45_142L,
                    PHASE6_ANCHOR_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
                    "b762441b9d0537240e231effbe5477b89713e7abc861ff9d5a614fc80008848c",
                    43_848L,
                    "57be8ccb44124d315c21e21e9041861cdcb4568a814af56dbe1725635a479374",
                    45_695L,
                    PHASE6_ANCHOR_CONTRACT),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_typed_"
                            + "normalization_anchor_contract.py",
                    "a96c4431b258b15d367250b668602fcb0ca04cab9555f13a4abfaa8914b0edec",
                    11_128L,
                    "cdc78a5f771d09eb1822f3dbcd10030e812e4a5ab6b7792ce2b0a9d8366e90ba",
                    13_443L,
                    PHASE6_ANCHOR_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchor"
                            + "ContractParityTest.java",
                    "f0f57fbd1c24e8f26878209eba298645c63bd962381d26d2505fb76ee495cda8",
                    14_962L,
                    "faff2f55f48cdaa8bab92530347cda47a0f3ba4dc4227c86242afb94d78aebc0",
                    17_295L,
                    PHASE6_ANCHOR_CONTRACT),
            transition(
                    "docs/refactor/05-progress.md",
                    "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
                    105_423L,
                    "8478e44622fc666fdb9a377b15ced624e34d104d1fcbb9b36a4913cfb3ddedf0",
                    107_912L,
                    PHASE6_ANCHOR_CONTRACT),
            transition(
                    "docs/refactor/phase4c/README.md",
                    "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
                    23_309L,
                    "4d75ba666d7d45d620a4fba4574e4c2640b754c5a6beadbdbfdee5498aa3cc48",
                    26_858L,
                    PHASE6_ANCHOR_CONTRACT),
            transition(
                    "tools/test_phase6_web_foundation_source_successor_contract.py",
                    "fb553e8d15c8b748dc62eb6517f775614132657a60b13716449ad1a72606685d",
                    9_139L,
                    "3bc6342e7dad775f7c92acfc0f8cb23cd94aabd6d395f4f0fae420faea14ee6b",
                    9_295L,
                    PHASE6_ANCHOR_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase6WebFoundationSourceSuccessorContractParityTest.java",
                    "34d6b638cf40667a2c0b1ce1214cc04b8e149321f3137ea8d5d09ee44290d694",
                    11_770L,
                    "e61b445cbedddd5b71efe7dda22811128414b58089bf1525aaa4017485f6675d",
                    11_762L,
                    PHASE6_ANCHOR_CONTRACT),
            transition(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "implementation_contract.py",
                    "d020cf859dcba608d9b67d122ebfaca0d1bfd3161a12fc7c386d090e65938ef0",
                    54_261L,
                    "1f1c31977c356d93bfabe6714692efa27c5b3c34178e6df6b3517a3362f610e3",
                    57_899L,
                    HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT),
            transition(
                    "tools/phase4c_http_implementation_successor_acceptance.py",
                    "54438d9ee44d391b813a1c3503444dd65d627e3b5932971e49ef549650fbbff4",
                    59_107L,
                    "f0eba1dbbe3f0cfdbd384c0aea8ba9b768d16edc414ed7c1b1cf5fa8fd31641d",
                    61_439L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_contract.py",
                    "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209",
                    61_952L,
                    "3064c164d300499d958947068d3acd50c8823c741d9a0144860b5f3b1b532f7d",
                    65_798L,
                    HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT),
            transition(
                    "tools/phase4c_http_target_execution_successor_acceptance.py",
                    "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a",
                    81_902L,
                    "daca285575123c6b3d690c52977bbf8797fa46d5db75862b774805acb586a230",
                    84_585L,
                    HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT),
            transition(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_anchor_contract.py",
                    "b87133b5c187561970c322a92eb22f84cb7a768a9168870cc7517dd973616667",
                    34_518L,
                    "624d741b383866ce1bb8ec49c24445164665096cdf5b9ab679b2561c61ab7e9a",
                    36_240L,
                    HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT),
            transition(
                    "tools/phase4c_http_target_execution_anchor_"
                            + "successor_acceptance.py",
                    "03b411be87bd9f8d4dbb94ddcfb9495ec7523fb5c9482f3c1fb4098d1ab7e455",
                    34_568L,
                    "e91c56e91cdeff3bf069407d8e43d7d1b76fb131c875cf536e561976fe395141",
                    36_566L,
                    HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_"
                            + "composition_contract.py",
                    "b81c8fb13f2ce4dd0d917a0876b88a20804bd1d272a7c261563dad9513d42f17",
                    55_453L,
                    "51ab42d0a220f3e91ac07a9b3ab1f6a2ca6c366b994de200effae31a074a766b",
                    60_156L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
                    "641c90d33de50daeb3a1a1c9a3ae5027562273f780f88e6a26cf00ad3bd462ac",
                    21_392L,
                    "6c302395dca0d7d319233e6463ed65b26aa3ea103c90511752ae4cac710dbaad",
                    24_536L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "ModuleContractParityTest.java",
                    "02a4b9bfabe2f9e3789e94826b1f337e8a0986e5d36f42ac243cbe79060a82d2",
                    181_374L,
                    "984863bff3762adc8e375f0073559bb1e0e1d0ed16c368147087fdc3ca4efcd1",
                    182_577L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/phase4c_read_successor_acceptance.py",
                    "1e494bce628e87bc2db3d01742fb929752fedaefd7563defccad7b972c951980",
                    13_218L,
                    "25792f3a1371b8a492d674d70228ce81872e0ce48c2aab8051805c8c0b41de8a",
                    15_161L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cReadSuccessorAcceptance.java",
                    "5047c8b0a36450a72ba74a460db115ab33a58861b64216fa2cc67a7ddb0a026d",
                    18_364L,
                    "4699c29cb6e5f790b448752896cc42c413e9f0b3c4844551c4a0b2931517d1a0",
                    19_159L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
                    "e37b0418e8018d58135c5b1c55149d9679dfedb21f8b67fca3425b874ea23efc",
                    23_701L,
                    "31dec8b10fad1f044ecbca4a76da0d4f1f97ffbbe32e075895e050372ff8ba4a",
                    24_249L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
                    "f236ed8080a4e73d294d0eb96f1b19f8b3116ef0a51ba1be6d5d8e695dc558e0",
                    18_911L,
                    "7afd91f0e0048cba029d38965c900da670d5f327b8b9541b0962533b1b1f09eb",
                    19_451L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
                    "c60e4d9abb01c70001e703cf8c4c5eed77bd65445c506e99a9e3dd38dadab2ee",
                    32_717L,
                    "32b4d8e625f452ba20852fe64805086a6d878f3f8518298e7340122ff6120943",
                    33_265L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/test_phase4b_personal_bank_share_list_read_contract.py",
                    "ffde7c337edf81ba8cf1a457800e89e3150df10b44ea7da50e99436534caa671",
                    45_007L,
                    "047563af77f5786b0af24eeb20f8d287163df44778aad1ee56d1805a05207ec4",
                    45_547L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
                    "84f7ee524b57e9417267380b73ebc68439382b578f2b7674c50cdbf2a6021e0e",
                    36_086L,
                    "162e057e07d6d0d0f73b6ee8bf9210fd98c492369222ce649a4f5bd5418b16b4",
                    37_033L,
                    HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT),
            transition(
                    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
                    "de1415897a0cef4e98266aaca699b162dd469caf17628dd2fde19bed691ef32c",
                    25_059L,
                    "4f3c9ab19370eabd6dbe6dbea047d1e176c3a4e8ed947035a54dc210b75e2057",
                    25_598L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
                    "90c77b28c1c08822d900f150e5c4c69fe4a7463b5dfc7a4ce021fc599c71a15a",
                    33_924L,
                    "0a980e05a5fd4204e5db630447c7b018d54e2e89b64e7f069eb1329f85a5d372",
                    34_463L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpImplementationSuccessorAcceptance.java",
                    "1d2c193fb7a63173850bfee7ce382e7b4bc417c5b3879f3ef4bb43187f980275",
                    79_412L,
                    "fff0820405e76a4b7c58b094e21619ea050664a3b3ebfbc59abc29a83755465d",
                    80_984L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
                    "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578",
                    89_014L,
                    "10d19deb68495db02f9113dd58bdf7bbf7dfa67a8885c49f7dd88685f574ff78",
                    91_381L,
                    HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_contract.py",
                    "a8ce7fc93fe022d16a10e4bdd0fa9bff55788b076eb78601efba373c29c54a4b",
                    32_651L,
                    "469c46bde8e339ef28a461f3fd2a34ee7e02bfa12cb75eec4f881454049e7957",
                    34_398L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "entry_contract.py",
                    "c87d528ad6ee912863da16a49e0a398cffe3c9479d1f58461e32035b76fafd26",
                    31_074L,
                    "fcc4eee103b33604addfd17e453793dd41c498de62fe0538e873520dbd285b26",
                    32_398L,
                    HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT),
            transition(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py",
                    "a215e6b65624630de990dcae7e8d718e8a38a1fadae3e00ee0f3ccb81788959f",
                    31_546L,
                    "bbafe62ee77ab0e5c25ed0daf96dc8207cc033d4f39f6cdb3d9cfa8f18365285",
                    33_559L,
                    HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py",
                    "87078f6d01957dcbbb37b488048a6702bc2212850ee9b2b75aa9b68aba352057",
                    12_208L,
                    "420a727733f4c3a72f1c78c933491ab89fff7bbba0ddb1f1c9f7a8867a73c3bf",
                    12_482L,
                    TYPED_ANCHOR_CONTRACT),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py",
                    "3ded87895b33befb0f80905a1490d5f9207ae4e9ee26e939e5c00ebbd30a7874",
                    19_311L,
                    "49621a580785ddd0c1210bf564e563b41e04bebbc87c33752e95bc6cb9cb89fd",
                    19_769L,
                    TYPED_ANCHOR_CONTRACT),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "implementation_contract.py",
                    "9c61d6cefdd980457197fb850f690c6adc1a84fdb3d21905a2a5cfdb1bc258c2",
                    10_281L,
                    "a6b70a441470d079b5bc2dc392887d49af72d6dc75a4feba3226a772b5b4c9d5",
                    10_308L,
                    HISTORICAL_TARGET_EXECUTION_CONTRACT),
            transition(
                    "tools/phase4c_http_target_execution_post_push_"
                            + "successor_acceptance.py",
                    "944c925704e1b237a7d8e16c76591a0e8b7965d388bedd9e2a52492e0511c90c",
                    30_640L,
                    "b19db64d6ddb71b0cac1d4ae296c02e65e82d476b37b9db5ec5fbfcfd7f4a8df",
                    32_538L,
                    HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
                    "46f68412ea0cf42687133ba87a2184b86fe1b0c29625b1ee3f6e8f7301399efa",
                    45_004L,
                    "a39a7b768979208e5bdcbdcbcbfa7d327521fb69e65d271b5d2f2da47f7ad348",
                    46_017L,
                    HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT),
            transition(
                    "tools/phase4c_http_typed_normalization_"
                            + "successor_acceptance.py",
                    "e71a5eec0e71ff824750f6eb20c4b310fdb0d8273fe89d83a23aee422ba282c5",
                    54_168L,
                    "a852f20ffccd8d2f1597a1bd2adb525ca66e83fed707ef6d44ff9a8d35c240c8",
                    57_882L,
                    TYPED_ANCHOR_CONTRACT),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
                    "f78882b20e38857c420b750677e4e8dd52922a1f0c04c249db9ed0d4f3db4fd5",
                    76_703L,
                    "ec7c98b04a26f25940fd5b9ec4120ebd478aa41798d4040f1cce97336898d6d2",
                    79_735L,
                    TYPED_ANCHOR_CONTRACT));

    private static final String CODE_FIXED_ACCEPTED_BYTES =
            "code_fixed_pending_bootstrap_external_git_anchor";
    private static final Map<String, AcceptedAuthorityFields>
            EXPLICIT_ACCEPTED_AUTHORITIES = Map.ofEntries(
            authority(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "implementation_contract.py",
                    HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT
                            + "#/source_contracts/contract_builder/sha256",
                    CODE_FIXED_ACCEPTED_BYTES),
            authority(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "entry_contract.py",
                    HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT
                            + "#/historical_successor_acceptance/"
                            + "http_entry_source_overrides/tools~1test_phase4c_"
                            + "personal_bank_user_counts_http_entry_contract.py/"
                            + "successor_sha256",
                    CODE_FIXED_ACCEPTED_BYTES),
            targetSourceAuthority(
                    "tools/phase4c_http_implementation_"
                            + "successor_acceptance.py",
                    "historical_python_implementation_successor_bridge"),
            targetSourceAuthority(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpImplementationSuccessorAcceptance.java",
                    "historical_java_implementation_successor_bridge"),
            targetSourceAuthority(
                    "tools/test_phase4c_personal_bank_user_counts_"
                            + "composition_contract.py",
                    "historical_composition_contract_test"),
            targetSourceAuthority(
                    "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
                    "historical_read_contract_test"),
            authority(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "ModuleContractParityTest.java",
                    HISTORICAL_READ_CONTRACT
                            + "#/historical_successor_acceptance/java_sources/"
                            + "server~1src~1test~1java~1io~1saksk~1ti~1"
                            + "architecture~1ModuleContractParityTest.java/"
                            + "successor_sha256",
                    CODE_FIXED_ACCEPTED_BYTES),
            targetSourceAuthority(
                    "tools/phase4c_read_successor_acceptance.py",
                    "historical_python_read_successor_bridge"),
            targetSourceAuthority(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cReadSuccessorAcceptance.java",
                    "historical_java_read_successor_bridge"),
            targetSourceAuthority(
                    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
                    "historical_all_shares_entry_contract_test"),
            authority(
                    "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
                    HISTORICAL_READ_CONTRACT
                            + "#/historical_successor_acceptance/python_sources/"
                            + "tools~1test_phase4b_personal_bank_all_shares_"
                            + "read_contract.py/successor_sha256",
                    CODE_FIXED_ACCEPTED_BYTES),
            authority(
                    "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
                    HISTORICAL_READ_CONTRACT
                            + "#/historical_successor_acceptance/python_sources/"
                            + "tools~1test_phase4b_personal_bank_share_list_"
                            + "entry_contract.py/successor_sha256",
                    CODE_FIXED_ACCEPTED_BYTES),
            targetSourceAuthority(
                    "tools/test_phase4b_personal_bank_share_list_read_contract.py",
                    "historical_share_list_read_contract_test"),
            authority(
                    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
                    HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT
                            + "#/source_contracts/"
                            + "historical_phase4b_entry_contract_test/sha256",
                    CODE_FIXED_ACCEPTED_BYTES),
            authority(
                    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
                    HISTORICAL_READ_CONTRACT
                            + "#/historical_successor_acceptance/python_sources/"
                            + "tools~1test_phase4b_personal_bank_usage_stats_"
                            + "entry_contract.py/successor_sha256",
                    CODE_FIXED_ACCEPTED_BYTES),
            authority(
                    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
                    HISTORICAL_READ_CONTRACT
                            + "#/historical_successor_acceptance/python_sources/"
                            + "tools~1test_phase4b_personal_bank_usage_stats_"
                            + "read_contract.py/successor_sha256",
                    CODE_FIXED_ACCEPTED_BYTES),
            targetSourceAuthority(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_contract.py",
                    "contract_test"),
            targetSourceAuthority(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "implementation_contract.py",
                    "historical_implementation_contract_test"),
            postPushAnchorArtifactAuthority(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_contract.py"),
            postPushAnchorArtifactAuthority(
                    "tools/phase4c_http_target_execution_"
                            + "successor_acceptance.py"),
            postPushAnchorArtifactAuthority(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionSuccessorAcceptance.java"),
            postPushContractArtifactAuthority(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_anchor_contract.py",
                    "anchor_builder"),
            postPushContractArtifactAuthority(
                    "tools/phase4c_http_target_execution_anchor_"
                            + "successor_acceptance.py",
                    "python_anchor_acceptance"),
            historicalOverrideAuthority(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py"),
            typedHistoricalOverrideAuthority(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py"),
            typedHistoricalOverrideAuthority(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py"),
            historicalOverrideAuthority(
                    "tools/phase4c_http_target_execution_post_push_"
                            + "successor_acceptance.py"),
            historicalOverrideAuthority(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java"),
            typedHistoricalOverrideAuthority(
                    "tools/phase4c_http_typed_normalization_"
                            + "successor_acceptance.py"),
            typedHistoricalOverrideAuthority(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java"));

    private static final List<WormNode> WORM_NODES = List.of(
            worm(
                    "infra/phase2/local-reference-verification.json",
                    "779154127fc700e213fbb3d5f83c112c090d3481236dcd361dbd72b74a0bd1ad",
                    "7e1da0e1af1d249b6bf5e13d3b6de94ea92920a95620294ffea369e84d448e16",
                    null),
            worm(
                    "docs/refactor/phase4c/"
                            + "personal-bank-user-counts-entry-worm-evidence.json",
                    "cfb262319ded0840218fd9bfb4deff1e7bc9c66b5849e3ff05f49a459e686884",
                    "c59ee688646b7c23f0f883b4c1377d2a33b507e7dd08b978e98cf3ebdc11825c",
                    "779154127fc700e213fbb3d5f83c112c090d3481236dcd361dbd72b74a0bd1ad"),
            worm(
                    "docs/refactor/phase4c/"
                            + "personal-bank-user-counts-read-worm-evidence.json",
                    "fade745bfa0da6ea7d4fc6a16dcee499149ee06dc1113fc92b5256df23cc42e9",
                    "b616ee8c53eaee58d1771422607d3e9215977a47245aa41e4f3553aee62d64fb",
                    "cfb262319ded0840218fd9bfb4deff1e7bc9c66b5849e3ff05f49a459e686884"),
            worm(
                    "docs/refactor/phase4c/"
                            + "personal-bank-user-counts-read-access-worm-evidence.json",
                    "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6",
                    "935e6a95a33621b01e1e04d752a09513c8037cffe807a73fa1ce9850fb5912f0",
                    "fade745bfa0da6ea7d4fc6a16dcee499149ee06dc1113fc92b5256df23cc42e9"),
            worm(
                    "docs/refactor/phase4c/"
                            + "personal-bank-user-counts-http-implementation-"
                            + "worm-evidence.json",
                    "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
                    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3",
                    "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"),
            worm(
                    "docs/refactor/phase4c/"
                            + "personal-bank-tag-global-preflight-worm-evidence.json",
                    "283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72",
                    "2b2f2b9956a9188a81606b50405ac82ded0253bbe2539d6fb841575b4c21dcf9",
                    "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39"),
            worm(
                    "docs/refactor/phase4c/"
                            + "personal-bank-tag-global-preflight-hardening-"
                            + "worm-evidence.json",
                    "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344",
                    "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17",
                    "283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72"));

    private Phase4cTagMigrationGlobalPreflightSuccessorAcceptance() {
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static Set<String> successorPaths() {
        return TRANSITIONS.keySet();
    }

    static String acceptedSha256(String relative) {
        Transition transition = TRANSITIONS.get(relative);
        return transition == null ? null : transition.acceptedSha256();
    }

    static String successorSha256(Path tiJavaRoot, String relative)
            throws IOException {
        Transition transition = TRANSITIONS.get(relative);
        if (transition == null) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadContractEnvelope(root);
        JsonNode actual = contract.path("source_successor_bridges")
                .path("overrides").path(relative);
        require(transition.acceptedSha256().equals(
                        actual.path("accepted_sha256").asString())
                        && transition.successorSha256().equals(
                        actual.path("successor_sha256").asString())
                        && transition.successorBytes()
                        == actual.path("successor_byte_count").asLong(),
                "tag preflight source-successor contract drifted: " + relative);
        Path path = fixedRegularFile(root, relative);
        long physicalBytes = Files.size(path);
        String physicalSha256 = sha256(path);
        if (physicalBytes == transition.successorBytes()
                && transition.successorSha256().equals(physicalSha256)) {
            return physicalSha256;
        }
        validateNodeCSourceTransition(
                root, relative,
                transition.successorSha256(), transition.successorBytes(),
                physicalSha256, physicalBytes);
        return physicalSha256;
    }

    static ProductionRuntimeSuccessor validateProductionRuntimeSuccessor(
            Path tiJavaRoot,
            Map<String, String> acceptedFiles,
            Map<String, String> currentFiles,
            String view
    ) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = load(root);
        JsonNode production = contract.path("historical_semantic_successors")
                .path("production_runtime_manifest");
        Map<String, String> historicalFiles = textMap(readJson(
                fixedRegularFile(root, HISTORICAL_TARGET_EXECUTION_CONTRACT))
                .path("production_surface").path("files"));
        JsonNode semantic;
        Map<String, String> expectedAccepted;
        if ("full_runtime".equals(view)) {
            semantic = production;
            expectedAccepted = historicalFiles;
        } else if ("learning_personalbank_main".equals(view)) {
            semantic = production.path("learning_personalbank_main");
            TreeMap<String, String> filtered = new TreeMap<>();
            historicalFiles.forEach((relative, digest) -> {
                if (relative.startsWith(
                        "server/src/main/java/io/saksk/ti/learning/")
                        || relative.startsWith(
                        "server/src/main/java/io/saksk/ti/personalbank/")) {
                    filtered.put(relative, digest);
                }
            });
            expectedAccepted = Map.copyOf(filtered);
        } else {
            throw new AssertionError(
                    "tag preflight unknown production view: " + view);
        }
        TreeMap<String, String> normalizedAccepted = new TreeMap<>(acceptedFiles);
        TreeMap<String, String> normalizedCurrent = new TreeMap<>(currentFiles);
        require(normalizedAccepted.equals(expectedAccepted)
                        && normalizedAccepted.size()
                        == semantic.path("accepted_file_count").asInt()
                        && semantic.path("accepted_manifest_sha256").asString()
                        .equals(canonicalSha256(
                                JSON.valueToTree(normalizedAccepted))),
                "tag preflight rejected historical production manifest");
        TreeMap<String, String> expectedCurrent = new TreeMap<>(normalizedAccepted);
        expectedCurrent.putAll(textMap(semantic.path("added_files")));
        boolean currentMatchesNodeA = normalizedCurrent.equals(expectedCurrent)
                && normalizedCurrent.size()
                == semantic.path("successor_file_count").asInt()
                && semantic.path("successor_manifest_sha256").asString()
                .equals(canonicalSha256(JSON.valueToTree(normalizedCurrent)));
        if (!currentMatchesNodeA) {
            var nodeC = Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                    .validateProductionRuntimeSuccessor(
                            root, expectedCurrent, normalizedCurrent, view);
            require(nodeC.acceptedFileCount()
                            == semantic.path("successor_file_count").asInt()
                            && nodeC.acceptedManifestSha256().equals(
                            semantic.path("successor_manifest_sha256")
                                    .asString()),
                    "tag preflight Node C runtime bridge drifted");
            TreeMap<String, String> composedAdditions = new TreeMap<>();
            TreeMap<String, String> composedChanges = new TreeMap<>();
            normalizedCurrent.forEach((relative, digest) -> {
                String acceptedDigest = normalizedAccepted.get(relative);
                if (acceptedDigest == null) {
                    composedAdditions.put(relative, digest);
                } else if (!acceptedDigest.equals(digest)) {
                    composedChanges.put(relative, digest);
                }
            });
            Set<String> composedDeletions = new LinkedHashSet<>(
                    normalizedAccepted.keySet());
            composedDeletions.removeAll(normalizedCurrent.keySet());
            return new ProductionRuntimeSuccessor(
                    view,
                    semantic.path("accepted_file_count").asInt(),
                    semantic.path("accepted_manifest_sha256").asString(),
                    nodeC.currentFileCount(),
                    nodeC.currentManifestSha256(),
                    Map.copyOf(composedAdditions),
                    Map.copyOf(composedChanges),
                    Set.copyOf(composedDeletions));
        }
        return new ProductionRuntimeSuccessor(
                view,
                semantic.path("accepted_file_count").asInt(),
                semantic.path("accepted_manifest_sha256").asString(),
                semantic.path("successor_file_count").asInt(),
                semantic.path("successor_manifest_sha256").asString(),
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
        JsonNode semantic = load(root).path("historical_semantic_successors")
                .path("java_build_context_and_worm_chain");
        require(acceptedReportSha256.equals(
                        semantic.path("accepted_worm").path("sha256").asString())
                        && acceptedBuildContextSha256.equals(
                        semantic.path("accepted_build_context_sha256").asString())
                        && semantic.path("accepted_chain_node_count").asInt() == 5
                        && semantic.path("first_successor_chain_node_count").asInt()
                        == 6
                        && semantic.path("terminal_successor_chain_node_count").asInt()
                        == 7
                        && semantic.path("appended_node_count").asInt() == 2
                        && !semantic.path("historical_nodes_rewritten").asBoolean(),
                "tag preflight rejected build-context/WORM successor");
        String physicalBuildContext = javaBuildContextSha256(root);
        String nodeABuildContext = semantic.path(
                "terminal_successor_build_context_sha256").asString();
        if (!physicalBuildContext.equals(nodeABuildContext)) {
            var nodeC = Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                    .validateWormSuccessor(
                            root,
                            semantic.path("terminal_successor_worm")
                                    .path("sha256").asString(),
                            nodeABuildContext);
            require(nodeC.acceptedChainNodeCount() == 7
                            && nodeC.currentChainNodeCount() == 8
                            && nodeC.currentBuildContextSha256().equals(
                            physicalBuildContext),
                    "tag preflight Node C WORM bridge drifted");
            return new WormSuccessor(
                    acceptedReportSha256,
                    acceptedBuildContextSha256,
                    semantic.path("accepted_chain_node_count").asInt(),
                    semantic.path("first_successor_worm")
                            .path("sha256").asString(),
                    semantic.path("first_successor_build_context_sha256")
                            .asString(),
                    semantic.path("first_successor_chain_node_count").asInt(),
                    nodeC.currentReportSha256(),
                    physicalBuildContext,
                    nodeC.currentChainNodeCount());
        }
        return new WormSuccessor(
                acceptedReportSha256,
                acceptedBuildContextSha256,
                semantic.path("accepted_chain_node_count").asInt(),
                semantic.path("first_successor_worm").path("sha256").asString(),
                semantic.path("first_successor_build_context_sha256").asString(),
                semantic.path("first_successor_chain_node_count").asInt(),
                semantic.path("terminal_successor_worm").path("sha256").asString(),
                physicalBuildContext,
                semantic.path("terminal_successor_chain_node_count").asInt());
    }

    static Set<String> minimalFixturePaths() {
        Set<String> paths = new LinkedHashSet<>();
        paths.add(CONTRACT_RELATIVE);
        paths.add(TYPED_ANCHOR_CONTRACT);
        paths.add(PHASE6_ANCHOR_CONTRACT);
        paths.addAll(TRANSITIONS.keySet());
        paths.addAll(FIXED_SOURCE_PATHS);
        WORM_NODES.forEach(node -> paths.add(node.relative()));
        paths.addAll(Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .minimalFixturePaths());
        return Set.copyOf(paths);
    }

    static Set<String> semanticFixturePaths(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Set<String> paths = new LinkedHashSet<>(minimalFixturePaths());
        paths.add("infra/phase2/hash-java-build-context.sh");
        JsonNode historical = readJson(fixedRegularFile(
                root, HISTORICAL_TARGET_EXECUTION_CONTRACT));
        historical.path("production_surface").path("files").properties()
                .forEach(entry -> {
                    String relative = entry.getKey();
                    if (relative.equals("server/Dockerfile")
                            || relative.equals("server/.dockerignore")
                            || relative.equals("server/mvnw")
                            || relative.equals("server/pom.xml")
                            || relative.equals("server/build-versions.properties")
                            || relative.startsWith("server/.mvn/")
                            || relative.startsWith("server/src/main/")) {
                        paths.add(relative);
                    }
                });
        paths.addAll(PRODUCTION_MANIFEST_ADDITIONS.keySet());
        return Set.copyOf(paths);
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadContractEnvelope(root);
        validate(contract, root);
        return contract;
    }

    private static JsonNode loadContractEnvelope(Path root) throws IOException {
        Path contractPath = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(CONTRACT_BYTES > 0
                        && Files.size(contractPath) == CONTRACT_BYTES
                        && CONTRACT_SHA256.equals(sha256(contractPath)),
                "tag preflight contract physical bytes drifted");
        JsonNode contract = JSON.readTree(Files.readAllBytes(contractPath));
        require(contract.path("schema_version").asInt() == 1
                        && CONTRACT_ID.equals(
                        contract.path("contract_id").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "tag preflight contract envelope drifted");
        return contract;
    }

    static void validate(JsonNode contract, Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        require(propertyNames(contract).equals(Set.of(
                        "schema_version", "contract_id", "captured_at", "scope",
                        "status", "append_only_predecessors",
                        "source_successor_bridges", "historical_semantic_successors",
                        "semantic_authority",
                        "global_preflight_protocol", "evidence",
                        "apply_fail_closed", "authorization", "route_state",
                        "build_context_authority", "source_authority", "next_gate",
                        "document_payload_sha256")),
                "tag preflight contract shape drifted");
        require(contract.path("schema_version").asInt() == 1
                        && CONTRACT_ID.equals(
                        contract.path("contract_id").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "tag preflight contract identity drifted");

        Map<String, JsonNode> fixedSources = validateSourceAuthority(
                contract.path("source_authority"), root);
        validateTransitions(
                contract.path("source_successor_bridges"), root, fixedSources);
        validateHistoricalSemanticSuccessors(
                contract.path("historical_semantic_successors"), root, fixedSources);
        validateWormChain(contract.path("build_context_authority"), root);
        validateAuthorization(contract.path("authorization"));
        validateRoute(contract.path("route_state"));
    }

    private static void validateTransitions(
            JsonNode bridges,
            Path root,
            Map<String, JsonNode> fixedSources)
            throws IOException {
        require(propertyNames(bridges).equals(Set.of(
                        "path_count", "paths", "path_allowlist_exact",
                        "typed_phase2_paths", "phase6_typed_bridge_paths",
                        "phase6_document_paths", "phase6_bootstrap_paths",
                        "semantic_consumer_paths", "post_push_bridge_paths",
                        "typed_normalization_bridge_paths",
                        "overrides", "historical_typed_anchor_contract",
                        "historical_phase6_source_successor_anchor_contract",
                        "unknown_paths", "symlink_or_root_escape",
                        "dynamic_source_discovery", "live_git_head_authority",
                        "source_successor_external_git_anchor_complete"))
                        && bridges.path("path_count").asInt() == TRANSITIONS.size()
                        && strings(bridges.path("paths")).equals(
                        TRANSITIONS.keySet().stream().sorted().toList())
                        && bridges.path("path_allowlist_exact").asBoolean()
                        && Set.copyOf(strings(bridges.path("typed_phase2_paths")))
                        .equals(TYPED_PHASE2_PATHS)
                        && Set.copyOf(strings(
                        bridges.path("phase6_typed_bridge_paths")))
                        .equals(PHASE6_TYPED_BRIDGE_PATHS)
                        && Set.copyOf(strings(bridges.path("phase6_document_paths")))
                        .equals(PHASE6_DOCUMENT_PATHS)
                        && Set.copyOf(strings(bridges.path("phase6_bootstrap_paths")))
                        .equals(PHASE6_BOOTSTRAP_PATHS)
                        && Set.copyOf(strings(bridges.path("semantic_consumer_paths")))
                        .equals(SEMANTIC_CONSUMER_PATHS)
                        && Set.copyOf(strings(bridges.path("post_push_bridge_paths")))
                        .equals(POST_PUSH_BRIDGE_PATHS)
                        && Set.copyOf(strings(bridges.path(
                        "typed_normalization_bridge_paths")))
                        .equals(TYPED_NORMALIZATION_BRIDGE_PATHS)
                        && transitionGroupsAreExact()
                        && "reject".equals(
                        bridges.path("unknown_paths").asString())
                        && "reject".equals(
                        bridges.path("symlink_or_root_escape").asString())
                        && !bridges.path("dynamic_source_discovery").asBoolean()
                        && !bridges.path("live_git_head_authority").asBoolean()
                        && !bridges.path(
                        "source_successor_external_git_anchor_complete")
                        .asBoolean(),
                "tag preflight source-successor boundary drifted");
        JsonNode overrides = bridges.path("overrides");
        require(propertyNames(overrides).equals(TRANSITIONS.keySet()),
                "tag preflight source-successor set drifted");
        for (Map.Entry<String, Transition> entry : TRANSITIONS.entrySet()) {
            String relative = entry.getKey();
            Transition expected = entry.getValue();
            JsonNode actual = overrides.path(relative);
            AcceptedAuthorityFields explicit =
                    EXPLICIT_ACCEPTED_AUTHORITIES.get(relative);
            Set<String> expectedFields = new LinkedHashSet<>(Set.of(
                            "source", "accepted_sha256", "accepted_byte_count",
                            "successor_sha256", "successor_byte_count",
                            "accepted_authority", "successor_authority",
                            "transition_fixed_by_this_contract",
                            "successor_external_git_anchor_complete"));
            if (explicit != null) {
                expectedFields.add("accepted_sha256_authority");
                expectedFields.add("accepted_byte_count_authority");
            }
            require(propertyNames(actual).equals(expectedFields)
                            && relative.equals(actual.path("source").asString())
                            && expected.acceptedSha256().equals(
                            actual.path("accepted_sha256").asString())
                            && expected.acceptedBytes()
                            == actual.path("accepted_byte_count").asLong()
                            && expected.successorSha256().equals(
                            actual.path("successor_sha256").asString())
                            && expected.successorBytes()
                            == actual.path("successor_byte_count").asLong()
                            && expected.acceptedAuthority().equals(
                            actual.path("accepted_authority").asString())
                            && (explicit == null
                            || (explicit.acceptedSha256Authority().equals(
                            actual.path("accepted_sha256_authority").asString())
                            && explicit.acceptedByteCountAuthority().equals(
                            actual.path("accepted_byte_count_authority")
                                    .asString())))
                            && actual.path("successor_authority").equals(
                            fixedSources.get(relative))
                            && actual.path(
                            "transition_fixed_by_this_contract").asBoolean()
                            && !actual.path(
                            "successor_external_git_anchor_complete").asBoolean(),
                    "tag preflight source-successor descriptor drifted: "
                            + relative);
            Path path = fixedRegularFile(root, relative);
            long physicalBytes = Files.size(path);
            String physicalSha256 = sha256(path);
            if (physicalBytes != expected.successorBytes()
                    || !expected.successorSha256().equals(physicalSha256)) {
                validateNodeCSourceTransition(
                        root, relative,
                        expected.successorSha256(), expected.successorBytes(),
                        physicalSha256, physicalBytes);
            }
        }
    }

    private static boolean transitionGroupsAreExact() {
        Set<String> union = new LinkedHashSet<>();
        for (Set<String> group : List.of(
                TYPED_PHASE2_PATHS,
                PHASE6_TYPED_BRIDGE_PATHS,
                PHASE6_DOCUMENT_PATHS,
                PHASE6_BOOTSTRAP_PATHS,
                SEMANTIC_CONSUMER_PATHS,
                POST_PUSH_BRIDGE_PATHS,
                TYPED_NORMALIZATION_BRIDGE_PATHS)) {
            if (!java.util.Collections.disjoint(union, group)) {
                return false;
            }
            union.addAll(group);
        }
        Set<String> expectedExplicit = new LinkedHashSet<>(
                SEMANTIC_CONSUMER_PATHS);
        expectedExplicit.addAll(POST_PUSH_BRIDGE_PATHS);
        expectedExplicit.addAll(TYPED_NORMALIZATION_BRIDGE_PATHS);
        return union.equals(TRANSITIONS.keySet())
                && EXPLICIT_ACCEPTED_AUTHORITIES.keySet().equals(
                expectedExplicit);
    }

    private static void validateHistoricalSemanticSuccessors(
            JsonNode semantic,
            Path root,
            Map<String, JsonNode> fixedSources
    ) throws IOException {
        require(propertyNames(semantic).equals(Set.of(
                        "production_runtime_manifest",
                        "java_build_context_and_worm_chain",
                        "historical_contracts_unchanged",
                        "historical_contract_fields_rewritten",
                        "semantic_successor_external_git_anchor_complete"))
                        && semantic.path("historical_contracts_unchanged").asBoolean()
                        && !semantic.path(
                        "historical_contract_fields_rewritten").asBoolean()
                        && !semantic.path(
                        "semantic_successor_external_git_anchor_complete")
                        .asBoolean(),
                "tag preflight historical semantic boundary drifted");

        JsonNode production = semantic.path("production_runtime_manifest");
        require(propertyNames(production).equals(Set.of(
                        "accepted_authority", "accepted_file_count",
                        "accepted_manifest_sha256", "successor_file_count",
                        "successor_manifest_sha256", "unchanged_file_count",
                        "added_files", "changed_files", "deleted_files",
                        "exact_additions_only", "unknown_or_extra_files",
                        "symlink_or_root_escape", "learning_personalbank_main"))
                        && production.path("accepted_authority").equals(
                        fixedSources.get(HISTORICAL_TARGET_EXECUTION_CONTRACT))
                        && production.path("accepted_file_count").asInt()
                        == HISTORICAL_PRODUCTION_FILE_COUNT
                        && HISTORICAL_PRODUCTION_MANIFEST_SHA256.equals(
                        production.path("accepted_manifest_sha256").asString())
                        && production.path("successor_file_count").asInt()
                        == SUCCESSOR_PRODUCTION_FILE_COUNT
                        && SUCCESSOR_PRODUCTION_MANIFEST_SHA256.equals(
                        production.path("successor_manifest_sha256").asString())
                        && production.path("unchanged_file_count").asInt()
                        == HISTORICAL_PRODUCTION_FILE_COUNT
                        && textMap(production.path("added_files"))
                        .equals(PRODUCTION_MANIFEST_ADDITIONS)
                        && production.path("changed_files").size() == 0
                        && production.path("deleted_files").isArray()
                        && production.path("deleted_files").size() == 0
                        && production.path("exact_additions_only").asBoolean()
                        && "reject".equals(
                        production.path("unknown_or_extra_files").asString())
                        && "reject".equals(
                        production.path("symlink_or_root_escape").asString()),
                "tag preflight production semantic successor drifted");

        JsonNode historical = readJson(fixedRegularFile(
                root, HISTORICAL_TARGET_EXECUTION_CONTRACT));
        Map<String, String> accepted = textMap(
                historical.path("production_surface").path("files"));
        require(accepted.size() == HISTORICAL_PRODUCTION_FILE_COUNT
                        && HISTORICAL_PRODUCTION_MANIFEST_SHA256.equals(
                        canonicalSha256(JSON.valueToTree(accepted))),
                "tag preflight historical production authority drifted");
        TreeMap<String, String> current = new TreeMap<>(accepted);
        current.putAll(PRODUCTION_MANIFEST_ADDITIONS);
        require(current.size() == SUCCESSOR_PRODUCTION_FILE_COUNT
                        && SUCCESSOR_PRODUCTION_MANIFEST_SHA256.equals(
                        canonicalSha256(JSON.valueToTree(current))),
                "tag preflight current production authority drifted");

        JsonNode main = production.path("learning_personalbank_main");
        require(propertyNames(main).equals(Set.of(
                        "accepted_file_count", "accepted_manifest_sha256",
                        "successor_file_count", "successor_manifest_sha256",
                        "unchanged_file_count", "added_files", "changed_files",
                        "deleted_files", "exact_additions_only"))
                        && main.path("accepted_file_count").asInt() == 40
                        && "d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1"
                        .equals(main.path("accepted_manifest_sha256").asString())
                        && main.path("successor_file_count").asInt() == 43
                        && "2cc855057a4b3b6b5693ad717404ea6b9828de3aa73ef9be8a9a1a62b177f751"
                        .equals(main.path("successor_manifest_sha256").asString())
                        && main.path("unchanged_file_count").asInt() == 40
                        && textMap(main.path("added_files"))
                        .equals(PRODUCTION_MANIFEST_ADDITIONS)
                        && main.path("changed_files").size() == 0
                        && main.path("deleted_files").isArray()
                        && main.path("deleted_files").size() == 0
                        && main.path("exact_additions_only").asBoolean(),
                "tag preflight learning/personalbank main successor drifted");

        JsonNode worm = semantic.path("java_build_context_and_worm_chain");
        require(propertyNames(worm).equals(Set.of(
                        "accepted_worm", "accepted_chain_node_count",
                        "accepted_build_context_sha256", "first_successor_worm",
                        "first_successor_chain_node_count",
                        "first_successor_build_context_sha256",
                        "terminal_successor_worm",
                        "terminal_successor_chain_node_count",
                        "terminal_successor_build_context_sha256",
                        "appended_node_count", "historical_nodes_rewritten",
                        "current_tip_is_terminal_successor",
                        "unknown_build_context"))
                        && worm.path("accepted_worm").equals(fixedSources.get(
                        "docs/refactor/phase4c/"
                                + "personal-bank-user-counts-http-implementation-"
                                + "worm-evidence.json"))
                        && worm.path("accepted_chain_node_count").asInt() == 5
                        && HISTORICAL_BUILD_CONTEXT_SHA256.equals(
                        worm.path("accepted_build_context_sha256").asString())
                        && worm.path("first_successor_worm").equals(fixedSources.get(
                        "docs/refactor/phase4c/"
                                + "personal-bank-tag-global-preflight-"
                                + "worm-evidence.json"))
                        && worm.path("first_successor_chain_node_count").asInt() == 6
                        && WORM_NODES.get(5).buildContextSha256().equals(
                        worm.path("first_successor_build_context_sha256").asString())
                        && worm.path("terminal_successor_worm").equals(fixedSources.get(
                        "docs/refactor/phase4c/"
                                + "personal-bank-tag-global-preflight-hardening-"
                                + "worm-evidence.json"))
                        && worm.path("terminal_successor_chain_node_count").asInt()
                        == 7
                        && TERMINAL_BUILD_CONTEXT_SHA256.equals(
                        worm.path("terminal_successor_build_context_sha256")
                                .asString())
                        && worm.path("appended_node_count").asInt() == 2
                        && !worm.path("historical_nodes_rewritten").asBoolean()
                        && worm.path("current_tip_is_terminal_successor").asBoolean()
                        && "reject".equals(
                        worm.path("unknown_build_context").asString()),
                "tag preflight build-context/WORM semantic successor drifted");
    }

    private static void validateWormChain(JsonNode authority, Path root)
            throws IOException {
        require(WORM_NODES.size() == 7,
                "tag preflight fixed WORM chain length drifted");
        for (int index = 0; index < WORM_NODES.size(); index++) {
            WormNode node = WORM_NODES.get(index);
            String expectedPredecessor = index == 0
                    ? null : WORM_NODES.get(index - 1).sha256();
            require(java.util.Objects.equals(
                            expectedPredecessor, node.predecessorSha256()),
                    "tag preflight fixed WORM predecessor drifted");
            Path path = fixedRegularFile(root, node.relative());
            require(Files.size(path) == 1_442L
                            && node.sha256().equals(sha256(path)),
                    "tag preflight fixed WORM bytes drifted: " + node.relative());
            JsonNode report = JSON.readTree(Files.readAllBytes(path));
            require(node.buildContextSha256().equals(
                            report.path("java").path("buildContextSha256").asString())
                            && DOCKERFILE_SHA256.equals(
                            report.path("java").path("dockerfileSha256").asString())
                            && report.path("java").path("startupPassed").asBoolean()
                            && report.path("java").path("readinessPassed").asBoolean()
                            && "unknown".equals(report.path(
                            "productionDatabaseVersion").asString())
                            && !report.path("flywayBaselineCreated").asBoolean(),
                    "tag preflight fixed WORM report drifted: " + node.relative());
        }

        JsonNode initial = authority.path("initial_worm_successor");
        JsonNode current = authority.path("new_worm_successor");
        require(initial.path("fixed_chain_node_count").asInt() == 6
                        && WORM_NODES.get(5).sha256().equals(
                        initial.path("sha256").asString())
                        && WORM_NODES.get(5).buildContextSha256().equals(
                        initial.path("java_build_context_sha256").asString())
                        && WORM_NODES.get(5).predecessorSha256().equals(
                        initial.path("predecessor_sha256").asString())
                        && current.path("fixed_chain_node_count").asInt() == 7
                        && WORM_NODES.get(6).sha256().equals(
                        current.path("sha256").asString())
                        && WORM_NODES.get(6).buildContextSha256().equals(
                        current.path("java_build_context_sha256").asString())
                        && WORM_NODES.get(6).predecessorSha256().equals(
                        current.path("predecessor_sha256").asString())
                        && authority.path("new_worm_successor_appended").asBoolean()
                        && authority.path("new_build_context_worm_closed").asBoolean()
                        && !authority.path("new_worm_successor_required").asBoolean()
                        && !authority.path(
                        "historical_worm_chain_overwritten").asBoolean(),
                "tag preflight build-context authority drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        require(propertyNames(authorization).equals(Set.of(
                        "newly_closed_gates",
                        "migration_global_preflight_evidence_closed",
                        "migration_design_closed", "operator_migration_implementation",
                        "production_schema_or_index", "real_data_migration_execution",
                        "production_cutover", "route_or_openapi_delta",
                        "http_security_or_rate_limit_delta",
                        "client_gateway_or_proxy_change",
                        "source_successor_external_git_anchor_complete",
                        "semantic_successor_external_git_anchor_complete",
                        "bootstrap_control_sources_external_git_anchor_complete"))
                        && strings(authorization.path("newly_closed_gates"))
                        .equals(List.of(
                                "migration_global_preflight_evidence_closed"))
                        && authorization.path(
                        "migration_global_preflight_evidence_closed").asBoolean()
                        && !authorization.path("migration_design_closed").asBoolean()
                        && !authorization.path(
                        "operator_migration_implementation").asBoolean()
                        && !authorization.path(
                        "production_schema_or_index").asBoolean()
                        && !authorization.path(
                        "real_data_migration_execution").asBoolean()
                        && !authorization.path("production_cutover").asBoolean()
                        && !authorization.path("route_or_openapi_delta").asBoolean()
                        && !authorization.path(
                        "http_security_or_rate_limit_delta").asBoolean()
                        && !authorization.path(
                        "client_gateway_or_proxy_change").asBoolean()
                        && !authorization.path(
                        "source_successor_external_git_anchor_complete")
                        .asBoolean()
                        && !authorization.path(
                        "semantic_successor_external_git_anchor_complete")
                        .asBoolean()
                        && !authorization.path(
                        "bootstrap_control_sources_external_git_anchor_complete")
                        .asBoolean(),
                "tag preflight authorization boundary drifted");
    }

    private static void validateRoute(JsonNode route) {
        require(route.path("total_operation_count").asInt() == 611
                        && route.path("migrated_operation_count").asInt() == 13
                        && route.path("pending_operation_count").asInt() == 598
                        && route.path(
                        "production_cutover_operation_count").asInt() == 0,
                "tag preflight route authority drifted");
    }

    private static Map<String, JsonNode> validateSourceAuthority(
            JsonNode authority,
            Path root
    ) throws IOException {
        Set<String> controls = Set.copyOf(strings(
                authority.path("control_sources")));
        JsonNode fixedSources = authority.path("fixed_sources");
        require(authority.path("fixed_source_count").asInt()
                        == FIXED_SOURCE_PATHS.size()
                        && fixedSources.size() == FIXED_SOURCE_PATHS.size()
                        && authority.path("control_source_count").asInt()
                        == CONTROL_SOURCE_PATHS.size()
                        && controls.equals(CONTROL_SOURCE_PATHS)
                        && authority.path("source_successor_path_count").asInt()
                        == TRANSITIONS.size()
                        && Set.copyOf(strings(
                        authority.path("source_successor_paths")))
                        .equals(TRANSITIONS.keySet())
                        && controls.contains(
                        "server/src/test/java/io/saksk/ti/architecture/"
                                + "Phase4cTagMigrationGlobalPreflight"
                                + "SuccessorAcceptance.java")
                        && controls.contains(
                        "server/src/test/java/io/saksk/ti/architecture/"
                                + "Phase4cTagMigrationGlobalPreflight"
                                + "ContractParityTest.java")
                        && java.util.Collections.disjoint(
                        controls, TRANSITIONS.keySet())
                        && authority.path(
                        "control_sources_excluded_from_self_authority").asBoolean()
                        && !authority.path(
                        "control_sources_external_git_anchor_complete").asBoolean()
                        && !authority.path("dynamic_source_discovery").asBoolean()
                        && !authority.path(
                        "historical_contracts_or_evidence_overwritten").asBoolean(),
                "tag preflight source authority drifted");
        Map<String, JsonNode> byPath = new TreeMap<>();
        for (Map.Entry<String, JsonNode> entry : fixedSources.properties()) {
            JsonNode descriptor = entry.getValue();
            Set<String> descriptorFields = propertyNames(descriptor);
            require(descriptorFields.equals(Set.of(
                            "source", "sha256", "byte_count"))
                            || descriptorFields.equals(Set.of(
                            "source", "sha256", "byte_count",
                            "document_payload_sha256")),
                    "tag preflight fixed source descriptor drifted: "
                            + entry.getKey());
            String relative = descriptor.path("source").asString();
            require(FIXED_SOURCE_PATHS.contains(relative)
                            && byPath.put(relative, descriptor) == null,
                    "tag preflight fixed source allowlist drifted: " + relative);
            Path path = fixedRegularFile(root, relative);
            long physicalBytes = Files.size(path);
            String physicalSha256 = sha256(path);
            long acceptedBytes = descriptor.path("byte_count").asLong();
            String acceptedSha256 = descriptor.path("sha256").asString();
            if (physicalBytes != acceptedBytes
                    || !acceptedSha256.equals(physicalSha256)) {
                require(NODE_C_SOURCE_SUCCESSOR_PATHS.contains(relative),
                        "tag preflight fixed source physical bytes drifted: "
                                + relative);
                validateNodeCSourceTransition(
                        root, relative, acceptedSha256, acceptedBytes,
                        physicalSha256, physicalBytes);
            }
            if (descriptor.has("document_payload_sha256")) {
                JsonNode document = JSON.readTree(Files.readAllBytes(path));
                String expectedPayload = descriptor.path(
                        "document_payload_sha256").asString();
                require(expectedPayload.equals(document.path(
                                "document_payload_sha256").asString())
                                && expectedPayload.equals(payloadSha256(document)),
                        "tag preflight fixed JSON payload drifted: " + relative);
            }
        }
        require(byPath.keySet().equals(FIXED_SOURCE_PATHS),
                "tag preflight fixed source path set drifted");
        return Map.copyOf(byPath);
    }

    private static void validateNodeCSourceTransition(
            Path root,
            String relative,
            String expectedAcceptedSha256,
            long expectedAcceptedBytes,
            String physicalSha256,
            long physicalBytes
    ) throws IOException {
        var transition = Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                .sourceTransition(root, relative);
        require(transition != null
                        && relative.equals(transition.source())
                        && expectedAcceptedSha256.equals(
                        transition.acceptedSha256())
                        && expectedAcceptedBytes == transition.acceptedByteCount()
                        && physicalSha256.equals(transition.successorSha256())
                        && physicalBytes == transition.successorByteCount(),
                "tag preflight Node C source bridge drifted: " + relative);
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path value = Path.of(relative);
        require(!value.isAbsolute() && !value.getName(0).toString().isBlank(),
                "tag preflight path escapes root: " + relative);
        for (Path part : value) {
            require(!part.toString().equals("..")
                            && !part.toString().equals("."),
                    "tag preflight path escapes root: " + relative);
        }
        Path cursor = root;
        for (Path part : value) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "tag preflight path contains symlink: " + relative);
        }
        Path resolved = root.resolve(value).normalize();
        require(resolved.startsWith(root)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "tag preflight path is not regular: " + relative);
        return resolved;
    }

    private static Set<String> propertyNames(JsonNode object) {
        Set<String> names = new LinkedHashSet<>();
        object.properties().forEach(entry -> names.add(entry.getKey()));
        return Set.copyOf(names);
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

    private static JsonNode readJson(Path path) throws IOException {
        return JSON.readTree(Files.readAllBytes(path));
    }

    private static String canonicalSha256(JsonNode value) {
        return sha256(JSON.writeValueAsBytes(canonicalNode(value)));
    }

    private static String javaBuildContextSha256(Path root) throws IOException {
        Path script = fixedRegularFile(
                root, "infra/phase2/hash-java-build-context.sh");
        Process process = new ProcessBuilder("/bin/sh", script.toString())
                .directory(root.toFile())
                .start();
        String stdout;
        String stderr;
        try {
            stdout = new String(
                    process.getInputStream().readAllBytes(), StandardCharsets.UTF_8)
                    .trim();
            stderr = new String(
                    process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8)
                    .trim();
            int exitCode = process.waitFor();
            require(exitCode == 0,
                    "tag preflight Java build-context hasher failed: " + stderr);
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IOException(
                    "tag preflight Java build-context hasher interrupted", error);
        }
        return stdout;
    }

    private static String payloadSha256(JsonNode value) {
        ObjectNode copy = (ObjectNode) value.deepCopy();
        copy.remove("document_payload_sha256");
        return sha256(JSON.writeValueAsBytes(canonicalNode(copy)));
    }

    private static JsonNode canonicalNode(JsonNode value) {
        if (value.isObject()) {
            ObjectNode object = JSON.createObjectNode();
            TreeMap<String, JsonNode> sorted = new TreeMap<>();
            value.properties().forEach(entry ->
                    sorted.put(entry.getKey(), canonicalNode(entry.getValue())));
            sorted.forEach(object::set);
            return object;
        }
        if (value.isArray()) {
            ArrayNode array = JSON.createArrayNode();
            value.forEach(item -> array.add(canonicalNode(item)));
            return array;
        }
        return value;
    }

    private static String sha256(Path path) throws IOException {
        return sha256(Files.readAllBytes(path));
    }

    private static String sha256(byte[] value) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(value));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static Map.Entry<String, Transition> transition(
            String relative,
            String acceptedSha256,
            long acceptedBytes,
            String successorSha256,
            long successorBytes,
            String acceptedAuthority) {
        return Map.entry(relative, new Transition(
                acceptedSha256, acceptedBytes, successorSha256,
                successorBytes, acceptedAuthority));
    }

    private static Map.Entry<String, AcceptedAuthorityFields> authority(
            String relative,
            String acceptedSha256Authority,
            String acceptedByteCountAuthority) {
        return Map.entry(relative, new AcceptedAuthorityFields(
                acceptedSha256Authority, acceptedByteCountAuthority));
    }

    private static Map.Entry<String, AcceptedAuthorityFields>
            targetSourceAuthority(String relative, String sourceKey) {
        return authority(
                relative,
                HISTORICAL_TARGET_EXECUTION_CONTRACT
                        + "#/source_contracts/" + sourceKey + "/sha256",
                CODE_FIXED_ACCEPTED_BYTES);
    }

    private static Map.Entry<String, AcceptedAuthorityFields>
            postPushAnchorArtifactAuthority(String relative) {
        String pointer = relative.replace("/", "~1");
        String prefix = HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT
                + "#/git_checkpoint/artifacts/" + pointer + "/";
        return authority(
                relative, prefix + "sha256", prefix + "byte_count");
    }

    private static Map.Entry<String, AcceptedAuthorityFields>
            postPushContractArtifactAuthority(
            String relative,
            String artifactKey) {
        String prefix = HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT
                + "#/git_checkpoint/artifacts/" + artifactKey + "/";
        return authority(
                relative, prefix + "sha256", prefix + "byte_count");
    }

    private static Map.Entry<String, AcceptedAuthorityFields>
            historicalOverrideAuthority(String relative) {
        String pointer = relative.replace("/", "~1");
        String prefix = HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT
                + "#/historical_source_successors/overrides/"
                + pointer + "/";
        return authority(
                relative,
                prefix + "successor_sha256",
                prefix + "successor_byte_count");
    }

    private static Map.Entry<String, AcceptedAuthorityFields>
            typedHistoricalOverrideAuthority(String relative) {
        String pointer = relative.replace("/", "~1");
        String prefix = TYPED_ANCHOR_CONTRACT
                + "#/historical_source_successors/overrides/"
                + pointer + "/";
        return authority(
                relative,
                prefix + "successor_sha256",
                prefix + "successor_byte_count");
    }

    private static WormNode worm(
            String relative,
            String sha256,
            String buildContextSha256,
            String predecessorSha256) {
        return new WormNode(
                relative, sha256, buildContextSha256, predecessorSha256);
    }

    private record Transition(
            String acceptedSha256,
            long acceptedBytes,
            String successorSha256,
            long successorBytes,
            String acceptedAuthority) {
    }

    private record AcceptedAuthorityFields(
            String acceptedSha256Authority,
            String acceptedByteCountAuthority) {
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
            String firstSuccessorReportSha256,
            String firstSuccessorBuildContextSha256,
            int firstSuccessorChainNodeCount,
            String currentReportSha256,
            String currentBuildContextSha256,
            int currentChainNodeCount) {
    }

    private record WormNode(
            String relative,
            String sha256,
            String buildContextSha256,
            String predecessorSha256) {
    }
}
