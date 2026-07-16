package io.saksk.ti.catalog.infrastructure.coordination;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(PublicBankSnapshotProperties.class)
class PublicBankSnapshotConfiguration {
}
