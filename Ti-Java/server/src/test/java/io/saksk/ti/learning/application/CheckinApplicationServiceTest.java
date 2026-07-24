package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.CheckinCommand;
import io.saksk.ti.learning.api.CheckinResult;
import io.saksk.ti.learning.api.CheckinView;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

class CheckinApplicationServiceTest {

    private static final Clock CLOCK = Clock.fixed(
            Instant.parse("2026-07-23T16:30:00Z"),
            ZoneOffset.UTC);

    private final CheckinWriteTransaction transaction =
            mock(CheckinWriteTransaction.class);
    private final CheckinApplicationService service =
            new CheckinApplicationService(transaction, CLOCK);

    @Test
    void derivesOneBeijingDateAndTimestampBeforeEnteringTheTransaction() {
        CheckinCommand command = command();
        CheckinResult expected = CheckinResult.success(
                new CheckinView(
                        LocalDate.parse("2026-07-24"),
                        true,
                        Optional.of(LocalDateTime.parse("2026-07-24T00:30:00")),
                        1,
                        1,
                        true,
                        List.of("2026-07-24")),
                false);
        when(transaction.execute(
                        org.mockito.ArgumentMatchers.eq(91L),
                        org.mockito.ArgumentMatchers.eq(LocalDate.parse("2026-07-24")),
                        org.mockito.ArgumentMatchers.eq(
                                LocalDateTime.parse("2026-07-24T00:30:00")),
                        org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(expected);

        assertThat(service.checkIn(command)).isEqualTo(expected);
        verify(transaction).execute(
                org.mockito.ArgumentMatchers.eq(91L),
                org.mockito.ArgumentMatchers.eq(LocalDate.parse("2026-07-24")),
                org.mockito.ArgumentMatchers.eq(
                        LocalDateTime.parse("2026-07-24T00:30:00")),
                org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                org.mockito.ArgumentMatchers.any(byte[].class));
    }

    @Test
    void databaseConstraintFailureBecomesSafeMutationRejection() {
        when(transaction.execute(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenThrow(new DataIntegrityViolationException("synthetic"));

        assertThat(service.checkIn(command()).outcome())
                .isEqualTo(CheckinResult.Outcome.MUTATION_REJECTED);
    }

    @Test
    void fingerprintSeparatesActorsAndBeijingNaturalKeys() {
        assertThat(LearningWriteRequestFingerprints.checkin(
                        91,
                        LocalDate.parse("2026-07-24")))
                .containsExactly(LearningWriteRequestFingerprints.checkin(
                        91,
                        LocalDate.parse("2026-07-24")))
                .isNotEqualTo(LearningWriteRequestFingerprints.checkin(
                        92,
                        LocalDate.parse("2026-07-24")))
                .isNotEqualTo(LearningWriteRequestFingerprints.checkin(
                        91,
                        LocalDate.parse("2026-07-25")));
    }

    private static CheckinCommand command() {
        return new CheckinCommand(
                new AuthenticatedLearningViewer(91),
                LearningWriteIdempotencyKey.of("checkin-key"));
    }
}
