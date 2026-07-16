package io.saksk.ti.web.config;

import io.saksk.ti.web.error.ErrorCode;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.compat.LegacySubjectSecurityErrorWriter;
import io.saksk.ti.web.security.SessionBoundCsrfTokens;
import io.saksk.ti.web.security.ClientAddressResolver;
import io.saksk.ti.web.security.CsrfIssuanceRateLimitFilter;
import io.saksk.ti.web.security.CsrfIssuanceRateLimitProperties;
import io.saksk.ti.web.security.CsrfIssuanceRateLimiter;
import io.saksk.ti.web.security.TargetSessionProperties;
import io.saksk.ti.web.security.TargetSessionAuthenticationFilter;
import io.saksk.ti.web.security.SubjectReadRateLimitFilter;
import io.saksk.ti.web.security.SubjectReadRateLimiter;
import io.saksk.ti.web.security.SubjectReadRequestResolver;
import jakarta.servlet.DispatcherType;
import java.time.Clock;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import org.springframework.security.web.csrf.CsrfFilter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.context.SecurityContextHolderFilter;
import org.springframework.security.web.header.writers.CacheControlHeadersWriter;
import org.springframework.security.web.header.writers.DelegatingRequestMatcherHeaderWriter;
import org.springframework.security.web.header.writers.frameoptions.XFrameOptionsHeaderWriter;
import org.springframework.security.web.header.writers.frameoptions.XFrameOptionsHeaderWriter.XFrameOptionsMode;
import org.springframework.security.web.util.matcher.NegatedRequestMatcher;
import org.springframework.security.web.util.matcher.RequestMatcher;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties({
        TargetSessionProperties.class,
        CsrfIssuanceRateLimitProperties.class
})
public class SecurityConfiguration {

    private static final RequestMatcher LEGACY_LOGIN_METHODS_READ = request -> {
        if (!"GET".equals(request.getMethod())) {
            return false;
        }
        String contextPath = request.getContextPath();
        String requestUri = request.getRequestURI();
        return requestUri.substring(contextPath.length()).equals("/api/auth/login-methods");
    };
    @Bean
    CsrfTokenRepository csrfTokenRepository(
            TargetSessionProperties sessionProperties,
            CsrfIssuanceRateLimitProperties issuanceProperties,
            Clock clock
    ) {
        return new SessionBoundCsrfTokens(sessionProperties, issuanceProperties, clock);
    }

    @Bean
    SecurityFilterChain applicationSecurityFilterChain(
            HttpSecurity http,
            SafeSecurityErrorWriter errorWriter,
            ObjectProvider<LegacySubjectSecurityErrorWriter> legacySubjectErrorWriter,
            CsrfTokenRepository csrfTokens,
            ObjectProvider<TargetSessionAuthenticationFilter> sessionAuthentication,
            ObjectProvider<CsrfIssuanceRateLimiter> csrfIssuanceRateLimiter,
            ObjectProvider<ClientAddressResolver> clientAddresses,
            ObjectProvider<SubjectReadRateLimiter> subjectReadRateLimiter,
            ObjectProvider<SubjectReadRequestResolver> subjectReadRequestResolver
    ) throws Exception {
        LegacySubjectSecurityErrorWriter legacySubjectErrors =
                legacySubjectErrorWriter.getIfAvailable();
        SubjectReadRequestResolver subjectReadRoutes =
                subjectReadRequestResolver.getIfAvailable();
        RequestMatcher subjectReadMatcher = request ->
                subjectReadRoutes != null && subjectReadRoutes.matches(request);
        RequestMatcher legacyCompatibilityReads = request ->
                LEGACY_LOGIN_METHODS_READ.matches(request) || subjectReadMatcher.matches(request);
        RequestMatcher otherRequests = new NegatedRequestMatcher(legacyCompatibilityReads);
        http
                .csrf(csrf -> csrf
                        .csrfTokenRepository(csrfTokens)
                        .csrfTokenRequestHandler(new CsrfTokenRequestAttributeHandler())
                        .ignoringRequestMatchers(request -> Boolean.TRUE.equals(request.getAttribute(
                                TargetSessionAuthenticationFilter
                                        .LEGACY_BEARER_AUTHENTICATED_ATTRIBUTE))))
                .authorizeHttpRequests(authorize -> authorize
                        .dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
                        .requestMatchers(
                                "/actuator/health",
                                "/actuator/health/**",
                                "/actuator/prometheus",
                                "/livez",
                                "/readyz",
                                "/api/auth/login-methods",
                                "/api/csrf",
                                "/api/login"
                        ).permitAll()
                        .requestMatchers(subjectReadMatcher).authenticated()
                        .anyRequest().denyAll())
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint((request, response, exception) -> {
                            if (subjectReadMatcher.matches(request)
                                    && legacySubjectErrors != null) {
                                legacySubjectErrors.writeAuthenticationRequired(request, response);
                                return;
                            }
                            errorWriter.write(
                                    request,
                                    response,
                                    ErrorCode.AUTHENTICATION_REQUIRED);
                        })
                        .accessDeniedHandler((request, response, exception) ->
                                errorWriter.write(request, response, ErrorCode.FORBIDDEN)))
                .headers(headers -> headers
                        .cacheControl(cache -> cache.disable())
                        .frameOptions(frame -> frame.disable())
                        .addHeaderWriter(new DelegatingRequestMatcherHeaderWriter(
                                otherRequests,
                                new CacheControlHeadersWriter()))
                        .addHeaderWriter(new DelegatingRequestMatcherHeaderWriter(
                                legacyCompatibilityReads,
                                new XFrameOptionsHeaderWriter(XFrameOptionsMode.SAMEORIGIN)))
                        .addHeaderWriter(new DelegatingRequestMatcherHeaderWriter(
                                otherRequests,
                                new XFrameOptionsHeaderWriter(XFrameOptionsMode.DENY))))
                .requestCache(cache -> cache.disable())
                .formLogin(AbstractHttpConfigurer::disable)
                .httpBasic(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable);

        TargetSessionAuthenticationFilter authenticationFilter = sessionAuthentication.getIfAvailable();
        if (authenticationFilter != null) {
            http.addFilterAfter(authenticationFilter, SecurityContextHolderFilter.class);
        }
        SubjectReadRateLimiter subjectLimiter = subjectReadRateLimiter.getIfAvailable();
        if (subjectLimiter != null) {
            if (legacySubjectErrors == null || subjectReadRoutes == null) {
                throw new IllegalStateException(
                        "Subject read limiter requires its route resolver and error writer");
            }
            SubjectReadRateLimitFilter subjectReadFilter =
                    new SubjectReadRateLimitFilter(
                            subjectLimiter,
                            legacySubjectErrors,
                            subjectReadRoutes);
            if (authenticationFilter != null) {
                http.addFilterAfter(subjectReadFilter, TargetSessionAuthenticationFilter.class);
            } else {
                http.addFilterAfter(subjectReadFilter, SecurityContextHolderFilter.class);
            }
        }
        CsrfIssuanceRateLimiter issuanceRateLimiter = csrfIssuanceRateLimiter.getIfAvailable();
        ClientAddressResolver addressResolver = clientAddresses.getIfAvailable();
        if (issuanceRateLimiter != null && addressResolver != null) {
            http.addFilterBefore(
                    new CsrfIssuanceRateLimitFilter(
                            issuanceRateLimiter,
                            addressResolver,
                            errorWriter),
                    CsrfFilter.class);
        }

        return http.build();
    }
}
