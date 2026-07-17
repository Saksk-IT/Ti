package io.saksk.ti.learning.api;

/** Public learning boundary for HTTP-neutral answer and progress use cases. */
public interface LearningApplicationApi {

    PersonalBankUserCountsResult findPersonalBankUserCounts(
            AuthenticatedLearningViewer viewer,
            PersonalBankUserCountsQuery query);
}
