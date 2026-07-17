package io.saksk.ti.learning.application.port;

import java.util.List;
import java.util.Optional;

/** Module-local learning memberships used to compose personal-bank user counts. */
public interface PersonalBankUserCountsQueryPort {

    List<Integer> findQuestionIdsByTag(long viewerId, int bankId, String tag);

    List<Integer> findFavoriteQuestionIds(
            long viewerId,
            Optional<List<Integer>> candidateQuestionIds);

    List<Integer> findMistakeQuestionIds(
            long viewerId,
            Optional<List<Integer>> candidateQuestionIds);
}
