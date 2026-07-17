package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankUserCountsEvidenceSql.EvidenceQuery;
import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankUserCountsEvidenceSql.Source;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.junit.jupiter.api.Test;

class PersonalBankUserCountsEvidenceSqlContractTest {

    private static final List<String> QUERY_FAMILY_IDS = List.of(
            PersonalBankUserCountsEvidenceSql.BANK_ACCESS_ID,
            PersonalBankUserCountsEvidenceSql.SHARE_ACCESS_ID,
            PersonalBankUserCountsEvidenceSql.ALL_COUNT_ID,
            PersonalBankUserCountsEvidenceSql.FAVORITES_COUNT_ID,
            PersonalBankUserCountsEvidenceSql.MISTAKES_COUNT_ID,
            PersonalBankUserCountsEvidenceSql.ALL_TYPES_ID,
            PersonalBankUserCountsEvidenceSql.FAVORITES_TYPES_ID,
            PersonalBankUserCountsEvidenceSql.MISTAKES_TYPES_ID);

    @Test
    void freezesBothLegacyAccessQueriesWithoutAddingAuthorizationPredicates() {
        EvidenceQuery bank = PersonalBankUserCountsEvidenceSql.accessBank();
        assertThat(normalized(bank.sql()))
                .isEqualTo("select * from user_question_banks where id = :bank_id");
        assertThat(bank.parameterOrder()).containsExactly("bank_id");
        assertThat(bank.parameters()).containsExactly(Map.entry("bank_id", "integer"));
        assertThat(normalized(bank.sql())).doesNotContain(
                "status =", "user_id =", "is_public =", "for update", "order by");

        EvidenceQuery share = PersonalBankUserCountsEvidenceSql.accessShare();
        assertThat(normalized(share.sql())).isEqualTo(
                "select bsr.*, bs.permission, bs.is_active, bs.expires_at "
                        + "from bank_share_records bsr "
                        + "join bank_shares bs on bsr.share_id = bs.id "
                        + "where bsr.user_id = :user_id and bsr.bank_id = :bank_id "
                        + "and bsr.status = 1");
        assertThat(share.parameterOrder()).containsExactly("user_id", "bank_id");
        assertThat(share.parameters()).containsExactly(
                Map.entry("user_id", "bigint"),
                Map.entry("bank_id", "integer"));
        assertThat(normalized(share.sql())).doesNotContain(
                "bs.bank_id =", "bs.is_active =", "bs.expires_at >", "order by", "limit ");
        assertThat(occurrences(normalized(share.sql()), "bs.expires_at")).isOne();
    }

    @Test
    void freezesAllSixStatisticsFamiliesAndTheirViewerScoping() {
        List<EvidenceQuery> families = PersonalBankUserCountsEvidenceSql.queryFamilies(false, 0);
        assertThat(families).extracting(EvidenceQuery::queryId)
                .containsExactlyElementsOf(QUERY_FAMILY_IDS);

        Map<String, String> expectedSql = Map.of(
                PersonalBankUserCountsEvidenceSql.ALL_COUNT_ID,
                "select count(*) as cnt from user_bank_questions q "
                        + "where q.bank_id = :bank_id",
                PersonalBankUserCountsEvidenceSql.FAVORITES_COUNT_ID,
                "select count(*) as cnt from user_bank_questions q "
                        + "join user_bank_favorites f on q.id = f.question_id "
                        + "where q.bank_id = :bank_id and f.user_id = :uid",
                PersonalBankUserCountsEvidenceSql.MISTAKES_COUNT_ID,
                "select count(*) as cnt from user_bank_questions q "
                        + "join user_bank_mistakes m on q.id = m.question_id "
                        + "where q.bank_id = :bank_id and m.user_id = :uid",
                PersonalBankUserCountsEvidenceSql.ALL_TYPES_ID,
                "select distinct q.type as p_type from user_bank_questions q "
                        + "where q.bank_id = :bank_id order by q.type",
                PersonalBankUserCountsEvidenceSql.FAVORITES_TYPES_ID,
                "select distinct q.type as p_type from user_bank_questions q "
                        + "join user_bank_favorites f on q.id = f.question_id "
                        + "where q.bank_id = :bank_id and f.user_id = :uid "
                        + "order by q.type",
                PersonalBankUserCountsEvidenceSql.MISTAKES_TYPES_ID,
                "select distinct q.type as p_type from user_bank_questions q "
                        + "join user_bank_mistakes m on q.id = m.question_id "
                        + "where q.bank_id = :bank_id and m.user_id = :uid "
                        + "order by q.type");

        for (EvidenceQuery family : families.subList(2, families.size())) {
            assertThat(normalized(family.sql())).isEqualTo(expectedSql.get(family.queryId()));
            assertThat(family.parameterOrder()).doesNotContain("user_id");
        }

        assertThat(families.subList(2, families.size()))
                .filteredOn(family -> family.sql().contains(":uid"))
                .hasSize(4)
                .allSatisfy(family -> assertThat(family.parameters())
                        .containsEntry("uid", "bigint"));

        for (EvidenceQuery family : families) {
            String sql = normalized(family.sql());
            assertThat(sql).doesNotContain(
                    "f.bank_id =", "m.bank_id =", "f.status", "m.status", "group by");
        }
    }

