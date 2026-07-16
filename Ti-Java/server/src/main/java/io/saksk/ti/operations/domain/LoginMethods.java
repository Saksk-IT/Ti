package io.saksk.ti.operations.domain;

public record LoginMethods(boolean phoneEnabled, boolean wechatEnabled) {

    public String defaultMode() {
        if (phoneEnabled) {
            return "phone";
        }
        return wechatEnabled ? "qr" : "password";
    }
}
