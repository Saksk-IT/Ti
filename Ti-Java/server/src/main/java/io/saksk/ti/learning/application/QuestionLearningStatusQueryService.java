package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.QuestionLearningStatusApplicationApi;
import io.saksk.ti.learning.api.QuestionLearningStatusView;
import io.saksk.ti.learning.application.port.QuestionLearningStatusQueryPort;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class QuestionLearningStatusQueryService
        implements QuestionLearningStatusApplicationApi {

    private final QuestionLearningStatusQueryPort statuses;

    QuestionLearningStatusQueryService(QuestionLearningStatusQueryPort statuses) {
        this.statuses = Objects.requireNonNull(statuses, "statuses");
    }

    @Override
    @Transactional(readOnly = true)
    public QuestionLearningStatusView findStatus(
            AuthenticatedLearningViewer viewer,
            long questionId
    ) {
        viewer = Objects.requireNonNull(viewer, "viewer");
        if (questionId <= 0) {
            return new QuestionLearningStatusView(false, false);
        }
        QuestionLearningStatusQueryPort.Status status =
                statuses.find(viewer.identityId(), questionId);
        return new QuestionLearningStatusView(status.favorite(), status.mistake());
    }
}
