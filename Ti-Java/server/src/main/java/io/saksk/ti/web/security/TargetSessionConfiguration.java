package io.saksk.ti.web.security;

import java.time.Duration;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.session.web.http.CookieSerializer;
import org.springframework.session.web.http.DefaultCookieSerializer;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(TargetSessionProperties.class)
class TargetSessionConfiguration {

    private static final int REMEMBER_MAX_AGE_SECONDS = Math.toIntExact(Duration.ofDays(7).toSeconds());

    @Bean
    CookieSerializer targetSessionCookieSerializer(TargetSessionProperties properties) {
        DefaultCookieSerializer delegate = new DefaultCookieSerializer();
        delegate.setCookieName(properties.cookieName());
        delegate.setCookiePath("/");
        delegate.setUseSecureCookie(properties.secureCookie());
        delegate.setUseHttpOnlyCookie(true);
        delegate.setUseBase64Encoding(true);
        delegate.setSameSite("Lax");

        return new CookieSerializer() {
            @Override
            public List<String> readCookieValues(jakarta.servlet.http.HttpServletRequest request) {
                List<String> values = delegate.readCookieValues(request);
                if (values.size() != 1
                        || !values.getFirst().matches("[A-Za-z0-9._-]{1,256}")) {
                    return List.of();
                }
                return List.of(values.getFirst());
            }

            @Override
            public void writeCookieValue(CookieValue cookieValue) {
                if (!cookieValue.getCookieValue().isEmpty()
                        && Boolean.TRUE.equals(cookieValue.getRequest().getAttribute(
                                TargetSessionCookiePolicy.REMEMBER_REQUEST_ATTRIBUTE))) {
                    cookieValue.setCookieMaxAge(REMEMBER_MAX_AGE_SECONDS);
                }
                delegate.writeCookieValue(cookieValue);
            }
        };
    }

    @Bean(name = "springSessionDefaultRedisSerializer")
    SafeSessionAttributeSerializer safeSessionAttributeSerializer() {
        return new SafeSessionAttributeSerializer();
    }
}
