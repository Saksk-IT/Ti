package io.saksk.ti.operations.api;

import java.util.Objects;

/** Public, immutable projection of the two observed legacy login switches. */
public record LoginMethodsView(
        boolean phoneLoginEnabled,
        boolean wechatLoginEnabled,
        String defaultMode
) {

    public LoginMethodsView {
        defaultMode = Objects.requireNonNull(defaultMode, "defaultMode");
    }
}
