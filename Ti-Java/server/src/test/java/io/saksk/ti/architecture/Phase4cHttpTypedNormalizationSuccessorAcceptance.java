package io.saksk.ti.architecture;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/** Gitless Java acceptance for the fixed Phase 4C typed-normalization node. */
final class Phase4cHttpTypedNormalizationSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-typed-normalization-contract.json";
    private static final String CONTRACT_SHA256 =
            "ff1a751e1576916618422e0775c916e1d3b20122ffc141a04512119a6b5e99cd";
    private static final long CONTRACT_BYTE_COUNT = 59_299;
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "eeb2b6dd9be091950867cfe8040c486b867179c49f0a0861c700864ec773eb99";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-typed-normalization-contract";
    private static final String CONTRACT_STATUS =
            "typed_normalization_executed_external_anchor_pending_routes_pending";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-user-counts-http-typed-normalization";
    private static final String CAPTURED_AT = "2026-07-18T15:28:17+08:00";
    private static final String NEXT_GATE =
            "pg16_pg18_termination_identity_sql_nine_table_fingerprints_then_real_"
                    + "tomcat_complete_response_headers_then_same_service_redis_refusal_"
                    + "interruption_and_recovery_before_route_migration";

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-"
                    + "anchor-contract.json";
    private static final String PREDECESSOR_SHA256 =
            "1aa86e7cd8fe4f6c6c808eee166ff0ed30f7e228e707941efde87323b9ae057a";
    private static final long PREDECESSOR_BYTE_COUNT = 32_763;
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "b38abd80403536c7e6db2ec9b8a8920dc06e9f740ed9c065941e483a0b5a30e2";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-user-counts-http-target-execution-"
                    + "post-push-anchor-contract";
    private static final String PREDECESSOR_STATUS =
            "target_execution_post_push_checkpoint_externally_anchored_"
                    + "typed_parity_pending_routes_pending";
    private static final String PREDECESSOR_SCOPE =
            "phase4c-personal-bank-user-counts-http-target-execution-"
                    + "post-push-external-anchor";
    private static final String PREDECESSOR_CAPTURED_AT = "2026-07-18T14:04:12+08:00";

    private static final String HISTORICAL_EVIDENCE_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-execution-evidence.json";
    private static final String HISTORICAL_MANIFEST_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-target-execution-junit-manifest.json";
    private static final String TYPED_MANIFEST_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-typed-normalization-junit-manifest.json";
    private static final String WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json";
    private static final String AWARE_CASE = "access-shared-aware-expiry-type-error";
    private static final String MALFORMED_CASE =
            "access-shared-malformed-expiry-value-error";

    private static final String GIT_COMMIT =
            "c38defa703b358a280122a09019031c040c58ea7";
    private static final String GIT_ROOT_TREE =
            "5ac75d896171039f34650c92829282d8a5e3c3f8";
    private static final String GIT_PARENT =
            "1dae013e11c76ad858d6695f166a32631eb1525e";
    private static final String GIT_TI_JAVA_TREE =
            "07086dc62157018ec1c989832e5e63bfefbae0f0";
    private static final String GIT_CAPTURED_AT = "2026-07-18T15:06:30+08:00";
    private static final String GIT_SUBJECT =
            "test(java): externally anchor user counts handoff";
    private static final String GIT_RAW_DELTA_SHA256 =
            "66bb02a32b94b858606b965b55c01cc1f09c7c6ded72ff7dcc639bb7c8284f72";

    private static final String LEDGER_PAYLOAD_SHA256 =
            "332953b40ac71157e20ff322a37e8abf8fc308b12d5997bd0343b5674f0c0654";
    private static final String ORDERED_CASE_IDS_SHA256 =
            "d8c9aa1c8fdcfd833f2d7bbba3e21adcc3e696954b8756ace69405428bbdfad8";
    private static final String TYPED_MANIFEST_PAYLOAD_SHA256 =
            "08bdcc19ee0f3607d4e367a135d9a6544a5a9b5e5e999a2738180bc3258c8236";
    private static final String TYPED_MANIFEST_PROOF_SHA256 =
            "8ea42f371664c6a664b0cd8b408c292a8a2a57524215a718a71c634a0bc93047";
    private static final String TYPED_RAW_REPORT_SHA256 =
            "e1d5caebd6dfc7c792c8e4b4af337081246f718da5d1c4c82e072f46d6a1603b";
    private static final String HISTORICAL_MANIFEST_PAYLOAD_SHA256 =
            "9f53234730888c5e3bcd682390093331daca61814c1111c195ea3def4fbe543c";
    private static final String WORM_SHA256 =
            "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39";
    private static final String WORM_PREDECESSOR_SHA256 =
            "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6";
    private static final String BUILD_CONTEXT_SHA256 =
            "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3";
    private static final String DOCKERFILE_SHA256 =
            "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499";
    private static final String CANONICAL_SCHEMA_SHA256 =
            "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b";

    private static final Set<String> CURRENT_NODE_SOURCES = Set.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalization"
                    + "ContractParityTest.java",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_contract.py",
            "tools/phase4c_http_typed_normalization_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_contract.py");

    private static final Set<String> CHECKPOINT_PATHS = Set.of(
            "Ti-Java/README.md",
            "Ti-Java/docs/refactor/05-progress.md",
            "Ti-Java/docs/refactor/phase4c/README.md",
            "Ti-Java/docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-"
                    + "anchor-contract.json",
            "Ti-Java/infra/phase2/README.md",
            "Ti-Java/infra/phase2/verify-static.sh",
            "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
            "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
            "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchor"
                    + "ContractParityTest.java",
            "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPush"
                    + "ContractParityTest.java",
            "Ti-Java/tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_anchor_contract.py",
            "Ti-Java/tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py",
            "Ti-Java/tools/phase2_wormhole_successor_acceptance.py",
            "Ti-Java/tools/phase4c_http_target_execution_post_push_anchor_"
                    + "successor_acceptance.py",
            "Ti-Java/tools/phase4c_http_target_execution_post_push_"
                    + "successor_acceptance.py",
            "Ti-Java/tools/test_phase2_wormhole_successor_acceptance.py",
            "Ti-Java/tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_anchor_contract.py",
            "Ti-Java/tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py");

    private static final Map<String, String> NODEA_OWNED_POST_PUSH_SOURCES = Map.of(
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_contract.py",
            "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py",
            "a215e6b65624630de990dcae7e8d718e8a38a1fadae3e00ee0f3ccb81788959f",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
            "46f68412ea0cf42687133ba87a2184b86fe1b0c29625b1ee3f6e8f7301399efa",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
            "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578",
            "tools/phase4c_http_target_execution_successor_acceptance.py",
            "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a",
            "tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
            "944c925704e1b237a7d8e16c76591a0e8b7965d388bedd9e2a52492e0511c90c");

    private static final Map<String, AnchoredSource> ANCHORED_SOURCES = Map.ofEntries(
            anchor(PREDECESSOR_RELATIVE,
                    "a010939ba208dd03387595ba191807eca5612ee8",
                    PREDECESSOR_SHA256, PREDECESSOR_BYTE_COUNT),
            anchor(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionPostPushAnchor"
                            + "SuccessorAcceptance.java",
                    "67ad65a5d482128549df3b5d012e5314cd5cb173",
                    "0042ca6deb05498b2d363c81843d7ec39e3f2cb6af2d43376b24b1d24b03940a",
                    54_058),
            anchor(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cPersonalBankUserCountsHttpTargetExecution"
                            + "PostPushAnchorContractParityTest.java",
                    "c275b712c210a21560bb2a91238ca4500eb4b907",
                    "4824d1aa3ecb5208277066731b16efe33eadf2748348071f04e43c6e5887b520",
                    18_477),
            anchor(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py",
                    "70951075267e29b9cb354f7f03888b23adc504c9",
                    "4f97c2fcdfd36ac943fce4a1e948d99bf52cb8418519602141d40614ce78af44",
                    37_163),
            anchor(
                    "tools/phase4c_http_target_execution_post_push_anchor_"
                            + "successor_acceptance.py",
                    "2a5ec91d4709d11709571805786a8c641dfeba04",
                    "fe074402bcb58cfd3a681769050dd80174c584a082b462047d9684950b60e363",
                    35_451),
            anchor(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py",
                    "368af3c122f52e35b66525f5e01362acbc956c20",
                    "f51784ae1831b54e630150af2af12d3692397f3191d74314f3f0816b847cdfae",
                    18_683));

    private static final Map<String, SourceContract> SOURCE_CONTRACTS = Map.ofEntries(
            source("docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
                    "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1",
                    1_200_690),
            source(HISTORICAL_EVIDENCE_RELATIVE,
                    "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002",
                    173_397),
            source(WORM_RELATIVE, WORM_SHA256, 1_442),
            source(HISTORICAL_MANIFEST_RELATIVE,
                    "64ff60cd56bf60f585af3d55b4ed4b4f7ee30b6a4c9e3e840688a1caaa45664b",
                    33_246),
            source("docs/refactor/phase4c/"
                            + "personal-bank-user-counts-typed-normalization-"
                            + "approved-difference.md",
                    "3c6ecb59cae4e8a2f31e7dd0ed74bcca56e0cf61830339254523f3f824e652be",
                    3_730),
            source(TYPED_MANIFEST_RELATIVE,
                    "b6c619ee1ed4be44fd68903c2449188fd6a65ee39b7c855b1796c901d3a0268c",
                    9_342),
            source("docs/refactor/phase4c/route-parity-delta.csv",
                    "40ead5f703f1a589989fd524107f1fc31994662fb7d3e3be54fe22705025b52b",
                    2_230),
            source("infra/phase2/verify-in-maven-container.sh",
                    "2a9fa5d2e7b17f2f8d691b3d8e9e7e615e6c960c12c351525baae4251a56090e",
                    3_131),
            source("openapi/phase4c-personal-bank-user-counts.openapi.json",
                    "076957f391fd9aed65861d0633ad4b21d88b391df5217b10e2105b88b56605c9",
                    87_401),
            source("server/.mvn/wrapper/maven-wrapper.properties",
                    "ec15e462d862b9ba5dc9d8cdf249576bfdad7c70ccd441d64117d9abcd808dab",
                    446),
            source("server/Dockerfile", DOCKERFILE_SHA256, 1_850),
            source("server/pom.xml",
                    "24b45d68c44c64a6b2fda2fbf6f342889640f7c3dbc088015703cd1a68ff916b",
                    9_582),
            source("server/src/test/java/io/saksk/ti/integration/"
                            + "LegacyPersonalBankUserCountsTypedNormalizationIT.java",
                    "f9bd7dbd51e65abe8f01e80d0d564b9dfdba6856f95c4b06ad21b3705a2f025f",
                    30_716),
            source("server/src/test/java/io/saksk/ti/support/Phase2ContainerImages.java",
                    "c3bcd6b78ed2606ddc1e7a685774b9d0c2969c93502b6983d5f8352e27c29f50",
                    1_220),
            source("server/src/test/java/io/saksk/ti/support/Phase2PostgresContainers.java",
                    "c5ecf36dc5e943f9baa34b61be65bf73cf4502b1e8bdccc0a012a8db55c29ffe",
                    1_698),
            source("server/src/test/java/io/saksk/ti/support/"
                            + "Phase4cUserCountsFaultInjectingDataSource.java",
                    "83f381e0766ebeb0c71aa3b8f3f024d9af1a0099776b2d8923082947d6116dae",
                    20_783),
            source("server/src/test/resources/db/phase3/030-auth-schema.sql",
                    "9f9546be5f32bd1babcb9a4711c2cc9b3641e4c22ff051738ba9d735a150c87e",
                    934),
            source("server/src/test/resources/db/phase4b/"
                            + "062-personal-bank-share-list-schema.sql",
                    "d0e51e7cd16d0275611a82c984a52538beb14b10b19c50925646dd48a4d1c29d",
                    1_654),
            source("server/src/test/resources/db/phase4b/"
                            + "065-personal-bank-usage-stats-schema.sql",
                    "90d94b6c90c09586908e3108626ddbace04a83b56ed2018a55709ccdc7a2f684",
                    1_291),
            source("server/src/test/resources/db/phase4b/"
                            + "067-personal-bank-user-counts-schema.sql",
                    "32367c8795654e0ae2f5e2f1d6d4e42fb70e354f745a7f06894e28ac4a45f934",
                    2_951),
            source("server/src/test/resources/db/phase4c/"
                            + "071-personal-bank-user-counts-golden-target-seed.sql",
                    "5fbdc1da8e15072995baffba15b3a430b1ddd93e4788237a44bc3a5965e7556e",
                    9_672),
            source("server/src/test/resources/db/phase4c/"
                            + "072-personal-bank-user-counts-typed-normalization-seed.sql",
                    "089b795d6e6a3efdb1af86641701bd1bf9d30e2c1a94c65a0a32865bdfca29c6",
                    363),
            source("tools/normalize_phase4c_personal_bank_user_counts_"
                            + "typed_normalization_junit.py",
                    "3ff33e3ef1ad3171ea2ca97f9b70fc49db1c3dd92d97a5d8c634497d78285acc",
                    22_318),
            source("tools/test_normalize_phase4c_personal_bank_user_counts_"
                            + "typed_normalization_junit.py",
                    "51b316b9370da51b3c4f93b601ffb600451494d2743c0f08fbe17335e8d8bdcd",
                    10_366));

    private static final Map<String, SuccessorSource> THIRD_HOP_SUCCESSORS = Map.ofEntries(
            Map.entry(
                    "README.md",
                    new SuccessorSource(
                            "9008df17aa8eba4945fde525a304c4d891da20004f18ab86ceda485fffab2b57",
                            "1700589a3031071c71dad21e019165c0cb635be3362f85f36a4f4ce7d42ca0ea",
                            37_941)),
            Map.entry(
                    "docs/refactor/05-progress.md",
                    new SuccessorSource(
                            "477d2dc0fce4946e511faa2c143fc76367ae6231a932ae204b6858ca5787e1bf",
                            "f37547e858db034361c23c7c886bf291f1783b343e98cd95a0efc328370b449a",
                            102_736)),
            Map.entry(
                    "docs/refactor/phase4c/README.md",
                    new SuccessorSource(
                            "50f1ee46eddac681b49281c3b348e4017fe6893ec38051a5485317cd766c2f61",
                            "fbdbf32d9a3c488c890ce5d71689e59eb9a7458989843a45433e247dca2f6d98",
                            18_266)),
            Map.entry(
                    "infra/phase2/README.md",
                    new SuccessorSource(
                            "7ae3e8a5bb36920039649ffa8a2aef2bd9bb59782fa03f50e4174cee9063b56f",
                            "30950043edcca47aa42543065ca0b6b08d5c4c4a4839f2034af2cdde47174622",
                            6_850)),
            Map.entry(
                    "infra/phase2/verify-static.sh",
                    new SuccessorSource(
                            "92a3a1ee30ddbb2b5c854dbff7fac23da37e5804e0628211e85725ba4523d835",
                            "78f6dd82e43d39f289b5962490aace65dba806581a16580903d32dbee4812752",
                            14_323)),
            Map.entry(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
                    new SuccessorSource(
                            "0042ca6deb05498b2d363c81843d7ec39e3f2cb6af2d43376b24b1d24b03940a",
                            "b95ee58fd66698d129ee9562959d21ffc3a3e0c0b49339f21c379a8d0c356090",
                            55_266)),
            Map.entry(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchor"
                            + "ContractParityTest.java",
                    new SuccessorSource(
                            "4824d1aa3ecb5208277066731b16efe33eadf2748348071f04e43c6e5887b520",
                            "bd2b0c554a19fb561919298bba1c23a9f35435390ff3a069e3ec8e7ec5959e12",
                            19_014)),
            Map.entry(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPush"
                            + "ContractParityTest.java",
                    new SuccessorSource(
                            "a8e81f0758928eb69c527a9d6bbcf00517160221ea7b1aca4b901b7d5a26cf48",
                            "efa8bd66c5df68bdd9617415b156450ba2ae12dafb2c284df75dcc44e8edcd02",
                            17_241)),
            Map.entry(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py",
                    new SuccessorSource(
                            "4f97c2fcdfd36ac943fce4a1e948d99bf52cb8418519602141d40614ce78af44",
                            "342990a999fa0873b6c33a9a2f735f88fb7a453ee27d94832b81b14b9c8fa2a1",
                            39_048)),
            Map.entry(
                    "tools/phase2_wormhole_successor_acceptance.py",
                    new SuccessorSource(
                            "868d5cebbcc695136083ac892e572483ffc40829f487cb8d9d2b407c2fc763d1",
                            "9e11c33623a10415b28a5aadf1cf0855ef4bdd1dc9a3d81eeeff41e76a98f735",
                            24_939)),
            Map.entry(
                    "tools/phase4c_http_target_execution_post_push_anchor_"
                            + "successor_acceptance.py",
                    new SuccessorSource(
                            "fe074402bcb58cfd3a681769050dd80174c584a082b462047d9684950b60e363",
                            "c1abc55435cd3c3e1c62a72412dc5b62b300fb9f76b8ebc2b6c5482fe726403d",
                            37_853)),
            Map.entry(
                    "tools/test_phase2_wormhole_successor_acceptance.py",
                    new SuccessorSource(
                            "691198f36292c460b6bb516e9deb4e4efe064ae12fe60efb85280a52753cb5cb",
                            "b273ae2f450238b709d409e07e6ab7c7f39fbe71d162563a18350f62adaca7ab",
                            40_416)),
            Map.entry(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py",
                    new SuccessorSource(
                            "f51784ae1831b54e630150af2af12d3692397f3191d74314f3f0816b847cdfae",
                            "b2f0feefd23f88c357c1bb6e72f417a4de212465e79577930a7c671c3138e47c",
                            19_187)),
            Map.entry(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py",
                    new SuccessorSource(
                            "d99d36f8b17e5072dcd130c4570ac074096a3c9ee2b9bf4f0f49fd2b1cd907e6",
                            "9bb6c53fd9c833ff2ed9d2bdcf09af80ae436a9bcfc4c2ee2d54c03f2274acca",
                            12_084)));

    private Phase4cHttpTypedNormalizationSuccessorAcceptance() {
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Path contractPath = validateContractPhysicalBytes(root);
        JsonNode contract = readJson(contractPath);
        validate(contract);
        validateLocalFiles(contract, root);
        return contract;
    }

    private static Path validateContractPhysicalBytes(Path root) throws IOException {
        Path contractPath = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(Files.size(contractPath) == CONTRACT_BYTE_COUNT
                        && CONTRACT_SHA256.equals(sha256(contractPath)),
                "typed-normalization contract physical bytes drifted");
        return contractPath;
    }

    static void validate(JsonNode contract) {
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status", "scope",
                        "predecessor", "predecessor_external_git_anchor",
                        "production_surface", "typed_normalization",
                        "malformed_typed_rejection", "disposition_ledger",
                        "junit_execution", "worm_evidence", "authorization",
                        "acceptance", "source_contracts", "current_node_trust_boundary",
                        "document_payload_sha256")),
                "unexpected typed-normalization top-level shape");
        require(contract.path("schema_version").asInt() == 1
                        && CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && CONTRACT_STATUS.equals(contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(contract.path("scope").asString())
                        && CAPTURED_AT.equals(contract.path("captured_at").asString()),
                "typed-normalization identity drifted");
        require(CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "typed-normalization canonical payload drifted");

        validatePredecessor(contract.path("predecessor"));
        validatePredecessorExternalAnchor(
                contract.path("predecessor_external_git_anchor"));
        validateProductionSurface(contract.path("production_surface"));
        validateTypedNormalization(contract.path("typed_normalization"));
        validateMalformedRejection(contract.path("malformed_typed_rejection"));
        validateLedger(contract.path("disposition_ledger"));
        validateJunit(contract.path("junit_execution"));
        validateWorm(contract.path("worm_evidence"));
        validateAuthorization(contract.path("authorization"));
        validateAcceptance(contract.path("acceptance"));
        validateSourceContracts(contract.path("source_contracts"));
        validateCurrentTrustBoundary(contract.path("current_node_trust_boundary"));
    }

    static String acceptedHash(String relative) {
        SuccessorSource source = THIRD_HOP_SUCCESSORS.get(relative);
        if (source != null) {
            return source.acceptedSha256();
        }
        String declared = NODEA_OWNED_POST_PUSH_SOURCES.get(relative);
        if (declared == null) {
            return null;
        }
        require(declared.equals(
                        Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                                .acceptedSha256(relative)),
                "tag-preflight successor does not accept typed-owned source: "
                        + relative);
        return declared;
    }

    static Set<String> successorPaths() {
        return THIRD_HOP_SUCCESSORS.keySet();
    }

    static String successorHash(Path tiJavaRoot, String relative) throws IOException {
        SuccessorSource source = THIRD_HOP_SUCCESSORS.get(relative);
        String fixedNodeaAccepted = NODEA_OWNED_POST_PUSH_SOURCES.get(relative);
        if (source == null && fixedNodeaAccepted == null) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        // Phase 2 performs one full terminal load.  A transition lookup must
        // re-hash its exact contract and target bytes, but must not recursively
        // re-parse every fixed source for each historical successor path.
        validateContractPhysicalBytes(root);
        Path path = fixedRegularFile(root, relative);
        String physical = sha256(path);
        if (source == null) {
            return currentOrTypedNormalizationAnchorSuccessorHash(
                    root, relative, fixedNodeaAccepted, physical);
        }
        String transitioned = currentOrTypedNormalizationAnchorSuccessorHash(
                root, relative, source.successorSha256(), physical);
        require(!source.successorSha256().equals(physical)
                        || Files.size(path) == source.successorByteCount(),
                "typed-normalization third-hop successor drifted: " + relative);
        return transitioned;
    }

    private static String currentOrTypedNormalizationAnchorSuccessorHash(
            Path root,
            String relative,
            String declared,
            String physical
    ) throws IOException {
        if (declared.equals(physical)) {
            return physical;
        }
        String anchorAccepted =
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .acceptedHash(relative);
        if (anchorAccepted != null) {
            require(declared.equals(anchorAccepted),
                    "typed-normalization anchor does not accept historical bytes: "
                            + relative);
            require(physical.equals(
                            Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                                    .successorHash(root, relative)),
                    "typed-normalization anchor does not bind current bytes: "
                            + relative);
            return physical;
        }
        require(declared.equals(NODEA_OWNED_POST_PUSH_SOURCES.get(relative)),
                "typed-normalization anchor does not accept historical bytes: "
                        + relative);
        require(declared.equals(
                        Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                                .acceptedSha256(relative)),
                "tag-preflight successor does not accept historical bytes: "
                        + relative);
        require(physical.equals(
                        Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                                .successorSha256(root, relative)),
                "tag-preflight successor does not bind current bytes: " + relative);
        return physical;
    }

    static Set<String> minimalFixturePaths() {
        Set<String> paths = new LinkedHashSet<>();
        paths.add(CONTRACT_RELATIVE);
        paths.add(PREDECESSOR_RELATIVE);
        paths.addAll(SOURCE_CONTRACTS.keySet());
        paths.add(
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .contractRelative());
        paths.add(
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .contractRelative());
        paths.add(
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .contractRelative());
        return Set.copyOf(paths);
    }

    private static void validatePredecessor(JsonNode predecessor) {
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "byte_count", "document_payload_sha256",
                        "contract_id", "status", "scope", "captured_at", "immutable")),
                "unexpected typed-normalization predecessor shape");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString())
                        && PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString())
                        && predecessor.path("byte_count").asLong()
                        == PREDECESSOR_BYTE_COUNT
                        && PREDECESSOR_PAYLOAD_SHA256.equals(predecessor
                        .path("document_payload_sha256").asString())
                        && PREDECESSOR_ID.equals(
                        predecessor.path("contract_id").asString())
                        && PREDECESSOR_STATUS.equals(predecessor.path("status").asString())
                        && PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString())
                        && PREDECESSOR_CAPTURED_AT.equals(
                        predecessor.path("captured_at").asString())
                        && predecessor.path("immutable").asBoolean(),
                "typed-normalization predecessor reference drifted");
    }

    private static void validatePredecessorExternalAnchor(JsonNode anchor) {
        require(propertyNames(anchor).equals(Set.of(
                        "object_format", "commit_oid", "root_tree_oid", "parent_oid",
                        "ti_java_tree_oid", "authored_at", "committed_at", "subject",
                        "raw_delta_sha256", "exact_changed_paths", "changed_path_count",
                        "added_path_count", "modified_path_count", "deleted_path_count",
                        "non_ti_java_path_count", "inserted_line_count",
                        "deleted_line_count", "anchored_sources", "anchored_source_count",
                        "anchored_source_total_bytes",
                        "predecessor_current_anchor_sources_external_git_anchor_complete",
                        "mutable_ref_is_validation_authority",
                        "ordinary_contract_load_requires_git",
                        "explicit_git_replay_supported")),
                "unexpected typed-normalization predecessor Git-anchor shape");
        require("sha1".equals(anchor.path("object_format").asString())
                        && GIT_COMMIT.equals(anchor.path("commit_oid").asString())
                        && GIT_ROOT_TREE.equals(anchor.path("root_tree_oid").asString())
                        && GIT_PARENT.equals(anchor.path("parent_oid").asString())
                        && GIT_TI_JAVA_TREE.equals(
                        anchor.path("ti_java_tree_oid").asString())
                        && GIT_CAPTURED_AT.equals(anchor.path("authored_at").asString())
                        && GIT_CAPTURED_AT.equals(anchor.path("committed_at").asString())
                        && GIT_SUBJECT.equals(anchor.path("subject").asString())
                        && GIT_RAW_DELTA_SHA256.equals(
                        anchor.path("raw_delta_sha256").asString())
                        && strings(anchor.path("exact_changed_paths")).equals(
                        CHECKPOINT_PATHS.stream().sorted().toList())
                        && anchor.path("changed_path_count").asInt() == 18
                        && anchor.path("added_path_count").asInt() == 6
                        && anchor.path("modified_path_count").asInt() == 12
                        && anchor.path("deleted_path_count").asInt() == 0
                        && anchor.path("non_ti_java_path_count").asInt() == 0
                        && anchor.path("inserted_line_count").asInt() == 4_544
                        && anchor.path("deleted_line_count").asInt() == 40
                        && anchor.path("anchored_source_count").asInt() == 6
                        && anchor.path("anchored_source_total_bytes").asLong() == 196_595
                        && anchor.path("predecessor_current_anchor_sources_"
                        + "external_git_anchor_complete").asBoolean()
                        && !anchor.path("mutable_ref_is_validation_authority").asBoolean()
                        && !anchor.path("ordinary_contract_load_requires_git").asBoolean()
                        && anchor.path("explicit_git_replay_supported").asBoolean(),
                "typed-normalization predecessor Git anchor drifted");

        JsonNode sources = anchor.path("anchored_sources");
        require(propertyNames(sources).equals(ANCHORED_SOURCES.keySet()),
                "unexpected externally anchored predecessor source set");
        ANCHORED_SOURCES.forEach((relative, expected) -> {
            JsonNode actual = sources.path(relative);
            require(propertyNames(actual).equals(Set.of(
                            "ti_java_relative_path", "repository_path", "git_blob_oid",
                            "sha256", "byte_count", "mode")),
                    "unexpected anchored-source descriptor shape: " + relative);
            require(relative.equals(actual.path("ti_java_relative_path").asString())
                            && ("Ti-Java/" + relative).equals(
                            actual.path("repository_path").asString())
                            && expected.gitBlobOid().equals(
                            actual.path("git_blob_oid").asString())
                            && expected.sha256().equals(actual.path("sha256").asString())
                            && expected.byteCount() == actual.path("byte_count").asLong()
                            && "100644".equals(actual.path("mode").asString()),
                    "externally anchored predecessor source drifted: " + relative);
        });
    }

    private static void validateProductionSurface(JsonNode production) {
        require(propertyNames(production).equals(Set.of(
                        "production_source_changed", "production_schema_or_index_changed",
                        "operator_changed", "client_changed", "gateway_or_proxy_changed",
                        "production_build_context_changed", "openapi_sha256",
                        "route_delta_sha256")),
                "unexpected typed-normalization production-surface shape");
        for (String flag : List.of(
                "production_source_changed", "production_schema_or_index_changed",
                "operator_changed", "client_changed", "gateway_or_proxy_changed",
                "production_build_context_changed")) {
            require(!production.path(flag).asBoolean(),
                    "typed-normalization overclaims a production change: " + flag);
        }
        require("076957f391fd9aed65861d0633ad4b21d88b391df5217b10e2105b88b56605c9"
                        .equals(production.path("openapi_sha256").asString())
                        && "40ead5f703f1a589989fd524107f1fc31994662fb7d3e3be54fe22705025b52b"
                        .equals(production.path("route_delta_sha256").asString()),
                "typed-normalization production descriptors drifted");
    }

    private static void validateTypedNormalization(JsonNode typed) {
        require(propertyNames(typed).equals(Set.of(
                        "case_id", "input", "input_kind", "postgresql_type",
                        "negative_offset_input", "cast_compatibility_versions",
                        "cast_session_time_zones", "cross_version_equal",
                        "session_timezone_independent", "full_filter_http_version",
                        "http_fixture_origin", "http_fixture_sql_literal_seeded",
                        "canonical_local_datetime", "offset_provenance_erased",
                        "historical_disposition", "effective_disposition",
                        "source_status", "target_status", "business_jdbc_reached",
                        "fixture_share_id", "fixture_share_record_id", "target_data",
                        "proof_scope", "request_interval_assertions",
                        "fixture_and_session_exchange_occur_before_request_trace",
                        "whole_test_lifecycle_zero_dml_claimed", "difference_id",
                        "difference_document", "behavior_difference_decision")),
                "unexpected typed-normalization decision shape");
        require(AWARE_CASE.equals(typed.path("case_id").asString())
                        && "2026-07-17T13:00:00+08:00".equals(
                        typed.path("input").asString())
                        && "2026-07-17T13:00:00-05:00".equals(
                        typed.path("negative_offset_input").asString())
                        && "string_bind_explicit_cast".equals(
                        typed.path("input_kind").asString())
                        && "timestamp without time zone".equals(
                        typed.path("postgresql_type").asString())
                        && "2026-07-17T13:00:00".equals(
                        typed.path("canonical_local_datetime").asString())
                        && typed.path("offset_provenance_erased").asBoolean()
                        && strings(typed.path("cast_compatibility_versions"))
                        .equals(List.of("16.14", "18.4"))
                        && strings(typed.path("cast_session_time_zones"))
                        .equals(List.of("UTC", "America/Los_Angeles"))
                        && typed.path("cross_version_equal").asBoolean()
                        && typed.path("session_timezone_independent").asBoolean()
                        && "18.4".equals(typed.path("full_filter_http_version").asString())
                        && "java_string_bind_explicit_cast_insert_before_request_trace"
                        .equals(typed.path("http_fixture_origin").asString())
                        && !typed.path("http_fixture_sql_literal_seeded").asBoolean()
                        && "EXECUTED_TYPED_COLLAPSE".equals(
                        typed.path("historical_disposition").asString())
                        && "EXECUTED_FULL_CONTEXT_HTTP".equals(
                        typed.path("effective_disposition").asString())
                        && typed.path("source_status").asInt() == 500
                        && typed.path("target_status").asInt() == 200
                        && typed.path("business_jdbc_reached").asBoolean()
                        && typed.path("fixture_share_id").asLong() == 99_661
                        && typed.path("fixture_share_record_id").asLong() == 99_681
                        && "Java String CAST compatibility on PostgreSQL 16.14 and 18.4 "
                        .concat("across UTC and America/Los_Angeles; full production filter ")
                        .concat("chain MockMvc HTTP on PostgreSQL 18.4 and Redis 7.4.7; not ")
                        .concat("random-port Tomcat network evidence")
                        .equals(typed.path("proof_scope").asString())
                        && typed.path("fixture_and_session_exchange_occur_before_"
                        + "request_trace").asBoolean()
                        && !typed.path("whole_test_lifecycle_zero_dml_claimed").asBoolean()
                        && "P4C-LEARNING-013".equals(
                        typed.path("difference_id").asString())
                        && "docs/refactor/phase4c/personal-bank-user-counts-"
                        .concat("typed-normalization-approved-difference.md")
                        .equals(typed.path("difference_document").asString())
                        && "documented_local_adr_pending_current_node_external_git_anchor"
                        .equals(typed.path("behavior_difference_decision").asString()),
                "typed-normalization decision drifted");

        JsonNode data = typed.path("target_data");
        require(propertyNames(data).equals(Set.of(
                        "total", "favorites", "mistakes", "types",
                        "shuffle_options_available"))
                        && data.path("total").asInt() == 9
                        && data.path("favorites").asInt() == 0
                        && data.path("mistakes").asInt() == 0
                        && strings(data.path("types")).equals(List.of(
                        "判断题", "简答题", "填空题", "多选题", "选择题", "选择题", "简答题"))
                        && !data.path("shuffle_options_available").asBoolean(),
                "typed-normalization target projection drifted");

        JsonNode trace = typed.path("request_interval_assertions");
        require(propertyNames(trace).equals(Set.of(
                        "authority_users_sql_count", "bank_access_sql_count",
                        "share_access_sql_count", "favorite_membership_sql_count",
                        "mistake_membership_sql_count", "question_summary_sql_count",
                        "tag_membership_sql_count", "write_dml_count",
                        "users_last_active_write_dml_count", "schema_mutation_count",
                        "nine_table_fingerprint_unchanged", "hmac_route_rate_key_count",
                        "each_route_rate_key_value"))
                        && trace.path("authority_users_sql_count").asInt() == 1
                        && trace.path("bank_access_sql_count").asInt() == 5
                        && trace.path("share_access_sql_count").asInt() == 5
                        && trace.path("favorite_membership_sql_count").asInt() == 1
                        && trace.path("mistake_membership_sql_count").asInt() == 1
                        && trace.path("question_summary_sql_count").asInt() == 2
                        && trace.path("tag_membership_sql_count").asInt() == 0
                        && trace.path("write_dml_count").asInt() == 0
                        && trace.path("users_last_active_write_dml_count").asInt() == 0
                        && trace.path("schema_mutation_count").asInt() == 0
                        && trace.path("nine_table_fingerprint_unchanged").asBoolean()
                        && trace.path("hmac_route_rate_key_count").asInt() == 3
                        && trace.path("each_route_rate_key_value").asInt() == 1,
                "typed-normalization request-interval proof drifted");
    }

    private static void validateMalformedRejection(JsonNode malformed) {
        require(propertyNames(malformed).equals(Set.of(
                        "case_id", "execution_disposition", "http_execution",
                        "target_status", "sqlstate", "persisted_bank_share_row_count",
                        "no_row_http_forbidden_from_claiming_malformed_semantics"))
                        && MALFORMED_CASE.equals(malformed.path("case_id").asString())
                        && "EXECUTED_TYPED_REJECTION".equals(
                        malformed.path("execution_disposition").asString())
                        && !malformed.path("http_execution").asBoolean()
                        && malformed.path("target_status").isNull()
                        && "22007".equals(malformed.path("sqlstate").asString())
                        && malformed.path("persisted_bank_share_row_count").asInt() == 0
                        && malformed.path("no_row_http_forbidden_from_claiming_"
                        + "malformed_semantics").asBoolean(),
                "typed-normalization malformed rejection drifted");
    }

    private static void validateLedger(JsonNode ledger) {
        require(propertyNames(ledger).equals(Set.of(
                        "ordered_by", "ordered_case_ids_sha256", "ledger_payload_sha256",
                        "case_id_set_equal_to_historical_predecessor",
                        "single_effective_override_case_id", "summary", "rows")),
                "unexpected typed-normalization ledger shape");
        JsonNode rows = ledger.path("rows");
        require("canonical_case_ordinal".equals(ledger.path("ordered_by").asString())
                        && ORDERED_CASE_IDS_SHA256.equals(
                        ledger.path("ordered_case_ids_sha256").asString())
                        && LEDGER_PAYLOAD_SHA256.equals(
                        ledger.path("ledger_payload_sha256").asString())
                        && ledger.path("case_id_set_equal_to_historical_"
                        + "predecessor").asBoolean()
                        && AWARE_CASE.equals(
                        ledger.path("single_effective_override_case_id").asString())
                        && rows.size() == 59
                        && LEDGER_PAYLOAD_SHA256.equals(canonicalSha256(rows)),
                "typed-normalization ledger identity drifted");

        ArrayNode orderedIds = JSON.createArrayNode();
        Set<String> caseIds = new HashSet<>();
        Set<Integer> executionOrdinals = new HashSet<>();
        Map<String, Integer> dispositions = new HashMap<>();
        Map<String, Integer> statuses = new HashMap<>();
        Map<String, Integer> aliases = new HashMap<>();
        int http = 0;
        int business = 0;
        int awareRows = 0;
        int malformedRows = 0;
        for (int index = 0; index < rows.size(); index++) {
            JsonNode row = rows.path(index);
            require(propertyNames(row).equals(Set.of(
                            "canonical_case_ordinal", "execution_ordinal", "case_id",
                            "route_id", "alias", "execution_disposition",
                            "http_execution", "target_status", "business_jdbc_reached",
                            "proof")),
                    "unexpected typed-normalization ledger-row shape: " + index);
            require(row.path("canonical_case_ordinal").asInt() == index + 1,
                    "typed-normalization canonical ordinal drifted: " + index);
            String caseId = row.path("case_id").asString();
            require(caseIds.add(caseId), "duplicate typed-normalization case: " + caseId);
            require(executionOrdinals.add(row.path("execution_ordinal").asInt()),
                    "duplicate typed-normalization execution ordinal: " + caseId);
            orderedIds.add(caseId);
            String disposition = row.path("execution_disposition").asString();
            dispositions.merge(disposition, 1, Integer::sum);
            if (row.path("http_execution").asBoolean()) {
                http++;
                statuses.merge(Integer.toString(row.path("target_status").asInt()),
                        1, Integer::sum);
                aliases.merge(row.path("alias").asString(), 1, Integer::sum);
                if (row.path("business_jdbc_reached").asBoolean()) {
                    business++;
                }
            } else {
                require(row.path("target_status").isNull(),
                        "non-HTTP disposition claims a target status: " + caseId);
            }
            JsonNode proof = row.path("proof");
            if (AWARE_CASE.equals(caseId)) {
                awareRows++;
                require(propertyNames(proof).equals(Set.of(
                                "manifest", "suite_leaf_ordinal", "xml_name",
                                "replaces_historical_leaf_ordinal"))
                                && TYPED_MANIFEST_RELATIVE.equals(
                                proof.path("manifest").asString())
                                && proof.path("suite_leaf_ordinal").asInt() == 1
                                && "executesAwareExpiryAsARealFullFilterChainHttpRead"
                                .equals(proof.path("xml_name").asString())
                                && proof.path("replaces_historical_leaf_ordinal").asInt()
                                == 60
                                && "EXECUTED_FULL_CONTEXT_HTTP".equals(disposition)
                                && row.path("http_execution").asBoolean()
                                && row.path("target_status").asInt() == 200
                                && row.path("business_jdbc_reached").asBoolean(),
                        "aware typed-normalization ledger row drifted");
            } else {
                require(propertyNames(proof).equals(Set.of(
                                "manifest", "suite_leaf_ordinal", "xml_name"))
                                && HISTORICAL_MANIFEST_RELATIVE.equals(
                                proof.path("manifest").asString()),
                        "historical ledger proof drifted: " + caseId);
            }
            if (MALFORMED_CASE.equals(caseId)) {
                malformedRows++;
                require("EXECUTED_TYPED_REJECTION".equals(disposition)
                                && !row.path("http_execution").asBoolean()
                                && !row.path("business_jdbc_reached").asBoolean(),
                        "malformed typed rejection ledger row drifted");
            }
        }
        require(executionOrdinals.equals(integerRange(1, 59))
                        && awareRows == 1 && malformedRows == 1
                        && ORDERED_CASE_IDS_SHA256.equals(canonicalSha256(orderedIds))
                        && http == 58 && business == 50
                        && dispositions.equals(Map.of(
                        "EXECUTED_FULL_CONTEXT_HTTP", 47,
                        "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT", 11,
                        "EXECUTED_TYPED_REJECTION", 1))
                        && statuses.equals(Map.of(
                        "200", 35, "302", 5, "401", 3, "403", 10, "500", 5))
                        && aliases.equals(Map.of("api", 44, "web", 14)),
                "typed-normalization ledger aggregate drifted");
        validateSummary(ledger.path("summary"));
    }

    private static void validateSummary(JsonNode summary) {
        require(propertyNames(summary).equals(Set.of(
                        "logical_disposition_count", "http_execution_count",
                        "business_jdbc_reached_http_count",
                        "pre_business_jdbc_termination_http_count",
                        "non_fault_http_execution_count",
                        "postgres_abort_http_execution_count", "typed_rejection_count",
                        "api_alias_http_execution_count", "web_alias_http_execution_count",
                        "http_status_counts", "execution_disposition_counts",
                        "bound_only_case_count", "mocked_application_result_case_count"))
                        && summary.path("logical_disposition_count").asInt() == 59
                        && summary.path("http_execution_count").asInt() == 58
                        && summary.path("business_jdbc_reached_http_count").asInt() == 50
                        && summary.path("pre_business_jdbc_termination_http_count")
                        .asInt() == 8
                        && summary.path("non_fault_http_execution_count").asInt() == 47
                        && summary.path("postgres_abort_http_execution_count")
                        .asInt() == 11
                        && summary.path("typed_rejection_count").asInt() == 1
                        && summary.path("api_alias_http_execution_count").asInt() == 44
                        && summary.path("web_alias_http_execution_count").asInt() == 14
                        && summary.path("bound_only_case_count").asInt() == 0
                        && summary.path("mocked_application_result_case_count")
                        .asInt() == 0,
                "typed-normalization ledger summary drifted");
        require(intProperties(summary.path("http_status_counts")).equals(Map.of(
                        "200", 35, "302", 5, "401", 3, "403", 10, "500", 5))
                        && intProperties(summary.path("execution_disposition_counts"))
                        .equals(Map.of(
                                "EXECUTED_FULL_CONTEXT_HTTP", 47,
                                "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT", 11,
                                "EXECUTED_TYPED_REJECTION", 1)),
                "typed-normalization ledger count map drifted");
    }

    private static void validateJunit(JsonNode junit) {
        require(propertyNames(junit).equals(Set.of(
                        "historical_manifest", "typed_normalization_manifest",
                        "historical_physical_leaf_count", "new_physical_leaf_count",
                        "aggregate_physical_leaf_count", "logical_disposition_leaf_count",
                        "supplementary_authentication_leaf_count",
                        "replacement_leaf_count",
                        "superseded_historical_representation_leaf_count",
                        "selected_effective_proof_leaf_count",
                        "superseded_leaf_double_counted",
                        "failed_error_skipped_or_flaky_leaf_count",
                        "new_raw_report_sha256", "new_raw_report_byte_count",
                        "new_manifest_document_payload_sha256",
                        "new_manifest_proof_payload_sha256"))
                        && HISTORICAL_MANIFEST_RELATIVE.equals(
                        junit.path("historical_manifest").asString())
                        && TYPED_MANIFEST_RELATIVE.equals(
                        junit.path("typed_normalization_manifest").asString())
                        && junit.path("historical_physical_leaf_count").asInt() == 60
                        && junit.path("new_physical_leaf_count").asInt() == 1
                        && junit.path("aggregate_physical_leaf_count").asInt() == 61
                        && junit.path("logical_disposition_leaf_count").asInt() == 59
                        && junit.path("supplementary_authentication_leaf_count")
                        .asInt() == 1
                        && junit.path("replacement_leaf_count").asInt() == 1
                        && junit.path("superseded_historical_representation_leaf_count")
                        .asInt() == 1
                        && junit.path("selected_effective_proof_leaf_count").asInt() == 60
                        && !junit.path("superseded_leaf_double_counted").asBoolean()
                        && junit.path("failed_error_skipped_or_flaky_leaf_count")
                        .asInt() == 0
                        && TYPED_RAW_REPORT_SHA256.equals(
                        junit.path("new_raw_report_sha256").asString())
                        && junit.path("new_raw_report_byte_count").asLong() == 51_169
                        && TYPED_MANIFEST_PAYLOAD_SHA256.equals(junit
                        .path("new_manifest_document_payload_sha256").asString())
                        && TYPED_MANIFEST_PROOF_SHA256.equals(junit
                        .path("new_manifest_proof_payload_sha256").asString()),
                "typed-normalization JUnit proof selection drifted");
    }

    private static void validateManifestRuntimeScope(JsonNode runtime) {
        require(propertyNames(runtime).equals(Set.of(
                        "typed_cast_compatibility", "full_filter_http")),
                "typed-normalization manifest runtime-scope shape drifted");
        JsonNode cast = runtime.path("typed_cast_compatibility");
        require(propertyNames(cast).equals(Set.of(
                        "postgresql_versions", "session_time_zones",
                        "positive_offset_input", "negative_offset_input",
                        "canonical_local_datetime", "cross_version_equal",
                        "session_timezone_independent"))
                        && strings(cast.path("postgresql_versions"))
                        .equals(List.of("16.14", "18.4"))
                        && strings(cast.path("session_time_zones"))
                        .equals(List.of("UTC", "America/Los_Angeles"))
                        && "2026-07-17T13:00:00+08:00".equals(
                        cast.path("positive_offset_input").asString())
                        && "2026-07-17T13:00:00-05:00".equals(
                        cast.path("negative_offset_input").asString())
                        && "2026-07-17T13:00:00".equals(
                        cast.path("canonical_local_datetime").asString())
                        && cast.path("cross_version_equal").asBoolean()
                        && cast.path("session_timezone_independent").asBoolean(),
                "typed-normalization manifest CAST scope drifted");

        JsonNode http = runtime.path("full_filter_http");
        require(propertyNames(http).equals(Set.of(
                        "postgresql_version", "redis_version", "fixture_origin",
                        "fixture_sql_literal_seeded", "fixture_dml_before_request_trace"))
                        && "18.4".equals(http.path("postgresql_version").asString())
                        && "7.4.7".equals(http.path("redis_version").asString())
                        && "java_string_bind_explicit_cast_insert_before_request_trace"
                        .equals(http.path("fixture_origin").asString())
                        && !http.path("fixture_sql_literal_seeded").asBoolean()
                        && http.path("fixture_dml_before_request_trace").asBoolean(),
                "typed-normalization manifest HTTP scope drifted");
    }

    private static void validateWorm(JsonNode worm) {
        require(propertyNames(worm).equals(Set.of(
                        "source", "sha256", "fixed_chain_node_count",
                        "predecessor_sha256", "reused", "new_worm_report_created",
                        "java_build_context_sha256", "dockerfile_sha256",
                        "canonical_schema_dump_sha256"))
                        && WORM_RELATIVE.equals(worm.path("source").asString())
                        && WORM_SHA256.equals(worm.path("sha256").asString())
                        && worm.path("fixed_chain_node_count").asInt() == 5
                        && WORM_PREDECESSOR_SHA256.equals(
                        worm.path("predecessor_sha256").asString())
                        && worm.path("reused").asBoolean()
                        && !worm.path("new_worm_report_created").asBoolean()
                        && BUILD_CONTEXT_SHA256.equals(
                        worm.path("java_build_context_sha256").asString())
                        && DOCKERFILE_SHA256.equals(
                        worm.path("dockerfile_sha256").asString())
                        && CANONICAL_SCHEMA_SHA256.equals(
                        worm.path("canonical_schema_dump_sha256").asString()),
                "typed-normalization WORM boundary drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        Set<String> trueFlags = Set.of(
                "behavior_difference_adr_documented",
                "typed_execution_normalization_complete");
        Set<String> falseFlags = Set.of(
                "current_node_sources_external_git_anchor_complete",
                "typed_parity_review_complete", "full_target_parity_closed",
                "route_migration_eligible", "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated",
                "pg16_pg18_termination_fingerprints_complete",
                "real_tomcat_complete_response_header_matrix_complete",
                "same_service_redis_outage_and_recovery_complete", "production_cutover");
        Set<String> expected = new LinkedHashSet<>(trueFlags);
        expected.addAll(falseFlags);
        require(propertyNames(authorization).equals(expected),
                "unexpected typed-normalization authorization shape");
        trueFlags.forEach(flag -> require(authorization.path(flag).asBoolean(),
                "typed-normalization authorization unexpectedly open: " + flag));
        falseFlags.forEach(flag -> require(!authorization.path(flag).asBoolean(),
                "typed-normalization authorization overclaims: " + flag));
    }

    private static void validateAcceptance(JsonNode acceptance) {
        Set<String> summaryKeys = Set.of(
                "logical_disposition_count", "http_execution_count",
                "business_jdbc_reached_http_count",
                "pre_business_jdbc_termination_http_count",
                "non_fault_http_execution_count",
                "postgres_abort_http_execution_count", "typed_rejection_count",
                "api_alias_http_execution_count", "web_alias_http_execution_count",
                "http_status_counts", "execution_disposition_counts",
                "bound_only_case_count", "mocked_application_result_case_count");
        Set<String> expectedKeys = new LinkedHashSet<>(summaryKeys);
        expectedKeys.addAll(Set.of(
                "junit_physical_leaf_count", "junit_selected_effective_leaf_count",
                "implemented_pending_get_count", "migrated_operation_count",
                "pending_operation_count", "production_cutover_operation_count",
                "route_migration_eligible", "typed_parity_review_complete",
                "full_target_parity_closed", "production_cutover", "next_gate"));
        require(propertyNames(acceptance).equals(expectedKeys),
                "unexpected typed-normalization acceptance shape");
        ObjectNode summary = JSON.createObjectNode();
        summaryKeys.forEach(key -> summary.set(key, acceptance.path(key)));
        validateSummary(summary);
        require(acceptance.path("junit_physical_leaf_count").asInt() == 61
                        && acceptance.path("junit_selected_effective_leaf_count")
                        .asInt() == 60
                        && acceptance.path("implemented_pending_get_count").asInt() == 2
                        && acceptance.path("migrated_operation_count").asInt() == 11
                        && acceptance.path("pending_operation_count").asInt() == 600
                        && acceptance.path("production_cutover_operation_count")
                        .asInt() == 0
                        && !acceptance.path("route_migration_eligible").asBoolean()
                        && !acceptance.path("typed_parity_review_complete").asBoolean()
                        && !acceptance.path("full_target_parity_closed").asBoolean()
                        && !acceptance.path("production_cutover").asBoolean()
                        && NEXT_GATE.equals(acceptance.path("next_gate").asString()),
                "typed-normalization acceptance boundary drifted");
    }

    private static void validateSourceContracts(JsonNode contracts) {
        require(propertyNames(contracts).equals(SOURCE_CONTRACTS.keySet()),
                "unexpected typed-normalization fixed source-contract allowlist");
        SOURCE_CONTRACTS.forEach((relative, expected) -> {
            JsonNode actual = contracts.path(relative);
            require(propertyNames(actual).equals(Set.of("path", "sha256", "byte_count"))
                            && relative.equals(actual.path("path").asString())
                            && expected.sha256().equals(actual.path("sha256").asString())
                            && expected.byteCount() == actual.path("byte_count").asLong(),
                    "typed-normalization source contract drifted: " + relative);
        });
    }

    private static void validateCurrentTrustBoundary(JsonNode trust) {
        require(propertyNames(trust).equals(Set.of(
                        "source_paths", "source_path_allowlist_exact", "source_count",
                        "sources_excluded_from_self_authority",
                        "source_bytes_external_git_anchor_complete",
                        "post_push_external_anchor_required",
                        "dynamic_source_discovery_forbidden",
                        "independently_signed_provenance"))
                        && strings(trust.path("source_paths")).equals(
                        CURRENT_NODE_SOURCES.stream().sorted().toList())
                        && trust.path("source_path_allowlist_exact").asBoolean()
                        && trust.path("source_count").asInt() == 6
                        && trust.path("sources_excluded_from_self_authority").asBoolean()
                        && !trust.path("source_bytes_external_git_anchor_complete")
                        .asBoolean()
                        && trust.path("post_push_external_anchor_required").asBoolean()
                        && trust.path("dynamic_source_discovery_forbidden").asBoolean()
                        && !trust.path("independently_signed_provenance").asBoolean(),
                "typed-normalization current-node trust boundary drifted");
    }

    private static void validateLocalFiles(JsonNode contract, Path root) throws IOException {
        Path predecessorPath = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        require(Files.size(predecessorPath) == PREDECESSOR_BYTE_COUNT
                        && PREDECESSOR_SHA256.equals(sha256(predecessorPath)),
                "typed-normalization predecessor physical bytes drifted");
        JsonNode predecessor = readJson(predecessorPath);
        require(PREDECESSOR_ID.equals(predecessor.path("contract_id").asString())
                        && PREDECESSOR_STATUS.equals(predecessor.path("status").asString())
                        && PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString())
                        && PREDECESSOR_CAPTURED_AT.equals(
                        predecessor.path("captured_at").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(predecessor
                        .path("document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(payloadSha256(predecessor))
                        && !predecessor.path("post_push_source_anchor")
                        .path("current_anchor_source_bytes_external_git_anchor_complete")
                        .asBoolean()
                        && !predecessor.path("authorization")
                        .path("route_migration_eligible").asBoolean(),
                "typed-normalization predecessor payload boundary drifted");

        for (Map.Entry<String, SourceContract> entry : SOURCE_CONTRACTS.entrySet()) {
            Path path = fixedRegularFile(root, entry.getKey());
            SourceContract expected = entry.getValue();
            require(Files.size(path) == expected.byteCount()
                            && expected.sha256().equals(sha256(path)),
                    "typed-normalization fixed source drifted: " + entry.getKey());
        }

        JsonNode typedManifest = readJson(fixedRegularFile(root, TYPED_MANIFEST_RELATIVE));
        require(TYPED_MANIFEST_PAYLOAD_SHA256.equals(typedManifest
                        .path("document_payload_sha256").asString())
                        && TYPED_MANIFEST_PAYLOAD_SHA256.equals(
                        payloadSha256(typedManifest))
                        && TYPED_MANIFEST_PROOF_SHA256.equals(typedManifest
                        .path("result").path("proof_payload_sha256").asString())
                        && TYPED_RAW_REPORT_SHA256.equals(typedManifest
                        .path("raw_report").path("sha256").asString())
                        && typedManifest.path("raw_report").path("byte_count").asLong()
                        == 51_169,
                "typed-normalization JUnit manifest payload drifted");
        validateManifestRuntimeScope(typedManifest.path("result").path("runtime_scope"));

        JsonNode historicalManifest = readJson(
                fixedRegularFile(root, HISTORICAL_MANIFEST_RELATIVE));
        require(HISTORICAL_MANIFEST_PAYLOAD_SHA256.equals(historicalManifest
                        .path("document_payload_sha256").asString())
                        && HISTORICAL_MANIFEST_PAYLOAD_SHA256.equals(
                        payloadSha256(historicalManifest))
                        && historicalManifest.path("result").path("leaves").size() == 60,
                "typed-normalization historical JUnit manifest drifted");

        JsonNode worm = readJson(fixedRegularFile(root, WORM_RELATIVE));
        require(BUILD_CONTEXT_SHA256.equals(worm.path("java")
                        .path("buildContextSha256").asString())
                        && DOCKERFILE_SHA256.equals(worm.path("java")
                        .path("dockerfileSha256").asString())
                        && CANONICAL_SCHEMA_SHA256.equals(worm.path("restore")
                        .path("canonicalSchemaDumpSha256").asString())
                        && !worm.path("flywayBaselineCreated").asBoolean(),
                "typed-normalization WORM physical evidence drifted");

        validateHistoricalProjection(contract.path("disposition_ledger").path("rows"),
                readJson(fixedRegularFile(root, HISTORICAL_EVIDENCE_RELATIVE)));
    }

    private static void validateHistoricalProjection(JsonNode rows, JsonNode evidence) {
        JsonNode cases = evidence.path("cases");
        require(cases.size() == 59, "historical disposition case count drifted");
        Map<String, JsonNode> historical = new LinkedHashMap<>();
        cases.forEach(value -> historical.put(value.path("case_id").asString(), value));
        require(historical.size() == 59, "historical disposition case ids drifted");

        int changed = 0;
        for (JsonNode row : rows) {
            String caseId = row.path("case_id").asString();
            JsonNode old = historical.get(caseId);
            require(old != null
                            && old.path("canonical_case_ordinal").asInt()
                            == row.path("canonical_case_ordinal").asInt()
                            && old.path("execution_ordinal").asInt()
                            == row.path("execution_ordinal").asInt()
                            && old.path("route_id").asString().equals(
                            row.path("route_id").asString())
                            && old.path("alias").asString().equals(
                            row.path("alias").asString()),
                    "historical identity projection drifted: " + caseId);

            boolean sameDisposition = old.path("execution_disposition").asString()
                    .equals(row.path("execution_disposition").asString());
            boolean sameHttp = old.path("http_execution").asBoolean()
                    == row.path("http_execution").asBoolean();
            boolean sameStatus = old.path("target_status").isNull()
                    ? row.path("target_status").isNull()
                    : old.path("target_status").asInt()
                    == row.path("target_status").asInt();
            boolean oldBusiness = old.path("sql_boundary")
                    .path("business_jdbc_reached").asBoolean();
            boolean sameBusiness = oldBusiness
                    == row.path("business_jdbc_reached").asBoolean();
            if (!(sameDisposition && sameHttp && sameStatus && sameBusiness)) {
                changed++;
                require(AWARE_CASE.equals(caseId)
                                && "EXECUTED_TYPED_COLLAPSE".equals(
                                old.path("execution_disposition").asString())
                                && !old.path("http_execution").asBoolean()
                                && old.path("target_status").isNull()
                                && "EXECUTED_FULL_CONTEXT_HTTP".equals(
                                row.path("execution_disposition").asString())
                                && row.path("http_execution").asBoolean()
                                && row.path("target_status").asInt() == 200
                                && row.path("business_jdbc_reached").asBoolean(),
                        "unexpected effective disposition override: " + caseId);
            }
        }
        require(changed == 1, "aware expiry was not the unique effective override");
    }

    private static JsonNode readJson(Path path) throws IOException {
        return JSON.readTree(Files.readString(path, StandardCharsets.UTF_8));
    }

    private static String payloadSha256(JsonNode document) {
        ObjectNode payload = (ObjectNode) document.deepCopy();
        payload.remove("document_payload_sha256");
        return canonicalSha256(payload);
    }

    private static String canonicalSha256(JsonNode value) {
        return sha256(JSON.writeValueAsBytes(canonicalNode(value)));
    }

    private static JsonNode canonicalNode(JsonNode node) {
        if (node.isObject()) {
            ObjectNode result = JSON.createObjectNode();
            TreeMap<String, JsonNode> sorted = new TreeMap<>();
            node.properties().forEach(entry -> sorted.put(entry.getKey(), entry.getValue()));
            sorted.forEach((key, value) -> result.set(key, canonicalNode(value)));
            return result;
        }
        if (node.isArray()) {
            ArrayNode result = JSON.createArrayNode();
            node.forEach(item -> result.add(canonicalNode(item)));
            return result;
        }
        return node.deepCopy();
    }

    private static Path fixedRegularFile(Path root, String relative) throws IOException {
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute() && !candidate.normalize().startsWith(".."),
                "fixed typed-normalization path escaped Ti-Java: " + relative);
        Path cursor = root;
        for (Path part : candidate) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "fixed typed-normalization path contains a symlink: " + relative);
        }
        Path resolved = root.resolve(candidate).toRealPath();
        require(resolved.startsWith(root)
                        && Files.isRegularFile(resolved, LinkOption.NOFOLLOW_LINKS),
                "fixed typed-normalization path is not a regular Ti-Java file: "
                        + relative);
        return resolved;
    }

    private static Set<String> propertyNames(JsonNode node) {
        Set<String> names = new LinkedHashSet<>();
        node.properties().forEach(entry -> names.add(entry.getKey()));
        return Set.copyOf(names);
    }

    private static List<String> strings(JsonNode values) {
        List<String> result = new ArrayList<>();
        values.forEach(value -> result.add(value.asString()));
        return List.copyOf(result);
    }

    private static Map<String, Integer> intProperties(JsonNode node) {
        Map<String, Integer> result = new HashMap<>();
        node.properties().forEach(entry -> result.put(
                entry.getKey(), entry.getValue().asInt()));
        return Map.copyOf(result);
    }

    private static Set<Integer> integerRange(int first, int last) {
        Set<Integer> result = new HashSet<>();
        for (int value = first; value <= last; value++) {
            result.add(value);
        }
        return Set.copyOf(result);
    }

    private static Map.Entry<String, SourceContract> source(
            String relative,
            String sha256,
            long byteCount
    ) {
        return Map.entry(relative, new SourceContract(sha256, byteCount));
    }

    private static Map.Entry<String, AnchoredSource> anchor(
            String relative,
            String gitBlobOid,
            String sha256,
            long byteCount
    ) {
        return Map.entry(relative, new AnchoredSource(gitBlobOid, sha256, byteCount));
    }

    private static String sha256(Path path) throws IOException {
        return sha256(Files.readAllBytes(path));
    }

    private static String sha256(byte[] value) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(value));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 unavailable", exception);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private record SourceContract(String sha256, long byteCount) {
    }

    private record AnchoredSource(String gitBlobOid, String sha256, long byteCount) {
    }

    private record SuccessorSource(
            String acceptedSha256,
            String successorSha256,
            long successorByteCount
    ) {
    }
}
