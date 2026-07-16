package io.saksk.ti.web.security;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

@ConfigurationProperties("ti.security.client-address")
public record ClientAddressProperties(
        @DefaultValue List<String> trustedProxyCidrs
) {

    public ClientAddressProperties {
        trustedProxyCidrs = trustedProxyCidrs == null ? List.of() : List.copyOf(trustedProxyCidrs);
        if (trustedProxyCidrs.size() > 64) {
            throw new IllegalArgumentException("At most 64 trusted proxy networks are allowed");
        }
        trustedProxyCidrs.forEach(TrustedProxyClientAddressResolver::validateCidr);
    }
}
