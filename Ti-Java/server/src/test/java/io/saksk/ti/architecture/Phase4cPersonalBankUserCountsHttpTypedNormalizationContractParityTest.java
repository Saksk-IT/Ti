package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

/** Java parity gate for the fixed Phase 4C typed-normalization successor node. */
class Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest {

    private static final String CONTRACT_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-typed-normalization-contract.json";
    private static final String PREDECESSOR_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-"
                    + "anchor-contract.json";
    private static final String AWARE_CASE = "access-shared-aware-expiry-type-error";
    private static final String MALFORMED_CASE =
            "access-shared-malformed-expiry-value-error";
    private static final String NEW_JAVA_ACCEPTANCE_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java";
    private static final String NEW_JAVA_PARITY_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalization"
                    + "ContractParityTest.java";

    private static final Set<String> CURRENT_NODE_SOURCES = Set.of(
            CONTRACT_PATH,
            NEW_JAVA_ACCEPTANCE_PATH,
            NEW_JAVA_PARITY_PATH,
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_contract.py",
            "tools/phase4c_http_typed_normalization_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "typed_normalization_contract.py");

    private static final Set<String> FIXED_SOURCE_PATHS = Set.of(
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-execution-evidence.json",
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json",
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-target-execution-junit-manifest.json",
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-typed-normalization-approved-difference.md",
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-typed-normalization-junit-manifest.json",
            "docs/refactor/phase4c/route-parity-delta.csv",
            "infra/phase2/verify-in-maven-container.sh",
            "openapi/phase4c-personal-bank-user-counts.openapi.json",
            "server/.mvn/wrapper/maven-wrapper.properties",
            "server/Dockerfile",
            "server/pom.xml",
            "server/src/test/java/io/saksk/ti/integration/"
                    + "LegacyPersonalBankUserCountsTypedNormalizationIT.java",
            "server/src/test/java/io/saksk/ti/support/Phase2ContainerImages.java",
            "server/src/test/java/io/saksk/ti/support/Phase2PostgresContainers.java",
            "server/src/test/java/io/saksk/ti/support/"
                    + "Phase4cUserCountsFaultInjectingDataSource.java",
            "server/src/test/resources/db/phase3/030-auth-schema.sql",
            "server/src/test/resources/db/phase4b/"
                    + "062-personal-bank-share-list-schema.sql",
            "server/src/test/resources/db/phase4b/"
                    + "065-personal-bank-usage-stats-schema.sql",
            "server/src/test/resources/db/phase4b/"
                    + "067-personal-bank-user-counts-schema.sql",
            "server/src/test/resources/db/phase4c/"
                    + "071-personal-bank-user-counts-golden-target-seed.sql",
            "server/src/test/resources/db/phase4c/"
                    + "072-personal-bank-user-counts-typed-normalization-seed.sql",
            "tools/normalize_phase4c_personal_bank_user_counts_"
                    + "typed_normalization_junit.py",
            "tools/test_normalize_phase4c_personal_bank_user_counts_"
                    + "typed_normalization_junit.py");

    private static final Map<String, HashPair> THIRD_HOP_SUCCESSORS = Map.ofEntries(
            Map.entry(
                    "README.md",
                    new HashPair(
                            "9008df17aa8eba4945fde525a304c4d891da20004f18ab86ceda485fffab2b57",
                            "1700589a3031071c71dad21e019165c0cb635be3362f85f36a4f4ce7d42ca0ea")),
            Map.entry(
                    "docs/refactor/05-progress.md",
                    new HashPair(
                            "477d2dc0fce4946e511faa2c143fc76367ae6231a932ae204b6858ca5787e1bf",
                            "f37547e858db034361c23c7c886bf291f1783b343e98cd95a0efc328370b449a")),
            Map.entry(
                    "docs/refactor/phase4c/README.md",
                    new HashPair(
                            "50f1ee46eddac681b49281c3b348e4017fe6893ec38051a5485317cd766c2f61",
                            "fbdbf32d9a3c488c890ce5d71689e59eb9a7458989843a45433e247dca2f6d98")),
            Map.entry(
                    "infra/phase2/README.md",
                    new HashPair(
                            "7ae3e8a5bb36920039649ffa8a2aef2bd9bb59782fa03f50e4174cee9063b56f",
                            "30950043edcca47aa42543065ca0b6b08d5c4c4a4839f2034af2cdde47174622")),
            Map.entry(
                    "infra/phase2/verify-static.sh",
                    new HashPair(
                            "92a3a1ee30ddbb2b5c854dbff7fac23da37e5804e0628211e85725ba4523d835",
                            "78f6dd82e43d39f289b5962490aace65dba806581a16580903d32dbee4812752")),
            Map.entry(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
                    new HashPair(
                            "0042ca6deb05498b2d363c81843d7ec39e3f2cb6af2d43376b24b1d24b03940a",
                            "b95ee58fd66698d129ee9562959d21ffc3a3e0c0b49339f21c379a8d0c356090")),
            Map.entry(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchor"
                            + "ContractParityTest.java",
                    new HashPair(
                            "4824d1aa3ecb5208277066731b16efe33eadf2748348071f04e43c6e5887b520",
                            "bd2b0c554a19fb561919298bba1c23a9f35435390ff3a069e3ec8e7ec5959e12")),
            Map.entry(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPush"
                            + "ContractParityTest.java",
                    new HashPair(
                            "a8e81f0758928eb69c527a9d6bbcf00517160221ea7b1aca4b901b7d5a26cf48",
                            "efa8bd66c5df68bdd9617415b156450ba2ae12dafb2c284df75dcc44e8edcd02")),
            Map.entry(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py",
                    new HashPair(
                            "4f97c2fcdfd36ac943fce4a1e948d99bf52cb8418519602141d40614ce78af44",
                            "342990a999fa0873b6c33a9a2f735f88fb7a453ee27d94832b81b14b9c8fa2a1")),
            Map.entry(
                    "tools/phase2_wormhole_successor_acceptance.py",
                    new HashPair(
                            "868d5cebbcc695136083ac892e572483ffc40829f487cb8d9d2b407c2fc763d1",
                            "9e11c33623a10415b28a5aadf1cf0855ef4bdd1dc9a3d81eeeff41e76a98f735")),
            Map.entry(
                    "tools/phase4c_http_target_execution_post_push_anchor_"
                            + "successor_acceptance.py",
                    new HashPair(
                            "fe074402bcb58cfd3a681769050dd80174c584a082b462047d9684950b60e363",
                            "c1abc55435cd3c3e1c62a72412dc5b62b300fb9f76b8ebc2b6c5482fe726403d")),
            Map.entry(
                    "tools/test_phase2_wormhole_successor_acceptance.py",
                    new HashPair(
                            "691198f36292c460b6bb516e9deb4e4efe064ae12fe60efb85280a52753cb5cb",
                            "b273ae2f450238b709d409e07e6ab7c7f39fbe71d162563a18350f62adaca7ab")),
            Map.entry(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py",
                    new HashPair(
                            "f51784ae1831b54e630150af2af12d3692397f3191d74314f3f0816b847cdfae",
                            "b2f0feefd23f88c357c1bb6e72f417a4de212465e79577930a7c671c3138e47c")),
            Map.entry(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py",
                    new HashPair(
                            "d99d36f8b17e5072dcd130c4570ac074096a3c9ee2b9bf4f0f49fd2b1cd907e6",
                            "9bb6c53fd9c833ff2ed9d2bdcf09af80ae436a9bcfc4c2ee2d54c03f2274acca")));

    @Test
    void loadsTheFixedCanonicalPayloadAndExplicitTrustAllowlist() throws Exception {
        JsonNode contract = contract();
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-typed-normalization-contract");
        assertThat(contract.path("document_payload_sha256").asString()).isEqualTo(
                "eeb2b6dd9be091950867cfe8040c486b867179c49f0a0861c700864ec773eb99");
        assertThat(contract.path("predecessor").path("sha256").asString()).isEqualTo(
                "1aa86e7cd8fe4f6c6c808eee166ff0ed30f7e228e707941efde87323b9ae057a");
        assertThat(contract.path("predecessor_external_git_anchor")
                .path("commit_oid").asString()).isEqualTo(
                "c38defa703b358a280122a09019031c040c58ea7");
        assertThat(contract.path("predecessor_external_git_anchor")
                .path("anchored_sources")).hasSize(6);

        JsonNode trust = contract.path("current_node_trust_boundary");
        assertThat(strings(trust.path("source_paths")))
                .containsExactlyElementsOf(CURRENT_NODE_SOURCES.stream().sorted().toList());
        assertThat(trust.path("source_count").asInt()).isEqualTo(6);
        assertThat(trust.path("source_path_allowlist_exact").asBoolean()).isTrue();
        assertThat(trust.path("sources_excluded_from_self_authority").asBoolean())
                .isTrue();
        assertThat(trust.path("source_bytes_external_git_anchor_complete").asBoolean())
                .isFalse();
        assertThat(trust.path("post_push_external_anchor_required").asBoolean()).isTrue();
    }

    @Test
    void reclassifiesOnlyAwareExpiryAndKeepsMalformedAsTypedRejection()
            throws Exception {
        JsonNode contract = contract();
        JsonNode rows = contract.path("disposition_ledger").path("rows");
        assertThat(rows).hasSize(59);
        assertThat(contract.path("disposition_ledger")
                .path("single_effective_override_case_id").asString())
                .isEqualTo(AWARE_CASE);

        JsonNode aware = row(rows, AWARE_CASE);
        assertThat(aware.path("execution_disposition").asString())
                .isEqualTo("EXECUTED_FULL_CONTEXT_HTTP");
        assertThat(aware.path("http_execution").asBoolean()).isTrue();
        assertThat(aware.path("target_status").asInt()).isEqualTo(200);
        assertThat(aware.path("business_jdbc_reached").asBoolean()).isTrue();
        assertThat(aware.path("proof").path("replaces_historical_leaf_ordinal").asInt())
                .isEqualTo(60);
        assertThat(contract.path("typed_normalization")
                .path("historical_disposition").asString())
                .isEqualTo("EXECUTED_TYPED_COLLAPSE");
        assertThat(contract.path("typed_normalization")
                .path("canonical_local_datetime").asString())
                .isEqualTo("2026-07-17T13:00:00");
        assertThat(contract.path("typed_normalization")
                .path("offset_provenance_erased").asBoolean()).isTrue();
        assertThat(strings(contract.path("typed_normalization")
                .path("cast_compatibility_versions")))
                .containsExactly("16.14", "18.4");
        assertThat(strings(contract.path("typed_normalization")
                .path("cast_session_time_zones")))
                .containsExactly("UTC", "America/Los_Angeles");
        assertThat(contract.path("typed_normalization")
                .path("cross_version_equal").asBoolean()).isTrue();
        assertThat(contract.path("typed_normalization")
                .path("session_timezone_independent").asBoolean()).isTrue();
        assertThat(contract.path("typed_normalization")
                .path("full_filter_http_version").asString()).isEqualTo("18.4");
        assertThat(contract.path("typed_normalization")
                .path("http_fixture_origin").asString()).isEqualTo(
                "java_string_bind_explicit_cast_insert_before_request_trace");
        assertThat(contract.path("typed_normalization")
                .path("http_fixture_sql_literal_seeded").asBoolean()).isFalse();

        JsonNode malformed = row(rows, MALFORMED_CASE);
        assertThat(malformed.path("execution_disposition").asString())
                .isEqualTo("EXECUTED_TYPED_REJECTION");
        assertThat(malformed.path("http_execution").asBoolean()).isFalse();
        assertThat(malformed.path("target_status").isNull()).isTrue();
        assertThat(contract.path("malformed_typed_rejection")
                .path("sqlstate").asString()).isEqualTo("22007");
        assertThat(contract.path("malformed_typed_rejection")
                .path("persisted_bank_share_row_count").asInt()).isZero();
    }

    @Test
    void fixesFiftyEightHttpExecutionsPlusOneTypedDisposition() throws Exception {
        JsonNode summary = contract().path("disposition_ledger").path("summary");
        assertThat(summary.path("logical_disposition_count").asInt()).isEqualTo(59);
        assertThat(summary.path("http_execution_count").asInt()).isEqualTo(58);
        assertThat(summary.path("typed_rejection_count").asInt()).isEqualTo(1);
        assertThat(summary.path("non_fault_http_execution_count").asInt())
                .isEqualTo(47);
        assertThat(summary.path("postgres_abort_http_execution_count").asInt())
                .isEqualTo(11);
        assertThat(summary.path("business_jdbc_reached_http_count").asInt())
                .isEqualTo(50);
        assertThat(summary.path("pre_business_jdbc_termination_http_count").asInt())
                .isEqualTo(8);
        assertThat(summary.path("api_alias_http_execution_count").asInt())
                .isEqualTo(44);
        assertThat(summary.path("web_alias_http_execution_count").asInt())
                .isEqualTo(14);
        assertThat(summary.path("http_status_counts").toString())
                .isEqualTo("{\"200\":35,\"302\":5,\"401\":3,\"403\":10,\"500\":5}");
    }

    @Test
    void selectsSixtyOfSixtyOnePhysicalLeavesWithoutDoubleCounting() throws Exception {
        JsonNode junit = contract().path("junit_execution");
        assertThat(junit.path("historical_physical_leaf_count").asInt()).isEqualTo(60);
        assertThat(junit.path("new_physical_leaf_count").asInt()).isEqualTo(1);
        assertThat(junit.path("aggregate_physical_leaf_count").asInt()).isEqualTo(61);
        assertThat(junit.path("logical_disposition_leaf_count").asInt()).isEqualTo(59);
        assertThat(junit.path("supplementary_authentication_leaf_count").asInt())
                .isEqualTo(1);
        assertThat(junit.path("replacement_leaf_count").asInt()).isEqualTo(1);
        assertThat(junit.path("superseded_historical_representation_leaf_count")
                .asInt()).isEqualTo(1);
        assertThat(junit.path("selected_effective_proof_leaf_count").asInt())
                .isEqualTo(60);
        assertThat(junit.path("superseded_leaf_double_counted").asBoolean()).isFalse();
    }

    @Test
    void preservesWormFiveAndTheElevenSixHundredZeroRouteBoundary()
            throws Exception {
        JsonNode contract = contract();
        assertThat(contract.path("worm_evidence")
                .path("fixed_chain_node_count").asInt()).isEqualTo(5);
        assertThat(contract.path("worm_evidence")
                .path("new_worm_report_created").asBoolean()).isFalse();

        JsonNode acceptance = contract.path("acceptance");
        assertThat(acceptance.path("implemented_pending_get_count").asInt())
                .isEqualTo(2);
        assertThat(acceptance.path("migrated_operation_count").asInt()).isEqualTo(11);
        assertThat(acceptance.path("pending_operation_count").asInt()).isEqualTo(600);
        assertThat(acceptance.path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(acceptance.path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(acceptance.path("typed_parity_review_complete").asBoolean()).isFalse();
        assertThat(acceptance.path("full_target_parity_closed").asBoolean()).isFalse();
        assertThat(acceptance.path("production_cutover").asBoolean()).isFalse();
    }

    @Test
    void exposesOnlyTheFourteenFixedThirdHopSuccessorTransitions() throws Exception {
        assertThat(THIRD_HOP_SUCCESSORS).hasSize(14);
        assertThat(Phase4cHttpTypedNormalizationSuccessorAcceptance.successorPaths())
                .containsExactlyInAnyOrderElementsOf(THIRD_HOP_SUCCESSORS.keySet());
        for (Map.Entry<String, HashPair> entry : THIRD_HOP_SUCCESSORS.entrySet()) {
            assertThat(entry.getValue().accepted()).isNotEqualTo(entry.getValue().successor());
            assertThat(Phase4cHttpTypedNormalizationSuccessorAcceptance
                    .acceptedHash(entry.getKey())).as(entry.getKey())
                    .isEqualTo(entry.getValue().accepted());
            assertThat(Phase4cHttpTypedNormalizationSuccessorAcceptance
                    .successorHash(root(), entry.getKey())).as(entry.getKey())
                    .isEqualTo(entry.getValue().successor());
        }
        Set<String> forbiddenPaths = new LinkedHashSet<>(CURRENT_NODE_SOURCES);
        forbiddenPaths.addAll(FIXED_SOURCE_PATHS);
        forbiddenPaths.add(PREDECESSOR_PATH);
        forbiddenPaths.add("tools/unknown-source.py");
        forbiddenPaths.removeAll(THIRD_HOP_SUCCESSORS.keySet());
        for (String forbidden : forbiddenPaths) {
            assertThat(Phase4cHttpTypedNormalizationSuccessorAcceptance
                    .acceptedHash(forbidden)).as(forbidden).isNull();
            assertThat(Phase4cHttpTypedNormalizationSuccessorAcceptance
                    .successorHash(root(), forbidden)).as(forbidden).isNull();
        }
    }

    @Test
    void loadsFromAMinimalGitlessCopyWithoutCurrentNodeValidators(
            @TempDir Path temporary
    ) throws Exception {
        copyMinimalFixture(temporary);
        assertThat(temporary.resolve(".git")).doesNotExist();
        assertThat(temporary.resolve(NEW_JAVA_ACCEPTANCE_PATH)).doesNotExist();
        assertThat(temporary.resolve(NEW_JAVA_PARITY_PATH)).doesNotExist();
        assertThat(temporary.resolve(
                "tools/phase4c_http_typed_normalization_successor_acceptance.py"))
                .doesNotExist();
        assertThat(Phase4cHttpTypedNormalizationSuccessorAcceptance.load(temporary)
                .path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-typed-normalization-contract");
    }

    @Test
    void rejectsFixedSourceTamperingInAGitlessCopy(@TempDir Path temporary)
            throws Exception {
        copyMinimalFixture(temporary);
        Path seed = temporary.resolve(
                "server/src/test/resources/db/phase4c/"
                        + "072-personal-bank-user-counts-typed-normalization-seed.sql");
        Files.writeString(seed, "-- tampered\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cHttpTypedNormalizationSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class);
    }

    @Test
    void thirdHopLookupRehashesTheContractAndRequestedPath(@TempDir Path temporary)
            throws Exception {
        String relative = "README.md";
        for (String sourceRelative : List.of(CONTRACT_PATH, relative)) {
            Path target = temporary.resolve(sourceRelative);
            Files.createDirectories(target.getParent());
            Files.copy(root().resolve(sourceRelative), target);
        }
        assertThat(temporary.resolve(PREDECESSOR_PATH)).doesNotExist();
        assertThat(Phase4cHttpTypedNormalizationSuccessorAcceptance.successorHash(
                temporary, relative)).isEqualTo(THIRD_HOP_SUCCESSORS.get(relative).successor());

        Path contract = temporary.resolve(CONTRACT_PATH);
        Files.writeString(contract, " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cHttpTypedNormalizationSuccessorAcceptance.successorHash(
                        temporary, relative))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("contract physical bytes");

        Files.copy(root().resolve(CONTRACT_PATH), contract,
                StandardCopyOption.REPLACE_EXISTING);
        Files.writeString(temporary.resolve(relative), " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cHttpTypedNormalizationSuccessorAcceptance.successorHash(
                        temporary, relative))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("third-hop successor");
    }

    @Test
    void rejectsSymlinkSubstitutionInAGitlessCopy(@TempDir Path temporary)
            throws Exception {
        copyMinimalFixture(temporary);
        Path seed = temporary.resolve(
                "server/src/test/resources/db/phase4c/"
                        + "072-personal-bank-user-counts-typed-normalization-seed.sql");
        Path outside = temporary.resolve("outside-seed.sql");
        Files.move(seed, outside);
        Files.createSymbolicLink(seed, outside);
        assertThatThrownBy(() ->
                Phase4cHttpTypedNormalizationSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class);
    }

    @Test
    void rejectsEveryTrustRouteAndEvidenceOverclaim() throws Exception {
        JsonNode fixed = contract();
        List<Mutation> mutations = List.of(
                new Mutation("aware reversion", value -> ((ObjectNode) row(
                        value.path("disposition_ledger").path("rows"), AWARE_CASE))
                        .put("execution_disposition", "EXECUTED_TYPED_COLLAPSE")),
                new Mutation("second override", value -> ((ObjectNode) value
                        .path("disposition_ledger"))
                        .put("single_effective_override_case_id", MALFORMED_CASE)),
                new Mutation("malformed HTTP", value -> ((ObjectNode) value
                        .path("malformed_typed_rejection"))
                        .put("http_execution", true)),
                new Mutation("double count", value -> ((ObjectNode) value
                        .path("junit_execution"))
                        .put("superseded_leaf_double_counted", true)),
                new Mutation("effective 61", value -> ((ObjectNode) value
                        .path("junit_execution"))
                        .put("selected_effective_proof_leaf_count", 61)),
                new Mutation("WORM six", value -> ((ObjectNode) value
                        .path("worm_evidence")).put("fixed_chain_node_count", 6)),
                new Mutation("self anchor", value -> ((ObjectNode) value
                        .path("current_node_trust_boundary"))
                        .put("source_bytes_external_git_anchor_complete", true)),
                new Mutation("typed review", value -> ((ObjectNode) value
                        .path("authorization"))
                        .put("typed_parity_review_complete", true)),
                new Mutation("full parity", value -> ((ObjectNode) value
                        .path("authorization")).put("full_target_parity_closed", true)),
                new Mutation("route eligible", value -> ((ObjectNode) value
                        .path("authorization")).put("route_migration_eligible", true)),
                new Mutation("migrated 13", value -> ((ObjectNode) value
                        .path("acceptance")).put("migrated_operation_count", 13)),
                new Mutation("pending 598", value -> ((ObjectNode) value
                        .path("acceptance")).put("pending_operation_count", 598)),
                new Mutation("cutover", value -> ((ObjectNode) value
                        .path("authorization")).put("production_cutover", true)));
        for (Mutation mutation : mutations) {
            JsonNode changed = fixed.deepCopy();
            mutation.action().apply(changed);
            assertThatThrownBy(() ->
                    Phase4cHttpTypedNormalizationSuccessorAcceptance.validate(changed))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }
    }

    private static JsonNode contract() throws Exception {
        return Phase4cHttpTypedNormalizationSuccessorAcceptance.load(root());
    }

    private static JsonNode row(JsonNode rows, String caseId) {
        for (JsonNode row : rows) {
            if (caseId.equals(row.path("case_id").asString())) {
                return row;
            }
        }
        throw new AssertionError("missing fixed typed-normalization case: " + caseId);
    }

    private static void copyMinimalFixture(Path targetRoot) throws Exception {
        Set<String> relatives = new LinkedHashSet<>(FIXED_SOURCE_PATHS);
        relatives.add(CONTRACT_PATH);
        relatives.add(PREDECESSOR_PATH);
        for (String relative : relatives) {
            Path source = root().resolve(relative);
            Path target = targetRoot.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(source, target);
        }
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }

    private static List<String> strings(JsonNode values) {
        List<String> result = new ArrayList<>();
        values.forEach(value -> result.add(value.asString()));
        return List.copyOf(result);
    }

    private record HashPair(String accepted, String successor) {
    }

    private record Mutation(String label, MutationAction action) {
    }

    @FunctionalInterface
    private interface MutationAction {
        void apply(JsonNode value);
    }
}
