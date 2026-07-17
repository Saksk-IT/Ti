package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

/** Emits the exact runtime SQL consumed by the all-shares plan parity gate. */
class PersonalBankOwnedShareRuntimeSqlManifestTest {

    @Test
    void exportsExactRuntimeStatementForTheOwnedSharePlanGate() throws Exception {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("query_id", "personal-bank-all-shares");
        query.put("operation", "personal-bank-owned-share-list");
        query.put("sql", JdbcPersonalBankOwnedShareQueryAdapter.SELECT_OWNED_SHARES);
        query.put("parameters", Map.of("viewer_id", "bigint"));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4b.personal-bank-owned-share-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcPersonalBankOwnedShareQueryAdapter.class.getName());
        manifest.put("query_count", 1);
        manifest.put("queries", List.of(query));

        String json = new ObjectMapper().writerWithDefaultPrettyPrinter()
                .writeValueAsString(manifest) + "\n";
        Path output = outputPath();
        Files.createDirectories(output.getParent());
        Files.writeString(output, json, StandardCharsets.UTF_8);

        assertThat(Files.readString(output, StandardCharsets.UTF_8)).isEqualTo(json);
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty("ti.personal-bank-owned-share.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4b-personal-bank-owned-share-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Personal-bank owned-share runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
