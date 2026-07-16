package io.saksk.ti.web.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.core.env.Environment;

@Configuration(proxyBeanMethods = false)
@Profile("prod")
public class ProductionSecretsConfiguration {

    @Bean
    ProductionSecretsGuard productionSecretsGuard(Environment environment) {
        requireNonBlank(environment, "spring.datasource.url");
        requireNonBlank(environment, "spring.datasource.username");
        requireNonBlank(environment, "spring.datasource.password");
        requireNonBlank(environment, "spring.data.redis.host");
        requireNonBlank(environment, "spring.data.redis.password");
        requireNonBlank(environment, "ti.security.login-rate-limit.key-secret");
        requireSecureHostCookie(environment, "ti.security.session.cookie-name");
        requireSecureHostCookie(environment, "ti.security.session.csrf-cookie-name");
        if (!environment.getProperty("ti.security.session.secure-cookie", Boolean.class, false)) {
            throw new IllegalStateException("Production session cookies must be secure");
        }
        if (environment.getProperty("ti.security.legacy-auth.enabled", Boolean.class, false)) {
            requireNonBlank(environment, "ti.security.legacy-auth.accept-until");
            requireNonBlank(environment, "ti.security.legacy-auth.secret");
        }
        return new ProductionSecretsGuard();
    }

    private void requireSecureHostCookie(Environment environment, String propertyName) {
        String value = environment.getRequiredProperty(propertyName);
        if (!value.startsWith("__Host-") || value.length() <= "__Host-".length()) {
            throw new IllegalStateException(
                    "Production cookie must use the __Host- prefix: " + propertyName);
        }
    }

    private void requireNonBlank(Environment environment, String propertyName) {
        String value = environment.getRequiredProperty(propertyName);
        if (value.isBlank()) {
            throw new IllegalStateException("Required production property is blank: " + propertyName);
        }
    }

    static final class ProductionSecretsGuard {
    }
}
