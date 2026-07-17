package io.saksk.ti.personalbank.api;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;

/** Immutable bank/question membership snapshot with a canonical SHA-256 digest. */
public record PersonalBankQuestionMembershipView(
        int bankId,
        boolean bankExists,
        List<Integer> existingQuestionIds,
        String membershipDigest
) {

    public PersonalBankQuestionMembershipView {
        if (bankId <= 0) {
            throw new IllegalArgumentException("bankId must be positive");
        }
        existingQuestionIds = normalizedIds(existingQuestionIds);
        membershipDigest = Objects.requireNonNull(membershipDigest, "membershipDigest");
        String expectedDigest = digest(bankId, bankExists, existingQuestionIds);
        if (!membershipDigest.equals(expectedDigest)) {
            throw new IllegalArgumentException(
                    "membershipDigest must match the canonical membership snapshot");
        }
    }

    public static PersonalBankQuestionMembershipView create(
            int bankId,
            boolean bankExists,
            List<Integer> existingQuestionIds
    ) {
        List<Integer> normalized = normalizedIds(existingQuestionIds);
        return new PersonalBankQuestionMembershipView(
                bankId,
                bankExists,
                normalized,
                digest(bankId, bankExists, normalized));
    }

    static String canonicalJson(
            int bankId,
            boolean bankExists,
            List<Integer> existingQuestionIds
    ) {
        return "{\"bank_id\":" + bankId
                + ",\"bank_exists\":" + bankExists
                + ",\"existing_question_ids\":["
                + existingQuestionIds.stream()
                        .map(String::valueOf)
                        .collect(java.util.stream.Collectors.joining(","))
                + "]}";
    }

    private static List<Integer> normalizedIds(List<Integer> questionIds) {
        Objects.requireNonNull(questionIds, "existingQuestionIds");
        if (questionIds.stream().anyMatch(Objects::isNull)) {
            throw new NullPointerException("existingQuestionIds must not contain null");
        }
        if (questionIds.stream().anyMatch(questionId -> questionId <= 0)) {
            throw new IllegalArgumentException(
                    "existingQuestionIds must contain only positive IDs");
        }
        return List.copyOf(questionIds.stream().distinct().sorted().toList());
    }

    private static String digest(
            int bankId,
            boolean bankExists,
            List<Integer> existingQuestionIds
    ) {
        try {
            byte[] payload = canonicalJson(bankId, bankExists, existingQuestionIds)
                    .getBytes(StandardCharsets.UTF_8);
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(payload));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }
}
