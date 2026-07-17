package io.saksk.ti.architecture;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Fixed second-level trust root for historical tests that admit the Phase 4C read. */
final class Phase4cReadSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-read-contract";
    private static final String CONTRACT_STATUS =
            "implemented_and_targeted_verified_http_aliases_deferred";
    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json";
    private static final String PREDECESSOR_CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-composition-contract";
    private static final String PREDECESSOR_STATUS =
            "composition_and_migration_primitives_closed_"
                    + "http_neutral_implementation_authorized";
    private static final String PREDECESSOR_SHA256 =
            "ba900795d92046693617d92f4de7599d604e389e7b60e1cc145d08a737518f6b";
    private static final Map<String, FixedSource> AUXILIARY_SOURCES =
            fixedAuxiliarySources();
    private static final Map<String, FixedSource> PYTHON_SOURCES = fixedPythonSources();
    private static final Map<String, FixedSource> JAVA_SOURCES = fixedJavaSources();
    private static volatile Map<String, String> verifiedTerminalSuccessorHashes = Map.of();

    private Phase4cReadSuccessorAcceptance() {
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Phase4cHttpEntrySuccessorAcceptance.load(root);
        Phase4cHttpImplementationSuccessorAcceptance.load(root);
        JsonNode contract = JSON.readTree(Files.readString(
                fixedRegularFile(root, CONTRACT_RELATIVE), StandardCharsets.UTF_8));
        validate(contract);

        Path predecessorPath = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        require(PREDECESSOR_SHA256.equals(sha256(predecessorPath)),
                "Phase4C composition predecessor is not byte-for-byte immutable");
        JsonNode predecessor = JSON.readTree(Files.readString(
                predecessorPath, StandardCharsets.UTF_8));
        Phase4cSuccessorAcceptance.validate(predecessor);

        Map<String, String> terminalHashes = new LinkedHashMap<>();
        terminalHashes.putAll(validateFixedFiles(root, PYTHON_SOURCES));
        terminalHashes.putAll(validateFixedFiles(root, JAVA_SOURCES));
        terminalHashes.putAll(validateFixedFiles(root, AUXILIARY_SOURCES));
        verifiedTerminalSuccessorHashes = Map.copyOf(terminalHashes);
        return contract;
    }

    static void validate(JsonNode contract) {
        require(contract.path("schema_version").asInt() == 1,
                "unexpected Phase4C read contract schema version");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString()),
                "unexpected Phase4C read successor contract id");
        require(CONTRACT_STATUS.equals(contract.path("status").asString()),
                "unexpected Phase4C read successor status");

        JsonNode predecessor = contract.path("predecessor");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString()),
                "unexpected Phase4C read predecessor source");
        require(PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString()),
                "Phase4C composition predecessor was not preserved");
        require(PREDECESSOR_CONTRACT_ID.equals(
                        predecessor.path("contract_id").asString()),
                "unexpected Phase4C read predecessor id");
        require(PREDECESSOR_STATUS.equals(predecessor.path("status").asString()),
                "unexpected Phase4C read predecessor status");

        JsonNode history = contract.path("historical_successor_acceptance");
        require(PREDECESSOR_CONTRACT_ID.equals(
                        history.path("predecessor_contract_id").asString()),
                "unexpected historical predecessor id");
        require(PREDECESSOR_SHA256.equals(
                        history.path("predecessor_sha256").asString()),
                "unexpected historical predecessor hash");
        require(history.path("successor_allowlist_exact").asBoolean(),
                "Phase4C read successor allowlist is not exact");
        require(history.path("arbitrary_source_hash_lookup_forbidden").asBoolean(),
                "arbitrary Phase4C read successor lookup is not forbidden");

        validateSourceReferences(history, "python_sources", "Python", PYTHON_SOURCES);
        validateSourceReferences(history, "java_sources", "Java", JAVA_SOURCES);
        validateSourceReferences(
                history, "auxiliary_sources", "auxiliary", AUXILIARY_SOURCES);
        validateAuxiliaryReferences(contract.path("source_contracts"));

        JsonNode implementation = contract.path("implementation");
        require(implementation.path("http_neutral_java_implemented").asBoolean(),
                "Phase4C HTTP-neutral Java implementation is not closed");
        require(implementation.path("implemented_public_application_method_count")
                        .asInt() == 27,
                "unexpected Phase4C public application method count");
        require(implementation.path("public_application_methods").size() == 27,
                "unexpected Phase4C public application method manifest size");
        require(implementation.path("main_source_file_count").asInt() == 40,
                "unexpected Phase4C main source file count");
        require(implementation.path("learning_and_personalbank_main_source_manifest")
                        .size() == 40,
                "unexpected Phase4C main source manifest size");
    }

    static String successorHash(JsonNode contract, String relative) {
        String httpEntrySuccessor =
                Phase4cHttpEntrySuccessorAcceptance.successorHash(relative);
        if (httpEntrySuccessor != null) {
            validate(contract);
            return httpEntrySuccessor;
        }
        FixedSource fixed = JAVA_SOURCES.get(relative);
        if (fixed == null) {
            fixed = PYTHON_SOURCES.get(relative);
        }
        if (fixed == null) {
            fixed = AUXILIARY_SOURCES.get(relative);
        }
        if (fixed == null) {
            return null;
        }
        validate(contract);
        return verifiedTerminalSuccessorHashes.getOrDefault(
                relative, fixed.successorSha256());
    }

    private static Map<String, String> validateFixedFiles(
            Path root,
            Map<String, FixedSource> sources
    ) throws IOException {
        Map<String, String> terminalHashes = new LinkedHashMap<>();
        for (Map.Entry<String, FixedSource> entry : sources.entrySet()) {
            Path source = fixedRegularFile(root, entry.getKey());
            String expected = entry.getValue().successorSha256();
            String httpEntrySuccessor =
                    Phase4cHttpEntrySuccessorAcceptance.successorHash(entry.getKey());
            if (httpEntrySuccessor != null) {
                require(expected.equals(
                                Phase4cHttpEntrySuccessorAcceptance.acceptedHash(
                                        entry.getKey())),
                        "HTTP entry did not accept the exact read successor for "
                                + entry.getKey());
                expected = httpEntrySuccessor;
            } else {
                String implementationSuccessor =
                        Phase4cHttpImplementationSuccessorAcceptance.successorHash(
                                root, entry.getKey());
                if (implementationSuccessor != null) {
                    require(expected.equals(
                                    Phase4cHttpImplementationSuccessorAcceptance
                                            .acceptedHash(entry.getKey())),
                            "HTTP implementation did not accept the exact read "
                                    + "successor for " + entry.getKey());
                    expected = implementationSuccessor;
                }
            }
            require(expected.equals(sha256(source)),
                    "Phase4C read successor file hash drift for " + entry.getKey());
            terminalHashes.put(entry.getKey(), expected);
        }
        return Map.copyOf(terminalHashes);
    }

    private static void validateSourceReferences(
            JsonNode history,
            String sourceField,
            String label,
            Map<String, FixedSource> fixedSources
    ) {
        JsonNode sources = history.path(sourceField);
        require(propertyNames(sources).equals(fixedSources.keySet()),
                "unexpected Phase4C read " + label + " successor source set");
        Set<String> referenceFields = Set.of(
                "source", "accepted_sha256", "successor_sha256");
        for (Map.Entry<String, FixedSource> entry : fixedSources.entrySet()) {
            String relative = entry.getKey();
            FixedSource fixed = entry.getValue();
            JsonNode reference = sources.path(relative);
            require(propertyNames(reference).equals(referenceFields),
                    "unexpected Phase4C read successor reference shape for " + relative);
            require(relative.equals(reference.path("source").asString()),
                    "Phase4C read successor source drift for " + relative);
            require(fixed.acceptedSha256().equals(
                            reference.path("accepted_sha256").asString()),
                    "Phase4C read accepted hash drift for " + relative);
            require(fixed.successorSha256().equals(
                            reference.path("successor_sha256").asString()),
                    "Phase4C read successor hash is not fixed for " + relative);
        }
    }

    private static void validateAuxiliaryReferences(JsonNode sourceContracts) {
        Set<String> referenceFields = Set.of("source", "sha256");
        for (Map.Entry<String, FixedSource> entry : AUXILIARY_SOURCES.entrySet()) {
            String relative = entry.getKey();
            FixedSource fixed = entry.getValue();
            JsonNode reference = sourceContracts.path("progress");
            require(propertyNames(reference).equals(referenceFields),
                    "unexpected Phase4C read auxiliary reference shape for " + relative);
            require(relative.equals(reference.path("source").asString()),
                    "Phase4C read auxiliary source drift for " + relative);
            require(fixed.successorSha256().equals(reference.path("sha256").asString()),
                    "Phase4C read auxiliary hash is not fixed for " + relative);
        }
    }

    private static Path fixedRegularFile(Path root, String relative) throws IOException {
        Path path = root.resolve(relative).normalize();
        require(path.startsWith(root), "fixed Phase4C read path escapes Ti-Java: " + relative);
        Path cursor = root;
        for (Path part : Path.of(relative)) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "fixed Phase4C read path contains symlink: " + relative);
        }
        Path resolved = path.toRealPath();
        require(resolved.startsWith(root),
                "fixed Phase4C read path resolves outside Ti-Java: " + relative);
        require(Files.isRegularFile(resolved, LinkOption.NOFOLLOW_LINKS),
                "fixed Phase4C read path is not a regular file: " + relative);
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

    private static Set<String> propertyNames(JsonNode node) {
        return Set.copyOf(node.propertyNames());
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static Map<String, FixedSource> fixedJavaSources() {
        Map<String, FixedSource> sources = new LinkedHashMap<>();
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "ModuleContractParityTest.java",
                new FixedSource(
                        "35e25fa5ed4d5771701f8c1819b615bee9af441a6c64cbf1386df168f16610cb",
                        "02a4b9bfabe2f9e3789e94826b1f337e8a0986e5d36f42ac243cbe79060a82d2"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankAllSharesContractParityTest.java",
                new FixedSource(
                        "171c36f7c3cdd2d2ff97998cade67ec99c3d825ec3bce4191094a3bcf0095b48",
                        "8946d000de7927cf258d6c8acaf025bcd85fe29c709b7b162b5dfade95115409"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankShareListContractParityTest.java",
                new FixedSource(
                        "1bc3ba26b932eba694d0aeb4762e7973d51a0fee5bd69d0454799c223d56248a",
                        "d7e3be7430e5cfc1cd43988eb8cb42e05536286dac58d2d075b72ad32c8819b9"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankUsageStatsContractParityTest.java",
                new FixedSource(
                        "1b24e8a8f1861a5adad96de9f087abc684b73e9a4dd496ffb7f1d071ddc307bc",
                        "07648bcf8c80c392b355df029893dac9411877a1d4adeb05e1ee83666b86ca42"));
        return Map.copyOf(sources);
    }

    private static Map<String, FixedSource> fixedAuxiliarySources() {
        return Map.of(
                "docs/refactor/05-progress.md",
                new FixedSource(
                        "47ec2b9a2178dee8db91f0461b9abffbbe9dea0a5ba4dd3694d4f33643735bbf",
                        "71407c0fd99d1b8f982ea4e108e1dc5e0d9d472584824fb7a8ade325be65f1c2"));
    }

    private static Map<String, FixedSource> fixedPythonSources() {
        Map<String, FixedSource> sources = new LinkedHashMap<>();
        sources.put(
                "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
                new FixedSource(
                        "866b749cdc00fe22451e4a4663702d98e4917e0d546f996f0d6cac6326f39d75",
                        "c60e4d9abb01c70001e703cf8c4c5eed77bd65445c506e99a9e3dd38dadab2ee"));
        sources.put(
                "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
                new FixedSource(
                        "114a07ce3ada1027c7e30a595b249c9f88244ffd0d0838b1507019f64711eb59",
                        "2ed3c3d1168aeea07d863bcdd6c81522bc59e78d253242b9f36f3808b9ca0b40"));
        sources.put(
                "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
                new FixedSource(
                        "03a5cefe9ea73ad86ff8755019d88abbb84778488fdb117dd9c4517a91040b86",
                        "f236ed8080a4e73d294d0eb96f1b19f8b3116ef0a51ba1be6d5d8e695dc558e0"));
        sources.put(
                "tools/test_phase4b_personal_bank_share_list_read_contract.py",
                new FixedSource(
                        "3459e74ed669e3f0aa6e4bc3e2e600f4a4b644a03fc7a382cd01a78ce873d254",
                        "6869964c169b6970df0c9f762957664f2e711c2abb309a4e5a2a3689cb636f29"));
        sources.put(
                "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
                new FixedSource(
                        "5854e591041b8cb1892b805208903c5115027a8dbaeec56f8db8b98223301ada",
                        "de1415897a0cef4e98266aaca699b162dd469caf17628dd2fde19bed691ef32c"));
        sources.put(
                "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
                new FixedSource(
                        "2251ab9b5c15c0badf59b782fd9e7f76030f1bef33f8943fcfbf459972abc4be",
                        "90c77b28c1c08822d900f150e5c4c69fe4a7463b5dfc7a4ce021fc599c71a15a"));
        sources.put(
                "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
                new FixedSource(
                        "9fcd432a81f78eb78f0001e4e6d029e01f27047e56714c96d7fd47607d98c016",
                        "590f4d62c45c4fc9fdde9332f2de376f62481b672120c72389071e4a8bf334a7"));
        sources.put(
                "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
                new FixedSource(
                        "c5c0a52d90553acc3699dab2534f6dc1ac0261940be6611f57ca293f3fb92207",
                        "08e82154d66ab4a112091ee97b40bc1c155aae14a4bd9ca0b6afbb9032e71bdd"));
        return Map.copyOf(sources);
    }

    private record FixedSource(String acceptedSha256, String successorSha256) {
    }
}
