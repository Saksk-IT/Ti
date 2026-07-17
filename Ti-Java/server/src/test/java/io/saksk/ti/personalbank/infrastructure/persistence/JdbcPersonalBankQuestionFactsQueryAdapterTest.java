package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.RawTypeCount;
import java.sql.Array;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Types;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.support.SqlArrayValue;

class JdbcPersonalBankQuestionFactsQueryAdapterTest {

    @Test
    void joinsShareRecordToRequestedBank() throws Exception {
        String sql = JdbcPersonalBankQuestionFactsQueryAdapter.SELECT_SHARE_GRANTS;

        assertThat(sql)
                .contains("FROM user_question_banks requested_bank")
                .contains("bsr.bank_id = requested_bank.id")
                .contains("bs.bank_id = requested_bank.id")
                .contains("requested_bank.id = :bank_id")
                .containsSubsequence("ORDER BY bs.id ASC NULLS LAST", "bsr.id ASC NULLS LAST")
                .doesNotContain(
                        "user_bank_favorites",
                        "user_bank_mistakes",
                        "user_progress",
                        "user_question_tag_items");

        assertThat(JdbcPersonalBankQuestionFactsQueryAdapter.SELECT_BANK_ACCESS)
                .contains("FROM user_question_banks requested_bank")
                .doesNotContain("bank_share_records", "bank_shares");
    }

    @Test
    void preservesMembershipDigestAndTypedIds() throws Exception {
        JdbcClient jdbc = mock(JdbcClient.class);
        JdbcClient.StatementSpec statement = mock(JdbcClient.StatementSpec.class);
        @SuppressWarnings("unchecked")
        JdbcClient.MappedQuerySpec<JdbcPersonalBankQuestionFactsQueryAdapter.MembershipRow>
                query = mock(JdbcClient.MappedQuerySpec.class);
        when(jdbc.sql(anyString())).thenReturn(statement);
        when(statement.param("bank_id", 7_101, Types.INTEGER)).thenReturn(statement);
        when(statement.param(eq("question_ids"), any(SqlArrayValue.class)))
                .thenReturn(statement);
        when(statement.query(anyMembershipMapper())).thenReturn(query);
        when(query.list()).thenReturn(List.of(
                new JdbcPersonalBankQuestionFactsQueryAdapter.MembershipRow(
                        true, Optional.of(8_101)),
                new JdbcPersonalBankQuestionFactsQueryAdapter.MembershipRow(
                        true, Optional.of(8_102)),
                new JdbcPersonalBankQuestionFactsQueryAdapter.MembershipRow(
                        true, Optional.of(8_102))));

        var adapter = new JdbcPersonalBankQuestionFactsQueryAdapter(jdbc);
        var membership = adapter.inspectQuestionMembership(
                7_101, List.of(8_103, 8_101, 8_102));

        assertThat(membership.bankExists()).isTrue();
        assertThat(membership.existingQuestionIds()).containsExactly(8_101, 8_102);
        var view = PersonalBankQuestionMembershipView.create(
                7_101, membership.bankExists(), membership.existingQuestionIds());
        assertThat(view.membershipDigest())
                .isEqualTo("f2facd9015ce6bbd5c947ad9abcd5c0da076dc51ecdfbcac4e3197f17b917b9d");

        ArgumentCaptor<SqlArrayValue> value = ArgumentCaptor.forClass(SqlArrayValue.class);
        verify(statement, times(1)).param(eq("question_ids"), value.capture());
        assertIntegerArray(value.getValue(), 2, 8_103, 8_101, 8_102);
        assertThat(JdbcPersonalBankQuestionFactsQueryAdapter.SELECT_MEMBERSHIP)
                .contains("q.bank_id = :bank_id")
                .contains("q.id = ANY(CAST(:question_ids AS integer[]))")
                .contains("ORDER BY q.id ASC");
    }

