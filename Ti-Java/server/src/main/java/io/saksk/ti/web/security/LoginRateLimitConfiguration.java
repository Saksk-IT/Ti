package io.saksk.ti.web.security;

import java.security.MessageDigest;
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
        ClientAddressProperties.class,
        SubjectReadRateLimitProperties.class,
        PublicBankReadRateLimitProperties.class,
        PersonalBankUserCountsReadRateLimitProperties.class,
        TransactionWriteRateLimitProperties.class
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

    @Bean
    SubjectReadRateLimiter subjectReadRateLimiter(
            StringRedisTemplate redis,
            SubjectReadRateLimitProperties properties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        return new RedisSubjectReadRateLimiter(redis, properties, loginProperties, clock);
    }

    @Bean
    PublicBankReadRateLimiter publicBankReadRateLimiter(
            StringRedisTemplate redis,
            PublicBankReadRateLimitProperties properties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        return new RedisPublicBankReadRateLimiter(
                redis,
                properties,
                loginProperties,
                clock);
    }

    @Bean
    PersonalBankUserCountsReadRateLimiter personalBankUserCountsReadRateLimiter(
            StringRedisTemplate redis,
            PersonalBankUserCountsReadRateLimitProperties properties,
            PublicBankReadRateLimitProperties publicBankProperties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        if (properties.namespace().equals(publicBankProperties.namespace())) {
            throw new IllegalStateException(
                    "User-counts and public-bank rate limits require independent namespaces");
        }
        if (MessageDigest.isEqual(
                properties.keySecretBytes(),
                loginProperties.keySecretBytes())) {
            throw new IllegalStateException(
                    "User-counts and login rate limits require independent key material");
        }
        return new RedisPersonalBankUserCountsReadRateLimiter(redis, properties, clock);
    }

    @Bean
    TransactionWriteRateLimiter transactionWriteRateLimiter(
            StringRedisTemplate redis,
            TransactionWriteRateLimitProperties properties,
            PersonalBankUserCountsReadRateLimitProperties userCountsProperties,
            LoginRateLimitProperties loginProperties,
            Clock clock
    ) {
        if (properties.namespace().equals(userCountsProperties.namespace())) {
            throw new IllegalStateException(
                    "Transaction-write and user-counts limits require independent namespaces");
        }
        if (MessageDigest.isEqual(
                properties.keySecretBytes(),
                loginProperties.keySecretBytes())) {
            throw new IllegalStateException(
                    "Transaction-write and login limits require independent key material");
        }
        return new RedisTransactionWriteRateLimiter(redis, properties, clock);
    }
}
