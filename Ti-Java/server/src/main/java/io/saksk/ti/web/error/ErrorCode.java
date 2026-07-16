package io.saksk.ti.web.error;

import org.springframework.http.HttpStatus;

public enum ErrorCode {
    INVALID_REQUEST(HttpStatus.BAD_REQUEST, "请求格式无效"),
    AUTHENTICATION_REQUIRED(HttpStatus.UNAUTHORIZED, "需要登录后访问"),
    FORBIDDEN(HttpStatus.FORBIDDEN, "无权执行此操作"),
    RESOURCE_NOT_FOUND(HttpStatus.NOT_FOUND, "资源不存在"),
    METHOD_NOT_ALLOWED(HttpStatus.METHOD_NOT_ALLOWED, "请求方法不受支持"),
    UNSUPPORTED_MEDIA_TYPE(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "请求内容类型不受支持"),
    PAYLOAD_TOO_LARGE(HttpStatus.CONTENT_TOO_LARGE, "请求内容过大"),
    CONFLICT(HttpStatus.CONFLICT, "请求与当前状态冲突"),
    BUSINESS_RULE_VIOLATION(HttpStatus.UNPROCESSABLE_CONTENT, "请求违反业务规则"),
    RATE_LIMITED(HttpStatus.TOO_MANY_REQUESTS, "请求过于频繁"),
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "服务暂时无法处理请求"),
    UPSTREAM_FAILURE(HttpStatus.BAD_GATEWAY, "上游服务调用失败"),
    SERVICE_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE, "服务暂时不可用"),
    UPSTREAM_TIMEOUT(HttpStatus.GATEWAY_TIMEOUT, "上游服务响应超时");

    private final HttpStatus status;
    private final String safeMessage;

    ErrorCode(HttpStatus status, String safeMessage) {
        this.status = status;
        this.safeMessage = safeMessage;
    }

    public HttpStatus status() {
        return status;
    }

    public String safeMessage() {
        return safeMessage;
    }
}
