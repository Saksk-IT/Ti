package io.saksk.ti.identity.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.sql.ResultSet;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;

class JdbcAuthoritativeIdentityStateStoreTest {

    @Test
    void mapsNullableLegacyFlagsAndSessionVersionWithoutExposingOpenid() throws Exception {
        ResultSet row = mock(ResultSet.class);
        when(row.getLong("id")).thenReturn(4242L);
        when(row.getString("username")).thenReturn("database-user");
        when(row.getString("openid")).thenReturn("database-openid");
        when(row.getObject("is_admin", Boolean.class)).thenReturn(null);
        when(row.getObject("is_locked", Boolean.class)).thenReturn(null);
        when(row.getObject("session_version", Integer.class)).thenReturn(null);
        when(row.getObject("is_subject_admin", Boolean.class)).thenReturn(true);
        when(row.getObject("is_notification_admin", Boolean.class)).thenReturn(false);

        var state = JdbcAuthoritativeIdentityStateStore.mapState(row, 0);
        var authorized = state.authorize();

        assertThat(state.acceptsLegacyJwtOpenid("database-openid")).isTrue();
        assertThat(authorized.id()).isEqualTo(4242);
        assertThat(authorized.username()).isEqualTo("database-user");
        assertThat(authorized.administrator()).isFalse();
        assertThat(authorized.subjectAdministrator()).isTrue();
        assertThat(authorized.notificationAdministrator()).isFalse();
        assertThat(authorized.sessionVersion()).isZero();
        assertThat(authorized.toString()).doesNotContain("database-openid");
    }

    @Test
    void invalidIdentityIdDoesNotReachJdbc() {
        JdbcClient jdbc = mock(JdbcClient.class);
        var store = new JdbcAuthoritativeIdentityStateStore(jdbc);

        assertThat(store.findById(0)).isEmpty();
        assertThat(store.findById(-1)).isEmpty();

        verifyNoInteractions(jdbc);
    }
}
