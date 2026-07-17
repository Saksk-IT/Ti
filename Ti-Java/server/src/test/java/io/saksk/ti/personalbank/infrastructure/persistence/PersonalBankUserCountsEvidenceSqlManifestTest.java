package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankUserCountsEvidenceSql.EvidenceQuery;
import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankUserCountsEvidenceSql.Source;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

/** Emits test-only SQL evidence for dual-PostgreSQL plans and JDBC execution. */
class PersonalBankUserCountsEvidenceSqlManifestTest {

    @Test
    void exportsOwnershipBoundariesQueryFamiliesSequencesAndCanonicalVariants()
            throws Exception {
        List<EvidenceQuery> queryFamilies =
                PersonalBankUserCountsEvidenceSql.queryFamilies(false, 0);
        List<String> queryOrder = queryFamilies.stream().map(EvidenceQuery::queryId).toList();

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put(
                "manifest_id",
                "ti.phase4b.personal-bank-user-counts-preimplementation-sql");
        manifest.put("schema_version", 1);
        manifest.put("source_class", PersonalBankUserCountsEvidenceSql.class.getName());
        manifest.put("scope", "test-only-preimplementation-evidence");
        manifest.put("baseline_route_owner", "personalbank");
        manifest.put("production_owner_authorized", false);
        manifest.put("implementation_authorized", false);
        manifest.put("schema_or_index_delta_authorized", false);
        manifest.put("cross_context_table_owner", "learning");
        manifest.put("cross_context_table_owner_approval", "not-granted");
        manifest.put("runtime_tag_ddl_or_legacy_migration_in_scope", false);
        manifest.put("postgres_transaction_poisoning_sqlstate", "25P02");
        manifest.put("jdbc_compatibility_evidence", jdbcCompatibilityEvidence());
        manifest.put("q_type_parameter_type_evidence", qTypeParameterTypeEvidence());
        manifest.put("access_query_count", 2);
        manifest.put("statistics_query_count_per_nonempty_read", 4);
        manifest.put("query_family_count", queryFamilies.size());
        manifest.put("query_order", queryOrder);
        manifest.put("queries", ordinalQueries(queryFamilies));
        manifest.put("statistics_sequences", statisticsSequences());
        manifest.put("canonical_variants", canonicalVariants());
        manifest.put("large_tag_safety", largeTagSafety());
        manifest.put("empty_resolved_tag_ids", emptyResolvedTagIds());
        manifest.put("raw_type_projection", rawTypeProjection());
        manifest.put("legacy_join_shape", legacyJoinShape());

        assertThat(queryOrder).containsExactly(
                PersonalBankUserCountsEvidenceSql.BANK_ACCESS_ID,
                PersonalBankUserCountsEvidenceSql.SHARE_ACCESS_ID,
                PersonalBankUserCountsEvidenceSql.ALL_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.FAVORITES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.MISTAKES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.ALL_TYPES_ID,
                PersonalBankUserCountsEvidenceSql.FAVORITES_TYPES_ID,
                PersonalBankUserCountsEvidenceSql.MISTAKES_TYPES_ID);
        assertThat(queryFamilies).hasSize(8);
        assertThat(canonicalVariants()).hasSize(5);
        assertThat(statisticsSequences()).containsOnlyKeys("all", "favorites", "mistakes");
        assertThat(queryFamilies.get(1).parameterOrder())
                .containsExactly("user_id", "bank_id");
        assertThat(queryFamilies.get(1).parameters()).containsExactly(
                Map.entry("user_id", "bigint"),
                Map.entry("bank_id", "integer"));
        assertThat(qTypeParameterTypeEvidence()).containsExactly(
                Map.entry("parameter_name", "q_type_f"),
                Map.entry(
                        "manifest_parameters_field_scope",
                        "postgresql-explicit-prepare-declaration-for-query-plan-evidence"),
                Map.entry("manifest_prepare_type", "text"),
                Map.entry(
                        "jdbc_client_observation_scope",
                        "spring-jdbcclient-java-string-binding-in-compatibility-it"),
                Map.entry("jdbc_client_observed_pg_typeof", "character varying"),
                Map.entry("legacy_runtime_bind_type_claimed", false),
                Map.entry("cross_scope_type_identity_claimed", false),
                Map.entry("legacy_q_type_predicate_changed", false));

        ObjectMapper objectMapper = new ObjectMapper();
        String json = objectMapper.writerWithDefaultPrettyPrinter()
                .writeValueAsString(manifest) + "\n";
        assertThat(objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(manifest) + "\n")
                .isEqualTo(json);
        Path output = outputPath();
        Files.createDirectories(output.getParent());
        Files.writeString(output, json, StandardCharsets.UTF_8);

        assertThat(Files.readString(output, StandardCharsets.UTF_8)).isEqualTo(json);
    }

    private static List<Map<String, Object>> ordinalQueries(List<EvidenceQuery> queries) {
        return java.util.stream.IntStream.range(0, queries.size())
                .mapToObj(index -> query(index + 1, queries.get(index)))
                .toList();
    }

    private static Map<String, Object> query(int ordinal, EvidenceQuery evidenceQuery) {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("ordinal", ordinal);
        query.put("query_id", evidenceQuery.queryId());
        query.put("operation", evidenceQuery.operation());
        query.put("sql", evidenceQuery.sql());
        query.put("parameter_order", evidenceQuery.parameterOrder());
        query.put("parameters", new LinkedHashMap<>(evidenceQuery.parameters()));
        return query;
    }

