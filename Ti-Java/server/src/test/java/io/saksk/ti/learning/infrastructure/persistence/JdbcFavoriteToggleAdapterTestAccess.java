package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.FavoriteTogglePort;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcFavoriteToggleAdapterTestAccess {

    private JdbcFavoriteToggleAdapterTestAccess() {
    }

    public static FavoriteTogglePort create(JdbcClient jdbc) {
        return new JdbcFavoriteToggleAdapter(jdbc);
    }
}
