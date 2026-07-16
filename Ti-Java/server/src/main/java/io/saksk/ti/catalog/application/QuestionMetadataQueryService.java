package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.QuestionMetadataApplicationApi;
import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionCatalogListQuery;
import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionCatalogSummaryView;
import io.saksk.ti.catalog.api.QuestionExportQuery;
import io.saksk.ti.catalog.api.QuestionExportRecordView;
import io.saksk.ti.catalog.api.QuestionTypeCatalogView;
import io.saksk.ti.catalog.application.port.QuestionCountQueryPort;
import io.saksk.ti.catalog.application.port.QuestionDetailQueryPort;
import io.saksk.ti.catalog.application.port.QuestionExportQueryPort;
import io.saksk.ti.catalog.application.port.QuestionSummaryQueryPort;
import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class QuestionMetadataQueryService implements QuestionMetadataApplicationApi {

    private final QuestionTypeQueryPort questionTypes;
    private final QuestionCountQueryPort questionCounts;
    private final QuestionDetailQueryPort questionDetails;
    private final QuestionSummaryQueryPort questionSummaries;
    private final QuestionExportQueryPort questionExports;

    QuestionMetadataQueryService(
            QuestionTypeQueryPort questionTypes,
            QuestionCountQueryPort questionCounts,
            QuestionDetailQueryPort questionDetails,
            QuestionSummaryQueryPort questionSummaries,
            QuestionExportQueryPort questionExports
    ) {
        this.questionTypes = questionTypes;
        this.questionCounts = questionCounts;
        this.questionDetails = questionDetails;
        this.questionSummaries = questionSummaries;
        this.questionExports = questionExports;
    }

    @Override
    @Transactional(readOnly = true)
    public QuestionTypeCatalogView questionTypes() {
        return new QuestionTypeCatalogView(questionTypes.findDistinctQuestionTypes().stream()
                .filter(Objects::nonNull)
                .distinct()
                .sorted()
                .toList());
    }

    @Override
    @Transactional(readOnly = true)
    public long countQuestions(QuestionCatalogCountQuery query) {
        Objects.requireNonNull(query, "query");
        if (query.candidateQuestionIds().filter(List::isEmpty).isPresent()) {
            return 0;
        }
        return questionCounts.countQuestions(query);
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<QuestionCatalogRecordView> findQuestionById(long questionId) {
        if (questionId < 0) {
            throw new IllegalArgumentException("questionId must not be negative");
        }
        return questionDetails.findQuestionById(questionId);
    }

    @Override
    @Transactional(readOnly = true)
    public List<QuestionCatalogSummaryView> listQuestionSummaries(QuestionCatalogListQuery query) {
        Objects.requireNonNull(query, "query");
        return List.copyOf(questionSummaries.listQuestionSummaries(query));
    }

    @Override
    @Transactional(readOnly = true)
    public List<QuestionExportRecordView> listQuestionExportRecords(QuestionExportQuery query) {
        Objects.requireNonNull(query, "query");
        return List.copyOf(questionExports.listQuestionExportRecords(query));
    }
}
