package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.CatalogQuestionEditReceiptPort;
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
class JdbcCatalogQuestionEditReceiptAdapter implements CatalogQuestionEditReceiptPort {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final byte[] HMAC_DOMAIN =
            "ti-java:catalog-question-edit-idempotency:v1\u0000"
                    .getBytes(StandardCharsets.UTF_8);

    private final JdbcClient jdbc;
    private final byte[] keySecret;
    private final java.time.Duration receiptTtl;
    private final Clock clock;

    @Autowired
    JdbcCatalogQuestionEditReceiptAdapter(
            JdbcClient jdbc,
            CatalogQuestionEditIdempotencyProperties properties,
            ObjectProvider<Clock> clocks
    ) {
        this(
                jdbc,
                properties,
                Objects.requireNonNull(clocks, "clocks").getIfAvailable(Clock::systemUTC));
    }

    JdbcCatalogQuestionEditReceiptAdapter(
            JdbcClient jdbc,
            CatalogQuestionEditIdempotencyProperties properties,
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
                        DELETE FROM catalog_question_edit_commands
                         WHERE actor_id = :actorId
                           AND key_hmac = :keyHmac
                           AND expires_at <= :now
                        """)
                .param("actorId", command.actorId())
                .param("keyHmac", keyHmac)
                .param("now", now)
                .update();

        int inserted = jdbc.sql("""
                        INSERT INTO catalog_question_edit_commands (
                            actor_id, key_hmac, request_sha256, question_id,
                            state, created_at, expires_at
                        ) VALUES (
                            :actorId, :keyHmac, :requestSha256, :questionId,
                            'PENDING', :createdAt, :expiresAt
                        )
                        ON CONFLICT (actor_id, key_hmac) DO NOTHING
                        """)
                .param("actorId", command.actorId())
                .param("keyHmac", keyHmac)
                .param("requestSha256", command.requestSha256())
                .param("questionId", command.questionId())
                .param("createdAt", now)
                .param("expiresAt", now.plus(receiptTtl))
                .update();
        if (inserted == 1) {
            return BeginResult.acquired();
        }
        if (inserted != 0) {
            throw new IllegalStateException(
                    "Unexpected catalog question-edit receipt insert count: " + inserted);
        }

        ReceiptRow existing = jdbc.sql("""
                        SELECT request_sha256, question_id, state,
                               response_status, response_body::text
                          FROM catalog_question_edit_commands
                         WHERE actor_id = :actorId
                           AND key_hmac = :keyHmac
                        """)
                .param("actorId", command.actorId())
                .param("keyHmac", keyHmac)
                .query((row, rowNumber) -> new ReceiptRow(
                        row.getBytes("request_sha256"),
                        row.getLong("question_id"),
                        row.getString("state"),
                        (Integer) row.getObject("response_status"),
                        row.getString("response_body")))
                .optional()
                .orElseThrow(() -> new IllegalStateException(
                        "Conflicting catalog receipt was not visible after insert arbitration"));

        if (existing.questionId() != command.questionId()
                || !MessageDigest.isEqual(existing.requestSha256(), command.requestSha256())) {
            return BeginResult.conflict();
        }
        if ("PENDING".equals(existing.state())) {
            return BeginResult.inProgress();
        }
        if (!"COMPLETED".equals(existing.state())
                || existing.responseStatus() == null
                || existing.responseBodyJson() == null) {
            throw new IllegalStateException("Catalog question-edit receipt has an invalid state");
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
                        UPDATE catalog_question_edit_commands
                           SET state = 'COMPLETED',
                               response_status = :responseStatus,
                               response_body = CAST(:responseBody AS jsonb),
                               completed_at = :completedAt
                         WHERE actor_id = :actorId
                           AND key_hmac = :keyHmac
                           AND request_sha256 = :requestSha256
                           AND question_id = :questionId
                           AND state = 'PENDING'
                           AND expires_at > :completedAt
                     RETURNING response_status, response_body::text
                        """)
                .param("responseStatus", command.responseStatus())
                .param("responseBody", command.responseBodyJson())
                .param("completedAt", now)
                .param("actorId", command.actorId())
                .param("keyHmac", keyHmac)
                .param("requestSha256", command.requestSha256())
                .param("questionId", command.questionId())
                .query((row, rowNumber) -> new StoredResponse(
                        row.getInt("response_status"),
                        row.getString("response_body")))
                .optional()
                .orElseThrow(() -> new IllegalStateException(
                        "Catalog receipt completion did not match one active acquisition"));
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
                    "Catalog idempotency receipts require an active writable transaction");
        }
    }

    private record ReceiptRow(
            byte[] requestSha256,
            long questionId,
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
