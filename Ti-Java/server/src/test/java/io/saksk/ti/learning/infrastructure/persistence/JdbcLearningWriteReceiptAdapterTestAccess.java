package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import java.time.Clock;
import java.time.Duration;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class JdbcLearningWriteReceiptAdapterTestAccess {

    private JdbcLearningWriteReceiptAdapterTestAccess() {
    }

    public static LearningWriteReceiptPort create(
            JdbcClient jdbc,
            String keySecret,
            Duration receiptTtl,
            Clock clock
    ) {
        return new JdbcLearningWriteReceiptAdapter(
                jdbc,
                new LearningWriteIdempotencyProperties(keySecret, receiptTtl),
                clock);
    }
}
