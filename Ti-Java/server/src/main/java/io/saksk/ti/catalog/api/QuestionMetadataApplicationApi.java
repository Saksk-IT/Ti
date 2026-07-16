package io.saksk.ti.catalog.api;

/** Internal catalog boundary for question metadata owned by the catalog module. */
public interface QuestionMetadataApplicationApi {

    QuestionTypeCatalogView questionTypes();

    long countQuestions(QuestionCatalogCountQuery query);
}
