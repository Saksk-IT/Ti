package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.QuestionMetadataApplicationApi;
import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionTypeCatalogView;
import io.saksk.ti.catalog.application.port.QuestionCountQueryPort;
import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
import java.util.List;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class QuestionMetadataQueryService implements QuestionMetadataApplicationApi {

    private final QuestionTypeQueryPort questionTypes;
    private final QuestionCountQueryPort questionCounts;

    QuestionMetadataQueryService(
            QuestionTypeQueryPort questionTypes,
            QuestionCountQueryPort questionCounts
    ) {
        this.questionTypes = questionTypes;
        this.questionCounts = questionCounts;
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
}
