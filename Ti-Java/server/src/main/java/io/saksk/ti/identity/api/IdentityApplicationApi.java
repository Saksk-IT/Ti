package io.saksk.ti.identity.api;

public interface IdentityApplicationApi {

    AuthenticationResult authenticate(AuthenticateCommand command);
}
