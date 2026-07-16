package io.saksk.ti.catalog.application.port;

import java.util.List;

/** Raw distinct question types from the legacy questions relation. */
public interface QuestionTypeQueryPort {

    List<String> findDistinctQuestionTypes();
}
