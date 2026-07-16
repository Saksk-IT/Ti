package io.saksk.ti.web.security;

import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.session")
public record TargetSessionProperties(
        @NotBlank String cookieName,
        @NotBlank String csrfCookieName,
        boolean secureCookie
) {

    public TargetSessionProperties {
        requireSafeCookieName(cookieName, "session");
        requireSafeCookieName(csrfCookieName, "CSRF");
        if ((cookieName.startsWith("__Host-") || csrfCookieName.startsWith("__Host-"))
                && !secureCookie) {
            throw new IllegalArgumentException("__Host- cookies require secure-cookie=true");
        }
    }

    private static void requireSafeCookieName(String name, String label) {
        if (name == null || name.isBlank() || !name.matches("[A-Za-z0-9_-]{1,64}")) {
            throw new IllegalArgumentException("Unsafe " + label + " cookie name");
        }
    }
}
