package io.saksk.ti.identity.infrastructure.security;

import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.Semaphore;
import java.util.function.BooleanSupplier;
import java.util.function.Supplier;

/** Process-wide, non-nestable resource budget for every password KDF. */
final class PasswordKdfBudget {
    static final int MAXIMUM_CONCURRENT_KDFS = 2;

    private static final PasswordKdfBudget PROCESS_WIDE =
            new PasswordKdfBudget(new Semaphore(MAXIMUM_CONCURRENT_KDFS, true));

    private final Semaphore permits;
    private final ThreadLocal<Boolean> heldByCurrentThread =
            ThreadLocal.withInitial(() -> Boolean.FALSE);

    PasswordKdfBudget(Semaphore permits) {
        this.permits = Objects.requireNonNull(permits, "permits");
    }

    static PasswordKdfBudget processWide() {
        return PROCESS_WIDE;
    }

    boolean tryRun(BooleanSupplier operation) {
        return tryCall(operation::getAsBoolean).orElse(false);
    }

    <T> T callOrThrow(Supplier<T> operation) {
        return tryCall(operation).orElseThrow(PasswordKdfCapacityException::new);
    }

    <T> Optional<T> tryCall(Supplier<T> operation) {
        Objects.requireNonNull(operation, "operation");
        if (heldByCurrentThread.get()) {
            throw new IllegalStateException("nested password KDF execution is forbidden");
        }
        if (!permits.tryAcquire()) {
            return Optional.empty();
        }

        heldByCurrentThread.set(Boolean.TRUE);
        try {
            return Optional.of(Objects.requireNonNull(operation.get(), "KDF result"));
        } finally {
            heldByCurrentThread.remove();
            permits.release();
        }
    }

    int availablePermits() {
        return permits.availablePermits();
    }

    static final class PasswordKdfCapacityException extends IllegalStateException {
        private PasswordKdfCapacityException() {
            super("password KDF capacity is exhausted");
        }
    }
}
