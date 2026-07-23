package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.CatalogQuestionEditReceiptPort;
import java.time.Clock;
import java.time.Duration;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcCatalogQuestionEditReceiptAdapterTestAccess {

    private JdbcCatalogQuestionEditReceiptAdapterTestAccess() {
    }

    public static CatalogQuestionEditReceiptPort create(
            JdbcClient jdbc,
            String keySecret,
            Duration receiptTtl,
            Clock clock
    ) {
        return new JdbcCatalogQuestionEditReceiptAdapter(
                jdbc,
                new CatalogQuestionEditIdempotencyProperties(keySecret, receiptTtl),
                clock);
    }
}
