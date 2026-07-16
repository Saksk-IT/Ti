package io.saksk.ti.operations.application;

import io.saksk.ti.operations.api.LoginMethodsView;
import io.saksk.ti.operations.api.OperationsApplicationApi;
import io.saksk.ti.operations.application.port.LoginMethodsReadPort;
import io.saksk.ti.operations.domain.LoginMethods;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class LoginMethodsQueryService implements OperationsApplicationApi {

    private final LoginMethodsReadPort loginMethods;

    LoginMethodsQueryService(LoginMethodsReadPort loginMethods) {
        this.loginMethods = loginMethods;
    }

    @Override
    @Transactional(readOnly = true)
    public LoginMethodsView getLoginMethods() {
        LoginMethods current = loginMethods.read();
        return new LoginMethodsView(
                current.phoneEnabled(),
                current.wechatEnabled(),
                current.defaultMode());
    }
}
