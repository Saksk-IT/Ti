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
        return new ProductionSecretsGuard();
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
