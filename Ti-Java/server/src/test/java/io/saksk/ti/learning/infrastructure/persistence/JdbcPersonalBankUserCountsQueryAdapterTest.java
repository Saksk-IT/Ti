package io.saksk.ti.learning.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.sql.Array;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.Types;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.support.SqlArrayValue;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

class JdbcPersonalBankUserCountsQueryAdapterTest {

    @Test
    void bindsCandidateIdsAsSinglePostgresqlIntegerArray() throws Exception {
        JdbcClient jdbc = mock(JdbcClient.class);
        JdbcClient.StatementSpec statement = mock(JdbcClient.StatementSpec.class);
        @SuppressWarnings("unchecked")
        JdbcClient.MappedQuerySpec<Integer> query = mock(JdbcClient.MappedQuerySpec.class);
        when(jdbc.sql(anyString())).thenReturn(statement);
        when(statement.param("viewer_id", 7_001L, Types.BIGINT)).thenReturn(statement);
        when(statement.param(eq("candidate_question_ids"), any(SqlArrayValue.class)))
                .thenReturn(statement);
        when(statement.query(Integer.class)).thenReturn(query);
        when(query.list()).thenReturn(List.of(8_101, 8_103));

        var adapter = new JdbcPersonalBankUserCountsQueryAdapter(jdbc);
        assertThat(adapter.findFavoriteQuestionIds(
                7_001L, Optional.of(List.of(8_103, 8_101))))
                .containsExactly(8_101, 8_103);

        ArgumentCaptor<String> sql = ArgumentCaptor.forClass(String.class);
        verify(jdbc).sql(sql.capture());
        assertThat(sql.getValue())
                .contains("question_id = ANY(CAST(:candidate_question_ids AS integer[]))")
                .doesNotContain(" IN (");

        ArgumentCaptor<SqlArrayValue> value = ArgumentCaptor.forClass(SqlArrayValue.class);
        verify(statement, times(1)).param(eq("candidate_question_ids"), value.capture());

        PreparedStatement preparedStatement = mock(PreparedStatement.class);
        Connection connection = mock(Connection.class);
        Array sqlArray = mock(Array.class);
        when(preparedStatement.getConnection()).thenReturn(connection);
        when(connection.createArrayOf(anyString(), any(Object[].class))).thenReturn(sqlArray);

        value.getValue().setValue(preparedStatement, 2);

        ArgumentCaptor<Object[]> elements = ArgumentCaptor.forClass(Object[].class);
        verify(connection).createArrayOf(eq("integer"), elements.capture());
        assertThat(elements.getValue()).containsExactly(8_103, 8_101);
        verify(preparedStatement).setArray(2, sqlArray);
    }

    @Test
    void keepsOptionalQueriesInIndependentReadOnlyTransactions() throws Exception {
        assertRequiresNewReadOnly(
                "findQuestionIdsByTag", long.class, int.class, String.class);
        assertRequiresNewReadOnly(
                "findFavoriteQuestionIds", long.class, Optional.class);
        assertRequiresNewReadOnly(
                "findMistakeQuestionIds", long.class, Optional.class);
    }

    @Test
    void keepsTagScopeExactAndRelationMembershipGlobalToTheViewer() {
        assertThat(JdbcPersonalBankUserCountsQueryAdapter.SELECT_TAG_QUESTION_IDS)
                .contains("scope = 'user_bank'")
                .contains("scope_id = :bank_id")
                .contains("tag = :tag")
                .contains("ORDER BY question_id");
        assertThat(JdbcPersonalBankUserCountsQueryAdapter.SELECT_FAVORITE_QUESTION_IDS)
                .contains("user_id = :viewer_id")
                .doesNotContain("bank_id");
        assertThat(JdbcPersonalBankUserCountsQueryAdapter.SELECT_MISTAKE_QUESTION_IDS)
                .contains("user_id = :viewer_id")
                .doesNotContain("bank_id");
    }

    @Test
    void presentEmptyCandidatesAreDeterminateWithoutTouchingJdbc() {
        JdbcClient jdbc = mock(JdbcClient.class);
        var adapter = new JdbcPersonalBankUserCountsQueryAdapter(jdbc);

        assertThat(adapter.findFavoriteQuestionIds(7_001L, Optional.of(List.of())))
                .isEmpty();
        assertThat(adapter.findMistakeQuestionIds(7_001L, Optional.of(List.of())))
                .isEmpty();
        verifyNoInteractions(jdbc);
    }

    private static void assertRequiresNewReadOnly(
            String methodName,
            Class<?>... parameterTypes
    ) throws Exception {
        Transactional transaction = JdbcPersonalBankUserCountsQueryAdapter.class
                .getDeclaredMethod(methodName, parameterTypes)
                .getAnnotation(Transactional.class);
        assertThat(transaction).isNotNull();
        assertThat(transaction.propagation()).isEqualTo(Propagation.REQUIRES_NEW);
        assertThat(transaction.readOnly()).isTrue();
    }
}