    @Test
    void bindsSummaryCandidatesAsSinglePostgresqlIntegerArray() throws Exception {
        JdbcClient jdbc = mock(JdbcClient.class);
        JdbcClient.StatementSpec statement = mock(JdbcClient.StatementSpec.class);
        @SuppressWarnings("unchecked")
        JdbcClient.MappedQuerySpec<RawTypeCount> query =
                mock(JdbcClient.MappedQuerySpec.class);
        when(jdbc.sql(anyString())).thenReturn(statement);
        when(statement.param("bank_id", 7_101, Types.INTEGER)).thenReturn(statement);
        when(statement.param(eq("candidate_question_ids"), any(SqlArrayValue.class)))
                .thenReturn(statement);
        when(statement.query(anyRawTypeMapper())).thenReturn(query);
        when(query.list()).thenReturn(List.of(
                new RawTypeCount(Optional.of("single_choice"), 2L),
                new RawTypeCount(Optional.empty(), 1L)));
        var selection = new PersonalBankQuestionSelection(
                7_101,
                Optional.empty(),
                Optional.of(List.of(8_103, 8_101, 8_103)));

        var facts = new JdbcPersonalBankQuestionFactsQueryAdapter(jdbc)
                .summarizeQuestions(selection);

        assertThat(facts.total()).isEqualTo(3L);
        assertThat(facts.rawTypes()).hasSize(2);
        ArgumentCaptor<String> sql = ArgumentCaptor.forClass(String.class);
        verify(jdbc).sql(sql.capture());
        assertThat(sql.getValue())
                .contains("q.id = ANY(CAST(:candidate_question_ids AS integer[]))")
                .contains("GROUP BY q.type")
                .contains("ORDER BY q.type ASC")
                .doesNotContain(" IN (");

        ArgumentCaptor<SqlArrayValue> value = ArgumentCaptor.forClass(SqlArrayValue.class);
        verify(statement).param(eq("candidate_question_ids"), value.capture());
        assertIntegerArray(value.getValue(), 2, 8_101, 8_103);
    }

    @Test
    void mapsNullAndEmptyRawTypesWithoutLosingTheirBigintCounts() throws Exception {
        ResultSet nullType = mock(ResultSet.class);
        when(nullType.getString("raw_type")).thenReturn(null);
        when(nullType.getLong("question_count")).thenReturn(4_294_967_296L);
        assertThat(JdbcPersonalBankQuestionFactsQueryAdapter.mapRawTypeCount(nullType, 0))
                .isEqualTo(new RawTypeCount(Optional.empty(), 4_294_967_296L));

        ResultSet emptyType = mock(ResultSet.class);
        when(emptyType.getString("raw_type")).thenReturn("");
        when(emptyType.getLong("question_count")).thenReturn(2L);
        assertThat(JdbcPersonalBankQuestionFactsQueryAdapter.mapRawTypeCount(emptyType, 0))
                .isEqualTo(new RawTypeCount(Optional.of(""), 2L));
    }

    @SuppressWarnings("unchecked")
    private static RowMapper<JdbcPersonalBankQuestionFactsQueryAdapter.MembershipRow>
            anyMembershipMapper() {
        return any(RowMapper.class);
    }

    @SuppressWarnings("unchecked")
    private static RowMapper<RawTypeCount> anyRawTypeMapper() {
        return any(RowMapper.class);
    }

    private static void assertIntegerArray(
            SqlArrayValue value,
            int parameterIndex,
            Object... expectedElements
    ) throws Exception {
        PreparedStatement preparedStatement = mock(PreparedStatement.class);
        Connection connection = mock(Connection.class);
        Array sqlArray = mock(Array.class);
        when(preparedStatement.getConnection()).thenReturn(connection);
        when(connection.createArrayOf(anyString(), any(Object[].class))).thenReturn(sqlArray);

        value.setValue(preparedStatement, parameterIndex);

        ArgumentCaptor<Object[]> elements = ArgumentCaptor.forClass(Object[].class);
        verify(connection).createArrayOf(eq("integer"), elements.capture());
        assertThat(elements.getValue()).containsExactly(expectedElements);
        verify(preparedStatement).setArray(parameterIndex, sqlArray);
    }
}
