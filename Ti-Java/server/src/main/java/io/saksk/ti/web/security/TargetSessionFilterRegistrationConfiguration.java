package io.saksk.ti.web.security;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.session.web.http.SessionRepositoryFilter;

@Configuration(proxyBeanMethods = false)
class TargetSessionFilterRegistrationConfiguration {

    @Bean
    FilterRegistrationBean<TargetSessionAuthenticationFilter>
            targetSessionAuthenticationFilterRegistration(
                    TargetSessionAuthenticationFilter filter
            ) {
        FilterRegistrationBean<TargetSessionAuthenticationFilter> registration =
                new FilterRegistrationBean<>(filter);
        registration.setEnabled(false);
        return registration;
    }

    @Bean
    FilterRegistrationBean<TargetSessionReconciliationFilter>
            targetSessionReconciliationFilterRegistration(
                    TargetSessionReconciliationFilter filter
            ) {
        FilterRegistrationBean<TargetSessionReconciliationFilter> registration =
                new FilterRegistrationBean<>(filter);
        registration.setOrder(SessionRepositoryFilter.DEFAULT_ORDER - 1);
        return registration;
    }
}
