package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.Objects;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Repository
class JdbcLearningWriteReceiptAdapter implements LearningWriteReceiptPort {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final byte[] HMAC_DOMAIN =
            "ti-java:learning-write-idempotency:v1\u0000".getBytes(StandardCharsets.UTF_8);

    private final JdbcClient jdbc;
    private final byte[] keySecret;
    private final java.time.Duration receiptTtl;
    private final Clock clock;

    @Autowired
    JdbcLearningWriteReceiptAdapter(
            JdbcClient jdbc,
            LearningWriteIdempotencyProperties properties,
            ObjectProvider<Clock> clocks
    ) {
        this(
                jdbc,
                properties,
                Objects.requireNonNull(clocks, "clocks").getIfAvailable(Clock::systemUTC));
    }

    JdbcLearningWriteReceiptAdapter(
            JdbcClient jdbc,
            LearningWriteIdempotencyProperties properties,
            Clock clock
    ) {
        this.jdbc = Objects.requireNonNull(jdbc, "jdbc");
        properties = Objects.requireNonNull(properties, "properties");
        this.keySecret = properties.keySecretBytes();
        this.receiptTtl = properties.receiptTtl();
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    @Override
    @Transactional(propagation = Propagation.MANDATORY)
    public BeginResult begin(BeginCommand command) {
        requireWritableTransaction();
        command = Objects.requireNonNull(command, "command");
        OffsetDateTime now = now();
        byte[] keyHmac = keyHmac(command.idempotencyKey());

        jdbc.sql("""
                        DELETE FROM learning_idempotency_receipts
                         WHERE actor_id = :actorId
                           AND operation = :operation
                           AND key_hmac = :keyHmac
                           AND expires_at <= :now
                        """)
                .param("actorId", command.actorId())
                .param("operation", command.operation().databaseValue())
                .param("keyHmac", keyHmac)
                .param("now", now)
                .update();

        int inserted = jdbc.sql("""
                        INSERT INTO learning_idempotency_receipts (
                            actor_id, operation, key_hmac, request_sha256,
                            state, created_at, expires_at
                        ) VALUES (
                            :actorId, :operation, :keyHmac, :requestSha256,
                            'PENDING', :createdAt, :expiresAt
                        )
                        ON CONFLICT (actor_id, operation, key_hmac) DO NOTHING
                        """)
                .param("actorId", command.actorId())
                .param("operation", command.operation().databaseValue())
                .param("keyHmac", keyHmac)
                .param("requestSha256", command.requestSha256())
                .param("createdAt", now)
                .param("expiresAt", now.plus(receiptTtl))
                .update();
        if (inserted == 1) {
            return BeginResult.acquired();
        }
        if (inserted != 0) {
            throw new IllegalStateException("Unexpected learning receipt insert count: " + inserted);
        }

        ReceiptRow existing = jdbc.sql("""
                        SELECT request_sha256, state, response_status, response_body::text
                          FROM learning_idempotency_receipts
                         WHERE actor_id = :actorId
                           AND operation = :operation
                           AND key_hmac = :keyHmac
                        """)
                .param("actorId", command.actorId())
                .param("operation", command.operation().databaseValue())
                .param("keyHmac", keyHmac)
                .query((row, rowNumber) -> new ReceiptRow(
                        row.getBytes("request_sha256"),
                        row.getString("state"),
                        (Integer) row.getObject("response_status"),
                        row.getString("response_body")))
                .optional()
                .orElseThrow(() -> new IllegalStateException(
                        "Conflicting learning receipt was not visible after insert arbitration"));

        if (!MessageDigest.isEqual(existing.requestSha256(), command.requestSha256())) {
            return BeginResult.conflict();
        }
        if ("PENDING".equals(existing.state())) {
            return BeginResult.inProgress();
        }
        if (!"COMPLETED".equals(existing.state())
                || existing.responseStatus() == null
                || existing.responseBodyJson() == null) {
            throw new IllegalStateException("Learning receipt has an invalid persisted state");
        }
        return BeginResult.replay(
                new StoredResponse(existing.responseStatus(), existing.responseBodyJson()));
    }

    @Override
    @Transactional(propagation = Propagation.MANDATORY)
    public StoredResponse complete(CompleteCommand command) {
        requireWritableTransaction();
        command = Objects.requireNonNull(command, "command");
        OffsetDateTime now = now();
        byte[] keyHmac = keyHmac(command.idempotencyKey());

        return jdbc.sql("""
                        UPDATE learning_idempotency_receipts
                           SET state = 'COMPLETED',
                               response_status = :responseStatus,
                               response_body = CAST(:responseBody AS jsonb),
                               completed_at = :completedAt
                         WHERE actor_id = :actorId
                           AND operation = :operation
                           AND key_hmac = :keyHmac
                           AND request_sha256 = :requestSha256
                           AND state = 'PENDING'
                           AND expires_at > :completedAt
                     RETURNING response_status, response_body::text
                        """)
                .param("responseStatus", command.responseStatus())
                .param("responseBody", command.responseBodyJson())
                .param("completedAt", now)
                .param("actorId", command.actorId())
                .param("operation", command.operation().databaseValue())
                .param("keyHmac", keyHmac)
                .param("requestSha256", command.requestSha256())
                .query((row, rowNumber) -> new StoredResponse(
                        row.getInt("response_status"),
                        row.getString("response_body")))
                .optional()
                .orElseThrow(() -> new IllegalStateException(
                        "Learning receipt completion did not match one active acquisition"));
    }

    private OffsetDateTime now() {
        return OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }

    private byte[] keyHmac(String rawKey) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(keySecret, HMAC_ALGORITHM));
            mac.update(HMAC_DOMAIN);
            return mac.doFinal(rawKey.getBytes(StandardCharsets.UTF_8));
        } catch (java.security.GeneralSecurityException exception) {
            throw new IllegalStateException("HMAC-SHA-256 is unavailable", exception);
        }
    }

    private static void requireWritableTransaction() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()
                || TransactionSynchronizationManager.isCurrentTransactionReadOnly()) {
            throw new IllegalStateException(
                    "Learning idempotency receipts require an active writable transaction");
        }
    }

    private record ReceiptRow(
            byte[] requestSha256,
            String state,
            Integer responseStatus,
            String responseBodyJson
    ) {
        private ReceiptRow {
            requestSha256 = Arrays.copyOf(
                    Objects.requireNonNull(requestSha256, "requestSha256"),
                    requestSha256.length);
            state = Objects.requireNonNull(state, "state");
        }

        @Override
        public byte[] requestSha256() {
            return Arrays.copyOf(requestSha256, requestSha256.length);
        }
    }
}
