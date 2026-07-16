package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.QuestionMetadataApplicationApi;
import io.saksk.ti.catalog.api.QuestionTypeCatalogView;
import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class QuestionMetadataQueryService implements QuestionMetadataApplicationApi {

    private final QuestionTypeQueryPort questionTypes;

    QuestionMetadataQueryService(QuestionTypeQueryPort questionTypes) {
        this.questionTypes = questionTypes;
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
}
