package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/** Fixed-object bootstrap anchor; never invokes Git or accesses a parent repository. */
final class Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance {
    private static final ObjectMapper JSON = new ObjectMapper();
    static final String CONTRACT = "docs/refactor/phase4c/learning-transaction-write-http-full-parity-anchor-contract.json";
    static final String SNAPSHOT = "docs/refactor/phase4c/learning-transaction-write-http-full-parity-bootstrap-snapshot.json";
    static final String PROGRESS = "docs/refactor/05-progress.md";
    private static final String BOOTSTRAP = "docs/refactor/phase4c/learning-transaction-write-http-full-parity-contract.json";
    private static final String CONTRACT_SHA = "956ce6f59bb42df821aa77c6350f4214e62bacfa4a079e347fc2e506a088adc8";
    private static final long CONTRACT_BYTES = 10681;
    private static final String SNAPSHOT_SHA = "6696930a6cce0af544d67a2decd7d9309b7d550852b34bd1bb11f21580bef9a7";
    private static final String COMMIT = "6ed81347467a4155887300b7e4ae36589204af79";

    private Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance() { }

    static JsonNode load(Path root) throws IOException {
        JsonNode contract = JSON.readTree(fixedBytes(root, CONTRACT, CONTRACT_SHA, CONTRACT_BYTES));
        JsonNode snapshot = JSON.readTree(fixedBytes(root, SNAPSHOT, SNAPSHOT_SHA, 246770));
        JsonNode artifacts = contract.path("git_checkpoint").path("artifacts");
        require(COMMIT.equals(snapshot.path("commit_oid").asString())
                && COMMIT.equals(contract.path("git_checkpoint").path("commit_oid").asString())
                && names(snapshot.path("sources")).equals(names(artifacts))
                && artifacts.size() == 8, "anchor checkpoint drifted");
        for (String relative : names(artifacts)) {
            JsonNode descriptor = artifacts.path(relative);
            JsonNode images = snapshot.path("sources").path(relative);
            checkBlob(images.path("after"), descriptor, "", relative);
            if ("A".equals(descriptor.path("change_type").asString())) {
                require(images.path("before").isNull(), "anchor added preimage drifted");
            } else {
                checkBlob(images.path("before"), descriptor, "previous_", relative);
            }
        }
        JsonNode bootstrap = JSON.readTree(fixedBytes(root, BOOTSTRAP,
                artifacts.path(BOOTSTRAP).path("sha256").asString(),
                artifacts.path(BOOTSTRAP).path("byte_count").asLong()));
        for (Map.Entry<String, JsonNode> entry : fixedInputs(root, contract, bootstrap).entrySet()) {
            JsonNode descriptor = entry.getValue();
            fixedBytes(root, entry.getKey(), descriptor.path("sha256").asString(),
                    descriptor.path("byte_count").asLong());
        }
        JsonNode progress = contract.path("progress_successor");
        fixedBytes(root, PROGRESS, progress.path("successor_sha256").asString(),
                progress.path("successor_byte_count").asLong());
        return contract;
    }

    private static Map<String, JsonNode> fixedInputs(Path root, JsonNode contract, JsonNode bootstrap)
            throws IOException {
        Map<String, JsonNode> inputs = new LinkedHashMap<>();
        for (var entry : bootstrap.path("predecessor").properties()) {
            JsonNode descriptor = entry.getValue();
            if (descriptor.has("source")) {
                inputs.put(descriptor.path("source").asString(), descriptor);
                fixedBytes(root, descriptor.path("source").asString(),
                        descriptor.path("sha256").asString(), descriptor.path("byte_count").asLong());
            }
        }
        JsonNode nodeD = JSON.readTree(Files.readAllBytes(fixedRegularFile(root,
                bootstrap.path("predecessor").path("node_d_contract").path("source").asString())));
        nodeD.path("source_authority").path("fixed_non_control_sources").properties()
                .forEach(entry -> inputs.put(entry.getKey(), entry.getValue()));
        bootstrap.path("historical_source_successors").path("transitions").properties().forEach(entry -> {
            var descriptor = JSON.createObjectNode();
            descriptor.put("sha256", entry.getValue().path("successor_sha256").asString());
            descriptor.put("byte_count", entry.getValue().path("successor_byte_count").asLong());
            inputs.put(entry.getKey(), descriptor);
        });
        bootstrap.path("fixed_evidence").path("artifacts").properties()
                .forEach(entry -> inputs.put(entry.getKey(), entry.getValue()));
        inputs.remove(PROGRESS); // validated against the exact anchored successor in load()
        contract.path("unchanged_bootstrap_sources").forEach(relative -> inputs.put(relative.asString(),
                contract.path("git_checkpoint").path("artifacts").path(relative.asString())));
        return inputs;
    }

