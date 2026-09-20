package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** Exact additive reconciliation; independent of Git and historical loaders. */
final class Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance {
    static final String CONTRACT = "docs/refactor/phase4c/learning-transaction-write-http-integration-successor-contract.json";
    private static final String CONTRACT_SHA256 = "9e14033e117348746a07a6ea0250b2ace38c10fe0aa5062c3f021b15d7b0830d";
    private static final ObjectMapper JSON = new ObjectMapper();

    private Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance() { }

    static JsonNode load(Path root) throws IOException {
        byte[] payload = Files.readAllBytes(fixedFile(root, CONTRACT));
        require(CONTRACT_SHA256.equals(sha256(payload)), "integration successor contract drifted");
        return JSON.readTree(payload);
    }

    static boolean accepts(Path root, String relative, String digest, long count) throws IOException {
        JsonNode transition = load(root).path("transitions").path(relative);
        boolean accepted = false;
        for (JsonNode previous : transition.path("accepted")) {
            if (digest.equals(previous.path("sha256").asString())
                    && count == previous.path("byte_count").asLong()) {
                accepted = true;
                break;
            }
        }
        if (!accepted) {
            return false;
        }
        byte[] payload = Files.readAllBytes(fixedFile(root, relative));
        return payload.length == transition.path("current").path("byte_count").asLong()
                && sha256(payload).equals(transition.path("current").path("sha256").asString());
    }

    static Path fixedFile(Path root, String relative) throws IOException {
        require(!relative.isBlank() && !relative.startsWith("/")
                && !relative.contains("\\") && !relative.contains(":"), "integration path escapes root");
        Path cursor = root.toRealPath();
        for (String part : relative.split("/", -1)) {
            require(!part.isBlank() && !part.equals(".") && !part.equals(".."), "integration path escapes root");
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor), "integration path is a symlink");
        }
        require(Files.isRegularFile(cursor), "integration file is absent: " + relative);
        return cursor;
    }

    private static String sha256(byte[] payload) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(payload));
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
