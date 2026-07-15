package io.saksk.ti.web.error;

import jakarta.servlet.RequestDispatcher;
import jakarta.servlet.http.HttpServletRequest;
import io.saksk.ti.web.contract.ApiErrorEnvelope;
import io.saksk.ti.web.contract.ApiResponses;
import org.springframework.boot.webmvc.error.ErrorController;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SafeErrorController implements ErrorController {

    @RequestMapping("${spring.web.error.path:/error}")
    ResponseEntity<ApiErrorEnvelope> error(HttpServletRequest request) {
        HttpStatus status = resolveStatus(request);
        ErrorCode errorCode = mapErrorCode(status);
        return ResponseEntity
                .status(status)
                .body(ApiResponses.error(errorCode, null, request));
    }

    private HttpStatus resolveStatus(HttpServletRequest request) {
        Object statusCode = request.getAttribute(RequestDispatcher.ERROR_STATUS_CODE);
        if (statusCode instanceof Integer value) {
            HttpStatus resolved = HttpStatus.resolve(value);
            if (resolved != null) {
                return resolved;
            }
        }
        return HttpStatus.INTERNAL_SERVER_ERROR;
    }

    private ErrorCode mapErrorCode(HttpStatus status) {
        return switch (status) {
            case BAD_REQUEST -> ErrorCode.INVALID_REQUEST;
            case UNAUTHORIZED -> ErrorCode.AUTHENTICATION_REQUIRED;
            case FORBIDDEN -> ErrorCode.FORBIDDEN;
            case NOT_FOUND -> ErrorCode.RESOURCE_NOT_FOUND;
            case METHOD_NOT_ALLOWED -> ErrorCode.METHOD_NOT_ALLOWED;
            case UNSUPPORTED_MEDIA_TYPE -> ErrorCode.UNSUPPORTED_MEDIA_TYPE;
            case TOO_MANY_REQUESTS -> ErrorCode.RATE_LIMITED;
            case BAD_GATEWAY -> ErrorCode.UPSTREAM_FAILURE;
            case SERVICE_UNAVAILABLE -> ErrorCode.SERVICE_UNAVAILABLE;
            case GATEWAY_TIMEOUT -> ErrorCode.UPSTREAM_TIMEOUT;
            default -> ErrorCode.INTERNAL_ERROR;
        };
    }
}