    static boolean acceptsProgress(Path root, String relative, String previousSha, long previousBytes)
            throws IOException {
        if (!PROGRESS.equals(relative)) {
            return false;
        }
        JsonNode transition = load(root).path("progress_successor");
        require(previousSha.equals(transition.path("accepted_sha256").asString())
                && previousBytes == transition.path("accepted_byte_count").asLong(),
                "anchor progress predecessor drifted");
        return true;
    }

    static Set<String> minimalFixturePaths(Path root) throws IOException {
        JsonNode contract = load(root);
        JsonNode bootstrap = JSON.readTree(Files.readAllBytes(root.resolve(BOOTSTRAP)));
        Set<String> paths = new LinkedHashSet<>(fixedInputs(root, contract, bootstrap).keySet());
        paths.add(CONTRACT);
        paths.add(SNAPSHOT);
        paths.add(PROGRESS);
        paths.add(Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.CONTRACT);
        return Set.copyOf(paths);
    }

    private static void checkBlob(JsonNode image, JsonNode descriptor, String prefix, String relative) {
        require(image.isString(), "anchor image is not text: " + relative);
        byte[] raw = image.asString().getBytes(StandardCharsets.UTF_8);
        require(raw.length == descriptor.path(prefix + "byte_count").asLong()
                && digest("SHA-256", raw).equals(descriptor.path(prefix + "sha256").asString()),
                "anchor snapshot bytes drifted: " + relative);
        byte[] header = ("blob " + raw.length + "\0").getBytes(StandardCharsets.US_ASCII);
        byte[] object = new byte[header.length + raw.length];
        System.arraycopy(header, 0, object, 0, header.length);
        System.arraycopy(raw, 0, object, header.length, raw.length);
        require(digest("SHA-1", object).equals(descriptor.path(prefix + "git_blob_oid").asString()),
                "anchor Git blob drifted: " + relative);
    }

    private static byte[] fixedBytes(Path root, String relative, String sha, long count) throws IOException {
        byte[] payload = Files.readAllBytes(fixedRegularFile(root, relative));
        require((payload.length == count && digest("SHA-256", payload).equals(sha))
                        || Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance
                        .accepts(root, relative, sha, count),
                "anchor fixed source drifted: " + relative);
        return payload;
    }

    static Path fixedRegularFile(Path root, String relative) throws IOException {
        require(!relative.isBlank() && !relative.startsWith("/")
                && !relative.contains("\\") && !relative.contains(":"), "anchor path escapes root");
        Path cursor = root.toRealPath();
        for (String part : relative.split("/", -1)) {
            require(!part.isBlank() && !part.equals(".") && !part.equals(".."), "anchor path escapes root");
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor), "anchor path is a symlink");
        }
        require(Files.isRegularFile(cursor), "anchor file is absent: " + relative);
        return cursor;
    }

    private static Set<String> names(JsonNode object) {
        Set<String> result = new LinkedHashSet<>();
        object.properties().forEach(entry -> result.add(entry.getKey()));
        return Set.copyOf(result);
    }

    private static String digest(String algorithm, byte[] payload) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance(algorithm).digest(payload));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException(error);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }
}
