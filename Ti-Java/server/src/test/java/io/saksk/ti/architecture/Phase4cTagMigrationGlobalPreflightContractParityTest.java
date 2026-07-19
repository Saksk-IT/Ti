package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity gate for the tag global-preflight successor. */
class Phase4cTagMigrationGlobalPreflightContractParityTest {

    private static final Map<String, HashPair> TRANSITIONS = Map.ofEntries(
            transition(
                    "infra/phase2/README.md",
                    "414901d53174c7875ea000c323652a1ddf046a2e97018bbbd1dc4c9a4b3bf988",
                    "a0c467bfc8aa0f0b64b4d520f9cda60ff081a340f016647e1da934c73b7b99d5"),
            transition(
                    "infra/phase2/verify-static.sh",
                    "410108998f03e4d857d230c75687e854bd3bad99ba85d18c2fb090978ffa46d7",
                    "893ca920d0ed1bd62e16509893fa30bbfc72b88368d66d96c2ebc5c2fbae38dc"),
            transition(
                    "tools/phase2_wormhole_successor_acceptance.py",
                    "1164b6c584f4905a8011c5320eac62591e039ad0526b5a0657908f7b82688480",
                    "5c93b9aa00d3faec19ebc8d6472bd9e8ab1903a7116d487ff8a711fc60fd8d20"),
            transition(
                    "tools/test_phase2_wormhole_successor_acceptance.py",
                    "ff3250a88eb6e16102fc91930beec627f79ed57720140a32e7ad4410d7856e9f",
                    "e61ed72335bba631cf34ebfe06fae8d391e7828622eba17d0240f59efed379a3"),
            transition(
                    "tools/phase4c_http_typed_normalization_anchor_"
                            + "successor_acceptance.py",
                    "cf434c2dc8e33c0b60d09646292fc358bc2df678bfe2f83d04edae79c7bd4aee",
                    "c54843d2c759882e4d5e7553e9b76598a1ecd31038ace27ac265275887a414d2"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
                    "b762441b9d0537240e231effbe5477b89713e7abc861ff9d5a614fc80008848c",
                    "57be8ccb44124d315c21e21e9041861cdcb4568a814af56dbe1725635a479374"),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_typed_"
                            + "normalization_anchor_contract.py",
                    "a96c4431b258b15d367250b668602fcb0ca04cab9555f13a4abfaa8914b0edec",
                    "cdc78a5f771d09eb1822f3dbcd10030e812e4a5ab6b7792ce2b0a9d8366e90ba"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchor"
                            + "ContractParityTest.java",
                    "f0f57fbd1c24e8f26878209eba298645c63bd962381d26d2505fb76ee495cda8",
                    "faff2f55f48cdaa8bab92530347cda47a0f3ba4dc4227c86242afb94d78aebc0"),
            transition(
                    "docs/refactor/05-progress.md",
                    "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
                    "8478e44622fc666fdb9a377b15ced624e34d104d1fcbb9b36a4913cfb3ddedf0"),
            transition(
                    "docs/refactor/phase4c/README.md",
                    "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
                    "4d75ba666d7d45d620a4fba4574e4c2640b754c5a6beadbdbfdee5498aa3cc48"),
            transition(
                    "tools/test_phase6_web_foundation_source_successor_contract.py",
                    "fb553e8d15c8b748dc62eb6517f775614132657a60b13716449ad1a72606685d",
                    "3bc6342e7dad775f7c92acfc0f8cb23cd94aabd6d395f4f0fae420faea14ee6b"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase6WebFoundationSourceSuccessorContractParityTest.java",
                    "34d6b638cf40667a2c0b1ce1214cc04b8e149321f3137ea8d5d09ee44290d694",
                    "e61b445cbedddd5b71efe7dda22811128414b58089bf1525aaa4017485f6675d"),
            transition(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "implementation_contract.py",
                    "d020cf859dcba608d9b67d122ebfaca0d1bfd3161a12fc7c386d090e65938ef0",
                    "1f1c31977c356d93bfabe6714692efa27c5b3c34178e6df6b3517a3362f610e3"),
            transition(
                    "tools/phase4c_http_implementation_successor_acceptance.py",
                    "54438d9ee44d391b813a1c3503444dd65d627e3b5932971e49ef549650fbbff4",
                    "f0eba1dbbe3f0cfdbd384c0aea8ba9b768d16edc414ed7c1b1cf5fa8fd31641d"),
            transition(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_contract.py",
                    "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209",
                    "3064c164d300499d958947068d3acd50c8823c741d9a0144860b5f3b1b532f7d"),
            transition(
                    "tools/phase4c_http_target_execution_successor_acceptance.py",
                    "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a",
                    "daca285575123c6b3d690c52977bbf8797fa46d5db75862b774805acb586a230"),
            transition(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_anchor_contract.py",
                    "b87133b5c187561970c322a92eb22f84cb7a768a9168870cc7517dd973616667",
                    "624d741b383866ce1bb8ec49c24445164665096cdf5b9ab679b2561c61ab7e9a"),
            transition(
                    "tools/phase4c_http_target_execution_anchor_"
                            + "successor_acceptance.py",
                    "03b411be87bd9f8d4dbb94ddcfb9495ec7523fb5c9482f3c1fb4098d1ab7e455",
                    "e91c56e91cdeff3bf069407d8e43d7d1b76fb131c875cf536e561976fe395141"),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_"
                            + "composition_contract.py",
                    "b81c8fb13f2ce4dd0d917a0876b88a20804bd1d272a7c261563dad9513d42f17",
                    "51ab42d0a220f3e91ac07a9b3ab1f6a2ca6c366b994de200effae31a074a766b"),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
                    "641c90d33de50daeb3a1a1c9a3ae5027562273f780f88e6a26cf00ad3bd462ac",
                    "6c302395dca0d7d319233e6463ed65b26aa3ea103c90511752ae4cac710dbaad"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "ModuleContractParityTest.java",
                    "02a4b9bfabe2f9e3789e94826b1f337e8a0986e5d36f42ac243cbe79060a82d2",
                    "984863bff3762adc8e375f0073559bb1e0e1d0ed16c368147087fdc3ca4efcd1"),
            transition(
                    "tools/phase4c_read_successor_acceptance.py",
                    "1e494bce628e87bc2db3d01742fb929752fedaefd7563defccad7b972c951980",
                    "25792f3a1371b8a492d674d70228ce81872e0ce48c2aab8051805c8c0b41de8a"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cReadSuccessorAcceptance.java",
                    "5047c8b0a36450a72ba74a460db115ab33a58861b64216fa2cc67a7ddb0a026d",
                    "4699c29cb6e5f790b448752896cc42c413e9f0b3c4844551c4a0b2931517d1a0"),
            transition(
                    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
                    "e37b0418e8018d58135c5b1c55149d9679dfedb21f8b67fca3425b874ea23efc",
                    "31dec8b10fad1f044ecbca4a76da0d4f1f97ffbbe32e075895e050372ff8ba4a"),
            transition(
                    "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
                    "f236ed8080a4e73d294d0eb96f1b19f8b3116ef0a51ba1be6d5d8e695dc558e0",
                    "7afd91f0e0048cba029d38965c900da670d5f327b8b9541b0962533b1b1f09eb"),
            transition(
                    "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
                    "c60e4d9abb01c70001e703cf8c4c5eed77bd65445c506e99a9e3dd38dadab2ee",
                    "32b4d8e625f452ba20852fe64805086a6d878f3f8518298e7340122ff6120943"),
            transition(
                    "tools/test_phase4b_personal_bank_share_list_read_contract.py",
                    "ffde7c337edf81ba8cf1a457800e89e3150df10b44ea7da50e99436534caa671",
                    "047563af77f5786b0af24eeb20f8d287163df44778aad1ee56d1805a05207ec4"),
            transition(
                    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
                    "84f7ee524b57e9417267380b73ebc68439382b578f2b7674c50cdbf2a6021e0e",
                    "162e057e07d6d0d0f73b6ee8bf9210fd98c492369222ce649a4f5bd5418b16b4"),
            transition(
                    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
                    "de1415897a0cef4e98266aaca699b162dd469caf17628dd2fde19bed691ef32c",
                    "4f3c9ab19370eabd6dbe6dbea047d1e176c3a4e8ed947035a54dc210b75e2057"),
            transition(
                    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
                    "90c77b28c1c08822d900f150e5c4c69fe4a7463b5dfc7a4ce021fc599c71a15a",
                    "0a980e05a5fd4204e5db630447c7b018d54e2e89b64e7f069eb1329f85a5d372"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpImplementationSuccessorAcceptance.java",
                    "1d2c193fb7a63173850bfee7ce382e7b4bc417c5b3879f3ef4bb43187f980275",
                    "fff0820405e76a4b7c58b094e21619ea050664a3b3ebfbc59abc29a83755465d"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
                    "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578",
                    "10d19deb68495db02f9113dd58bdf7bbf7dfa67a8885c49f7dd88685f574ff78"),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_contract.py",
                    "a8ce7fc93fe022d16a10e4bdd0fa9bff55788b076eb78601efba373c29c54a4b",
                    "469c46bde8e339ef28a461f3fd2a34ee7e02bfa12cb75eec4f881454049e7957"),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "entry_contract.py",
                    "c87d528ad6ee912863da16a49e0a398cffe3c9479d1f58461e32035b76fafd26",
                    "fcc4eee103b33604addfd17e453793dd41c498de62fe0538e873520dbd285b26"),
            transition(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py",
                    "a215e6b65624630de990dcae7e8d718e8a38a1fadae3e00ee0f3ccb81788959f",
                    "bbafe62ee77ab0e5c25ed0daf96dc8207cc033d4f39f6cdb3d9cfa8f18365285"),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py",
                    "87078f6d01957dcbbb37b488048a6702bc2212850ee9b2b75aa9b68aba352057",
                    "420a727733f4c3a72f1c78c933491ab89fff7bbba0ddb1f1c9f7a8867a73c3bf"),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_anchor_contract.py",
                    "3ded87895b33befb0f80905a1490d5f9207ae4e9ee26e939e5c00ebbd30a7874",
                    "49621a580785ddd0c1210bf564e563b41e04bebbc87c33752e95bc6cb9cb89fd"),
            transition(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "implementation_contract.py",
                    "9c61d6cefdd980457197fb850f690c6adc1a84fdb3d21905a2a5cfdb1bc258c2",
                    "a6b70a441470d079b5bc2dc392887d49af72d6dc75a4feba3226a772b5b4c9d5"),
            transition(
                    "tools/phase4c_http_target_execution_post_push_"
                            + "successor_acceptance.py",
                    "944c925704e1b237a7d8e16c76591a0e8b7965d388bedd9e2a52492e0511c90c",
                    "b19db64d6ddb71b0cac1d4ae296c02e65e82d476b37b9db5ec5fbfcfd7f4a8df"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
                    "46f68412ea0cf42687133ba87a2184b86fe1b0c29625b1ee3f6e8f7301399efa",
                    "a39a7b768979208e5bdcbdcbcbfa7d327521fb69e65d271b5d2f2da47f7ad348"),
            transition(
                    "tools/phase4c_http_typed_normalization_"
                            + "successor_acceptance.py",
                    "e71a5eec0e71ff824750f6eb20c4b310fdb0d8273fe89d83a23aee422ba282c5",
                    "a852f20ffccd8d2f1597a1bd2adb525ca66e83fed707ef6d44ff9a8d35c240c8"),
            transition(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
                    "f78882b20e38857c420b750677e4e8dd52922a1f0c04c249db9ed0d4f3db4fd5",
                    "ec7c98b04a26f25940fd5b9ec4120ebd478aa41798d4040f1cce97336898d6d2"));

    @Test
    void loadsTheCanonicalContractAndKeepsAllAuthorityClosed() throws Exception {
        JsonNode contract = contract();

        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-tag-migration-global-preflight-contract");
        assertThat(contract.path("authorization")
                .path("migration_global_preflight_evidence_closed")
                .asBoolean()).isTrue();
        for (String field : Set.of(
                "migration_design_closed",
                "operator_migration_implementation",
                "production_schema_or_index",
                "real_data_migration_execution",
                "production_cutover",
                "route_or_openapi_delta",
                "http_security_or_rate_limit_delta",
                "client_gateway_or_proxy_change",
                "source_successor_external_git_anchor_complete",
                "semantic_successor_external_git_anchor_complete",
                "bootstrap_control_sources_external_git_anchor_complete")) {
            assertThat(contract.path("authorization").path(field).asBoolean())
                    .as(field).isFalse();
        }
        assertThat(contract.path("route_state")
                .path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(contract.path("route_state")
                .path("pending_operation_count").asInt()).isEqualTo(598);
        assertThat(contract.path("route_state")
                .path("production_cutover_operation_count").asInt()).isZero();
        assertThat(contract.path("source_authority")
                .path("control_source_count").asInt()).isEqualTo(11);
        assertThat(contract.path("source_authority")
                .path("control_sources_external_git_anchor_complete")
                .asBoolean()).isFalse();
    }

    @Test
    void exposesOnlyTheExactFixedTransitionsAndRejectsUnknownPaths()
            throws Exception {
        assertThat(Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .successorPaths()).containsExactlyInAnyOrderElementsOf(
                TRANSITIONS.keySet());
        for (Map.Entry<String, HashPair> entry : TRANSITIONS.entrySet()) {
            String relative = entry.getKey();
            assertThat(Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                    .acceptedSha256(relative)).as(relative)
                    .isEqualTo(entry.getValue().accepted());
            assertThat(Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                    .successorSha256(root(), relative)).as(relative)
                    .isEqualTo(entry.getValue().successor());
        }
        assertThat(Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .acceptedSha256("tools/unknown.py")).isNull();
        assertThat(Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .successorSha256(root(), "tools/unknown.py")).isNull();
    }

    @Test
    void fixesTheSevenNodeWormChainWithoutApplyOrCutover() throws Exception {
        JsonNode authority = contract().path("build_context_authority");
        assertThat(authority.path("initial_worm_successor")
                .path("fixed_chain_node_count").asInt()).isEqualTo(6);
        assertThat(authority.path("new_worm_successor")
                .path("fixed_chain_node_count").asInt()).isEqualTo(7);
        assertThat(authority.path("new_worm_successor")
                .path("sha256").asString()).isEqualTo(
                "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344");
        assertThat(authority.path("new_worm_successor")
                .path("predecessor_sha256").asString()).isEqualTo(
                "283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72");
        assertThat(authority.path("new_build_context_worm_closed").asBoolean())
                .isTrue();
        assertThat(authority.path("new_worm_successor_required").asBoolean())
                .isFalse();
        assertThat(authority.path(
                "apply_statement_or_operator_entrypoint_added").asBoolean())
                .isFalse();
    }

    @Test
    void loadsFromTheExactGitlessFixture(@TempDir Path temporary)
            throws Exception {
        copyMinimalFixture(temporary);

        assertThat(temporary.resolve(".git")).doesNotExist();
        JsonNode loaded =
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .load(temporary);
        assertThat(loaded.path("source_successor_bridges")
                .path("path_count").asInt()).isEqualTo(TRANSITIONS.size());
    }

    @Test
    void rejectsSuccessorTamperAndSymlinkSubstitution(@TempDir Path temporary)
            throws Exception {
        Path tampered = temporary.resolve("tampered");
        copyMinimalFixture(tampered);
        Files.writeString(
                tampered.resolve("infra/phase2/README.md"),
                " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .load(tampered))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("physical bytes");

        Path symlinked = temporary.resolve("symlinked");
        copyMinimalFixture(symlinked);
        Path report = symlinked.resolve(
                "docs/refactor/phase4c/"
                        + "personal-bank-tag-global-preflight-hardening-"
                        + "worm-evidence.json");
        Path outside = symlinked.resolve("outside.json");
        Files.move(report, outside);
        Files.createSymbolicLink(report, outside);
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .load(symlinked))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("symlink");

        Path semanticTamper = temporary.resolve("semantic-tamper");
        copyMinimalFixture(semanticTamper);
        Files.writeString(
                semanticTamper.resolve(
                        "tools/test_phase4c_personal_bank_user_counts_"
                                + "http_entry_contract.py"),
                " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .successorSha256(
                                semanticTamper,
                                "tools/test_phase4c_personal_bank_user_counts_"
                                        + "http_entry_contract.py"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("source-successor bytes drifted");
    }

    @Test
    void rejectsBridgeWormRouteAndAuthorizationOverclaims() throws Exception {
        JsonNode fixed = contract();
        Set<Mutation> mutations = Set.of(
                new Mutation("bridge", value -> ((ObjectNode) value
                        .path("source_successor_bridges").path("overrides")
                        .path("infra/phase2/README.md")).put(
                        "successor_sha256", "f".repeat(64))),
                new Mutation("WORM", value -> ((ObjectNode) value
                        .path("build_context_authority")
                        .path("new_worm_successor")).put(
                        "fixed_chain_node_count", 8)),
                new Mutation("route", value -> ((ObjectNode) value
                        .path("route_state")).put(
                        "migrated_operation_count", 14)),
                new Mutation("operator", value -> ((ObjectNode) value
                        .path("authorization")).put(
                        "operator_migration_implementation", true)),
                new Mutation("cutover", value -> ((ObjectNode) value
                        .path("authorization")).put(
                        "production_cutover", true)),
                new Mutation("external anchor", value -> ((ObjectNode) value
                        .path("authorization")).put(
                        "source_successor_external_git_anchor_complete", true)));
        for (Mutation mutation : mutations) {
            JsonNode changed = fixed.deepCopy();
            mutation.action().apply(changed);
            assertThatThrownBy(() ->
                    Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                            .validate(changed, root()))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }
    }

    @Test
    void validatesFixedProductionAndWormSemanticSuccessors() throws Exception {
        JsonNode historical = new ObjectMapper().readTree(Files.readAllBytes(
                root().resolve("docs/refactor/phase4c/"
                        + "personal-bank-user-counts-http-target-execution-"
                        + "contract.json")));
        Map<String, String> accepted = new TreeMap<>();
        historical.path("production_surface").path("files").properties()
                .forEach(entry -> accepted.put(
                        entry.getKey(), entry.getValue().asString()));
        Map<String, String> current = new TreeMap<>(accepted);
        current.put(
                "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                        + "migration/LegacyPersonalBankTagGlobalPreflight.java",
                "cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76");
        current.put(
                "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                        + "migration/LegacyPersonalBankTagPreflightParser.java",
                "c3311e28f33c8bc447fd72191af696ceca333162747e94eb91681dd75c0f5bf3");
        current.put(
                "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                        + "migration/LegacyPersonalBankTagPreflightReport.java",
                "d7d988f5bfe7c86e30a5410e8eac0032a24ad5c85011b6c03de159c97d3ff750");

        var runtime = Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .validateProductionRuntimeSuccessor(
                        root(), accepted, current, "full_runtime");
        assertThat(runtime.acceptedFileCount()).isEqualTo(297);
        assertThat(runtime.currentFileCount()).isEqualTo(300);
        assertThat(runtime.currentManifestSha256()).isEqualTo(
                "8d28a382447c8756b2ec4cfc4107bc55fd744587d81a8835b71eee1f1942fbb3");
        assertThat(runtime.addedFiles()).hasSize(3);
        assertThat(runtime.changedFiles()).isEmpty();
        assertThat(runtime.deletedFiles()).isEmpty();

        Map<String, String> acceptedMain = new TreeMap<>();
        Map<String, String> currentMain = new TreeMap<>();
        accepted.forEach((relative, digest) -> {
            if (relative.startsWith(
                    "server/src/main/java/io/saksk/ti/learning/")
                    || relative.startsWith(
                    "server/src/main/java/io/saksk/ti/personalbank/")) {
                acceptedMain.put(relative, digest);
            }
        });
        current.forEach((relative, digest) -> {
            if (relative.startsWith(
                    "server/src/main/java/io/saksk/ti/learning/")
                    || relative.startsWith(
                    "server/src/main/java/io/saksk/ti/personalbank/")) {
                currentMain.put(relative, digest);
            }
        });
        var main = Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .validateProductionRuntimeSuccessor(
                        root(), acceptedMain, currentMain,
                        "learning_personalbank_main");
        assertThat(main.acceptedFileCount()).isEqualTo(40);
        assertThat(main.currentFileCount()).isEqualTo(43);

        var worm = Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .validateWormSuccessor(
                        root(),
                        "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
                        "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3");
        assertThat(worm.acceptedChainNodeCount()).isEqualTo(5);
        assertThat(worm.firstSuccessorChainNodeCount()).isEqualTo(6);
        assertThat(worm.currentChainNodeCount()).isEqualTo(7);
        assertThat(worm.currentBuildContextSha256()).isEqualTo(
                "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17");
        assertThat(Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .semanticFixturePaths(root()))
                .contains("infra/phase2/hash-java-build-context.sh",
                        "server/Dockerfile", "server/pom.xml",
                        "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                                + "migration/LegacyPersonalBankTagGlobalPreflight.java",
                        "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                                + "migration/LegacyPersonalBankTagPreflightParser.java",
                        "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                                + "migration/LegacyPersonalBankTagPreflightReport.java");

        Map<String, String> changed = new TreeMap<>(current);
        changed.put(changed.keySet().iterator().next(), "f".repeat(64));
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(), accepted, changed, "full_runtime"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("current production manifest");
        Map<String, String> changedAccepted = new TreeMap<>(accepted);
        changedAccepted.put(
                changedAccepted.keySet().iterator().next(), "f".repeat(64));
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(), changedAccepted, current, "full_runtime"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("historical production manifest");
        Map<String, String> extra = new TreeMap<>(current);
        extra.put("server/src/main/java/Unexpected.java", "f".repeat(64));
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(), accepted, extra, "full_runtime"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("current production manifest");
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(), accepted, current, "unknown"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("unknown production view");
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateWormSuccessor(
                                root(), "f".repeat(64),
                                "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("WORM successor");
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateWormSuccessor(
                                root(),
                                "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
                                "f".repeat(64)))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("WORM successor");
    }

    @Test
    void executesSemanticSuccessorsFromGitlessFixtureAndRejectsMissingOrTamper(
            @TempDir Path temporary) throws Exception {
        Path valid = temporary.resolve("valid");
        copySemanticFixture(valid);
        assertThat(valid.resolve(".git")).doesNotExist();

        JsonNode historicalDocument = new ObjectMapper().readTree(
                Files.readAllBytes(valid.resolve(
                        "docs/refactor/phase4c/"
                                + "personal-bank-user-counts-http-target-"
                                + "execution-contract.json")));
        Map<String, String> accepted = new TreeMap<>();
        historicalDocument.path("production_surface").path("files")
                .properties().forEach(entry -> accepted.put(
                        entry.getKey(), entry.getValue().asString()));
        Map<String, String> current = new TreeMap<>(accepted);
        current.put(
                "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                        + "migration/LegacyPersonalBankTagGlobalPreflight.java",
                "cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76");
        current.put(
                "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                        + "migration/LegacyPersonalBankTagPreflightParser.java",
                "c3311e28f33c8bc447fd72191af696ceca333162747e94eb91681dd75c0f5bf3");
        current.put(
                "server/src/main/java/io/saksk/ti/learning/infrastructure/"
                        + "migration/LegacyPersonalBankTagPreflightReport.java",
                "d7d988f5bfe7c86e30a5410e8eac0032a24ad5c85011b6c03de159c97d3ff750");
        var runtime = Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .validateProductionRuntimeSuccessor(
                        valid, accepted, current, "full_runtime");
        assertThat(runtime.acceptedFileCount()).isEqualTo(297);
        assertThat(runtime.currentFileCount()).isEqualTo(300);

        Map<String, String> acceptedMain = new TreeMap<>();
        Map<String, String> currentMain = new TreeMap<>();
        accepted.forEach((relative, digest) -> {
            if (isLearningOrPersonalBankMain(relative)) {
                acceptedMain.put(relative, digest);
            }
        });
        current.forEach((relative, digest) -> {
            if (isLearningOrPersonalBankMain(relative)) {
                currentMain.put(relative, digest);
            }
        });
        var main = Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .validateProductionRuntimeSuccessor(
                        valid, acceptedMain, currentMain,
                        "learning_personalbank_main");
        assertThat(main.acceptedFileCount()).isEqualTo(40);
        assertThat(main.currentFileCount()).isEqualTo(43);
        var worm = Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .validateWormSuccessor(
                        valid,
                        "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
                        "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3");
        assertThat(worm.currentChainNodeCount()).isEqualTo(7);

        Path missingHasher = temporary.resolve("missing-hasher");
        copySemanticFixture(missingHasher);
        Files.delete(missingHasher.resolve(
                "infra/phase2/hash-java-build-context.sh"));
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateWormSuccessor(
                                missingHasher,
                                "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
                                "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("path is not regular");

        Path missingInput = temporary.resolve("missing-input");
        copySemanticFixture(missingInput);
        Files.delete(missingInput.resolve("server/pom.xml"));
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateWormSuccessor(
                                missingInput,
                                "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
                                "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("physical build-context successor");

        Path tampered = temporary.resolve("tampered-main");
        copySemanticFixture(tampered);
        Files.writeString(
                tampered.resolve(
                        "server/src/main/java/io/saksk/ti/TiApplication.java"),
                "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .validateWormSuccessor(
                                tampered,
                                "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
                                "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("physical build-context successor");
    }

    private static JsonNode contract() throws Exception {
        return Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                .load(root());
    }

    private static void copyMinimalFixture(Path targetRoot) throws Exception {
        Set<String> paths = new LinkedHashSet<>(
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .minimalFixturePaths());
        for (String relative : paths) {
            Path target = targetRoot.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(
                    root().resolve(relative),
                    target,
                    StandardCopyOption.COPY_ATTRIBUTES);
        }
    }

    private static void copySemanticFixture(Path targetRoot) throws Exception {
        Set<String> paths = new LinkedHashSet<>(
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .semanticFixturePaths(root()));
        for (String relative : paths) {
            Path target = targetRoot.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(
                    root().resolve(relative),
                    target,
                    StandardCopyOption.COPY_ATTRIBUTES);
        }
    }

    private static boolean isLearningOrPersonalBankMain(String relative) {
        return relative.startsWith(
                "server/src/main/java/io/saksk/ti/learning/")
                || relative.startsWith(
                "server/src/main/java/io/saksk/ti/personalbank/");
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }

    private static Map.Entry<String, HashPair> transition(
            String relative,
            String accepted,
            String successor) {
        return Map.entry(relative, new HashPair(accepted, successor));
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
