package io.saksk.ti.learning.infrastructure.persistence;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(LearningWriteIdempotencyProperties.class)
class LearningWriteIdempotencyConfiguration {
}
