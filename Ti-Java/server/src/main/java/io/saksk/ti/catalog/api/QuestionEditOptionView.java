package io.saksk.ti.catalog.api;

import java.util.Objects;

/** One legacy-compatible key/value option in an edited question response. */
public record QuestionEditOptionView(String key, String value) {

    public QuestionEditOptionView {
        key = Objects.requireNonNull(key, "key");
        value = Objects.requireNonNull(value, "value");
    }
}
