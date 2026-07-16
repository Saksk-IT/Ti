package io.saksk.ti.catalog.api;

import java.util.List;
import java.util.Objects;

/** Visible subject metadata and the compatible visible-question aggregate. */
public record SubjectCatalogView(List<SubjectSummaryView> subjects, long quizCount) {

    public SubjectCatalogView {
        subjects = List.copyOf(Objects.requireNonNull(subjects, "subjects"));
        if (quizCount < 0) {
            throw new IllegalArgumentException("quizCount must not be negative");
        }
        long sum = subjects.stream().mapToLong(SubjectSummaryView::questionCount).sum();
        if (sum != quizCount) {
            throw new IllegalArgumentException("quizCount must equal visible subject counts");
        }
    }
}
