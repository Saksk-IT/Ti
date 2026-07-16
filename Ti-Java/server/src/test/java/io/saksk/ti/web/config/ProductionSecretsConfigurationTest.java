package io.saksk.ti.web.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.test.context.support.TestPropertySourceUtils;

class ProductionSecretsConfigurationTest {

    @Test
    void productionProfileFailsClosedWhenRequiredConnectionSecretsAreMissing() {
        try (AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext()) {
            context.getEnvironment().setActiveProfiles("prod");
            context.register(ProductionSecretsConfiguration.class);

            assertThatThrownBy(context::refresh)
                    .hasRootCauseInstanceOf(IllegalStateException.class)
                    .hasMessageContaining("spring.datasource.url");
        }
    }

    @Test
    void productionProfileAcceptsExplicitNonBlankConnectionConfiguration() {
        try (AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext()) {
            context.getEnvironment().setActiveProfiles("prod");
            TestPropertySourceUtils.addInlinedPropertiesToEnvironment(
                    context,
                    "spring.datasource.url=jdbc:postgresql://db:5432/ti",
                    "spring.datasource.username=ti",
                    "spring.datasource.password=db-secret",
                    "spring.data.redis.host=redis",
                    "spring.data.redis.password=redis-secret",
                    "ti.security.login-rate-limit.key-secret=production-login-rate-key-secret-0001",
                    "ti.security.session.cookie-name=__Host-ti_session",
                    "ti.security.session.csrf-cookie-name=__Host-ti_csrf",
                    "ti.security.session.secure-cookie=true"
            );
            context.register(ProductionSecretsConfiguration.class);
            context.refresh();

            assertThat(context.getBean(ProductionSecretsConfiguration.ProductionSecretsGuard.class))
                    .isNotNull();
        }
    }

    @Test
    void enabledLegacyCompatibilityRequiresItsOwnExplicitSecretsAndDeadline() {
        try (AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext()) {
            context.getEnvironment().setActiveProfiles("prod");
            TestPropertySourceUtils.addInlinedPropertiesToEnvironment(
                    context,
                    "spring.datasource.url=jdbc:postgresql://db:5432/ti",
                    "spring.datasource.username=ti",
                    "spring.datasource.password=db-secret",
                    "spring.data.redis.host=redis",
                    "spring.data.redis.password=redis-secret",
                    "ti.security.login-rate-limit.key-secret=production-login-rate-key-secret-0001",
                    "ti.security.session.cookie-name=__Host-ti_session",
                    "ti.security.session.csrf-cookie-name=__Host-ti_csrf",
                    "ti.security.session.secure-cookie=true",
                    "ti.security.legacy-auth.enabled=true",
                    "ti.security.legacy-auth.accept-until=",
                    "ti.security.legacy-auth.secret="
            );
            context.register(ProductionSecretsConfiguration.class);

            assertThatThrownBy(context::refresh)
                    .hasRootCauseInstanceOf(IllegalStateException.class)
                    .hasMessageContaining("ti.security.legacy-auth.accept-until");
        }
    }
}