    @Test
    void rendersQTypeAndDynamicNamedTagParametersInLegacyOrder() {
        assertThat(PersonalBankUserCountsEvidenceSql.dynamicTagPredicate(0))
                .isEqualTo("q.id IN (NULL)");
        assertThat(PersonalBankUserCountsEvidenceSql.dynamicTagPredicate(1))
                .isEqualTo("q.id IN (:tq_0)");
        assertThat(PersonalBankUserCountsEvidenceSql.dynamicTagPredicate(3))
                .isEqualTo("q.id IN (:tq_0, :tq_1, :tq_2)");
        assertThatThrownBy(() -> PersonalBankUserCountsEvidenceSql.dynamicTagPredicate(-1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("tagParameterCount must not be negative");
        assertThatThrownBy(() -> PersonalBankUserCountsEvidenceSql.queryFamilies(false, -1))
                .isInstanceOf(IllegalArgumentException.class);

        List<EvidenceQuery> families = PersonalBankUserCountsEvidenceSql.queryFamilies(true, 3);
        for (EvidenceQuery query : families.subList(2, families.size())) {
            String sql = normalized(query.sql());
            assertThat(sql).containsSubsequence(
                    "q.type = :q_type_f",
                    "q.id in (:tq_0, :tq_1, :tq_2)");
            assertThat(query.parameterOrder()).containsSubsequence(
                    "bank_id", "q_type_f", "tq_0", "tq_1", "tq_2");
            assertThat(query.parameters()).contains(
                    Map.entry("bank_id", "integer"),
                    Map.entry("q_type_f", "text"),
                    Map.entry("tq_0", "integer"),
                    Map.entry("tq_1", "integer"),
                    Map.entry("tq_2", "integer"));
        }

        assertThat(PersonalBankUserCountsEvidenceSql.queryFamilies(false, 0))
                .allSatisfy(query -> assertThat(normalized(query.sql()))
                        .doesNotContain(":q_type_f", ":tq_", "in (null)"));
    }

    @Test
    void evidenceLargeTagBoundaryUsesUniqueOrderedPlaceholdersWithoutChangingLegacySemantics() {
        int maximum = PersonalBankUserCountsEvidenceSql.EVIDENCE_MAX_TAG_PARAMETER_COUNT;
        EvidenceQuery query = PersonalBankUserCountsEvidenceSql
                .queryFamilies(true, maximum)
                .get(4);
        List<String> tagParameters = query.parameterOrder().stream()
                .filter(parameter -> parameter.startsWith("tq_"))
                .toList();

        assertThat(tagParameters).hasSize(maximum).doesNotHaveDuplicates();
        assertThat(tagParameters.getFirst()).isEqualTo("tq_0");
        assertThat(tagParameters.getLast()).isEqualTo("tq_899");
        assertThat(query.parameters().keySet()).containsSubsequence(
                "bank_id", "uid", "q_type_f", "tq_0", "tq_1", "tq_2");
        assertThat(query.parameters()).hasSize(maximum + 3);
        assertThat(query.sql())
                .contains("q.id IN (:tq_0, :tq_1, :tq_2")
                .contains(":tq_899)")
                .doesNotContain("8101", "8201", "89999");
        assertThatThrownBy(() -> PersonalBankUserCountsEvidenceSql.dynamicTagPredicate(
                maximum + 1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("tagParameterCount exceeds the evidence render bound of 900");
    }

    @Test
    void preservesParameterInsertionOrderAcrossRepeatedFamilyRendering() {
        List<List<Map.Entry<String, String>>> expected =
                PersonalBankUserCountsEvidenceSql.queryFamilies(true, 3).stream()
                        .map(query -> List.copyOf(query.parameters().entrySet()))
                        .toList();

        for (int iteration = 0; iteration < 32; iteration++) {
            assertThat(PersonalBankUserCountsEvidenceSql.queryFamilies(true, 3).stream()
                            .map(query -> List.copyOf(query.parameters().entrySet()))
                            .toList())
                    .isEqualTo(expected);
        }
    }

    @Test
    void freezesFourStatementSourceSequencesIncludingRepeatedQueries() {
        List<EvidenceQuery> all = sequence(Source.ALL);
        assertThat(all).extracting(EvidenceQuery::queryId).containsExactly(
                PersonalBankUserCountsEvidenceSql.ALL_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.FAVORITES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.MISTAKES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.ALL_TYPES_ID);

        List<EvidenceQuery> favorites = sequence(Source.FAVORITES);
        assertThat(favorites).extracting(EvidenceQuery::queryId).containsExactly(
                PersonalBankUserCountsEvidenceSql.FAVORITES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.FAVORITES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.MISTAKES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.FAVORITES_TYPES_ID);
        assertThat(favorites.get(0).sql()).isEqualTo(favorites.get(1).sql());

        List<EvidenceQuery> mistakes = sequence(Source.MISTAKES);
        assertThat(mistakes).extracting(EvidenceQuery::queryId).containsExactly(
                PersonalBankUserCountsEvidenceSql.MISTAKES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.FAVORITES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.MISTAKES_COUNT_ID,
                PersonalBankUserCountsEvidenceSql.MISTAKES_TYPES_ID);
        assertThat(mistakes.get(0).sql()).isEqualTo(mistakes.get(2).sql());

        for (List<EvidenceQuery> sequence : List.of(all, favorites, mistakes)) {
            assertThat(sequence).extracting(EvidenceQuery::operation)
                    .containsExactly("total", "favorites", "mistakes", "types");
        }
    }

    @Test
    void preimplementationEvidenceRemainsSelectOnlyWithNoSchemaOrIndexDelta() {
        for (boolean qTypeFilter : List.of(false, true)) {
            for (int tagParameterCount : List.of(0, 1, 3)) {
                for (EvidenceQuery query : PersonalBankUserCountsEvidenceSql.queryFamilies(
                        qTypeFilter, tagParameterCount)) {
                    assertThat(normalized(query.sql())).startsWith("select ").doesNotContain(
                            " insert ", " update ", " delete ", " merge ", " create ",
                            " alter ", " drop ", " truncate ", " grant ", " revoke ",
                            " create index ", " reindex ", ";");
                }
            }
        }
    }

    private static List<EvidenceQuery> sequence(Source source) {
        List<EvidenceQuery> sequence =
                PersonalBankUserCountsEvidenceSql.statisticsSequence(source, true, 3);
        assertThat(sequence).hasSize(4);
        return sequence;
    }

    private static String normalized(String sql) {
        return sql.strip().replaceAll("\\s+", " ").toLowerCase(Locale.ROOT);
    }

    private static int occurrences(String value, String fragment) {
        return (value.length() - value.replace(fragment, "").length()) / fragment.length();
    }
}
