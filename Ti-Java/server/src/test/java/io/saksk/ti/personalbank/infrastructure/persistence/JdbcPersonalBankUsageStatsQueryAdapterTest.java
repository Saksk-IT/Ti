package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.BankAccess;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.SharedUserAccess;
import java.sql.ResultSet;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

class JdbcPersonalBankUsageStatsQueryAdapterTest {

    @Test
    void mapsNullableBankProjectionWithoutApplyingAuthorizationOrStatusPolicy()
            throws Exception {
        ResultSet row = mock(ResultSet.class);
        when(row.getInt("id")).thenReturn(-7);
        when(row.getObject("user_id")).thenReturn(null);
        when(row.getObject("is_public", Boolean.class)).thenReturn(null);
        when(row.getObject("status", Integer.class)).thenReturn(-2);

        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.mapBank(row, 0))
                .isEqualTo(new BankAccess(-7, null, null, -2));
    }

    @Test
    void widensThePostgresInt4OwnerProjectionWithoutNarrowing() throws Exception {
        ResultSet row = mock(ResultSet.class);
        when(row.getInt("id")).thenReturn(7_101);
        when(row.getObject("user_id")).thenReturn(7_001);
        when(row.getObject("is_public", Boolean.class)).thenReturn(false);
        when(row.getObject("status", Integer.class)).thenReturn(1);

        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.mapBank(row, 0))
                .isEqualTo(new BankAccess(7_101, 7_001L, false, 1));
    }

    @Test
    void keepsSharedUserAndExpiryValuesRawForTheApplicationPolicy() throws Exception {
        ResultSet row = mock(ResultSet.class);
        Object rawUserId = " 7003 ";
        Object rawExpiry = "malformed-expiry";
        when(row.getObject("user_id")).thenReturn(rawUserId);
        when(row.getObject("expires_at")).thenReturn(rawExpiry);

        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.mapSharedUser(row, 0))
                .isEqualTo(new SharedUserAccess(rawUserId, rawExpiry));
    }

    @Test
    void keepsPublicUserIdRawForTheApplicationPolicy() throws Exception {
        ResultSet row = mock(ResultSet.class);
        Object rawUserId = -9L;
        when(row.getObject("user_id")).thenReturn(rawUserId);

        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.mapPublicUserId(row, 0))
                .isSameAs(rawUserId);
        assertRequiresNewReadOnly("listSharedUsers");
        assertRequiresNewReadOnly("listPublicUserIds");
    }

    private static void assertRequiresNewReadOnly(String methodName) throws Exception {
        Transactional transaction = JdbcPersonalBankUsageStatsQueryAdapter.class
                .getDeclaredMethod(methodName, int.class)
                .getAnnotation(Transactional.class);
        assertThat(transaction).isNotNull();
        assertThat(transaction.propagation()).isEqualTo(Propagation.REQUIRES_NEW);
        assertThat(transaction.readOnly()).isTrue();
    }
}
