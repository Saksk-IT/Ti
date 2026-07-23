package io.saksk.ti.learning.api;

/** Stable quota facts used by the legacy-compatible 403 response. */
public record QuizLimitReached(long currentCount, int limitCount) {

    public String message() {
        return "已达到刷题限制（" + limitCount + "题），请付费或联系管理员";
    }
}
