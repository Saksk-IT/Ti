package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;

/** Counts catalog-owned questions without reading identity or learning-owned relations. */
public interface QuestionCountQueryPort {

    long countQuestions(QuestionCatalogCountQuery query);
}
