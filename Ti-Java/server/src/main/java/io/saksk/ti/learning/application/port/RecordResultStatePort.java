package io.saksk.ti.learning.application.port;

/**
 * Learning-owned persistence boundary for one public-question answer attempt.
 *
 * <p>Every method requires the caller's writable learning transaction. The actor lock serializes
 * quota and latest-answer transitions without touching catalog or identity tables.
 */
public interface RecordResultStatePort {

    void lockActor(long actorId);

    long currentQuizCount(long actorId);

    void addOrIncrementMistake(long actorId, long questionId);

    void removeMistake(long actorId, long questionId);

    void replaceLatestAnswer(long actorId, long questionId, boolean correct);

    void incrementQuizCount(long actorId);
}
