package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.CheckinApplicationApi;
import io.saksk.ti.learning.api.CheckinCommand;
import io.saksk.ti.learning.api.CheckinResult;
import java.time.Clock;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Objects;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

@Service
class CheckinApplicationService implements CheckinApplicationApi {

    private static final ZoneId BEIJING = ZoneId.of("Asia/Shanghai");

    private final CheckinWriteTransaction transaction;
    private final Clock clock;

    @Autowired
    CheckinApplicationService(
            CheckinWriteTransaction transaction,
            ObjectProvider<Clock> clocks
    ) {
        this(
                transaction,
                Objects.requireNonNull(clocks, "clocks")
                        .getIfAvailable(Clock::systemUTC));
    }

    CheckinApplicationService(CheckinWriteTransaction transaction, Clock clock) {
        this.transaction = Objects.requireNonNull(transaction, "transaction");
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    @Override
    public CheckinResult checkIn(CheckinCommand command) {
        command = Objects.requireNonNull(command, "command");
        LocalDateTime now = LocalDateTime.ofInstant(clock.instant(), BEIJING);
        try {
            return transaction.execute(
                    command.viewer().identityId(),
                    now.toLocalDate(),
                    now,
                    command.idempotencyKey(),
                    LearningWriteRequestFingerprints.checkin(
                            command.viewer().identityId(),
                            now.toLocalDate()));
        } catch (DataIntegrityViolationException exception) {
            return CheckinResult.mutationRejected();
        }
    }
}
