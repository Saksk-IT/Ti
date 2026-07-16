package io.saksk.ti.web.security;

import java.time.Clock;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.StringRedisTemplate;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties({
        LoginRateLimitProperties.class,
        CsrfIssuanceRateLimitProperties.class,
        LegacySessionExchangeProperties.class,
        TargetSessionLimitProperties.class,
        ClientAddressProperties.class
})
class LoginRateLimitConfiguration {

    @Bean
    ClientAddressResolver clientAddressResolver(ClientAddressProperties properties) {
        return new TrustedProxyClientAddressResolver(properties);
    }

    @Bean
    LoginRateLimiter loginRateLimiter(
            StringRedisTemplate redis,
            LoginRateLimitProperties properties,
            Clock clock
    ) {
        return new RedisLoginRateLimiter(redis, properties, clock);
    }

    @Bean
    CsrfIssuanceRateLimiter csrfIssuanceRateLimiter(
            StringRedisTemplate redis,
            CsrfIssuanceRateLimitProperties properties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        return new RedisCsrfIssuanceRateLimiter(redis, properties, loginProperties, clock);
    }

    @Bean
    LegacySessionExchangeGuard legacySessionExchangeGuard(
            StringRedisTemplate redis,
            LegacySessionExchangeProperties properties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        return new RedisLegacySessionExchangeGuard(redis, properties, loginProperties, clock);
    }

    @Bean
    TargetSessionRegistry targetSessionRegistry(
            StringRedisTemplate redis,
            TargetSessionLimitProperties properties,
            LoginRateLimitProperties loginProperties
    ) {
        return new RedisTargetSessionRegistry(redis, properties, loginProperties);
    }
}
