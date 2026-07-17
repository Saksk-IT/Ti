package io.saksk.ti.personalbank.application.port;

import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/** Reads only personalbank-owned access, question-summary, and membership facts. */
public interface PersonalBankQuestionFactsQueryPort {

    Optional<BankAccess> findAccess(long viewerId, int bankId);

    QuestionFacts summarizeQuestions(PersonalBankQuestionSelection selection);

    QuestionMembership inspectQuestionMembership(
            int bankId,
            List<Integer> questionIds
    );

    record BankAccess(
            int bankId,
            Long ownerId,
            Boolean publicBank,
            Integer status,
            List<ShareGrant> shareGrants
    ) {

        public BankAccess {
            if (bankId <= 0) {
                throw new IllegalArgumentException("bankId must be positive");
            }
            shareGrants = List.copyOf(
                    Objects.requireNonNull(shareGrants, "shareGrants"));
        }
    }

    record ShareGrant(
            int shareRecordId,
            int shareRecordBankId,
            Integer shareRecordStatus,
            int shareId,
            int shareBankId,
            String permission,
            Boolean active,
            LocalDateTime expiresAt
    ) {

        public ShareGrant {
            if (shareRecordId <= 0 || shareId <= 0) {
                throw new IllegalArgumentException("share IDs must be positive");
            }
            if (shareRecordBankId <= 0 || shareBankId <= 0) {
                throw new IllegalArgumentException("share bank IDs must be positive");
            }
        }
    }

    record QuestionFacts(long total, List<RawTypeCount> rawTypes) {

        public QuestionFacts {
            if (total < 0) {
                throw new IllegalArgumentException("total must not be negative");
            }
            rawTypes = List.copyOf(Objects.requireNonNull(rawTypes, "rawTypes"));
        }
    }

    record RawTypeCount(Optional<String> rawType, long count) {

        public RawTypeCount {
            rawType = Objects.requireNonNull(rawType, "rawType");
            if (count < 0) {
                throw new IllegalArgumentException("count must not be negative");
            }
        }
    }

    record QuestionMembership(boolean bankExists, List<Integer> existingQuestionIds) {

        public QuestionMembership {
            existingQuestionIds = List.copyOf(
                    Objects.requireNonNull(existingQuestionIds, "existingQuestionIds"));
        }
    }
}
