package io.saksk.ti.personalbank.application;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import io.saksk.ti.personalbank.api.PersonalBankOwnedShareView;
import io.saksk.ti.personalbank.api.PersonalBankShareListView;
import io.saksk.ti.personalbank.api.PersonalBankUsageStatsResult;
import io.saksk.ti.personalbank.api.PersonalBankUsageStatsView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankOwnedShareQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.sql.Timestamp;
import java.time.Clock;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeParseException;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class PersonalBankQueryService implements PersonalBankApplicationApi {

    private static final ZoneId BEIJING = ZoneId.of("Asia/Shanghai");

    private final PersonalBankCategoryQueryPort categories;
    private final PersonalBankShareQueryPort shares;
    private final PersonalBankOwnedShareQueryPort ownedShares;
    private final PersonalBankUsageStatsQueryPort usageStats;
    private final Clock clock;

    PersonalBankQueryService(
            PersonalBankCategoryQueryPort categories,
            PersonalBankShareQueryPort shares,
            PersonalBankOwnedShareQueryPort ownedShares,
            PersonalBankUsageStatsQueryPort usageStats,
            Clock clock
    ) {
        this.categories = Objects.requireNonNull(categories, "categories");
        this.shares = Objects.requireNonNull(shares, "shares");
        this.ownedShares = Objects.requireNonNull(ownedShares, "ownedShares");
        this.usageStats = Objects.requireNonNull(usageStats, "usageStats");
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    @Override
    @Transactional(readOnly = true)
    public List<PersonalBankCategoryView> listCategories(
            AuthenticatedPersonalBankViewer viewer
    ) {
        Objects.requireNonNull(viewer, "viewer");
        return List.copyOf(categories.listCategories(viewer.identityId()));
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<PersonalBankShareListView> findShares(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    ) {
        Objects.requireNonNull(viewer, "viewer");
        return shares.findShares(viewer.identityId(), bankId)
                .map(PersonalBankShareListView::new);
    }

    @Override
    @Transactional(readOnly = true)
    public List<PersonalBankOwnedShareView> listOwnedShares(
            AuthenticatedPersonalBankViewer viewer
    ) {
        Objects.requireNonNull(viewer, "viewer");
        return List.copyOf(ownedShares.listOwnedShares(viewer.identityId()));
    }

    @Override
    @Transactional(readOnly = true)
    public PersonalBankUsageStatsResult findUsageStats(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    ) {
        Objects.requireNonNull(viewer, "viewer");
        Optional<PersonalBankUsageStatsQueryPort.BankAccess> availableBank =
                usageStats.findBank(bankId);
        if (availableBank.isEmpty()
                || !Integer.valueOf(1).equals(availableBank.orElseThrow().status())) {
            return PersonalBankUsageStatsResult.notFound();
        }

        PersonalBankUsageStatsQueryPort.BankAccess bank = availableBank.orElseThrow();
        long ownerId = bank.ownerId() == null ? 0L : bank.ownerId();
        if (viewer.identityId() <= 0L
                || ownerId <= 0L
                || viewer.identityId() != ownerId) {
            return PersonalBankUsageStatsResult.forbidden();
        }

        LocalDateTime now = LocalDateTime.ofInstant(clock.instant(), BEIJING);
        BigInteger ownerKey = BigInteger.valueOf(ownerId);
        Set<BigInteger> sharedUsers = loadSharedUsers(bankId, ownerKey, now);
        Set<BigInteger> publicUsers = loadPublicUsers(bankId, ownerKey);
        Set<BigInteger> allNonOwnerUsers = new HashSet<>(sharedUsers);
        allNonOwnerUsers.addAll(publicUsers);

        PersonalBankUsageStatsView view = new PersonalBankUsageStatsView(
                bankId,
                Boolean.TRUE.equals(bank.publicBank()),
                ownerId,
                1,
                sharedUsers.size(),
                publicUsers.size(),
                allNonOwnerUsers.size() + 1,
                allNonOwnerUsers.size());
        return PersonalBankUsageStatsResult.available(view);
    }

    private Set<BigInteger> loadSharedUsers(
            int bankId,
            BigInteger ownerId,
            LocalDateTime now
    ) {
        try {
            Set<BigInteger> users = new HashSet<>();
            for (PersonalBankUsageStatsQueryPort.SharedUserAccess row
                    : usageStats.listSharedUsers(bankId)) {
                Optional<BigInteger> userId = legacyUserId(row.userId());
                if (userId.isPresent()
                        && !userId.orElseThrow().equals(ownerId)
                        && !legacyExpiryIsExpired(row.expiresAt(), now)) {
                    users.add(userId.orElseThrow());
                }
            }
            return users;
        } catch (RuntimeException ignored) {
            return Set.of();
        }
    }

    private Set<BigInteger> loadPublicUsers(int bankId, BigInteger ownerId) {
        try {
            Set<BigInteger> users = new HashSet<>();
            for (Object rawUserId : usageStats.listPublicUserIds(bankId)) {
                Optional<BigInteger> userId = legacyUserId(rawUserId);
                if (userId.isPresent() && !userId.orElseThrow().equals(ownerId)) {
                    users.add(userId.orElseThrow());
                }
            }
            return users;
        } catch (RuntimeException ignored) {
            return Set.of();
        }
    }

    private static Optional<BigInteger> legacyUserId(Object value) {
        if (value == null) {
            return Optional.empty();
        }
        try {
            BigInteger converted;
            if (value instanceof BigInteger integer) {
                converted = integer;
            } else if (value instanceof BigDecimal decimal) {
                converted = decimal.toBigInteger();
            } else if (value instanceof Byte
                    || value instanceof Short
                    || value instanceof Integer
                    || value instanceof Long) {
                converted = BigInteger.valueOf(((Number) value).longValue());
            } else if (value instanceof Float || value instanceof Double) {
                double floating = ((Number) value).doubleValue();
                if (!Double.isFinite(floating)) {
                    return Optional.empty();
                }
                converted = new BigDecimal(floating).toBigInteger();
            } else if (value instanceof Number number) {
                converted = new BigDecimal(number.toString()).toBigInteger();
            } else if (value instanceof Boolean bool) {
                converted = bool ? BigInteger.ONE : BigInteger.ZERO;
            } else if (value instanceof CharSequence text) {
                converted = parseLegacyIntegerText(text.toString());
            } else {
                return Optional.empty();
            }
            return converted.signum() == 0 ? Optional.empty() : Optional.of(converted);
        } catch (RuntimeException ignored) {
            return Optional.empty();
        }
    }

    private static BigInteger parseLegacyIntegerText(String rawValue) {
        String value = rawValue.strip();
        if (!value.matches("[+-]?\\p{Nd}(?:_?\\p{Nd})*")) {
            throw new NumberFormatException("not a legacy decimal integer");
        }
        return new BigInteger(value.replace("_", ""));
    }

    private static boolean legacyExpiryIsExpired(Object expiresAt, LocalDateTime now) {
        if (expiresAt == null) {
            return false;
        }
        if (expiresAt instanceof Boolean bool) {
            return bool;
        }
        if (expiresAt instanceof Number number) {
            return number.doubleValue() != 0.0d;
        }
        if (expiresAt instanceof LocalDateTime localDateTime) {
            return localDateTime.isBefore(now);
        }
        if (expiresAt instanceof LocalDate localDate) {
            return localDate.atStartOfDay().isBefore(now);
        }
        if (expiresAt instanceof Timestamp timestamp) {
            return timestamp.toLocalDateTime().isBefore(now);
        }
        if (expiresAt instanceof java.sql.Date date) {
            return date.toLocalDate().atStartOfDay().isBefore(now);
        }
        if (expiresAt instanceof CharSequence text) {
            if (text.isEmpty()) {
                return false;
            }
            try {
                String value = text.toString();
                if (value.length() > 10 && value.charAt(10) == ' ') {
                    value = value.substring(0, 10) + 'T' + value.substring(11);
                }
                try {
                    OffsetDateTime.parse(value);
                    return true;
                } catch (DateTimeParseException ignored) {
                    // The legacy comparison is naive; offset-aware values fail closed.
                }
                try {
                    return LocalDateTime.parse(value).isBefore(now);
                } catch (DateTimeParseException ignored) {
                    return LocalDate.parse(value).atStartOfDay().isBefore(now);
                }
            } catch (RuntimeException ignored) {
                return true;
            }
        }
        return true;
    }
}
