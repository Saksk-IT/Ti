package io.saksk.ti.catalog.infrastructure.persistence;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(CatalogQuestionEditIdempotencyProperties.class)
class CatalogQuestionEditIdempotencyConfiguration {
}
