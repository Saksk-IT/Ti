package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class QuestionEditWriteArchitectureTest {

    @Test
    void onlyCatalogOwnedMutationBoundaryStartsTheTransaction() {
        assertThat(QuestionEditApplicationService.class.getAnnotation(Transactional.class))
                .isNull();
        assertThat(QuestionEditWriteTransaction.class
                        .getDeclaredMethods())
                .filteredOn(method -> method.getName().equals("execute"))
                .singleElement()
                .extracting(method -> method.getAnnotation(Transactional.class))
                .isNotNull();
    }
}
