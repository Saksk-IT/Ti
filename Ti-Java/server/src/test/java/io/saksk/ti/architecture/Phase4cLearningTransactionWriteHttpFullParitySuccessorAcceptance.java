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
import java.util.Set;
import java.util.TreeMap;

/** Gitless Java bridge for the transaction-write full-parity bootstrap. */
final class Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-http-full-parity-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.learning-transaction-write-http-full-parity-contract";
    private static final String CONTRACT_SHA256 =
            "40b38a443d7f7d754cc42ce43fa854b0c3c18dc66f4920a2f07d451601d6d1db";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "83ca7d51d768540ed744830c74f07eb1fd1f63db88c293ea4ec83e41d6a6c1e1";
    private static final long CONTRACT_BYTE_COUNT = 15_604L;
    private static final String NODE_D_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-execution-protocol-contract.json";
    private static final String NODE_D_SHA256 =
            "e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14";
    private static final long NODE_D_BYTE_COUNT = 44_336L;
    private static final String NODE_D_ANCHOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-execution-protocol-"
                    + "post-push-anchor-contract.json";
    private static final String NODE_D_ANCHOR_SHA256 =
            "a6dff0717d0da91091f50cb7a51d35ffc66db364e966c568fec40bdb3ca936cd";
    private static final long NODE_D_ANCHOR_BYTE_COUNT = 80_324L;
    private static final String BASE_CHECKPOINT =
            "2579dfd344dbe318c9fb59d067c843356b98fece";
    private static final String IMPLEMENTATION_CHECKPOINT =
            "b635d1db3b9d71698d9a40cc729a215d67a6906f";
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
    private static final Set<String> EVIDENCE_PATHS = Set.of(
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-implementation-contract.json",
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-implementation-post-push-anchor.json",
            "openapi/phase4c-learning-transaction-write.openapi.json",
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-http-worm-evidence.json",
            "docs/refactor/phase4c/"
                    + "learning-transaction-write-http-effective-data-ownership-status.json",
            "server/src/test/java/io/saksk/ti/integration/"
                    + "LegacyTransactionWriteRealTomcatIT.java",
            "server/src/test/java/io/saksk/ti/integration/"
                    + "LegacyTransactionWritePostgres16IT.java",
            "server/src/test/java/io/saksk/ti/web/security/"
                    + "RedisTransactionWriteRateLimiterIT.java");

    private Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance() {
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
                "transaction-write full-parity contract identity drifted");
        validatePredecessor(
                contract.path("predecessor"), contract, root);
        validateTransitions(
                contract.path("historical_source_successors"), root);
        validateEvidence(contract.path("fixed_evidence"), root);
        validateParityAndAuthorization(contract);
        return contract;
    }

    static JsonNode loadNodeDPredecessor(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        load(root);
        return readFixedJson(
                root, NODE_D_RELATIVE, NODE_D_SHA256, NODE_D_BYTE_COUNT);
    }

    static SourceTransition sourceTransition(Path tiJavaRoot, String relative)
            throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = load(root);
        JsonNode descriptor = contract.path("historical_source_successors")
                .path("transitions").path(relative);
        if (descriptor.isMissingNode()) {
            return null;
        }
        require(propertyNames(descriptor).equals(Set.of(
                        "source", "accepted_sha256", "accepted_byte_count",
                        "successor_sha256", "successor_byte_count")),
                "transaction-write full-parity transition shape drifted: "
                        + relative);
        SourceTransition transition = transition(descriptor);
        Path physical = fixedRegularFile(root, relative);
        require(relative.equals(transition.source())
                        && Files.size(physical)
                        == transition.successorByteCount()
                        && sha256(physical).equals(
                        transition.successorSha256()),
                "transaction-write full-parity transition bytes drifted: "
                        + relative);
        return transition;
    }

    static SourceTransition transitionFromNodeD(
            Path tiJavaRoot,
            String relative,
            String acceptedSha256,
            long acceptedByteCount
    ) throws IOException {
        SourceTransition transition = sourceTransition(tiJavaRoot, relative);
        if (transition == null) {
            return null;
        }
        require(acceptedSha256.equals(transition.acceptedSha256())
                        && acceptedByteCount
                        == transition.acceptedByteCount(),
                "transaction-write full-parity Node D origin drifted: "
                        + relative);
        return transition;
    }

    static String acceptedSha256(Path tiJavaRoot, String relative)
            throws IOException {
        SourceTransition transition = sourceTransition(tiJavaRoot, relative);
        return transition == null ? null : transition.acceptedSha256();
    }

    static String successorSha256(Path tiJavaRoot, String relative)
            throws IOException {
        SourceTransition transition = sourceTransition(tiJavaRoot, relative);
        return transition == null ? null : transition.successorSha256();
    }

    static void validateCurrentBuildContext(
            Path tiJavaRoot, String physicalBuildContextSha256
    ) throws IOException {
        JsonNode evidence = load(tiJavaRoot).path("fixed_evidence");
        require(physicalBuildContextSha256.equals(evidence.path(
                        "java_build_context_sha256").asString())
                        && evidence.path("worm_chain_node_count").asInt() == 10,
                "transaction-write full-parity build-context drifted");
    }

    static Set<String> minimalFixturePaths(Path tiJavaRoot)
            throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = load(root);
        require(propertyNames(contract.path("historical_source_successors")
                        .path("transitions")).equals(TRANSITION_PATHS)
                        && propertyNames(contract.path("fixed_evidence")
                        .path("artifacts")).equals(EVIDENCE_PATHS),
                "transaction-write full-parity fixture authority drifted");
        JsonNode nodeD = readFixedJson(
                root, NODE_D_RELATIVE, NODE_D_SHA256, NODE_D_BYTE_COUNT);
        Set<String> paths = new LinkedHashSet<>(minimalFixturePaths());
        paths.addAll(propertyNames(nodeD.path("source_authority")
                .path("fixed_non_control_sources")));
        return Set.copyOf(paths);
    }

    static Set<String> minimalFixturePaths() {
        Set<String> paths = new LinkedHashSet<>();
        paths.add(CONTRACT_RELATIVE);
        paths.add(NODE_D_RELATIVE);
        paths.add(NODE_D_ANCHOR_RELATIVE);
        paths.addAll(TRANSITION_PATHS);
        paths.addAll(EVIDENCE_PATHS);
        return Set.copyOf(paths);
    }

    private static void validatePredecessor(
            JsonNode predecessor, JsonNode contract, Path root
    )
            throws IOException {
        JsonNode nodeD = predecessor.path("node_d_contract");
        JsonNode anchor = predecessor.path("node_d_external_anchor");
        require(NODE_D_RELATIVE.equals(nodeD.path("source").asString())
                        && NODE_D_SHA256.equals(
                        nodeD.path("sha256").asString())
                        && NODE_D_BYTE_COUNT
                        == nodeD.path("byte_count").asLong()
                        && nodeD.path("immutable").asBoolean()
                        && NODE_D_ANCHOR_RELATIVE.equals(
                        anchor.path("source").asString())
                        && NODE_D_ANCHOR_SHA256.equals(
                        anchor.path("sha256").asString())
                        && NODE_D_ANCHOR_BYTE_COUNT
                        == anchor.path("byte_count").asLong()
                        && anchor.path("immutable").asBoolean()
                        && BASE_CHECKPOINT.equals(predecessor.path(
                        "fixed_checkpoint").path("commit_oid").asString()),
                "transaction-write full-parity predecessor drifted");
        JsonNode nodeDDocument = readFixedJson(
                root, NODE_D_RELATIVE, NODE_D_SHA256, NODE_D_BYTE_COUNT);
        JsonNode anchorDocument = readFixedJson(
                root,
                NODE_D_ANCHOR_RELATIVE,
                NODE_D_ANCHOR_SHA256,
                NODE_D_ANCHOR_BYTE_COUNT);
        require("ti.phase4c.personal-bank-tag-migration-execution-protocol-contract"
                        .equals(nodeDDocument.path("contract_id").asString())
                        && anchorDocument.path("authorization").path(
                        "execution_protocol_control_sources_external_git_anchor_complete")
                        .asBoolean(),
                "transaction-write full-parity predecessor identity drifted");
        validateNodeDSources(nodeDDocument, contract, root);
    }

    private static void validateNodeDSources(
            JsonNode nodeDDocument, JsonNode contract, Path root
    ) throws IOException {
        JsonNode fixedSources = nodeDDocument.path("source_authority")
                .path("fixed_non_control_sources");
        require(propertyNames(fixedSources).size() == 48,
                "transaction-write full-parity Node D source authority drifted");
        for (String relative : propertyNames(fixedSources)) {
            JsonNode descriptor = fixedSources.path(relative);
            Path physical = fixedRegularFile(root, relative);
            JsonNode current = contract.path("historical_source_successors")
                    .path("transitions")
                    .path(relative);
            if (current.isMissingNode()) {
                require(Files.size(physical)
                                == descriptor.path("byte_count").asLong()
                                && sha256(physical).equals(
                                descriptor.path("sha256").asString()),
                        "transaction-write full-parity fixed source drifted: "
                                + relative);
                continue;
            }
            require(descriptor.path("sha256").asString().equals(
                            current.path("accepted_sha256").asString())
                            && descriptor.path("byte_count").asLong()
                            == current.path("accepted_byte_count").asLong()
                            && Files.size(physical)
                            == current.path("successor_byte_count").asLong()
                            && sha256(physical).equals(
                            current.path("successor_sha256").asString()),
                    "transaction-write full-parity fixed source drifted: "
                            + relative);
        }
    }

    private static void validateTransitions(JsonNode historical, Path root)
            throws IOException {
        JsonNode transitions = historical.path("transitions");
        require(BASE_CHECKPOINT.equals(historical.path(
                        "accepted_checkpoint").asString())
                        && IMPLEMENTATION_CHECKPOINT.equals(historical.path(
                        "successor_checkpoint").asString())
                        && historical.path("transition_count").asInt() == 17
                        && propertyNames(transitions).equals(TRANSITION_PATHS)
                        && !historical.path(
                        "dynamic_source_discovery").asBoolean()
                        && "reject".equals(
                        historical.path("unknown_path").asString()),
                "transaction-write full-parity transition authority drifted");
        for (String relative : propertyNames(transitions)) {
            JsonNode descriptor = transitions.path(relative);
            SourceTransition transition = transition(descriptor);
            Path physical = fixedRegularFile(root, relative);
            require(relative.equals(transition.source())
                            && transition.acceptedSha256().matches(
                            "[0-9a-f]{64}")
                            && transition.successorSha256().matches(
                            "[0-9a-f]{64}")
                            && Files.size(physical)
                            == transition.successorByteCount()
                            && sha256(physical).equals(
                            transition.successorSha256()),
                    "transaction-write full-parity fixed source drifted: "
                            + relative);
        }
    }

    private static void validateEvidence(JsonNode evidence, Path root)
            throws IOException {
        JsonNode artifacts = evidence.path("artifacts");
        require(evidence.path("artifact_count").asInt() == 8
                        && propertyNames(artifacts).equals(EVIDENCE_PATHS)
                        && evidence.path(
                        "real_random_port_tomcat_full_filter_chain")
                        .asBoolean()
                        && evidence.path(
                        "target_session_flask_session_and_bearer_to_controller")
                        .asBoolean()
                        && evidence.path(
                        "redis_7_4_atomicity_outage_and_recovery").asBoolean()
                        && strings(evidence.path("postgresql_versions"))
                        .equals(List.of("16.14", "18.4"))
                        && evidence.path(
                        "users_last_active_business_dml_count").asInt() == 0
                        && evidence.path(
                        "openapi_3_1_2_exact_operation_count").asInt() == 9
                        && evidence.path("worm_chain_node_count").asInt() == 10,
                "transaction-write full-parity evidence drifted");
        for (String relative : propertyNames(artifacts)) {
            JsonNode descriptor = artifacts.path(relative);
            Path physical = fixedRegularFile(root, relative);
            require(relative.equals(descriptor.path("source").asString())
                            && Files.size(physical)
                            == descriptor.path("byte_count").asLong()
                            && sha256(physical).equals(
                            descriptor.path("sha256").asString()),
                    "transaction-write full-parity evidence bytes drifted: "
                            + relative);
        }
    }

    private static void validateParityAndAuthorization(JsonNode contract) {
        JsonNode parity = contract.path("parity");
        require(parity.path("operation_count").asInt() == 9
                        && parity.path(
                        "target_execution_complete").asBoolean()
                        && parity.path(
                        "authentication_execution_complete").asBoolean()
                        && parity.path("http_and_cors_complete").asBoolean()
                        && parity.path("idempotency_complete").asBoolean()
                        && parity.path("redis_complete").asBoolean()
                        && parity.path(
                        "postgresql_16_14_and_18_4_complete").asBoolean()
                        && parity.path("openapi_complete").asBoolean()
                        && parity.path("worm_complete").asBoolean()
                        && parity.path(
                        "full_target_parity_closed").asBoolean(),
                "transaction-write full-parity claim drifted");
        JsonNode authorization = contract.path("authorization");
        require(!authorization.path(
                        "bootstrap_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && !authorization.path(
                        "route_migration_eligible").asBoolean()
                        && !authorization.path(
                        "nine_transaction_write_operations_migrated")
                        .asBoolean()
                        && !authorization.path(
                        "production_cutover").asBoolean(),
                "transaction-write full-parity authorization drifted");
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
                "transaction-write full-parity route state drifted");
        JsonNode authority = contract.path("source_authority");
        require(authority.path("control_source_count").asInt() == 8
                        && authority.path(
                        "control_sources_excluded_from_self_authority")
                        .asBoolean()
                        && authority.path(
                        "fixed_transition_allowlist_exact").asBoolean()
                        && authority.path(
                        "ordinary_build_is_gitless").asBoolean()
                        && !authority.path(
                        "live_head_main_or_origin_authority").asBoolean(),
                "transaction-write full-parity source authority drifted");
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
                    "transaction-write full-parity fixed source drifted: "
                        + relative);
        JsonNode document = JSON.readTree(Files.readAllBytes(path));
        require(document.isObject(),
                "transaction-write full-parity JSON is not an object: "
                        + relative);
        return document;
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path value = Path.of(relative);
        require(!value.isAbsolute() && value.getNameCount() > 0,
                "transaction-write full-parity path escapes root: "
                        + relative);
        Path base = root.toRealPath();
        Path cursor = base;
        for (Path part : value) {
            require(!part.toString().isBlank()
                            && !part.toString().equals(".")
                            && !part.toString().equals(".."),
                    "transaction-write full-parity path escapes root: "
                            + relative);
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "transaction-write full-parity path is a symlink: "
                            + relative);
        }
        Path resolved = base.resolve(value).normalize();
        require(resolved.startsWith(base)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "transaction-write full-parity path is absent: " + relative);
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

    private static String documentPayloadSha256(JsonNode value) {
        ObjectNode copy = (ObjectNode) value.deepCopy();
        copy.remove("document_payload_sha256");
        return sha256(JSON.writeValueAsBytes(canonicalNode(copy)));
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
}
