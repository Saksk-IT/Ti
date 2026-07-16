package io.saksk.ti.web.compat;

import io.saksk.ti.operations.api.LoginMethodsView;
import io.saksk.ti.operations.api.OperationsApplicationApi;
import io.saksk.ti.web.request.RequestId;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
class LegacyLoginMethodsController {

    private static final String LEGACY_JSON_CONTENT_TYPE = "application/json; charset=utf-8";
    private final OperationsApplicationApi operations;

    LegacyLoginMethodsController(OperationsApplicationApi operations) {
        this.operations = operations;
    }

    @GetMapping(value = "/login-methods", produces = "application/json;charset=UTF-8")
    ResponseEntity<LegacyLoginMethodsResponse> getLoginMethods(HttpServletRequest request) {
        LoginMethodsView current = operations.getLoginMethods();
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, LEGACY_JSON_CONTENT_TYPE)
                .header(HttpHeaders.VARY, "Origin, Cookie")
                .body(new LegacyLoginMethodsResponse(
                        "success",
                        0,
                        new LegacyLoginMethodsData(
                                current.phoneLoginEnabled(),
                                current.wechatLoginEnabled(),
                                current.defaultMode()),
                        RequestId.from(request),
                        ""));
    }

    record LegacyLoginMethodsResponse(
            String status,
            int code,
            LegacyLoginMethodsData data,
            String requestId,
            String message
    ) {
    }

    record LegacyLoginMethodsData(
            boolean phoneLoginEnabled,
            boolean wechatLoginEnabled,
            String defaultMode
    ) {
    }
}
