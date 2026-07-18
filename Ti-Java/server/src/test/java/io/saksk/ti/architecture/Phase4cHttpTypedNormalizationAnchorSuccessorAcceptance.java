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
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * Gitless Java acceptance for the fixed Phase 4C typed-normalization anchor.
 * Python owns explicit Git replay; this class independently fixes the contract,
 * its 26 descriptors, six predecessor sources, successor transitions, and
 * route/WORM boundaries.
 */
final class Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-typed-normalization-anchor-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-typed-normalization-anchor-contract";
    private static final String CONTRACT_STATUS =
            "typed_normalization_checkpoint_externally_anchored_routes_pending";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-user-counts-http-typed-normalization-external-anchor";
    private static final String CONTRACT_CAPTURED_AT =
            "2026-07-18T18:18:23+08:00";
    private static final String CONTRACT_SHA256 =
            "c713aa04a82f340ea04fdd5ae870bd5cfae82f099101431c664f047c2d5218ca";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "430ef24103006265001ecd1f2f6aa5e4b24a886e82fcc1391cc516eba5dbde7c";
    private static final long CONTRACT_BYTES = 43_737L;

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-typed-normalization-contract.json";
    private static final String PREDECESSOR_SHA256 =
            "ff1a751e1576916618422e0775c916e1d3b20122ffc141a04512119a6b5e99cd";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "eeb2b6dd9be091950867cfe8040c486b867179c49f0a0861c700864ec773eb99";
    private static final long PREDECESSOR_BYTES = 59_299L;

    private static final String GIT_COMMIT =
            "b0861d61438f649ed48d5d5e6806e02c804fa2e4";
    private static final String GIT_PARENT =
            "c38defa703b358a280122a09019031c040c58ea7";
    private static final String GIT_ROOT_TREE =
            "9d295380b565307dc5ebe0a5b9bf3d8589452dbf";
    private static final String GIT_TI_JAVA_TREE =
            "ff845fbf8b7e3b7a4823ebb00bf8dcb164fde019";
    private static final String GIT_RAW_DELTA_SHA256 =
            "175dd8deb2cddb69e4bb6d6d985d312e041055699177d1054a8bb5ebef4f27c0";

    private static final String TYPED_MANIFEST =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-typed-normalization-junit-manifest.json";
    private static final String TYPED_MANIFEST_SHA256 =
            "b6c619ee1ed4be44fd68903c2449188fd6a65ee39b7c855b1796c901d3a0268c";
    private static final String WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json";
    private static final String WORM_SHA256 =
            "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39";
    private static final String BUILD_CONTEXT_SHA256 =
            "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3";
    private static final String DOCKERFILE_SHA256 =
            "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499";

    private static final Map<String, Artifact> CHECKPOINT = Map.ofEntries(
            Map.entry("README.md", new Artifact(
                    "M", "100644", "100644",
                    "8f7c55c7d787fb6ba4067abd67e2bcd4906b24f5",
                    "73b4c3a334955ddf5684f8ad40cfeea563149394",
                    "1700589a3031071c71dad21e019165c0cb635be3362f85f36a4f4ce7d42ca0ea", 37_941L)),
            Map.entry("docs/refactor/05-progress.md", new Artifact(
                    "M", "100644", "100644",
                    "ede2a034c0121042c4053c1e585e9762ae1f8049",
                    "31c5619b46370ed0dc9a1b7e1f1514598e538d5b",
                    "f37547e858db034361c23c7c886bf291f1783b343e98cd95a0efc328370b449a", 102_736L)),
            Map.entry("docs/refactor/phase4c/README.md", new Artifact(
                    "M", "100644", "100644",
                    "2a29318d27773ff40c2b4d7d63fbc52c09fbadb0",
                    "68fca94d05fc425f4c302d50e50054b060608868",
                    "fbdbf32d9a3c488c890ce5d71689e59eb9a7458989843a45433e247dca2f6d98", 18_266L)),
            Map.entry("docs/refactor/phase4c/personal-bank-user-counts-http-typed-normalization-contract.json", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "4d1b29ad082f17b59cd8262463f291f1c8c6c068",
                    "ff1a751e1576916618422e0775c916e1d3b20122ffc141a04512119a6b5e99cd", 59_299L)),
            Map.entry("docs/refactor/phase4c/personal-bank-user-counts-typed-normalization-approved-difference.md", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "e74c2fe38d2bb39fa1d064ec26a48653e9b83f87",
                    "3c6ecb59cae4e8a2f31e7dd0ed74bcca56e0cf61830339254523f3f824e652be", 3_730L)),
            Map.entry("docs/refactor/phase4c/personal-bank-user-counts-typed-normalization-junit-manifest.json", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "42f686014b17b9a9535dbb24e2cbc9e60ced1a90",
                    "b6c619ee1ed4be44fd68903c2449188fd6a65ee39b7c855b1796c901d3a0268c", 9_342L)),
            Map.entry("infra/phase2/README.md", new Artifact(
                    "M", "100644", "100644",
                    "13dfe524febcdad3f0b7faedd8cd2c4b02d42e2a",
                    "183ce4e90368e19f215fd54656e5da1b8733e260",
                    "30950043edcca47aa42543065ca0b6b08d5c4c4a4839f2034af2cdde47174622", 6_850L)),
            Map.entry("infra/phase2/verify-static.sh", new Artifact(
                    "M", "100755", "100755",
                    "eaa2f8c192de711747d55bffec1e81e1b57fcf2c",
                    "e69b9fda9d7030d66f5a9506d0774cce4e72f296",
                    "78f6dd82e43d39f289b5962490aace65dba806581a16580903d32dbee4812752", 14_323L)),
            Map.entry("server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java", new Artifact(
                    "M", "100644", "100644",
                    "67ad65a5d482128549df3b5d012e5314cd5cb173",
                    "964709792ad98337990b41614098774d512506dd",
                    "b95ee58fd66698d129ee9562959d21ffc3a3e0c0b49339f21c379a8d0c356090", 55_266L)),
            Map.entry("server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "e2b7960b89b2dddf9b68a634613f24df272ad43e",
                    "43a903c797ebc2af5aa85d65ca70709544eb068841dddca1505b2c95b3529d16", 75_517L)),
            Map.entry("server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java", new Artifact(
                    "M", "100644", "100644",
                    "c275b712c210a21560bb2a91238ca4500eb4b907",
                    "1943c251a40877fd0d34aa7629220a67e860e8cc",
                    "bd2b0c554a19fb561919298bba1c23a9f35435390ff3a069e3ec8e7ec5959e12", 19_014L)),
            Map.entry("server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java", new Artifact(
                    "M", "100644", "100644",
                    "34312828552cd30ed62a4ec7b0e813aed2880d73",
                    "09a733afaf0675961f50f7d2e39125b985c1c579",
                    "efa8bd66c5df68bdd9617415b156450ba2ae12dafb2c284df75dcc44e8edcd02", 17_241L)),
            Map.entry("server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "e2a6bc27e46d5f1ab35d03591b8645ccbe021414",
                    "3da21589512652bf3a6f26f65e00d2a531d735218a5483613353e183f3eb1d25", 27_970L)),
            Map.entry("server/src/test/java/io/saksk/ti/integration/LegacyPersonalBankUserCountsTypedNormalizationIT.java", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "732c45c4d968dc761759d30449e4d79bce658517",
                    "f9bd7dbd51e65abe8f01e80d0d564b9dfdba6856f95c4b06ad21b3705a2f025f", 30_716L)),
            Map.entry("server/src/test/resources/db/phase4c/072-personal-bank-user-counts-typed-normalization-seed.sql", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "f11e49a60610901b81423ebae024d73764fe5998",
                    "089b795d6e6a3efdb1af86641701bd1bf9d30e2c1a94c65a0a32865bdfca29c6", 363L)),
            Map.entry("tools/build_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py", new Artifact(
                    "M", "100644", "100644",
                    "70951075267e29b9cb354f7f03888b23adc504c9",
                    "f224874e62297680741004c967f35d4f083adc96",
                    "342990a999fa0873b6c33a9a2f735f88fb7a453ee27d94832b81b14b9c8fa2a1", 39_048L)),
            Map.entry("tools/build_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "5bec56940e2dd15ac71a20852b25a8489bce8d03",
                    "46089a29a518c624dd87ceed6d464890acb9a530adfae3fc9eb46d26da81fd0a", 40_434L)),
            Map.entry("tools/normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "8201348aeecbb7061890070c62b49344e4c85654",
                    "3ff33e3ef1ad3171ea2ca97f9b70fc49db1c3dd92d97a5d8c634497d78285acc", 22_318L)),
            Map.entry("tools/phase2_wormhole_successor_acceptance.py", new Artifact(
                    "M", "100644", "100644",
                    "d6de042c4c1f38aceb701045fce46777f5c9a83f",
                    "a7ce09960adae56ff9aab156f3838532cd60d3c3",
                    "9e11c33623a10415b28a5aadf1cf0855ef4bdd1dc9a3d81eeeff41e76a98f735", 24_939L)),
            Map.entry("tools/phase4c_http_target_execution_post_push_anchor_successor_acceptance.py", new Artifact(
                    "M", "100644", "100644",
                    "2a5ec91d4709d11709571805786a8c641dfeba04",
                    "8cb03dba4c9feec82329bcbc8ad458faffc37d54",
                    "c1abc55435cd3c3e1c62a72412dc5b62b300fb9f76b8ebc2b6c5482fe726403d", 37_853L)),
            Map.entry("tools/phase4c_http_typed_normalization_successor_acceptance.py", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "45a60e1194ba0fe292eb488160c66843cc4eef11",
                    "86de6fe3449a379c3ce960edd7a843768ccc0521ab7d9502c492c6ad1cf6a9f3", 52_080L)),
            Map.entry("tools/test_normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "fa2b3b0b5816054594ca8d9cccc4fcb917e8c07b",
                    "51b316b9370da51b3c4f93b601ffb600451494d2743c0f08fbe17335e8d8bdcd", 10_366L)),
            Map.entry("tools/test_phase2_wormhole_successor_acceptance.py", new Artifact(
                    "M", "100644", "100644",
                    "eff3ddd92670bb00f094dcc80c96f4d6ec458edd",
                    "5ea0fd0a7294ce01ad169284cfad04c329116cb8",
                    "b273ae2f450238b709d409e07e6ab7c7f39fbe71d162563a18350f62adaca7ab", 40_416L)),
            Map.entry("tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py", new Artifact(
                    "M", "100644", "100644",
                    "368af3c122f52e35b66525f5e01362acbc956c20",
                    "3a5a859015906168ea57f0efd90dc95bbc1cb4e3",
                    "b2f0feefd23f88c357c1bb6e72f417a4de212465e79577930a7c671c3138e47c", 19_187L)),
            Map.entry("tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py", new Artifact(
                    "M", "100644", "100644",
                    "72c87d9ab5c6555ee7ae52883def1916ece137ef",
                    "0d4a88685aff51d0f37d7705bbceaa797fdbcc44",
                    "9bb6c53fd9c833ff2ed9d2bdcf09af80ae436a9bcfc4c2ee2d54c03f2274acca", 12_084L)),
            Map.entry("tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py", new Artifact(
                    "A", "000000", "100644",
                    "0000000000000000000000000000000000000000",
                    "0f227599fd9c1674c018b474c84a752e1d2f3820",
                    "4203a585587b11bca41867c45d7a269f7ecb518f271fb6fd99919c9ba8a905bf", 25_364L))
    );

    private static final Map<String, Successor> SUCCESSORS = Map.ofEntries(
            Map.entry("README.md", new Successor(
                    "1700589a3031071c71dad21e019165c0cb635be3362f85f36a4f4ce7d42ca0ea", "524f03e89122b4d8a9af4ed805596a3b315a4859dac2777b0ab989ac25e82b47",
                    38_265L)),
            Map.entry("docs/refactor/05-progress.md", new Successor(
                    "f37547e858db034361c23c7c886bf291f1783b343e98cd95a0efc328370b449a", "62ff84e2cc3b525855f0a0eb07a1820c231ad50864956329d0da08a3d86b697c",
                    103_256L)),
            Map.entry("docs/refactor/phase4c/README.md", new Successor(
                    "fbdbf32d9a3c488c890ce5d71689e59eb9a7458989843a45433e247dca2f6d98", "dd0f41f78466636d09d3afa7669e507814aa78a04cb94d62bf7e96596c18e85a",
                    19_511L)),
            Map.entry("infra/phase2/README.md", new Successor(
                    "30950043edcca47aa42543065ca0b6b08d5c4c4a4839f2034af2cdde47174622", "414901d53174c7875ea000c323652a1ddf046a2e97018bbbd1dc4c9a4b3bf988",
                    6_959L)),
            Map.entry("infra/phase2/verify-static.sh", new Successor(
                    "78f6dd82e43d39f289b5962490aace65dba806581a16580903d32dbee4812752", "410108998f03e4d857d230c75687e854bd3bad99ba85d18c2fb090978ffa46d7",
                    14_719L)),
            Map.entry("server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java", new Successor(
                    "43a903c797ebc2af5aa85d65ca70709544eb068841dddca1505b2c95b3529d16", "f78882b20e38857c420b750677e4e8dd52922a1f0c04c249db9ed0d4f3db4fd5",
                    76_703L)),
            Map.entry("server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java", new Successor(
                    "3da21589512652bf3a6f26f65e00d2a531d735218a5483613353e183f3eb1d25", "beaed12d8ec96782ce55969a0e511458d78f4040b3eccf65971ce38e2caaed27",
                    28_553L)),
            Map.entry("tools/phase2_wormhole_successor_acceptance.py", new Successor(
                    "9e11c33623a10415b28a5aadf1cf0855ef4bdd1dc9a3d81eeeff41e76a98f735", "1164b6c584f4905a8011c5320eac62591e039ad0526b5a0657908f7b82688480",
                    25_791L)),
            Map.entry("tools/phase4c_http_typed_normalization_successor_acceptance.py", new Successor(
                    "86de6fe3449a379c3ce960edd7a843768ccc0521ab7d9502c492c6ad1cf6a9f3", "e71a5eec0e71ff824750f6eb20c4b310fdb0d8273fe89d83a23aee422ba282c5",
                    54_168L)),
            Map.entry("tools/test_phase2_wormhole_successor_acceptance.py", new Successor(
                    "b273ae2f450238b709d409e07e6ab7c7f39fbe71d162563a18350f62adaca7ab", "ff3250a88eb6e16102fc91930beec627f79ed57720140a32e7ad4410d7856e9f",
                    44_809L)),
            Map.entry("tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py", new Successor(
                    "b2f0feefd23f88c357c1bb6e72f417a4de212465e79577930a7c671c3138e47c", "3ded87895b33befb0f80905a1490d5f9207ae4e9ee26e939e5c00ebbd30a7874",
                    19_311L)),
            Map.entry("tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py", new Successor(
                    "9bb6c53fd9c833ff2ed9d2bdcf09af80ae436a9bcfc4c2ee2d54c03f2274acca", "87078f6d01957dcbbb37b488048a6702bc2212850ee9b2b75aa9b68aba352057",
                    12_208L)),
            Map.entry("tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py", new Successor(
                    "4203a585587b11bca41867c45d7a269f7ecb518f271fb6fd99919c9ba8a905bf", "72bd92b70d909c56598874328144835bc3e5a723c4f1e9f5bab041299d23be51",
                    25_018L))
    );

    private static final Set<String> TYPED_SOURCES = Set.of(
            PREDECESSOR_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_contract.py",
            "tools/phase4c_http_typed_normalization_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_contract.py");

    private static final Set<String> CURRENT_ANCHOR_SOURCES = Set.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchor"
                    + "ContractParityTest.java",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_anchor_contract.py",
            "tools/phase4c_http_typed_normalization_anchor_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_anchor_contract.py");

    private Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance() {
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static String acceptedHash(String relative) {
        Successor successor = SUCCESSORS.get(relative);
        return successor == null ? null : successor.acceptedSha256();
    }

    static Set<String> successorPaths() {
        return SUCCESSORS.keySet();
    }

    static String successorHash(Path tiJavaRoot, String relative) throws IOException {
        Successor successor = SUCCESSORS.get(relative);
        if (successor == null) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        validateContractPhysicalBytes(root);
        Path path = fixedRegularFile(root, relative);
        require(successor.successorSha256().equals(sha256(path))
                        && Files.size(path) == successor.successorBytes(),
                "typed-normalization anchor successor bytes drifted: " + relative);
        return successor.successorSha256();
    }

    static Set<String> minimalFixturePaths() {
        Set<String> paths = new LinkedHashSet<>();
        paths.add(CONTRACT_RELATIVE);
        paths.add(PREDECESSOR_RELATIVE);
        paths.add(TYPED_MANIFEST);
        paths.add(WORM_RELATIVE);
        paths.addAll(SUCCESSORS.keySet());
        return Set.copyOf(paths);
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = validateContractPhysicalBytes(root);
        validate(contract, root);
        return contract;
    }

    static void validate(JsonNode contract, Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status",
                        "scope", "predecessor", "git_checkpoint",
                        "typed_normalization_source_anchor",
                        "historical_source_successors", "junit_execution",
                        "worm_evidence", "authorization", "acceptance",
                        "document_payload_sha256")),
                "typed-normalization anchor contract shape drifted");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && contract.path("schema_version").asInt() == 1
                        && CONTRACT_CAPTURED_AT.equals(
                        contract.path("captured_at").asString())
                        && CONTRACT_STATUS.equals(contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(contract.path("scope").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "typed-normalization anchor identity drifted");

        validatePredecessor(contract.path("predecessor"), root);
        validateCheckpoint(contract.path("git_checkpoint"));
        validateSourceAnchor(contract.path("typed_normalization_source_anchor"));
        validateSuccessors(contract.path("historical_source_successors"), root);
        validateJunit(contract.path("junit_execution"), root);
        validateWorm(contract.path("worm_evidence"), root);
        validateAuthorization(contract.path("authorization"));
        validateAcceptance(contract.path("acceptance"));
    }

    private static JsonNode validateContractPhysicalBytes(Path root) throws IOException {
        Path path = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(Files.size(path) == CONTRACT_BYTES
                        && CONTRACT_SHA256.equals(sha256(path)),
                "typed-normalization anchor contract physical bytes drifted");
        return JSON.readTree(Files.readAllBytes(path));
    }

    private static void validatePredecessor(JsonNode predecessor, Path root)
            throws IOException {
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "byte_count",
                        "document_payload_sha256", "contract_id", "status",
                        "scope", "captured_at", "immutable")),
                "typed-normalization anchor predecessor shape drifted");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString())
                        && PREDECESSOR_SHA256.equals(
                        predecessor.path("sha256").asString())
                        && predecessor.path("byte_count").asLong() == PREDECESSOR_BYTES
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && predecessor.path("immutable").asBoolean(),
                "typed-normalization anchor predecessor descriptor drifted");
        Path path = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        JsonNode document = JSON.readTree(Files.readAllBytes(path));
        require(Files.size(path) == PREDECESSOR_BYTES
                        && PREDECESSOR_SHA256.equals(sha256(path))
                        && PREDECESSOR_PAYLOAD_SHA256.equals(payloadSha256(document)),
                "typed-normalization anchor predecessor bytes drifted");
    }

    private static void validateCheckpoint(JsonNode checkpoint) {
        require("sha1".equals(checkpoint.path("object_format").asString())
                        && GIT_COMMIT.equals(checkpoint.path("commit_oid").asString())
                        && GIT_PARENT.equals(checkpoint.path("parent_oid").asString())
                        && GIT_ROOT_TREE.equals(
                        checkpoint.path("root_tree_oid").asString())
                        && GIT_TI_JAVA_TREE.equals(
                        checkpoint.path("ti_java_tree_oid").asString())
                        && GIT_RAW_DELTA_SHA256.equals(
                        checkpoint.path("raw_delta_sha256").asString())
                        && !checkpoint.path(
                        "capture_ref_is_validation_authority").asBoolean(),
                "typed-normalization anchor checkpoint identity drifted");
        require(strings(checkpoint.path("exact_changed_paths")).equals(
                        CHECKPOINT.keySet().stream().sorted()
                                .map(path -> "Ti-Java/" + path).toList()),
                "typed-normalization anchor checkpoint paths drifted");
        JsonNode artifacts = checkpoint.path("artifacts");
        require(propertyNames(artifacts).equals(CHECKPOINT.keySet()),
                "typed-normalization anchor checkpoint artifact set drifted");
        CHECKPOINT.forEach((relative, expected) -> {
            JsonNode actual = artifacts.path(relative);
            require(propertyNames(actual).equals(Set.of(
                            "ti_java_relative_path", "repository_path",
                            "change_type", "previous_mode", "mode",
                            "previous_git_blob_oid", "object_type",
                            "git_blob_oid", "sha256", "byte_count"))
                            && relative.equals(
                            actual.path("ti_java_relative_path").asString())
                            && ("Ti-Java/" + relative).equals(
                            actual.path("repository_path").asString())
                            && expected.changeType().equals(
                            actual.path("change_type").asString())
                            && expected.previousMode().equals(
                            actual.path("previous_mode").asString())
                            && expected.mode().equals(actual.path("mode").asString())
                            && expected.previousOid().equals(
                            actual.path("previous_git_blob_oid").asString())
                            && "blob".equals(actual.path("object_type").asString())
                            && expected.oid().equals(
                            actual.path("git_blob_oid").asString())
                            && expected.sha256().equals(
                            actual.path("sha256").asString())
                            && expected.bytes() == actual.path("byte_count").asLong(),
                    "typed-normalization anchor artifact drifted: " + relative);
        });
        JsonNode diff = checkpoint.path("diff");
        require(diff.path("added_count").asInt() == 12
                        && diff.path("modified_count").asInt() == 14
                        && diff.path("deleted_count").asInt() == 0
                        && diff.path("non_ti_java_count").asInt() == 0
                        && diff.path("inserted_line_count").asInt() == 8_182
                        && diff.path("deleted_line_count").asInt() == 32
                        && diff.path("current_total_bytes").asLong() == 802_663L
                        && diff.path("exact_twenty_six_path_delta").asBoolean(),
                "typed-normalization anchor checkpoint aggregate drifted");
    }

    private static void validateSourceAnchor(JsonNode anchor) {
        require(GIT_COMMIT.equals(
                        anchor.path("accepted_checkpoint_commit_oid").asString())
                        && strings(anchor.path("source_paths")).equals(
                        TYPED_SOURCES.stream().sorted().toList())
                        && anchor.path("source_path_allowlist_exact").asBoolean()
                        && anchor.path("source_count").asInt() == 6
                        && anchor.path("source_total_bytes").asLong() == 280_664L
                        && anchor.path(
                        "predecessor_current_sources_external_git_anchor_complete")
                        .asBoolean()
                        && anchor.path(
                        "current_anchor_sources_excluded_from_self_authority")
                        .asBoolean()
                        && !anchor.path(
                        "current_anchor_source_bytes_external_git_anchor_complete")
                        .asBoolean()
                        && !anchor.path("independently_signed_provenance").asBoolean()
                        && strings(anchor.path("current_anchor_sources")).equals(
                        CURRENT_ANCHOR_SOURCES.stream().sorted().toList()),
                "typed-normalization anchor trust boundary drifted");
        JsonNode artifacts = anchor.path("artifacts");
        require(propertyNames(artifacts).equals(TYPED_SOURCES),
                "typed-normalization anchor six-source set drifted");
        for (String relative : TYPED_SOURCES) {
            Artifact expected = CHECKPOINT.get(relative);
            JsonNode actual = artifacts.path(relative);
            require(propertyNames(actual).equals(Set.of(
                            "ti_java_relative_path", "repository_path",
                            "change_type", "previous_mode", "mode",
                            "previous_git_blob_oid", "object_type",
                            "git_blob_oid", "sha256", "byte_count"))
                            && relative.equals(
                            actual.path("ti_java_relative_path").asString())
                            && expected.oid().equals(
                            actual.path("git_blob_oid").asString())
                            && expected.sha256().equals(
                            actual.path("sha256").asString())
                            && expected.bytes()
                            == actual.path("byte_count").asLong(),
                    "typed-normalization anchor six-source descriptor drifted: "
                            + relative);
        }
    }

    private static void validateSuccessors(JsonNode successors, Path root)
            throws IOException {
        require(successors.path("successor_allowlist_count").asInt()
                        == SUCCESSORS.size()
                        && strings(successors.path("successor_allowlist")).equals(
                        SUCCESSORS.keySet().stream().sorted().toList())
                        && successors.path("successor_allowlist_exact").asBoolean()
                        && successors.path("successor_transitions_settled").asBoolean()
                        && !successors.path(
                        "current_successor_bytes_external_git_anchor_complete")
                        .asBoolean(),
                "typed-normalization anchor successor boundary drifted");
        JsonNode overrides = successors.path("overrides");
        require(propertyNames(overrides).equals(SUCCESSORS.keySet()),
                "typed-normalization anchor successor set drifted");
        for (Map.Entry<String, Successor> entry : SUCCESSORS.entrySet()) {
            String relative = entry.getKey();
            Successor expected = entry.getValue();
            Artifact accepted = CHECKPOINT.get(relative);
            JsonNode actual = overrides.path(relative);
            require(expected.acceptedSha256().equals(
                            actual.path("accepted_sha256").asString())
                            && accepted.oid().equals(
                            actual.path("accepted_git_blob_oid").asString())
                            && expected.successorSha256().equals(
                            actual.path("successor_sha256").asString())
                            && expected.successorBytes()
                            == actual.path("successor_byte_count").asLong(),
                    "typed-normalization anchor successor descriptor drifted: "
                            + relative);
            Path path = fixedRegularFile(root, relative);
            require(expected.successorBytes() == Files.size(path)
                            && expected.successorSha256().equals(sha256(path)),
                    "typed-normalization anchor successor source drifted: "
                            + relative);
        }
    }

    private static void validateJunit(JsonNode junit, Path root) throws IOException {
        require(TYPED_MANIFEST.equals(junit.path("source").asString())
                        && TYPED_MANIFEST_SHA256.equals(
                        junit.path("sha256").asString())
                        && junit.path("aggregate_physical_leaf_count").asInt() == 61
                        && junit.path("selected_effective_leaf_count").asInt() == 60
                        && junit.path("logical_disposition_count").asInt() == 59
                        && junit.path("failures_errors_skipped_or_flaky").asInt() == 0
                        && !junit.path("raw_report_tracked").asBoolean()
                        && !junit.path("raw_report_embedded").asBoolean(),
                "typed-normalization anchor JUnit boundary drifted");
        Path path = fixedRegularFile(root, TYPED_MANIFEST);
        require(Files.size(path) == 9_342L
                        && TYPED_MANIFEST_SHA256.equals(sha256(path)),
                "typed-normalization anchor JUnit bytes drifted");
    }

    private static void validateWorm(JsonNode worm, Path root) throws IOException {
        require(WORM_RELATIVE.equals(worm.path("source").asString())
                        && WORM_SHA256.equals(worm.path("sha256").asString())
                        && worm.path("fixed_chain_node_count").asInt() == 5
                        && worm.path("reused").asBoolean()
                        && !worm.path("new_worm_report_created").asBoolean()
                        && BUILD_CONTEXT_SHA256.equals(
                        worm.path("java_build_context_sha256").asString())
                        && DOCKERFILE_SHA256.equals(
                        worm.path("dockerfile_sha256").asString()),
                "typed-normalization anchor WORM boundary drifted");
        Path path = fixedRegularFile(root, WORM_RELATIVE);
        require(Files.size(path) == 1_442L && WORM_SHA256.equals(sha256(path)),
                "typed-normalization anchor WORM bytes drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        require(authorization.path(
                        "typed_execution_normalization_complete").asBoolean()
                        && authorization.path(
                        "typed_normalization_checkpoint_and_six_excluded_sources_"
                                + "external_git_anchor_complete").asBoolean()
                        && authorization.path(
                        "historical_successor_transitions_settled").asBoolean()
                        && !authorization.path(
                        "current_anchor_source_bytes_external_git_anchor_complete")
                        .asBoolean(),
                "typed-normalization anchor authorization drifted");
        for (String field : Set.of(
                "typed_parity_review_complete",
                "pg16_pg18_termination_fingerprints_complete",
                "real_tomcat_complete_response_header_matrix_complete",
                "same_service_redis_outage_and_recovery_complete",
                "full_target_parity_closed", "route_migration_eligible",
                "two_legacy_get_routes_migrated", "production_cutover")) {
            require(!authorization.path(field).asBoolean(),
                    "typed-normalization anchor overclaims " + field);
        }
    }

    private static void validateAcceptance(JsonNode acceptance) {
        require(acceptance.path("checkpoint_changed_path_count").asInt() == 26
                        && acceptance.path("checkpoint_added_count").asInt() == 12
                        && acceptance.path("checkpoint_modified_count").asInt() == 14
                        && acceptance.path(
                        "checkpoint_current_total_bytes").asLong() == 802_663L
                        && acceptance.path("typed_source_anchor_count").asInt() == 6
                        && acceptance.path(
                        "typed_source_anchor_total_bytes").asLong() == 280_664L
                        && acceptance.path("junit_physical_leaf_count").asInt() == 61
                        && acceptance.path(
                        "junit_selected_effective_leaf_count").asInt() == 60
                        && acceptance.path("logical_disposition_count").asInt() == 59
                        && acceptance.path("http_execution_count").asInt() == 58
                        && acceptance.path("migrated_operation_count").asInt() == 11
                        && acceptance.path("pending_operation_count").asInt() == 600
                        && acceptance.path(
                        "production_cutover_operation_count").asInt() == 0
                        && !acceptance.path("typed_parity_review_complete").asBoolean()
                        && !acceptance.path("full_target_parity_closed").asBoolean()
                        && !acceptance.path("route_migration_eligible").asBoolean()
                        && !acceptance.path("production_cutover").asBoolean(),
                "typed-normalization anchor acceptance drifted");
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path canonicalRoot = root.toRealPath();
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute() && !relative.contains(".."),
                "typed-normalization anchor path escapes root: " + relative);
        Path cursor = canonicalRoot;
        for (Path part : candidate) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "typed-normalization anchor path contains symlink: " + relative);
        }
        Path resolved = canonicalRoot.resolve(candidate).toRealPath();
        require(resolved.startsWith(canonicalRoot)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "typed-normalization anchor path is not regular: " + relative);
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

    private record Artifact(
            String changeType,
            String previousMode,
            String mode,
            String previousOid,
            String oid,
            String sha256,
            long bytes
    ) {
    }

    private record Successor(
            String acceptedSha256,
            String successorSha256,
            long successorBytes
    ) {
    }
}