    private static Map<String, List<String>> statisticsSequences() {
        Map<String, List<String>> sequences = new LinkedHashMap<>();
        sequences.put("all", sequenceIds(Source.ALL));
        sequences.put("favorites", sequenceIds(Source.FAVORITES));
        sequences.put("mistakes", sequenceIds(Source.MISTAKES));
        return sequences;
    }

    private static Map<String, Object> jdbcCompatibilityEvidence() {
        Map<String, Object> evidence = new LinkedHashMap<>();
        evidence.put(
                "integration_test",
                "io.saksk.ti.integration."
                        + "Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT");
        evidence.put("postgres_versions", List.of("16.14", "18.4"));
        evidence.put("initial_statement_failure_sqlstate", "42703");
        evidence.put("poisoned_followup_sqlstate", "25P02");
        evidence.put("rollback_recovery_required", true);
        return evidence;
    }

    private static Map<String, Object> qTypeParameterTypeEvidence() {
        Map<String, Object> evidence = new LinkedHashMap<>();
        evidence.put("parameter_name", "q_type_f");
        evidence.put(
                "manifest_parameters_field_scope",
                "postgresql-explicit-prepare-declaration-for-query-plan-evidence");
        evidence.put("manifest_prepare_type", "text");
        evidence.put(
                "jdbc_client_observation_scope",
                "spring-jdbcclient-java-string-binding-in-compatibility-it");
        evidence.put("jdbc_client_observed_pg_typeof", "character varying");
        evidence.put("legacy_runtime_bind_type_claimed", false);
        evidence.put("cross_scope_type_identity_claimed", false);
        evidence.put("legacy_q_type_predicate_changed", false);
        return evidence;
    }

    private static Map<String, Object> emptyResolvedTagIds() {
        Map<String, Object> empty = new LinkedHashMap<>();
        empty.put("http_result", "zero-count-success");
        empty.put("statistics_query_count", 0);
        empty.put("dynamic_in_query_emitted", false);
        return empty;
    }

    private static Map<String, Object> rawTypeProjection() {
        Map<String, Object> projection = new LinkedHashMap<>();
        projection.put("jdbc_type", "text");
        projection.put("nullable", true);
        projection.put("blank_and_unknown_values_preserved", true);
        projection.put("application_type_mapping_in_scope", false);
        return projection;
    }

    private static Map<String, Object> legacyJoinShape() {
        Map<String, Object> shape = new LinkedHashMap<>();
        shape.put("favorites_bank_id_predicate", false);
        shape.put("mistakes_bank_id_predicate", false);
        return shape;
    }

    private static List<String> sequenceIds(Source source) {
        return PersonalBankUserCountsEvidenceSql.statisticsSequence(source, false, 0)
                .stream()
                .map(EvidenceQuery::queryId)
                .toList();
    }

    private static List<Map<String, Object>> canonicalVariants() {
        return List.of(
                variant("unfiltered", false, 0),
                variant("q-type-only", true, 0),
                variant("tag-1", false, 1),
                variant("tag-3", false, 3),
                variant("q-type+tag-3", true, 3));
    }

    private static Map<String, Object> largeTagSafety() {
        int maximum = PersonalBankUserCountsEvidenceSql.EVIDENCE_MAX_TAG_PARAMETER_COUNT;
        String predicate = PersonalBankUserCountsEvidenceSql.dynamicTagPredicate(maximum);
        List<String> parameterOrder = java.util.stream.IntStream.range(0, maximum)
                .mapToObj(index -> "tq_" + index)
                .toList();
        Map<String, Object> safety = new LinkedHashMap<>();
        safety.put("canonical_variant_id", "tag-900-boundary");
        safety.put("evidence_render_bound", maximum);
        safety.put("evidence_renderer_overflow_rejected", true);
        safety.put("legacy_explicit_tag_id_limit_present", false);
        safety.put("legacy_explicit_tag_id_limit", null);
        safety.put(
                "overflow_above_evidence_bound",
                "not-a-captured-legacy-rejection");
        safety.put("production_limit_strategy_authorized", false);
        safety.put("values_interpolated_into_sql", false);
        safety.put("full_query_plan_required", false);
        safety.put("predicate", predicate);
        safety.put("parameter_order", parameterOrder);
        safety.put("parameter_names_unique", parameterOrder.stream().distinct().count()
                == maximum);
        return safety;
    }

    private static Map<String, Object> variant(
            String variantId,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        List<EvidenceQuery> statistics = PersonalBankUserCountsEvidenceSql
                .queryFamilies(qTypeFilter, tagParameterCount)
                .subList(2, 8);
        Map<String, Object> variant = new LinkedHashMap<>();
        variant.put("variant_id", variantId);
        variant.put("q_type_filter", qTypeFilter);
        variant.put("tag_parameter_count", tagParameterCount);
        variant.put("query_count", statistics.size());
        variant.put("queries", ordinalQueries(statistics));
        return variant;
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty(
                "ti.personal-bank-user-counts-evidence.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4b-personal-bank-user-counts-evidence-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Personal-bank user-counts evidence SQL manifest must stay under server/target");
        }
        return output;
    }
}
