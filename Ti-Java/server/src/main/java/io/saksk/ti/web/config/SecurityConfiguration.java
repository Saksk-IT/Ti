package io.saksk.ti.web.config;

import io.saksk.ti.web.error.ErrorCode;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.compat.LegacyPublicBankSecurityErrorWriter;
import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.compat.LegacySubjectSecurityErrorWriter;
import io.saksk.ti.web.security.SessionBoundCsrfTokens;
import io.saksk.ti.web.security.ClientAddressResolver;
import io.saksk.ti.web.security.CsrfIssuanceRateLimitFilter;
import io.saksk.ti.web.security.CsrfIssuanceRateLimitProperties;
import io.saksk.ti.web.security.CsrfIssuanceRateLimiter;
import io.saksk.ti.web.security.PublicBankReadRequestResolver;
import io.saksk.ti.web.security.PublicBankReadRateLimitFilter;
import io.saksk.ti.web.security.PublicBankReadRateLimiter;
import io.saksk.ti.web.security.PersonalBankUserCountsCorsConfigurationSource;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimitFilter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimitFilter.WebAuthorizationBoundaryFilter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver;
import io.saksk.ti.web.security.TargetSessionProperties;
import io.saksk.ti.web.security.TargetSessionAuthenticationFilter;
import io.saksk.ti.web.security.SubjectReadRateLimitFilter;
import io.saksk.ti.web.security.SubjectReadRateLimiter;
import io.saksk.ti.web.security.SubjectReadRequestResolver;
import jakarta.servlet.DispatcherType;
import java.time.Clock;
import java.util.Enumeration;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpHeaders;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import org.springframework.security.web.csrf.CsrfFilter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.intercept.AuthorizationFilter;
import org.springframework.security.web.context.SecurityContextHolderFilter;
import org.springframework.security.web.header.writers.CacheControlHeadersWriter;
import org.springframework.security.web.header.writers.DelegatingRequestMatcherHeaderWriter;
import org.springframework.security.web.header.writers.frameoptions.XFrameOptionsHeaderWriter;
import org.springframework.security.web.header.writers.frameoptions.XFrameOptionsHeaderWriter.XFrameOptionsMode;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter.ReferrerPolicy;
import org.springframework.security.web.util.matcher.NegatedRequestMatcher;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.web.filter.CorsFilter;
import tools.jackson.databind.ObjectMapper;

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

    /**
     * Keeps authentication-stage availability failures inside the user-counts compatibility
     * envelope.  Those failures are emitted by {@link TargetSessionAuthenticationFilter} before
     * the route limiter or controller can select their alias-specific writer.
     */
    @Bean
    @Primary
    SafeSecurityErrorWriter compatibilityAwareSecurityErrorWriter(
            ObjectMapper objectMapper,
            ObjectProvider<PersonalBankUserCountsReadRequestResolver> userCountsRoutes,
            ObjectProvider<LegacyPersonalBankUserCountsSecurityErrorWriter> userCountsErrors,
            Clock clock
    ) {
        return new SafeSecurityErrorWriter(objectMapper) {
            @Override
            public void write(
                    jakarta.servlet.http.HttpServletRequest request,
                    jakarta.servlet.http.HttpServletResponse response,
                    ErrorCode errorCode
            ) throws java.io.IOException {
                PersonalBankUserCountsReadRequestResolver routes =
                        userCountsRoutes.getIfAvailable();
                LegacyPersonalBankUserCountsSecurityErrorWriter errors =
                        userCountsErrors.getIfAvailable();
                if ((errorCode == ErrorCode.SERVICE_UNAVAILABLE
                                || errorCode == ErrorCode.RATE_LIMITED)
                        && routes != null
                        && errors != null) {
                    var resolution = routes.resolveRateLimitedRoute(request);
                    if (resolution.isPresent()) {
                        var alias = resolution.orElseThrow().alias();
                        if (errorCode == ErrorCode.SERVICE_UNAVAILABLE) {
                            errors.writeServiceUnavailable(request, response, alias);
                        } else {
                            addAuthenticationRateLimitReset(response, clock);
                            errors.writeAuthenticationRateLimited(request, response, alias);
                        }
                        return;
                    }
                }
                super.write(request, response, errorCode);
            }
        };
    }

    private static void addAuthenticationRateLimitReset(
            jakarta.servlet.http.HttpServletResponse response,
            Clock clock
    ) {
        if (response.getHeader("X-RateLimit-Reset") != null) {
            return;
        }
        String rawRetryAfter = response.getHeader(HttpHeaders.RETRY_AFTER);
        if (rawRetryAfter == null) {
            return;
        }
        try {
            long retryAfter = Long.parseLong(rawRetryAfter);
            if (retryAfter >= 1 && retryAfter <= 604_800) {
                response.setHeader(
                        "X-RateLimit-Reset",
                        Long.toString(Math.addExact(
                                clock.instant().getEpochSecond(),
                                retryAfter)));
            }
        } catch (ArithmeticException | NumberFormatException ignored) {
            // The authentication guard owns Retry-After validation; never invent a reset value.
        }
    }

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
            ObjectProvider<SubjectReadRequestResolver> subjectReadRequestResolver,
            ObjectProvider<PublicBankReadRequestResolver> publicBankReadRequestResolver,
            ObjectProvider<PublicBankReadRateLimiter> publicBankReadRateLimiter,
            ObjectProvider<LegacyPublicBankSecurityErrorWriter> legacyPublicBankErrorWriter,
            ObjectProvider<PersonalBankUserCountsReadRequestResolver>
                    personalBankUserCountsReadRequestResolver,
            ObjectProvider<PersonalBankUserCountsReadRateLimiter>
                    personalBankUserCountsReadRateLimiter,
            ObjectProvider<LegacyPersonalBankUserCountsSecurityErrorWriter>
                    legacyPersonalBankUserCountsErrorWriter,
            Environment environment
    ) throws Exception {
        LegacySubjectSecurityErrorWriter legacySubjectErrors =
                legacySubjectErrorWriter.getIfAvailable();
        SubjectReadRequestResolver subjectReadRoutes =
                subjectReadRequestResolver.getIfAvailable();
        RequestMatcher subjectReadMatcher = request ->
                subjectReadRoutes != null && subjectReadRoutes.matches(request);
        PublicBankReadRequestResolver publicBankReadRoutes =
                publicBankReadRequestResolver.getIfAvailable();
        RequestMatcher publicBankReadMatcher = request ->
                publicBankReadRoutes != null && publicBankReadRoutes.matches(request);
        PersonalBankUserCountsReadRequestResolver userCountsReadRoutes =
                personalBankUserCountsReadRequestResolver.getIfAvailable();
        LegacyPersonalBankUserCountsSecurityErrorWriter userCountsErrors =
                legacyPersonalBankUserCountsErrorWriter.getIfAvailable();
        PersonalBankUserCountsReadRateLimiter userCountsLimiter =
                personalBankUserCountsReadRateLimiter.getIfAvailable();
        ClientAddressResolver addressResolver = clientAddresses.getIfAvailable();
        RequestMatcher userCountsCandidateMatcher = request ->
                userCountsReadRoutes != null
                        && userCountsReadRoutes.resolveCandidate(request).isPresent();
        RequestMatcher userCountsProtectedReadMatcher = request ->
                userCountsReadRoutes != null
                        && userCountsReadRoutes.resolveRateLimitedRoute(request).isPresent();
        RequestMatcher userCountsWebAuthorizationMatcher = request ->
                userCountsReadRoutes != null
                        && userCountsReadRoutes.resolveRateLimitedRoute(request)
                                .filter(resolution -> resolution.alias()
                                        == PersonalBankUserCountsReadRequestResolver.Alias.WEB)
                                .isPresent()
                        && hasAnyAuthorizationHeader(request);
        RequestMatcher legacyCompatibilityReads = request ->
                LEGACY_LOGIN_METHODS_READ.matches(request)
                        || subjectReadMatcher.matches(request)
                        || publicBankReadMatcher.matches(request)
                        || userCountsCandidateMatcher.matches(request);
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
                        .requestMatchers(publicBankReadMatcher).permitAll()
                        .requestMatchers(userCountsWebAuthorizationMatcher).denyAll()
                        .requestMatchers(userCountsProtectedReadMatcher).authenticated()
                        .requestMatchers(userCountsCandidateMatcher).permitAll()
                        .requestMatchers(subjectReadMatcher).authenticated()
                        .anyRequest().denyAll())
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint((request, response, exception) -> {
                            if (userCountsReadRoutes != null && userCountsErrors != null) {
                                var userCounts = userCountsReadRoutes
                                        .resolveRateLimitedRoute(request);
                                if (userCounts.isPresent()) {
                                    userCountsErrors.writeAuthenticationRequired(
                                            request,
                                            response,
                                            userCounts.orElseThrow().alias());
                                    return;
                                }
                            }
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
                        .accessDeniedHandler((request, response, exception) -> {
                            if (userCountsReadRoutes != null && userCountsErrors != null) {
                                var userCounts = userCountsReadRoutes
                                        .resolveRateLimitedRoute(request);
                                if (userCounts.isPresent()) {
                                    userCountsErrors.writeAuthenticationRequired(
                                            request,
                                            response,
                                            userCounts.orElseThrow().alias());
                                    return;
                                }
                            }
                            errorWriter.write(request, response, ErrorCode.FORBIDDEN);
                        }))
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
                                userCountsCandidateMatcher,
                                new ReferrerPolicyHeaderWriter(
                                        ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN)))
                        .addHeaderWriter(new DelegatingRequestMatcherHeaderWriter(
                                otherRequests,
                                new XFrameOptionsHeaderWriter(XFrameOptionsMode.DENY))))
                .requestCache(cache -> cache.disable())
                .formLogin(AbstractHttpConfigurer::disable)
                .httpBasic(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable);

        boolean userCountsBoundaryInstalled = false;
        if (userCountsReadRoutes != null) {
            if (userCountsLimiter == null
                    || userCountsErrors == null
                    || addressResolver == null) {
                throw new IllegalStateException(
                        "User-counts route boundary requires its rate limiter, address resolver, "
                                + "and compatibility error writer");
            }
            PersonalBankUserCountsCorsConfigurationSource userCountsCors =
                    new PersonalBankUserCountsCorsConfigurationSource(
                            userCountsReadRoutes,
                            environment);
            http.addFilterAt(userCountsCors.securityFilter(userCountsErrors), CorsFilter.class);
            http.addFilterAfter(
                    new WebAuthorizationBoundaryFilter(
                            userCountsLimiter,
                            userCountsErrors,
                            userCountsReadRoutes,
                            addressResolver),
                    CorsFilter.class);
            userCountsBoundaryInstalled = true;
        }

        TargetSessionAuthenticationFilter authenticationFilter = sessionAuthentication.getIfAvailable();
        if (authenticationFilter != null) {
            if (userCountsBoundaryInstalled) {
                http.addFilterAfter(authenticationFilter, WebAuthorizationBoundaryFilter.class);
            } else {
                http.addFilterAfter(authenticationFilter, SecurityContextHolderFilter.class);
            }
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
        PublicBankReadRateLimiter publicBankLimiter = publicBankReadRateLimiter.getIfAvailable();
        LegacyPublicBankSecurityErrorWriter legacyPublicBankErrors =
                legacyPublicBankErrorWriter.getIfAvailable();
        if (publicBankLimiter != null) {
            if (legacyPublicBankErrors == null
                    || publicBankReadRoutes == null
                    || addressResolver == null) {
                throw new IllegalStateException(
                        "Public-bank read limiter requires its route resolver, address resolver, "
                                + "and error writer");
            }
            PublicBankReadRateLimitFilter publicBankReadFilter =
                    new PublicBankReadRateLimitFilter(
                            publicBankLimiter,
                            legacyPublicBankErrors,
                            publicBankReadRoutes,
                            addressResolver);
            if (authenticationFilter != null) {
                http.addFilterAfter(
                        publicBankReadFilter,
                        TargetSessionAuthenticationFilter.class);
            } else {
                http.addFilterAfter(publicBankReadFilter, SecurityContextHolderFilter.class);
            }
        }
        if (userCountsReadRoutes != null) {
            if (userCountsLimiter == null
                    || userCountsErrors == null
                    || addressResolver == null) {
                throw new IllegalStateException(
                        "User-counts routes require their rate limiter, address resolver, "
                                + "and compatibility error writer");
            }
            PersonalBankUserCountsReadRateLimitFilter userCountsReadFilter =
                    new PersonalBankUserCountsReadRateLimitFilter(
                            userCountsLimiter,
                            userCountsErrors,
                            userCountsReadRoutes,
                            addressResolver);
            if (authenticationFilter != null) {
                http.addFilterAfter(
                        userCountsReadFilter,
                        TargetSessionAuthenticationFilter.class);
            } else {
                http.addFilterBefore(userCountsReadFilter, AuthorizationFilter.class);
            }
        }
        CsrfIssuanceRateLimiter issuanceRateLimiter = csrfIssuanceRateLimiter.getIfAvailable();
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

    private static boolean hasAnyAuthorizationHeader(jakarta.servlet.http.HttpServletRequest request) {
        Enumeration<String> values = request.getHeaders(HttpHeaders.AUTHORIZATION);
        return values != null && values.hasMoreElements();
    }
}
