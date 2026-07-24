package io.saksk.ti.learning.application.port;

/** Owner-local query for the learning flags attached to one question. */
public interface QuestionLearningStatusQueryPort {

    Status find(long identityId, long questionId);

    record Status(boolean favorite, boolean mistake) {
    }
}
