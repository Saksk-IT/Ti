package io.saksk.ti.learning.api;

/** Public learning boundary for the three legacy study write operations. */
public interface StudyWriteApplicationApi {

    StudyWriteResult<StudyLearnView> recordLearning(StudyLearnCommand command);

    StudyWriteResult<StudyReviewRecordView> recordReview(StudyReviewRecordCommand command);

    StudyWriteResult<StudyReviewMasterView> setReviewMastered(
            StudyReviewMasterCommand command);
}
