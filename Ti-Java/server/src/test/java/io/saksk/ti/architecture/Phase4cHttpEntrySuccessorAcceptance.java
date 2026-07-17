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
import java.util.List;
import java.util.Map;
import java.util.Set;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Independent trust root admitting the reviewed Phase 4C HTTP entry successor. */
final class Phase4cHttpEntrySuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/personal-bank-user-counts-http-entry-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-entry-contract";
    private static final String CONTRACT_STATUS =
            "entry_gate_passed_http_implementation_not_started";
    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-user-counts-read-contract";
    private static final String PREDECESSOR_STATUS =
            "implemented_and_targeted_verified_http_aliases_deferred";
    private static final String PREDECESSOR_SHA256 =
            "458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "216cf664c4d74e67169f4f5c8091f80296964938d31911e3a32aeb3630a3d7a5";
    private static final String MAIN_MANIFEST_SHA256 =
            "d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1";
    private static final String RUNTIME_MANIFEST_SHA256 =
            "145bcd8d5e662cffb87744b39b8eae03cdf5761b7fc9096d90300dd4742905dc";
    private static final String ROUTE_MANIFEST_SHA256 =
            "6f9cfdd6ba849233c51a27ed281856681d8a6ec3a0bda628da9184ec284e4b86";
    private static final String BUILD_CONTEXT_SHA256 =
            "935e6a95a33621b01e1e04d752a09513c8037cffe807a73fa1ce9850fb5912f0";
    private static final String TRUST_PAYLOAD_SHA256 =
            "6301db3499e9d166048c678d8851da00e62e6ce56f331b3c5f1af15aa7c5cfc6";
    private static final String BRIDGE_PROVENANCE_SENTINEL =
            "<bridge-self-provenance-sha256>";
    private static final Set<String> BRIDGE_SOURCE_KEYS = Set.of(
            "python_successor_bridge", "java_successor_bridge");
    private static final Map<String, FixedSource> SUCCESSOR_SOURCES = fixedSources();

    private Phase4cHttpEntrySuccessorAcceptance() {
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = JSON.readTree(Files.readString(
                fixedRegularFile(root, CONTRACT_RELATIVE), StandardCharsets.UTF_8));
        validate(contract);

        Path predecessorPath = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        require(PREDECESSOR_SHA256.equals(sha256(predecessorPath)),
                "Phase4C read predecessor is not byte-for-byte immutable");
        JsonNode predecessor = JSON.readTree(Files.readString(
                predecessorPath, StandardCharsets.UTF_8));
        require(PREDECESSOR_ID.equals(predecessor.path("contract_id").asString()),
                "unexpected physical Phase4C read predecessor id");
        require(PREDECESSOR_STATUS.equals(predecessor.path("status").asString()),
                "unexpected physical Phase4C read predecessor status");
        require(PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString()),
                "unexpected physical Phase4C read predecessor payload");
        validateFixedFiles(root);
        validateSourceContracts(root, contract.path("source_contracts"));
        return contract;
    }

    static void validate(JsonNode contract) {
        require(contract.path("schema_version").asInt() == 1,
                "unexpected Phase4C HTTP entry schema version");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString()),
                "unexpected Phase4C HTTP entry contract id");
        require(CONTRACT_STATUS.equals(contract.path("status").asString()),
                "unexpected Phase4C HTTP entry contract status");
        require("phase4c-personal-bank-user-counts-http-entry-gate".equals(
                        contract.path("scope").asString()),
                "unexpected Phase4C HTTP entry scope");
        require(contract.path("document_payload_sha256").asString().equals(
                        canonicalPayloadSha256(contract, false)),
                "invalid Phase4C HTTP entry document payload hash");

        JsonNode predecessor = contract.path("predecessor");
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "document_payload_sha256",
                        "contract_id", "status", "immutable")),
                "unexpected Phase4C HTTP entry predecessor shape");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString()),
                "unexpected Phase4C HTTP entry predecessor source");
        require(PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString()),
                "Phase4C read predecessor hash drifted");
        require(PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString()),
                "Phase4C read predecessor payload drifted");
        require(PREDECESSOR_ID.equals(predecessor.path("contract_id").asString()),
                "unexpected Phase4C HTTP entry predecessor id");
        require(PREDECESSOR_STATUS.equals(predecessor.path("status").asString()),
                "unexpected Phase4C HTTP entry predecessor status");
        require(predecessor.path("immutable").asBoolean(),
                "Phase4C read predecessor is not immutable");

        JsonNode history = contract.path("historical_successor_acceptance");
        require(PREDECESSOR_SHA256.equals(
                        history.path("predecessor_sha256").asString()),
                "unexpected HTTP entry historical predecessor hash");
        require(history.path("successor_allowlist_exact").asBoolean(),
                "HTTP entry successor allowlist is not exact");
        require(history.path("arbitrary_source_hash_lookup_forbidden").asBoolean(),
                "arbitrary HTTP entry source lookup is not forbidden");
        require(history.path("bridge_self_authorization_forbidden").asBoolean(),
                "HTTP entry bridge self-authorization is not forbidden");
        JsonNode references = history.path("read_source_overrides");
        require(propertyNames(references).equals(SUCCESSOR_SOURCES.keySet()),
                "unexpected HTTP entry successor source set");
        Set<String> sourceFields = Set.of(
                "source", "accepted_sha256", "successor_sha256");
        for (Map.Entry<String, FixedSource> entry : SUCCESSOR_SOURCES.entrySet()) {
            String relative = entry.getKey();
            FixedSource fixed = entry.getValue();
            JsonNode reference = references.path(relative);
            require(propertyNames(reference).equals(sourceFields),
                    "unexpected HTTP entry source shape for " + relative);
            require(relative.equals(reference.path("source").asString()),
                    "HTTP entry source path drift for " + relative);
            require(fixed.acceptedSha256().equals(
                            reference.path("accepted_sha256").asString()),
                    "HTTP entry accepted hash drift for " + relative);
            require(fixed.successorSha256().equals(
                            reference.path("successor_sha256").asString()),
                    "HTTP entry successor hash drift for " + relative);
        }

        JsonNode current = contract.path("current_state");
        for (String field : Set.of(
                "implementation_started", "controller_present", "route_security_present",
                "route_rate_limiter_present", "route_cors_present",
                "openapi_overlay_present")) {
            require(!current.path(field).asBoolean(),
                    "HTTP entry overclaims current " + field);
        }
        require(current.path("migrated_operation_count").asInt() == 11,
                "unexpected HTTP entry migrated route count");
        require(current.path("pending_operation_count").asInt() == 600,
                "unexpected HTTP entry pending route count");
        require(current.path("production_cutover_operation_count").asInt() == 0,
                "HTTP entry overclaims production cutover");
        JsonNode surface = current.path("current_production_surface");
        require(surface.path("public_application_method_count").asInt() == 27,
                "unexpected HTTP entry application method count");
        require(surface.path("learning_and_personalbank_main_source_file_count")
                        .asInt() == 40,
                "unexpected HTTP entry main source file count");
        require(MAIN_MANIFEST_SHA256.equals(surface.path(
                        "learning_and_personalbank_main_source_manifest_sha256").asString()),
                "HTTP entry main source manifest drifted");
        require(surface.path("production_runtime_file_count").asInt() == 288,
                "unexpected HTTP entry runtime file count");
        require(RUNTIME_MANIFEST_SHA256.equals(
                        surface.path("production_runtime_manifest_sha256").asString()),
                "HTTP entry runtime manifest drifted");
        require(surface.path("route_status_file_count").asInt() == 5,
                "unexpected HTTP entry route file count");
        require(ROUTE_MANIFEST_SHA256.equals(
                        surface.path("route_status_manifest_sha256").asString()),
                "HTTP entry route manifest drifted");
        require(BUILD_CONTEXT_SHA256.equals(
                        surface.path("java_build_context_sha256").asString()),
                "HTTP entry build context drifted");
        for (String field : Set.of(
                "server_src_main_changed_by_gate", "production_resources_changed_by_gate",
                "openapi_or_contracts_changed_by_gate", "route_status_changed_by_gate")) {
            require(!surface.path(field).asBoolean(),
                    "HTTP entry changed production surface: " + field);
        }

        JsonNode authorization = contract.path("authorization");
        for (String field : Set.of(
                "future_controller", "future_route_specific_security",
                "future_route_specific_rate_limit", "future_route_specific_cors",
                "future_route_and_openapi_delta", "future_required_configuration")) {
            require(authorization.path(field).asBoolean(),
                    "HTTP entry did not authorize " + field);
        }
        for (String field : Set.of(
                "current_http_implementation_started", "identity_api_or_global_auth_filter_change",
                "learning_or_personalbank_persistence_change", "production_schema_or_index",
                "operator_migration_implementation", "real_data_migration_execution",
                "migration_global_preflight_closed", "client_change",
                "gateway_or_proxy_change", "production_cutover")) {
            require(!authorization.path(field).asBoolean(),
                    "HTTP entry accidentally authorized " + field);
        }
        JsonNode acceptance = contract.path("acceptance");
        require(acceptance.path("entry_evidence_closed").asBoolean(),
                "HTTP entry evidence is not closed");
        require(!acceptance.path("current_http_implementation_started").asBoolean(),
                "HTTP entry acceptance overclaims implementation");
        require(acceptance.path("future_exact_http_slice_authorized").asBoolean(),
                "HTTP entry did not authorize its exact future slice");
        require(acceptance.path("routes_remain_pending").asBoolean(),
                "HTTP entry moved pending routes too early");
        require(!acceptance.path("production_cutover").asBoolean(),
                "HTTP entry overclaims production cutover");
        require(TRUST_PAYLOAD_SHA256.equals(canonicalPayloadSha256(contract, true)),
                "Phase4C HTTP entry independent trust payload drifted");
    }

    static String acceptedHash(String relative) {
        FixedSource fixed = SUCCESSOR_SOURCES.get(relative);
        return fixed == null ? null : fixed.acceptedSha256();
    }

    static String successorHash(String relative) {
        FixedSource fixed = SUCCESSOR_SOURCES.get(relative);
        return fixed == null ? null : fixed.successorSha256();
    }

    private static void validateFixedFiles(Path root) throws IOException {
        for (Map.Entry<String, FixedSource> entry : SUCCESSOR_SOURCES.entrySet()) {
            Path source = fixedRegularFile(root, entry.getKey());
            require(entry.getValue().successorSha256().equals(sha256(source)),
                    "HTTP entry successor file hash drift for " + entry.getKey());
        }
    }

    private static void validateSourceContracts(Path root, JsonNode sources)
            throws IOException {
        for (String name : propertyNames(sources)) {
            JsonNode reference = sources.path(name);
            String relative = reference.path("source").asString();
            Path source = fixedRegularFile(root, relative);
            require(reference.path("sha256").asString().equals(sha256(source)),
                    "HTTP entry source contract file hash drift for " + name);
        }
    }

    private static Path fixedRegularFile(Path root, String relative) throws IOException {
        Path path = root.resolve(relative).normalize();
        require(path.startsWith(root), "fixed HTTP entry path escapes Ti-Java: " + relative);
        Path cursor = root;
        for (Path part : Path.of(relative)) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "fixed HTTP entry path contains symlink: " + relative);
        }
        Path resolved = path.toRealPath();
        require(resolved.startsWith(root),
                "fixed HTTP entry path resolves outside Ti-Java: " + relative);
        require(Files.isRegularFile(resolved, LinkOption.NOFOLLOW_LINKS),
                "fixed HTTP entry path is not a regular file: " + relative);
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

    private static String canonicalPayloadSha256(JsonNode contract, boolean trust) {
        StringBuilder canonical = new StringBuilder();
        appendCanonical(contract, canonical, "", trust);
        return sha256(canonical.toString());
    }

    private static void appendCanonical(
            JsonNode node,
            StringBuilder output,
            String path,
            boolean trust
    ) {
        if (node.isObject()) {
            List<String> names = new ArrayList<>(propertyNames(node));
            if (path.isEmpty()) {
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
                if (trust
                        && childPath.startsWith("/source_contracts/")
                        && childPath.endsWith("/sha256")
                        && bridgeSourcePath(childPath)) {
                    appendJsonString(BRIDGE_PROVENANCE_SENTINEL, output);
                } else {
                    appendCanonical(node.path(name), output, childPath, trust);
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
                appendCanonical(node.path(index), output, path + "/" + index, trust);
            }
            output.append(']');
            return;
        }
        if (node.isTextual()) {
            appendJsonString(node.asString(), output);
            return;
        }
        if (node.isNull()) {
            output.append("null");
            return;
        }
        output.append(node.toString());
    }

    private static boolean bridgeSourcePath(String path) {
        for (String sourceKey : BRIDGE_SOURCE_KEYS) {
            if (path.equals("/source_contracts/" + sourceKey + "/sha256")) {
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
                        output.append("\\u")
                                .append(String.format("%04x", (int) character));
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

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static Map<String, FixedSource> fixedSources() {
        Map<String, FixedSource> sources = new LinkedHashMap<>();
        sources.put(
                "README.md",
                new FixedSource(
                        "685ffde5088acb7e6c1a8e7825d9d7549f0f0567faf7dadf74a6c045a4bd4832",
                        "3d18a7b86354b8cad4d54a76a9a3722435dd570b612a5a9e65ca9a4aed2864b6"));
        sources.put(
                "docs/refactor/05-progress.md",
                new FixedSource(
                        "71407c0fd99d1b8f982ea4e108e1dc5e0d9d472584824fb7a8ade325be65f1c2",
                        "f44a6efdec4342f13ea1f28831bdca9b36b84f48e932bd4f1d257070af555c7e"));
        sources.put(
                "docs/refactor/phase4c/README.md",
                new FixedSource(
                        "1b685c0e61e9db4aeecf52595760f579bb8fad2b167dd9c8ca6646487d4b2101",
                        "07852f793ed84c90212c5b52dedcf82ed9b52ce9b229e35c56c94eafea253a8b"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cReadSuccessorAcceptance.java",
                new FixedSource(
                        "8fec859106edd58364c04632afb978a2f7d7c36114e10d33157a60d1be17027d",
                        "8a008483f70788ffc10158ae789b7b318e8478ad249514f0551d8b0361dcf52b"));
        sources.put(
                "tools/phase4c_read_successor_acceptance.py",
                new FixedSource(
                        "732a03f5a736079676259b302d90252e045444ef0d9986d619785d283553bbe3",
                        "8b4a57393021a304640797cc64a7f4d44aad83ab6d57c50d81f8158aa9008f82"));
        sources.put(
                "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
                new FixedSource(
                        "95adccd41a0bec4780f881adf845a6c65df67ec42b0d1925d81dbe4b971d8195",
                        "6d493304cc01fcbc801b066700b98bb6b0a1750ee9e3d9ce03867ee6e92991cc"));
        sources.put(
                "docs/refactor/phase4c/approved-differences.md",
                new FixedSource(
                        "c8081e7adc62f6119b00a7f91cf5354da649510e6b3bde547670a807e9a52586",
                        "921d6626ab11d59a9667e1942953807b0aa1a81c06c01094cc109312f9d6b300"));
        sources.put(
                "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
                new FixedSource(
                        "08e82154d66ab4a112091ee97b40bc1c155aae14a4bd9ca0b6afbb9032e71bdd",
                        "c08ff0263d0da2c4e08733685256d7946a316a06772b8959c3520cc7947aaa76"));
        return Map.copyOf(sources);
    }

    private record FixedSource(String acceptedSha256, String successorSha256) {
    }
}
