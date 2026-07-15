package io.saksk.ti.web.config;

import jakarta.servlet.DispatcherType;
import io.saksk.ti.web.error.ErrorCode;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods = false)
public class SecurityConfiguration {

    @Bean
    SecurityFilterChain applicationSecurityFilterChain(
            HttpSecurity http,
            SafeSecurityErrorWriter errorWriter
    ) throws Exception {
        http
                .authorizeHttpRequests(authorize -> authorize
                        .dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
                        .requestMatchers(
                                "/actuator/health",
                                "/actuator/health/**",
                                "/actuator/prometheus",
                                "/livez",
                                "/readyz"
                        ).permitAll()
                        .anyRequest().denyAll())
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint((request, response, exception) ->
                                errorWriter.write(request, response, ErrorCode.AUTHENTICATION_REQUIRED))
                        .accessDeniedHandler((request, response, exception) ->
                                errorWriter.write(request, response, ErrorCode.FORBIDDEN)))
                .requestCache(cache -> cache.disable())
                .formLogin(AbstractHttpConfigurer::disable)
                .httpBasic(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable);

        return http.build();
    }
}
