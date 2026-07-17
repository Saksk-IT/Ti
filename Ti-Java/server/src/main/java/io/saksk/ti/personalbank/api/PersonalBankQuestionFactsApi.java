package io.saksk.ti.personalbank.api;

import java.util.List;

/** HTTP-neutral provider boundary for personal-bank question access and facts. */
public interface PersonalBankQuestionFactsApi {

    PersonalBankQuestionAccessResult checkQuestionAccess(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    );

    PersonalBankQuestionFactsResult summarizeQuestions(
            AuthenticatedPersonalBankViewer viewer,
            PersonalBankQuestionSelection selection
    );

    PersonalBankQuestionMembershipView inspectQuestionMembership(
            int bankId,
            List<Integer> questionIds
    );
}
