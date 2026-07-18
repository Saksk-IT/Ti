package io.saksk.ti.architecture;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Historical implementation validator with a target-execution bootstrap handoff. */
final class Phase4cHttpImplementationSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-contract.json";
    private static final String CONTRACT_SHA256 =
            "c6a977f260bdd0ab4af6dace1b4c7d48803b5e8f9bc5299723b662226e45cfbd";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-implementation-contract";
    private static final String CONTRACT_STATUS =
            "implementation_present_parity_incomplete_routes_pending";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-user-counts-http-implementation";
    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/personal-bank-user-counts-http-entry-contract.json";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-user-counts-http-entry-contract";
    private static final String PREDECESSOR_STATUS =
            "entry_gate_passed_http_implementation_not_started";
    private static final String PREDECESSOR_SHA256 =
            "d91d4ce6ccae982ded22a83ca9a7663042102c257565d3973b125e535f9c6676";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "ca430ec715d3b673e00f72fd8e290bed4b228970b9940864745e9c6d560a7402";
    private static final String READ_PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json";
    private static final String READ_PREDECESSOR_SHA256 =
            "458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73";
    private static final String READ_PREDECESSOR_PAYLOAD_SHA256 =
            "216cf664c4d74e67169f4f5c8091f80296964938d31911e3a32aeb3630a3d7a5";
    private static final String READ_BUILDER_RELATIVE =
            "tools/build_phase4c_personal_bank_user_counts_read_contract.py";
    private static final String READ_BUILDER_SHA256 =
            "f923257659b03ffb0fd52a60894ba5b59df3ba242cf187416bf52edda2eeb3bd";
    private static final String PREDECESSOR_RUNTIME_SHA256 =
            "145bcd8d5e662cffb87744b39b8eae03cdf5761b7fc9096d90300dd4742905dc";
    private static final String LEARNING_PERSONALBANK_SHA256 =
            "d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1";
    private static final String PUBLIC_APPLICATION_METHODS_SHA256 =
            "c3b6b2eb984c1f910605bdf08c389484e5a675969c7e4ab71e5208c40d45530d";

    // Replace only after WORM capture and final deterministic contract generation.
    private static final String TRUST_PAYLOAD_SHA256 =
            "624bb2b801a51e0fd19ae4d4583d77c6b6195355685b202b4c5ac3aa56d2cf8f";
    private static final String BRIDGE_PROVENANCE_SENTINEL =
            "<bridge-self-provenance-sha256>";
    private static final Set<String> BRIDGE_SOURCE_KEYS = Set.of(
            "python_successor_bridge", "java_successor_bridge");
    private static final String WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json";
    private static final String OWNERSHIP_PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/effective-data-ownership-status.json";
    private static final String OWNERSHIP_PREDECESSOR_SHA256 =
            "025a9f24edfb502b49e672c7c0a2e52b6bba022d6337dfe56159ebd498b69eb7";
    private static final String OWNERSHIP_DELTA_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-data-ownership-delta.csv";
    private static final String OWNERSHIP_EFFECTIVE_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-effective-data-ownership-status.json";
    private static final String OWNERSHIP_BASELINE_RELATIVE =
            "docs/refactor/03-data-ownership.csv";
    private static final String OWNERSHIP_BASELINE_SHA256 =
            "3f9cb0650c523593d7037dc24df902dbccdb3885f261f530e1725a9dc7a31748";
    private static final String OWNERSHIP_PHASE4A_RELATIVE =
            "docs/refactor/phase4a/effective-data-ownership-status.json";
    private static final String OWNERSHIP_PHASE4A_SHA256 =
            "455b45b6c838c2308b3018e690bd444b503d3493b6290fa3e5083c4f84e01127";
    private static final String OWNERSHIP_RESOURCE_NAME =
            "ti-java:learning:personal-bank-user-counts-read-rate:"
                    + "<api|web>:<identity:v1|ip:v1>:<hmac_sha256>:<second|hour|day>";
    private static final String OWNERSHIP_PREDECESSOR_MANIFEST_SHA256 =
            "76b6143812e7a352dd0c4eb515260d956ac963a26bc211f85c9bab182df45a3b";
    private static final String OWNERSHIP_EFFECTIVE_MANIFEST_SHA256 =
            "9767e2c6d6619be0db5f7b3f78335b23ff2020a9d756a2d6a3bf36eccc78908e";
    private static final Map<String, String> SOURCE_PATHS = sourcePaths();
    private static final Map<String, String> ACCEPTED_SOURCES = acceptedSources();
    private static final Map<String, String> READ_TERMINAL_ACCEPTED_SOURCES =
            readTerminalAcceptedSources();
    private static final Set<String> TARGET_EXECUTION_SUCCESSOR_PATHS = Set.of(
            "README.md",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "docs/refactor/phase4c/route-parity-delta.csv",
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py",
            "tools/phase4c_http_implementation_successor_acceptance.py",
            "tools/phase4c_read_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_"
                    + "http_implementation_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpImplementationSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cReadSuccessorAcceptance.java");
    private static final Set<String> ADDED_RUNTIME_PATHS = Set.of(
            "openapi/phase4c-personal-bank-user-counts.openapi.json",
            "server/src/main/java/io/saksk/ti/web/compat/"
                    + "LegacyPersonalBankUserCountsController.java",
            "server/src/main/java/io/saksk/ti/web/compat/"
                    + "LegacyPersonalBankUserCountsSecurityErrorWriter.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "PersonalBankUserCountsCorsConfigurationSource.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "PersonalBankUserCountsReadRateLimitFilter.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "PersonalBankUserCountsReadRateLimitProperties.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "PersonalBankUserCountsReadRateLimiter.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "PersonalBankUserCountsReadRequestResolver.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "RedisPersonalBankUserCountsReadRateLimiter.java");
    private static final Set<String> CHANGED_RUNTIME_PATHS = Set.of(
            ".env.example",
            "compose.dev.yml",
            "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "LoginRateLimitConfiguration.java",
            "server/src/main/resources/application-prod.yml",
            "server/src/main/resources/application.yml");
    private static final Set<String> FORBIDDEN_MAIN_PATHS = Set.of(
            "server/src/main/java/io/saksk/ti/identity/api/"
                    + "LegacyCredentialAuthenticationApi.java",
            "server/src/main/java/io/saksk/ti/web/security/"
                    + "TargetSessionAuthenticationFilter.java",
            "server/src/main/java/io/saksk/ti/web/request/RequestId.java",
            "server/src/main/java/io/saksk/ti/web/request/RequestIdFilter.java",
            "server/src/main/java/io/saksk/ti/web/LegacyDecimalPathInteger.java",
            "server/src/main/java/io/saksk/ti/web/error/GlobalExceptionHandler.java",
            "server/src/main/java/io/saksk/ti/web/error/SafeErrorController.java");

    private Phase4cHttpImplementationSuccessorAcceptance() {
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadImmutableContractEnvelope(root);

        JsonNode predecessor = readFixedJson(root, PREDECESSOR_RELATIVE);
        require(PREDECESSOR_SHA256.equals(sha256(
                        fixedRegularFile(root, PREDECESSOR_RELATIVE))),
                "HTTP entry predecessor physical hash drifted");
        require(PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString()),
                "HTTP entry predecessor payload field drifted");
        require(PREDECESSOR_PAYLOAD_SHA256.equals(canonicalPayloadSha256(
                        predecessor, false)),
                "HTTP entry predecessor payload is invalid");
        validateAcceptedSourcesAgainstPredecessor(predecessor);

        JsonNode readPredecessor = readFixedJson(root, READ_PREDECESSOR_RELATIVE);
        require(READ_PREDECESSOR_SHA256.equals(sha256(
                        fixedRegularFile(root, READ_PREDECESSOR_RELATIVE))),
                "read-runtime predecessor physical hash drifted");
        require(READ_PREDECESSOR_PAYLOAD_SHA256.equals(
                        readPredecessor.path("document_payload_sha256").asString()),
                "read-runtime predecessor payload field drifted");
        require(READ_PREDECESSOR_PAYLOAD_SHA256.equals(canonicalPayloadSha256(
                        readPredecessor, false)),
                "read-runtime predecessor payload is invalid");
        JsonNode readBuilderReference = readPredecessor.path("source_contracts")
                .path("contract_builder");
        require(propertyNames(readBuilderReference).equals(Set.of("source", "sha256"))
                        && READ_BUILDER_RELATIVE.equals(
                        readBuilderReference.path("source").asString())
                        && READ_BUILDER_SHA256.equals(
                        readBuilderReference.path("sha256").asString()),
                "read predecessor no longer fixes its contract builder");
        require(READ_BUILDER_SHA256.equals(sha256(
                        fixedRegularFile(root, READ_BUILDER_RELATIVE))),
                "read contract builder physical hash drifted");
        validateReadTerminalSourcesAgainstPredecessor(readPredecessor);

        validateFixedSources(root, contract);
        validateRuntimeTransition(root, contract, readPredecessor);
        validateDataOwnership(root, contract);
        validateGoldenMapping(root, contract);
        validateWorm(root, contract);
        return contract;
    }

    private static JsonNode loadImmutableContractEnvelope(Path root) throws IOException {
        require(isSha256(TRUST_PAYLOAD_SHA256),
                "unsettled HTTP implementation trust payload SHA-256");
        Path contractPath = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(CONTRACT_SHA256.equals(sha256(contractPath)),
                "HTTP implementation contract physical hash drifted");
        JsonNode contract = JSON.readTree(Files.readString(
                contractPath, StandardCharsets.UTF_8));
        validate(contract);
        return contract;
    }

    static void validate(JsonNode contract) {
        require(contract.path("schema_version").asInt() == 1,
                "unexpected HTTP implementation schema version");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString()),
                "unexpected HTTP implementation contract id");
        require(CONTRACT_STATUS.equals(contract.path("status").asString()),
                "unexpected HTTP implementation contract status");
        require(CONTRACT_SCOPE.equals(contract.path("scope").asString()),
                "unexpected HTTP implementation contract scope");
        require(contract.path("document_payload_sha256").asString().equals(
                        canonicalPayloadSha256(contract, false)),
                "invalid HTTP implementation document payload hash");

        JsonNode predecessor = contract.path("predecessor");
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "document_payload_sha256",
                        "contract_id", "status", "immutable")),
                "unexpected HTTP implementation predecessor shape");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString()),
                "unexpected HTTP entry predecessor source");
        require(PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString()),
                "HTTP entry predecessor hash drifted");
        require(PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString()),
                "HTTP entry predecessor payload drifted");
        require(PREDECESSOR_ID.equals(predecessor.path("contract_id").asString()),
                "unexpected HTTP entry predecessor id");
        require(PREDECESSOR_STATUS.equals(predecessor.path("status").asString()),
                "unexpected HTTP entry predecessor status");
        require(predecessor.path("immutable").asBoolean(),
                "HTTP entry predecessor is not immutable");

        JsonNode history = contract.path("historical_successor_acceptance");
        require(PREDECESSOR_SHA256.equals(
                        history.path("predecessor_sha256").asString()),
                "unexpected HTTP implementation historical predecessor");
        for (String flag : Set.of(
                "successor_allowlist_exact", "predecessor_rewrite_forbidden",
                "arbitrary_source_hash_lookup_forbidden",
                "bridge_self_authorization_forbidden")) {
            require(history.path(flag).asBoolean(),
                    "HTTP implementation trust flag is not closed: " + flag);
        }
        JsonNode overrides = history.path("http_entry_source_overrides");
        require(propertyNames(overrides).equals(ACCEPTED_SOURCES.keySet()),
                "unexpected HTTP implementation successor source set");
        for (Map.Entry<String, String> entry : ACCEPTED_SOURCES.entrySet()) {
            String relative = entry.getKey();
            JsonNode reference = overrides.path(relative);
            require(propertyNames(reference).equals(Set.of(
                            "source", "accepted_sha256", "successor_sha256")),
                    "unexpected HTTP implementation successor shape: " + relative);
            require(relative.equals(reference.path("source").asString()),
                    "HTTP implementation successor path drift: " + relative);
            require(entry.getValue().equals(
                            reference.path("accepted_sha256").asString()),
                    "HTTP implementation accepted hash drift: " + relative);
            require(isSha256(reference.path("successor_sha256").asString()),
                    "unsettled HTTP implementation successor hash: " + relative);
        }
        JsonNode readOverrides = history.path("read_terminal_source_overrides");
        require(propertyNames(readOverrides).equals(
                        READ_TERMINAL_ACCEPTED_SOURCES.keySet()),
                "unexpected read-terminal implementation successor set");
        for (Map.Entry<String, String> entry
                : READ_TERMINAL_ACCEPTED_SOURCES.entrySet()) {
            String relative = entry.getKey();
            JsonNode reference = readOverrides.path(relative);
            require(propertyNames(reference).equals(Set.of(
                            "source", "accepted_sha256", "successor_sha256")),
                    "unexpected read-terminal successor shape: " + relative);
            require(relative.equals(reference.path("source").asString()),
                    "read-terminal implementation successor path drift: " + relative);
            require(entry.getValue().equals(
                            reference.path("accepted_sha256").asString()),
                    "read-terminal implementation accepted hash drift: " + relative);
            require(isSha256(reference.path("successor_sha256").asString()),
                    "unsettled read-terminal implementation successor hash: " + relative);
        }

        JsonNode sources = contract.path("source_contracts");
        require(propertyNames(sources).equals(SOURCE_PATHS.keySet()),
                "unexpected HTTP implementation source contract set");
        for (Map.Entry<String, String> entry : SOURCE_PATHS.entrySet()) {
            JsonNode reference = sources.path(entry.getKey());
            require(propertyNames(reference).equals(Set.of("source", "sha256")),
                    "unexpected fixed implementation source shape: " + entry.getKey());
            require(entry.getValue().equals(reference.path("source").asString()),
                    "fixed implementation source path drift: " + entry.getKey());
            require(isSha256(reference.path("sha256").asString()),
                    "unsettled fixed implementation source hash: " + entry.getKey());
        }

        JsonNode implementation = contract.path("implementation");
        require("learning".equals(implementation.path("http_owner").asString()),
                "HTTP implementation owner drifted");
        require(("io.saksk.ti.learning.api.LearningApplicationApi"
                        + "#findPersonalBankUserCounts").equals(
                        implementation.path("application_api").asString()),
                "HTTP implementation application API drifted");
        JsonNode transition = implementation.path("production_runtime_transition");
        require(transition.path("predecessor").path("file_count").asInt() == 288,
                "unexpected HTTP implementation runtime predecessor count");
        require(PREDECESSOR_RUNTIME_SHA256.equals(transition.path("predecessor")
                        .path("manifest_sha256").asString()),
                "unexpected HTTP implementation runtime predecessor hash");
        require(transition.path("current").path("file_count").asInt() == 297,
                "unexpected HTTP implementation runtime current count");
        JsonNode delta = transition.path("exact_delta");
        require(propertyNames(delta.path("added_files")).equals(ADDED_RUNTIME_PATHS),
                "unexpected HTTP implementation added runtime paths");
        require(propertyNames(delta.path("changed_files")).equals(CHANGED_RUNTIME_PATHS),
                "unexpected HTTP implementation changed runtime paths");
        require(delta.path("deleted_file_count").asInt() == 0
                        && delta.path("deleted_files").isArray()
                        && delta.path("deleted_files").size() == 0,
                "HTTP implementation deleted predecessor runtime files");
        require(delta.path("added_file_count").asInt() == 9
                        && delta.path("new_main_source_count").asInt() == 8
                        && delta.path("new_openapi_file_count").asInt() == 1
                        && delta.path("changed_file_count").asInt() == 6
                        && delta.path("changed_main_source_count").asInt() == 2
                        && delta.path("changed_configuration_file_count").asInt() == 4,
                "HTTP implementation exact delta counts drifted");

        JsonNode modules = transition.path("learning_and_personalbank");
        require(modules.path("file_count").asInt() == 40,
                "unexpected learning/personalbank source count");
        require(LEARNING_PERSONALBANK_SHA256.equals(
                        modules.path("manifest_sha256").asString()),
                "learning/personalbank source manifest drifted");
        require(modules.path("unchanged_from_read_predecessor").asBoolean(),
                "learning/personalbank equality is not closed");
        JsonNode api = transition.path("public_application_api");
        require(api.path("method_count").asInt() == 27,
                "unexpected public application method count");
        require(PUBLIC_APPLICATION_METHODS_SHA256.equals(
                        api.path("methods_sha256").asString()),
                "public application API manifest drifted");
        require(api.path("unchanged_from_http_entry_predecessor").asBoolean(),
                "public application API equality is not closed");
        JsonNode forbidden = transition.path("forbidden_main_sources");
        require(forbidden.path("unchanged").asBoolean(),
                "forbidden main sources are not marked unchanged");
        require(propertyNames(forbidden.path("files")).equals(FORBIDDEN_MAIN_PATHS),
                "unexpected forbidden main source set");

        JsonNode routes = implementation.path("routes_and_openapi");
        require(routes.path("implemented_pending_get_count").asInt() == 2,
                "unexpected HTTP implementation pending GET count");
        require(routes.path("migrated_operation_count").asInt() == 11,
                "unexpected HTTP implementation migrated operation count");
        require(routes.path("pending_operation_count").asInt() == 600,
                "unexpected HTTP implementation pending operation count");
        require(!routes.path("route_migration_eligible").asBoolean(),
                "HTTP implementation overclaims route migration eligibility");
        require(routes.path("production_cutover_operation_count").asInt() == 0,
                "HTTP implementation overclaims production cutover");
        require(routes.path("routes").size() == 2,
                "HTTP implementation route count drifted");
        Set<String> routeIds = new LinkedHashSet<>();
        routes.path("routes").forEach(route -> {
            routeIds.add(route.path("route_id").asString());
            require("GET".equals(route.path("method").asString()),
                    "only the two legacy GET routes belong to this checkpoint");
            require("learning".equals(route.path("target_module").asString()),
                    "HTTP implementation owner drifted");
            require("pending".equals(route.path("migration_status").asString()),
                    "HTTP implementation route is not pending");
            require(!route.path("production_cutover").asBoolean(),
                    "HTTP implementation route overclaims cutover");
        });
        require(routeIds.equals(Set.of("6858f6fa506f", "006913d0d956")),
                "HTTP implementation route ids drifted");

        JsonNode ownership = contract.path("data_ownership");
        JsonNode ownershipPredecessor = ownership.path("predecessor");
        require(OWNERSHIP_PREDECESSOR_RELATIVE.equals(
                        ownershipPredecessor.path("source").asString())
                        && OWNERSHIP_PREDECESSOR_SHA256.equals(
                        ownershipPredecessor.path("sha256").asString())
                        && ownershipPredecessor.path("resource_count").asInt() == 159
                        && OWNERSHIP_PREDECESSOR_MANIFEST_SHA256.equals(
                        ownershipPredecessor.path(
                                "canonical_owner_manifest_sha256").asString())
                        && ownershipPredecessor.path("immutable").asBoolean(),
                "HTTP ownership predecessor drifted");
        JsonNode ownershipDelta = ownership.path("delta");
        require(OWNERSHIP_DELTA_RELATIVE.equals(
                        ownershipDelta.path("source").asString())
                        && isSha256(ownershipDelta.path("sha256").asString())
                        && ownershipDelta.path("new_resource_count").asInt() == 1,
                "HTTP ownership delta drifted");
        JsonNode effectiveOwnership = ownership.path("effective");
        require(OWNERSHIP_EFFECTIVE_RELATIVE.equals(
                        effectiveOwnership.path("source").asString())
                        && isSha256(effectiveOwnership.path("sha256").asString())
                        && isSha256(effectiveOwnership.path(
                        "document_payload_sha256").asString())
                        && effectiveOwnership.path("resource_count").asInt() == 160
                        && effectiveOwnership.path(
                        "resources_with_exactly_one_owner").asInt() == 160
                        && OWNERSHIP_EFFECTIVE_MANIFEST_SHA256.equals(
                        effectiveOwnership.path(
                                "canonical_owner_manifest_sha256").asString())
                        && effectiveOwnership.path(
                        "canonical_owner_manifest_recomputed").asBoolean(),
                "HTTP effective ownership drifted");
        require(effectiveOwnership.path("new_resources").size() == 1,
                "HTTP ownership new-resource count drifted");
        JsonNode ownedResource = effectiveOwnership.path("new_resources").path(0);
        require("redis_key".equals(ownedResource.path("resource_kind").asString())
                        && OWNERSHIP_RESOURCE_NAME.equals(
                        ownedResource.path("resource_name").asString())
                        && "learning".equals(ownedResource.path("owner").asString())
                        && "runtime_rate_limit".equals(
                        ownedResource.path("persistence_role").asString())
                        && !ownedResource.path("business_fact").asBoolean()
                        && !ownedResource.path("production_cutover").asBoolean(),
                "HTTP ownership resource drifted");

        JsonNode evidence = contract.path("verification_evidence");
        require(!evidence.path("real_network_tomcat").path("mock_mvc").asBoolean(),
                "real network evidence was replaced with MockMvc");
        require(strings(evidence.path("postgresql_16_14_and_18_4")
                        .path("versions")).equals(List.of("16.14", "18.4")),
                "PostgreSQL compatibility evidence drifted");
        for (String field : Set.of(
                "real_lua", "atomic_concurrency_and_ttl", "alias_isolation")) {
            require(evidence.path("redis_7").path(field).asBoolean(),
                    "Redis evidence is not closed: " + field);
        }
        JsonNode golden = evidence.path("phase4b_59_case_mapping");
        require("PARTIAL_EXECUTION_MAPPING_LEDGER".equals(
                        golden.path("claim_classification").asString()),
                "59-case mapping classification drifted");
        require(!golden.path("full_target_parity_closed").asBoolean()
                        && !golden.path("cutover_evidence").asBoolean()
                        && !golden.path("route_migration_eligible").asBoolean(),
                "59-case mapping overclaims parity, route migration, or cutover");
        require(golden.path("case_count").asInt() == 59
                        && golden.path("mockmvc_case_count").asInt() == 48
                        && golden.path("bound_only_case_count").asInt() == 11
                        && golden.path("bound_authentication_case_count").asInt() == 8
                        && golden.path("bound_typed_database_case_count").asInt() == 3,
                "59-case mapping counts drifted");
        require("P4C-LEARNING-006".equals(
                        golden.path("inherited_difference_id").asString()),
                "59-case inherited difference drifted");
        require(strings(golden.path("inherited_case_ids")).equals(List.of(
                        "access-shared-fetchone-first-row",
                        "access-shared-cross-bank-record")),
                "59-case inherited case set drifted");
        require(strings(golden.path("http_difference_ids")).equals(List.of(
                        "P4C-LEARNING-007", "P4C-LEARNING-008",
                        "P4C-LEARNING-009", "P4C-LEARNING-010",
                        "P4C-LEARNING-011", "P4C-LEARNING-012")),
                "59-case HTTP difference domain drifted");

        JsonNode adapter = evidence.path("http_adapter_security");
        require(adapter.path("mock_mvc").asBoolean(),
                "HTTP adapter evidence must remain explicitly MockMvc");
        require(!adapter.path("full_authentication_filter_chain").asBoolean(),
                "HTTP adapter evidence overclaims the authentication chain");
        require(strings(adapter.path("excluded_filters")).equals(List.of(
                        "TargetSessionAuthenticationFilter",
                        "TargetSessionReconciliationFilter")),
                "HTTP adapter excluded-filter evidence drifted");

        JsonNode authorization = contract.path("authorization");
        require(authorization.path("implementation_present").asBoolean(),
                "HTTP implementation presence is not authorized");
        require(!authorization.has("http_implementation_complete"),
                "obsolete HTTP completion claim is forbidden");
        for (String field : Set.of(
                "full_target_parity_closed", "route_migration_eligible",
                "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated",
                "identity_api_or_global_auth_filter_change",
                "learning_or_personalbank_persistence_change",
                "production_schema_or_index", "operator_migration_implementation",
                "real_data_migration_execution", "migration_global_preflight_closed",
                "client_change", "gateway_or_proxy_change", "production_cutover")) {
            require(!authorization.path(field).asBoolean(),
                    "HTTP implementation overclaims authorization: " + field);
        }
        JsonNode acceptance = contract.path("acceptance");
        for (String field : Set.of(
                "implementation_present",
                "predecessor_entry_contract_preserved",
                "exact_production_delta_verified",
                "learning_and_personalbank_sources_unchanged",
                "public_application_api_unchanged",
                "forbidden_main_sources_unchanged",
                "new_rate_limit_resource_has_one_learning_owner",
                "partial_network_postgres_redis_and_59_case_evidence_bound",
                "operator_and_real_migration_remain_blocked")) {
            require(acceptance.path(field).asBoolean(),
                    "HTTP implementation acceptance is not closed: " + field);
        }
        require(acceptance.path("effective_resource_count").asInt() == 160,
                "HTTP implementation effective resource count drifted");
        require(!acceptance.path("full_target_parity_closed").asBoolean()
                        && !acceptance.path("route_migration_eligible").asBoolean(),
                "HTTP implementation acceptance overclaims route migration");
        require(acceptance.path("implemented_pending_get_count").asInt() == 2,
                "HTTP implementation acceptance pending GET count drifted");
        require(acceptance.path("migrated_operation_count").asInt() == 11,
                "HTTP implementation acceptance migrated count drifted");
        require(acceptance.path("pending_operation_count").asInt() == 600,
                "HTTP implementation acceptance pending count drifted");
        require(acceptance.path("production_cutover_operation_count").asInt() == 0,
                "HTTP implementation acceptance overclaims cutover");
        require(("close_59_case_target_execution_and_full_authentication_chain_"
                        + "before_route_migration").equals(
                        acceptance.path("next_gate").asString()),
                "HTTP implementation next gate drifted");
        require(isSha256(TRUST_PAYLOAD_SHA256),
                "unsettled HTTP implementation trust payload SHA-256");
        require(TRUST_PAYLOAD_SHA256.equals(canonicalPayloadSha256(contract, true)),
                "HTTP implementation independent trust payload drifted");
    }

    static String acceptedHash(String relative) {
        String accepted = ACCEPTED_SOURCES.get(relative);
        return accepted != null ? accepted : READ_TERMINAL_ACCEPTED_SOURCES.get(relative);
    }

    static String successorHash(Path tiJavaRoot, String relative) throws IOException {
        String field;
        if (ACCEPTED_SOURCES.containsKey(relative)) {
            field = "http_entry_source_overrides";
        } else if (READ_TERMINAL_ACCEPTED_SOURCES.containsKey(relative)) {
            field = "read_terminal_source_overrides";
        } else {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadImmutableContractEnvelope(root);
        JsonNode reference = contract.path("historical_successor_acceptance")
                .path(field)
                .path(relative);
        require(relative.equals(reference.path("source").asString())
                        && acceptedHash(relative).equals(
                        reference.path("accepted_sha256").asString()),
                "HTTP implementation successor entry drifted: " + relative);
        String fixedSuccessor = reference.path("successor_sha256").asString();
        return validateTerminalSource(root, relative, fixedSuccessor,
                "HTTP implementation successor");
    }

    private static void validateAcceptedSourcesAgainstPredecessor(JsonNode predecessor) {
        Map<String, String> predecessorSources = new LinkedHashMap<>();
        predecessor.path("source_contracts").forEach(reference -> {
            String relative = reference.path("source").asString();
            require(predecessorSources.put(relative,
                            reference.path("sha256").asString()) == null,
                    "HTTP entry predecessor has duplicate source paths");
        });
        ACCEPTED_SOURCES.forEach((relative, accepted) -> require(
                accepted.equals(predecessorSources.get(relative)),
                "accepted hash is not fixed by HTTP entry predecessor: " + relative));
    }

    private static void validateReadTerminalSourcesAgainstPredecessor(
            JsonNode predecessor
    ) {
        Map<String, String> predecessorSources = new LinkedHashMap<>();
        predecessor.path("source_contracts").forEach(reference -> {
            String relative = reference.path("source").asString();
            require(predecessorSources.put(relative,
                            reference.path("sha256").asString()) == null,
                    "read predecessor has duplicate source paths");
        });
        READ_TERMINAL_ACCEPTED_SOURCES.forEach((relative, accepted) -> require(
                accepted.equals(predecessorSources.get(relative)),
                "accepted hash is not fixed by read predecessor: " + relative));
    }

    private static void validateFixedSources(Path root, JsonNode contract) throws IOException {
        JsonNode sources = contract.path("source_contracts");
        for (Map.Entry<String, String> entry : SOURCE_PATHS.entrySet()) {
            JsonNode reference = sources.path(entry.getKey());
            validateTerminalSource(
                    root,
                    entry.getValue(),
                    reference.path("sha256").asString(),
                    "fixed implementation source " + entry.getKey());
        }
        JsonNode overrides = contract.path("historical_successor_acceptance")
                .path("http_entry_source_overrides");
        for (String relative : ACCEPTED_SOURCES.keySet()) {
            validateTerminalSource(
                    root,
                    relative,
                    overrides.path(relative).path("successor_sha256").asString(),
                    "HTTP implementation successor override");
        }
        JsonNode readOverrides = contract.path("historical_successor_acceptance")
                .path("read_terminal_source_overrides");
        for (String relative : READ_TERMINAL_ACCEPTED_SOURCES.keySet()) {
            validateTerminalSource(
                    root,
                    relative,
                    readOverrides.path(relative).path("successor_sha256").asString(),
                    "read-terminal implementation successor override");
        }
    }

    private static String validateTerminalSource(
            Path root,
            String relative,
            String fixedSha256,
            String label
    ) throws IOException {
        String physicalSha256 = sha256(fixedRegularFile(root, relative));
        if (TARGET_EXECUTION_SUCCESSOR_PATHS.contains(relative)) {
            require(fixedSha256.equals(
                            Phase4cHttpTargetExecutionSuccessorAcceptance.acceptedHash(
                                    relative)),
                    "target-execution successor did not accept the exact " + label
                            + ": " + relative);
        } else {
            require(fixedSha256.equals(physicalSha256),
                    "unauthorized target-execution successor path for " + label
                            + ": " + relative);
        }
        if (fixedSha256.equals(physicalSha256)) {
            return physicalSha256;
        }
        String terminalSha256 =
                Phase4cHttpTargetExecutionSuccessorAcceptance.successorHash(
                        root, relative);
        require(physicalSha256.equals(terminalSha256),
                "target-execution successor file hash drift for " + relative);
        return physicalSha256;
    }

    private static void validateRuntimeTransition(
            Path root,
            JsonNode contract,
            JsonNode readPredecessor
    ) throws IOException {
        JsonNode baseline = readPredecessor.path("implementation")
                .path("production_runtime_surface");
        require(baseline.path("file_count").asInt() == 288,
                "unexpected physical read-runtime predecessor count");
        require(PREDECESSOR_RUNTIME_SHA256.equals(
                        baseline.path("manifest_sha256").asString()),
                "physical read-runtime predecessor manifest drifted");
        require(PREDECESSOR_RUNTIME_SHA256.equals(
                        canonicalNodeSha256(baseline.path("files"))),
                "invalid embedded read-runtime predecessor files");

        Map<String, String> physical = productionRuntimeManifest(root);
        JsonNode transition = contract.path("implementation")
                .path("production_runtime_transition");
        require(JSON.valueToTree(physical).equals(transition.path("current").path("files")),
                "HTTP implementation runtime manifest differs from worktree");
        require(canonicalNodeSha256(JSON.valueToTree(physical)).equals(
                        transition.path("current").path("manifest_sha256").asString()),
                "invalid HTTP implementation runtime manifest hash");

        Map<String, String> baselineFiles = textMap(baseline.path("files"));
        Map<String, String> added = new LinkedHashMap<>();
        Map<String, Map<String, String>> changed = new LinkedHashMap<>();
        List<String> deleted = new ArrayList<>();
        for (Map.Entry<String, String> entry : physical.entrySet()) {
            String oldHash = baselineFiles.get(entry.getKey());
            if (oldHash == null) {
                added.put(entry.getKey(), entry.getValue());
            } else if (!oldHash.equals(entry.getValue())) {
                changed.put(entry.getKey(), Map.of(
                        "predecessor_sha256", oldHash,
                        "successor_sha256", entry.getValue()));
            }
        }
        for (String relative : baselineFiles.keySet()) {
            if (!physical.containsKey(relative)) {
                deleted.add(relative);
            }
        }
        Collections.sort(deleted);
        JsonNode delta = transition.path("exact_delta");
        require(JSON.valueToTree(added).equals(delta.path("added_files")),
                "HTTP implementation added delta was not independently derived");
        require(JSON.valueToTree(changed).equals(delta.path("changed_files")),
                "HTTP implementation changed delta was not independently derived");
        require(JSON.valueToTree(deleted).equals(delta.path("deleted_files")),
                "HTTP implementation deleted delta was not independently derived");
        require(LEARNING_PERSONALBANK_SHA256.equals(canonicalNodeSha256(
                        transition.path("learning_and_personalbank").path("files"))),
                "invalid embedded learning/personalbank source manifest");

        JsonNode predecessorMethods = readFixedJson(root, PREDECESSOR_RELATIVE)
                .path("current_state").path("current_production_surface")
                .path("public_application_methods");
        require(predecessorMethods.equals(transition.path("public_application_api")
                        .path("methods")),
                "public application methods changed from HTTP entry");
        for (String relative : FORBIDDEN_MAIN_PATHS) {
            require(transition.path("forbidden_main_sources").path("files")
                            .path(relative).asString().equals(physical.get(relative)),
                    "forbidden main source drifted: " + relative);
        }
    }

    private static void validateDataOwnership(Path root, JsonNode contract)
            throws IOException {
        Path predecessor = fixedRegularFile(root, OWNERSHIP_PREDECESSOR_RELATIVE);
        require(OWNERSHIP_PREDECESSOR_SHA256.equals(sha256(predecessor)),
                "HTTP ownership predecessor physical hash drifted");
        JsonNode predecessorDocument = readFixedJson(
                root, OWNERSHIP_PREDECESSOR_RELATIVE);
        require(predecessorDocument.path("document_payload_sha256").asString().equals(
                        canonicalPayloadSha256(predecessorDocument, false)),
                "HTTP ownership predecessor payload is invalid");
        validateCanonicalOwnerManifest(root, predecessorDocument);

        Path delta = fixedRegularFile(root, OWNERSHIP_DELTA_RELATIVE);
        String expectedDelta = "resource_kind,resource_name,base_resource,phase4c_owner,"
                + "persistence_role,lifecycle,evidence,production_cutover\n"
                + "redis_key," + OWNERSHIP_RESOURCE_NAME
                + ",false,learning,runtime_rate_limit,endpoint-isolated first-hit fixed "
                + "windows; HMAC pseudonym only; integer counters with bounded PTTL,"
                + "RedisPersonalBankUserCountsReadRateLimiter + "
                + "RedisPersonalBankUserCountsReadRateLimiterIT + "
                + "LegacyPersonalBankUserCountsNetworkIT,false\n";
        require(expectedDelta.equals(Files.readString(delta, StandardCharsets.UTF_8)),
                "HTTP ownership delta content drifted");
        require(sha256(delta).equals(contract.path("data_ownership")
                        .path("delta").path("sha256").asString()),
                "HTTP ownership delta physical hash drifted");

        Path effectivePath = fixedRegularFile(root, OWNERSHIP_EFFECTIVE_RELATIVE);
        JsonNode effective = readFixedJson(root, OWNERSHIP_EFFECTIVE_RELATIVE);
        require(sha256(effectivePath).equals(contract.path("data_ownership")
                        .path("effective").path("sha256").asString()),
                "HTTP effective ownership physical hash drifted");
        require("ti.phase4c.personal-bank-user-counts-http-"
                        .concat("effective-data-ownership-status").equals(
                        effective.path("contract_id").asString())
                        && effective.path("schema_version").asInt() == 1,
                "HTTP effective ownership identity drifted");
        require(effective.path("document_payload_sha256").asString().equals(
                        canonicalPayloadSha256(effective, false)),
                "HTTP effective ownership payload is invalid");
        JsonNode effectivePredecessor = effective.path("predecessor");
        require("effective-data-ownership-status.json".equals(
                        effectivePredecessor.path("source").asString())
                        && OWNERSHIP_PREDECESSOR_SHA256.equals(
                        effectivePredecessor.path("sha256").asString())
                        && effectivePredecessor.path("resource_count").asInt() == 159
                        && OWNERSHIP_PREDECESSOR_MANIFEST_SHA256.equals(
                        effectivePredecessor.path(
                                "canonical_owner_manifest_sha256").asString())
                        && effectivePredecessor.path("immutable").asBoolean(),
                "HTTP effective ownership predecessor drifted");
        require(effective.path("delta").path("sha256").asString().equals(sha256(delta))
                        && OWNERSHIP_DELTA_RELATIVE.substring(
                        OWNERSHIP_DELTA_RELATIVE.lastIndexOf('/') + 1).equals(
                        effective.path("delta").path("source").asString())
                        && effective.path("delta").path(
                        "new_resource_count").asInt() == 1,
                "HTTP effective ownership delta drifted");
        JsonNode effectiveState = effective.path("effective");
        JsonNode effectiveReference = contract.path("data_ownership").path("effective");
        require(effective.path("document_payload_sha256").asString().equals(
                        effectiveReference.path(
                        "document_payload_sha256").asString()),
                "HTTP effective ownership payload reference drifted");
        require(effectiveState.path("resource_count").asInt() == 160
                        && effectiveState.path(
                        "resources_with_exactly_one_owner").asInt() == 160
                        && OWNERSHIP_EFFECTIVE_MANIFEST_SHA256.equals(
                        effectiveState.path(
                                "canonical_owner_manifest_sha256").asString())
                        && effectiveState.path("new_resources").equals(
                        effectiveReference.path("new_resources")),
                "HTTP effective ownership content differs from contract");
    }

    private static void validateCanonicalOwnerManifest(
            Path root, JsonNode predecessor) throws IOException {
        Path phase4aPath = fixedRegularFile(root, OWNERSHIP_PHASE4A_RELATIVE);
        require(OWNERSHIP_PHASE4A_SHA256.equals(sha256(phase4aPath)),
                "Phase4A ownership status physical hash drifted");
        JsonNode predecessorReference = predecessor.path("predecessor");
        require("../phase4a/effective-data-ownership-status.json".equals(
                        predecessorReference.path("source").asString())
                        && OWNERSHIP_PHASE4A_SHA256.equals(
                        predecessorReference.path("sha256").asString())
                        && predecessorReference.path("resource_count").asInt() == 159
                        && predecessorReference.path("immutable").asBoolean(),
                "Phase4C ownership predecessor link drifted");

        JsonNode phase4a = readFixedJson(root, OWNERSHIP_PHASE4A_RELATIVE);
        require("ti.phase4a.effective-data-ownership-status".equals(
                        phase4a.path("contract_id").asString()),
                "unexpected Phase4A ownership status id");
        JsonNode baselineReference = phase4a.path("baseline");
        require("../03-data-ownership.csv".equals(
                        baselineReference.path("source").asString())
                        && OWNERSHIP_BASELINE_SHA256.equals(
                        baselineReference.path("sha256").asString())
                        && baselineReference.path("resource_count").asInt() == 154
                        && baselineReference.path("immutable").asBoolean(),
                "Phase4A ownership baseline link drifted");
        JsonNode phase4aEffective = phase4a.path("effective");
        require(phase4aEffective.path("resource_count").asInt() == 159
                        && phase4aEffective.path(
                        "resources_with_exactly_one_owner").asInt() == 159,
                "Phase4A ownership is not uniquely owned");

        Path baselinePath = fixedRegularFile(root, OWNERSHIP_BASELINE_RELATIVE);
        require(OWNERSHIP_BASELINE_SHA256.equals(sha256(baselinePath)),
                "ownership baseline physical hash drifted");
        List<String> lines = Files.readAllLines(baselinePath, StandardCharsets.UTF_8);
        require(!lines.isEmpty(), "ownership baseline is empty");
        List<String> header = parseCsvLine(lines.getFirst());
        require(header.size() == 9
                        && "resource_kind".equals(header.get(0))
                        && "resource_name".equals(header.get(1))
                        && "target_owner".equals(header.get(4)),
                "ownership baseline header drifted");
        Map<String, String> owners = new TreeMap<>();
        for (String line : lines.subList(1, lines.size())) {
            if (line.isBlank()) {
                continue;
            }
            List<String> columns = parseCsvLine(line);
            require(columns.size() == 9, "ownership baseline row shape drifted");
            putUniqueOwner(owners, columns.get(0), columns.get(1), columns.get(4));
        }
        require(owners.size() == 154,
                "unexpected ownership baseline resource count");

        JsonNode phase4aNew = phase4aEffective.path("new_resources");
        require(phase4aNew.isArray() && phase4aNew.size() == 5,
                "unexpected Phase4A ownership additions");
        phase4aNew.forEach(resource -> putUniqueOwner(
                owners,
                resource.path("resource_kind").asString(),
                resource.path("resource_name").asString(),
                resource.path("owner").asString()));
        require(owners.size() == 159,
                "Phase4A effective ownership count mismatch");

        JsonNode overrides = predecessor.path("effective").path("owner_overrides");
        require(overrides.isArray() && overrides.size() == 1,
                "unexpected Phase4C ownership override count");
        JsonNode override = overrides.path(0);
        require("db_kv_namespace".equals(
                        override.path("resource_kind").asString())
                        && "bank_<bank_id>_tags".equals(
                        override.path("resource_name").asString())
                        && "personalbank".equals(
                        override.path("base_owner").asString())
                        && "learning".equals(override.path("owner").asString())
                        && !override.path("production_cutover").asBoolean(),
                "unexpected Phase4C ownership override");
        String overrideKey = ownerKey("db_kv_namespace", "bank_<bank_id>_tags");
        require("personalbank".equals(owners.get(overrideKey)),
                "Phase4C ownership override base owner drifted");
        owners.put(overrideKey, "learning");
        require(OWNERSHIP_PREDECESSOR_MANIFEST_SHA256.equals(
                        canonicalNodeSha256(ownerManifestNode(owners))),
                "recomputed Phase4C predecessor owner manifest drifted");

        String newKey = ownerKey("redis_key", OWNERSHIP_RESOURCE_NAME);
        require(!owners.containsKey(newKey),
                "HTTP rate-limit ownership resource collides with predecessor");
        owners.put(newKey, "learning");
        require(owners.size() == 160,
                "HTTP effective ownership count mismatch");
        require(OWNERSHIP_EFFECTIVE_MANIFEST_SHA256.equals(
                        canonicalNodeSha256(ownerManifestNode(owners))),
                "recomputed HTTP effective owner manifest drifted");
    }

    private static void validateGoldenMapping(Path root, JsonNode contract)
            throws IOException {
        JsonNode mapping = readFixedJson(root,
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-golden-target-mapping-evidence.json");
        JsonNode golden = readFixedJson(root,
                "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json");
        require("PARTIAL_EXECUTION_MAPPING_LEDGER".equals(
                        mapping.path("claim").path("classification").asString()),
                "physical 59-case mapping classification drifted");
        require(!mapping.path("claim").path("full_target_parity_closed").asBoolean(),
                "physical 59-case mapping overclaims target parity");
        require(!mapping.path("claim").path("cutover_evidence").asBoolean(),
                "physical 59-case mapping overclaims cutover evidence");
        require(!mapping.path("claim").path("route_migration_eligible").asBoolean(),
                "physical 59-case mapping overclaims route migration eligibility");
        List<String> mappingIds = new ArrayList<>();
        mapping.path("cases").forEach(item -> mappingIds.add(
                item.path("case_id").asString()));
        List<String> goldenIds = new ArrayList<>();
        golden.path("cases").forEach(item -> goldenIds.add(
                item.path("case_id").asString()));
        require(mappingIds.equals(goldenIds) && new LinkedHashSet<>(mappingIds).size() == 59,
                "physical 59-case mapping case ids drifted");
        JsonNode physicalSummary = mapping.path("summary");
        require(physicalSummary.path("case_count").asInt() == 59
                        && physicalSummary.path("mockmvc_case_count").asInt() == 48
                        && physicalSummary.path("bound_only_case_count").asInt() == 11
                        && physicalSummary.path("bound_authentication_case_count").asInt() == 8
                        && physicalSummary.path("bound_typed_database_case_count").asInt() == 3,
                "physical 59-case mapping counts drifted");

        Set<String> allowed = Set.of(
                "P4C-LEARNING-007", "P4C-LEARNING-008",
                "P4C-LEARNING-009", "P4C-LEARNING-010",
                "P4C-LEARNING-011", "P4C-LEARNING-012");
        List<String> inheritedCases = new ArrayList<>();
        mapping.path("cases").forEach(item -> {
            List<String> differences = strings(item.path("http_slice_difference_ids"));
            require(new LinkedHashSet<>(differences).size() == differences.size(),
                    "physical 59-case mapping repeats an HTTP difference");
            require(allowed.containsAll(differences),
                    "physical 59-case mapping has an unapproved HTTP difference");
            require(!differences.contains("P4C-LEARNING-006"),
                    "P4C-LEARNING-006 escaped inherited-only position");
            if (item.has("inherited_predecessor_difference_id")) {
                require("P4C-LEARNING-006".equals(item
                                .path("inherited_predecessor_difference_id").asString()),
                        "physical 59-case inherited difference drifted");
                inheritedCases.add(item.path("case_id").asString());
            }
        });
        require(inheritedCases.equals(List.of(
                        "access-shared-fetchone-first-row",
                        "access-shared-cross-bank-record")),
                "physical 59-case inherited case set drifted");
        JsonNode summary = contract.path("verification_evidence")
                .path("phase4b_59_case_mapping");
        require(strings(summary.path("inherited_case_ids")).equals(inheritedCases),
                "contract and physical inherited case sets differ");
    }

    private static void validateWorm(Path root, JsonNode contract) throws IOException {
        JsonNode reference = contract.path("worm_evidence");
        require(WORM_RELATIVE.equals(reference.path("source").asString()),
                "unexpected HTTP implementation WORM path");
        Path path = fixedRegularFile(root, WORM_RELATIVE);
        require(reference.path("sha256").asString().equals(sha256(path)),
                "HTTP implementation WORM hash drifted");
        JsonNode worm = readFixedJson(root, WORM_RELATIVE);
        require(worm.path("java").path("buildContextSha256").asString().equals(
                        contract.path("implementation")
                                .path("java_build_context_sha256").asString()),
                "HTTP implementation WORM build context drifted");
        JsonNode fixedChain = reference.path("fixed_phase2_chain");
        require(fixedChain.path("node_count").asInt() == 5,
                "HTTP implementation fixed WORM chain length drifted");
        require("phase4c-personal-bank-user-counts-http-implementation".equals(
                        fixedChain.path("tip_label").asString()),
                "HTTP implementation fixed WORM tip label drifted");
        require(reference.path("sha256").asString().equals(
                        fixedChain.path("tip_sha256").asString()),
                "HTTP implementation fixed WORM tip digest drifted");
        require("a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"
                        .equals(fixedChain.path("predecessor_sha256").asString()),
                "HTTP implementation fixed WORM predecessor drifted");
        require(sha256(fixedRegularFile(root, "server/Dockerfile")).equals(
                        fixedChain.path("dockerfile_sha256").asString()),
                "HTTP implementation fixed WORM Dockerfile drifted");
        require(contract.path("implementation").path("java_build_context_sha256")
                        .asString().equals(
                                fixedChain.path("java_build_context_sha256").asString()),
                "HTTP implementation fixed WORM build context drifted");
        for (String field : Set.of(
                "production_schema_or_index_changed", "operator_migration_executed",
                "real_data_migration_executed", "production_cutover")) {
            require(!reference.path(field).asBoolean(),
                    "HTTP implementation WORM overclaims " + field);
        }
    }

    private static String ownerKey(String kind, String name) {
        require(kind != null && !kind.isBlank()
                        && name != null && !name.isBlank(),
                "ownership resource key is blank");
        return kind + '\0' + name;
    }

    private static void putUniqueOwner(
            Map<String, String> owners,
            String kind,
            String name,
            String owner) {
        require(owner != null && !owner.isBlank(),
                "ownership resource owner is blank");
        String previous = owners.put(ownerKey(kind, name), owner.trim());
        require(previous == null,
                "ownership resource collides with an existing resource");
    }

    private static JsonNode ownerManifestNode(Map<String, String> owners) {
        var manifest = JSON.createArrayNode();
        owners.forEach((key, owner) -> {
            int separator = key.indexOf('\0');
            require(separator > 0 && separator < key.length() - 1,
                    "invalid canonical ownership key");
            var resource = JSON.createObjectNode();
            resource.put("resource_kind", key.substring(0, separator));
            resource.put("resource_name", key.substring(separator + 1));
            resource.put("owner", owner);
            manifest.add(resource);
        });
        return manifest;
    }

    private static List<String> parseCsvLine(String line) {
        List<String> columns = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int index = 0; index < line.length(); index++) {
            char character = line.charAt(index);
            if (character == '"') {
                if (quoted && index + 1 < line.length()
                        && line.charAt(index + 1) == '"') {
                    current.append('"');
                    index++;
                } else {
                    quoted = !quoted;
                }
            } else if (character == ',' && !quoted) {
                columns.add(current.toString());
                current.setLength(0);
            } else {
                current.append(character);
            }
        }
        require(!quoted, "unterminated ownership CSV quote");
        columns.add(current.toString());
        return List.copyOf(columns);
    }

    private static Map<String, String> productionRuntimeManifest(Path root)
            throws IOException {
        Map<String, String> manifest = new LinkedHashMap<>();
        for (String relative : List.of(
                "server/src/main", "server/pom.xml", "server/Dockerfile",
                "server/.dockerignore", "server/.mvn", "server/mvnw",
                "server/mvnw.cmd", "server/build-versions.properties",
                "compose.dev.yml", ".env.example", "contracts", "openapi")) {
            addManifestPath(root, relative, manifest);
        }
        return manifest.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .collect(
                        LinkedHashMap::new,
                        (map, entry) -> map.put(entry.getKey(), entry.getValue()),
                        LinkedHashMap::putAll);
    }

    private static void addManifestPath(
            Path root,
            String relative,
            Map<String, String> manifest
    ) throws IOException {
        Path path = fixedPath(root, relative);
        if (Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) {
            manifest.put(relative, sha256(path));
            return;
        }
        require(Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS),
                "runtime manifest source is not file/directory: " + relative);
        try (var paths = Files.walk(path)) {
            for (Path child : paths.sorted().toList()) {
                require(!Files.isSymbolicLink(child),
                        "runtime manifest contains symlink: " + child);
                if (Files.isRegularFile(child, LinkOption.NOFOLLOW_LINKS)) {
                    manifest.put(root.relativize(child).toString().replace('\\', '/'),
                            sha256(child));
                }
            }
        }
    }

    private static JsonNode readFixedJson(Path root, String relative) throws IOException {
        return JSON.readTree(Files.readString(
                fixedRegularFile(root, relative), StandardCharsets.UTF_8));
    }

    private static Path fixedRegularFile(Path root, String relative) throws IOException {
        Path path = fixedPath(root, relative);
        require(Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS),
                "fixed implementation path is not a regular file: " + relative);
        return path;
    }

    private static Path fixedPath(Path root, String relative) throws IOException {
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute() && !relative.contains(".."),
                "fixed implementation path escapes Ti-Java: " + relative);
        Path cursor = root;
        for (Path part : candidate) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "fixed implementation path contains symlink: " + relative);
        }
        Path resolved = root.resolve(candidate).normalize().toRealPath();
        require(resolved.startsWith(root),
                "fixed implementation path resolves outside Ti-Java: " + relative);
        return resolved;
    }

    private static String sha256(Path path) throws IOException {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(Files.readAllBytes(path)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static String canonicalNodeSha256(JsonNode node) {
        StringBuilder canonical = new StringBuilder();
        appendCanonical(node, canonical, "", false, false);
        return sha256(canonical.toString());
    }

    private static String canonicalPayloadSha256(JsonNode contract, boolean trust) {
        StringBuilder canonical = new StringBuilder();
        appendCanonical(contract, canonical, "", trust, true);
        return sha256(canonical.toString());
    }

    private static void appendCanonical(
            JsonNode node,
            StringBuilder output,
            String path,
            boolean trust,
            boolean omitDocumentPayloadAtRoot
    ) {
        if (node.isObject()) {
            List<String> names = new ArrayList<>(propertyNames(node));
            if (path.isEmpty() && omitDocumentPayloadAtRoot) {
                names.remove("document_payload_sha256");
            }
            Collections.sort(names);
            output.append('{');
            boolean first = true;
            for (String name : names) {
                if (!first) {
                    output.append(',');
                }
                first = false;
                appendJsonString(name, output);
                output.append(':');
                String childPath = path + "/" + name;
                if (trust && bridgeSourceHashPath(childPath)) {
                    appendJsonString(BRIDGE_PROVENANCE_SENTINEL, output);
                } else {
                    appendCanonical(node.path(name), output, childPath, trust, false);
                }
            }
            output.append('}');
            return;
        }
        if (node.isArray()) {
            output.append('[');
            for (int index = 0; index < node.size(); index++) {
                if (index > 0) {
                    output.append(',');
                }
                appendCanonical(node.path(index), output, path + "/" + index, trust, false);
            }
            output.append(']');
            return;
        }
        if (node.isTextual()) {
            appendJsonString(node.asString(), output);
        } else if (node.isNull()) {
            output.append("null");
        } else {
            output.append(node.toString());
        }
    }

    private static boolean bridgeSourceHashPath(String path) {
        for (String key : BRIDGE_SOURCE_KEYS) {
            if (path.equals("/source_contracts/" + key + "/sha256")) {
                return true;
            }
        }
        return false;
    }

    private static void appendJsonString(String value, StringBuilder output) {
        output.append('"');
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            switch (character) {
                case '"' -> output.append("\\\"");
                case '\\' -> output.append("\\\\");
                case '\b' -> output.append("\\b");
                case '\f' -> output.append("\\f");
                case '\n' -> output.append("\\n");
                case '\r' -> output.append("\\r");
                case '\t' -> output.append("\\t");
                default -> {
                    if (character < 0x20) {
                        output.append("\\u").append(String.format("%04x", (int) character));
                    } else {
                        output.append(character);
                    }
                }
            }
        }
        output.append('"');
    }

    private static String sha256(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static Set<String> propertyNames(JsonNode node) {
        return Set.copyOf(node.propertyNames());
    }

    private static List<String> strings(JsonNode array) {
        List<String> values = new ArrayList<>();
        array.forEach(item -> values.add(item.asString()));
        return List.copyOf(values);
    }

    private static Map<String, String> textMap(JsonNode object) {
        Map<String, String> values = new LinkedHashMap<>();
        List<String> names = new ArrayList<>(propertyNames(object));
        Collections.sort(names);
        names.forEach(name -> values.put(name, object.path(name).asString()));
        return values;
    }

    private static boolean isSha256(String value) {
        return value != null && value.matches("[0-9a-f]{64}");
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static Map<String, String> sourcePaths() {
        Map<String, String> sources = new LinkedHashMap<>();
        sources.put("predecessor", PREDECESSOR_RELATIVE);
        sources.put("read_predecessor", READ_PREDECESSOR_RELATIVE);
        sources.put("read_contract_builder", READ_BUILDER_RELATIVE);
        sources.put("phase4b_goldens",
                "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json");
        sources.put("http_boundary_evidence",
                "docs/refactor/phase4c/personal-bank-user-counts-http-boundary-evidence.json");
        sources.put("rate_limit_evidence",
                "docs/refactor/phase4c/personal-bank-user-counts-rate-limit-evidence.json");
        sources.put("golden_target_evidence",
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-golden-target-mapping-evidence.json");
        sources.put("worm_tip", WORM_RELATIVE);
        sources.put("openapi_overlay",
                "openapi/phase4c-personal-bank-user-counts.openapi.json");
        sources.put("route_delta", "docs/refactor/phase4c/route-parity-delta.csv");
        sources.put("ownership_predecessor", OWNERSHIP_PREDECESSOR_RELATIVE);
        sources.put("ownership_baseline", OWNERSHIP_BASELINE_RELATIVE);
        sources.put("ownership_phase4a", OWNERSHIP_PHASE4A_RELATIVE);
        sources.put("ownership_delta", OWNERSHIP_DELTA_RELATIVE);
        sources.put("ownership_effective", OWNERSHIP_EFFECTIVE_RELATIVE);
        sources.put("network_it",
                "server/src/test/java/io/saksk/ti/integration/"
                        + "LegacyPersonalBankUserCountsNetworkIT.java");
        sources.put("postgres_it",
                "server/src/test/java/io/saksk/ti/integration/"
                        + "Phase4cPersonalBankUserCountsJdbcCompatibilityIT.java");
        sources.put("redis_it",
                "server/src/test/java/io/saksk/ti/web/security/"
                        + "RedisPersonalBankUserCountsReadRateLimiterIT.java");
        sources.put("golden_target_test",
                "server/src/test/java/io/saksk/ti/web/compat/"
                        + "LegacyPersonalBankUserCountsGoldenTargetMappingTest.java");
        sources.put("http_adapter_security_test",
                "server/src/test/java/io/saksk/ti/web/compat/"
                        + "LegacyPersonalBankUserCountsHttpTest.java");
        sources.put("controller_unit_test",
                "server/src/test/java/io/saksk/ti/web/compat/"
                        + "LegacyPersonalBankUserCountsControllerTest.java");
        sources.put("security_error_writer_unit_test",
                "server/src/test/java/io/saksk/ti/web/compat/"
                        + "LegacyPersonalBankUserCountsSecurityErrorWriterTest.java");
        sources.put("cors_configuration_unit_test",
                "server/src/test/java/io/saksk/ti/web/security/"
                        + "PersonalBankUserCountsCorsConfigurationSourceTest.java");
        sources.put("rate_limit_filter_unit_test",
                "server/src/test/java/io/saksk/ti/web/security/"
                        + "PersonalBankUserCountsReadRateLimitFilterTest.java");
        sources.put("rate_limit_properties_unit_test",
                "server/src/test/java/io/saksk/ti/web/security/"
                        + "PersonalBankUserCountsReadRateLimitPropertiesTest.java");
        sources.put("request_resolver_unit_test",
                "server/src/test/java/io/saksk/ti/web/security/"
                        + "PersonalBankUserCountsReadRequestResolverTest.java");
        sources.put("redis_rate_limiter_unit_test",
                "server/src/test/java/io/saksk/ti/web/security/"
                        + "RedisPersonalBankUserCountsReadRateLimiterTest.java");
        sources.put("user_counts_rate_limit_secret_example",
                "infra/phase2/secrets/"
                        + "ti-personal-bank-user-counts-rate-limit-key-secret.example");
        sources.put("openapi_route_contract_test",
                "tools/test_phase4c_personal_bank_user_counts_openapi_route_contract.py");
        sources.put("contract_builder",
                "tools/build_phase4c_personal_bank_user_counts_http_implementation_contract.py");
        sources.put("contract_test",
                "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py");
        sources.put("python_successor_bridge",
                "tools/phase4c_http_implementation_successor_acceptance.py");
        sources.put("java_successor_bridge",
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpImplementationSuccessorAcceptance.java");
        sources.put("java_contract_parity_test",
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cPersonalBankUserCountsHttpImplementationContractParityTest.java");
        sources.put("phase2_worm_validator",
                "tools/phase2_wormhole_successor_acceptance.py");
        sources.put("phase2_worm_validator_test",
                "tools/test_phase2_wormhole_successor_acceptance.py");
        sources.put("phase2_worm_runner",
                "infra/phase2/verify-local-reference-wormhole.sh");
        sources.put("phase2_static_gate", "infra/phase2/verify-static.sh");
        sources.put("phase2_worm_readme", "infra/phase2/README.md");
        sources.put("phase2_reference_drift_manifest",
                "infra/phase2/reference-drift-manifest.json");
        sources.put("phase2_build_context_hasher",
                "infra/phase2/hash-java-build-context.sh");
        sources.put("java_dockerfile", "server/Dockerfile");
        sources.put("historical_phase4b_entry_contract_test",
                "tools/test_phase4b_personal_bank_user_counts_entry_contract.py");
        sources.put("historical_python_read_successor_bridge",
                "tools/phase4c_read_successor_acceptance.py");
        return Map.copyOf(sources);
    }

    private static Map<String, String> acceptedSources() {
        Map<String, String> sources = new LinkedHashMap<>();
        sources.put("README.md",
                "3d18a7b86354b8cad4d54a76a9a3722435dd570b612a5a9e65ca9a4aed2864b6");
        sources.put("docs/refactor/05-progress.md",
                "f44a6efdec4342f13ea1f28831bdca9b36b84f48e932bd4f1d257070af555c7e");
        sources.put("docs/refactor/phase4c/README.md",
                "07852f793ed84c90212c5b52dedcf82ed9b52ce9b229e35c56c94eafea253a8b");
        sources.put("tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py",
                "fdbf282f7be37e6138702e973bf67737c940e7944ac6103f8954902d5b8621e4");
        sources.put("tools/phase4c_http_entry_successor_acceptance.py",
                "f66bdc4746f3ee720bfc13213e24c44e30140d4b0f311d2f8a53cd01b8e90f11");
        sources.put("tools/phase4c_read_successor_acceptance.py",
                "8b4a57393021a304640797cc64a7f4d44aad83ab6d57c50d81f8158aa9008f82");
        sources.put("server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpEntrySuccessorAcceptance.java",
                "57930b46f1bcd0f0df4bedce1fb41de7b63c53f58b3a45eae49ab858ea1c277a");
        sources.put("server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cReadSuccessorAcceptance.java",
                "8a008483f70788ffc10158ae789b7b318e8478ad249514f0551d8b0361dcf52b");
        sources.put("tools/test_phase4c_personal_bank_user_counts_read_contract.py",
                "6d493304cc01fcbc801b066700b98bb6b0a1750ee9e3d9ce03867ee6e92991cc");
        sources.put("tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
                "c08ff0263d0da2c4e08733685256d7946a316a06772b8959c3520cc7947aaa76");
        sources.put("server/src/main/java/io/saksk/ti/web/config/"
                        + "SecurityConfiguration.java",
                "aaf0b5cd5431dbaa6033bae195dcd42d04c3000d3c3f9ce1083abac54b18cb5a");
        sources.put("server/src/main/java/io/saksk/ti/web/security/"
                        + "LoginRateLimitConfiguration.java",
                "e681903ee752b3452bdbe5e7a4f2e93f60f95c7b34c77e6f1e552a7e891c08fe");
        sources.put("server/src/main/resources/application.yml",
                "c760cebe37e4433874c1171782163a3572e92a73c565120b0fa2a52d45a40c5e");
        sources.put("server/src/main/resources/application-prod.yml",
                "c7a804c93e0937676c4f398899700830df854bdcc404cc72361423d92525ce3f");
        return Map.copyOf(sources);
    }

    private static Map<String, String> readTerminalAcceptedSources() {
        return Map.of(
                "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
                "590f4d62c45c4fc9fdde9332f2de376f62481b672120c72389071e4a8bf334a7");
    }
}
