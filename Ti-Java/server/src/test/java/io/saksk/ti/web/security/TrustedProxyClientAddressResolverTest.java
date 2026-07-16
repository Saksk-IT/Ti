package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

class TrustedProxyClientAddressResolverTest {

    @Test
    void ignoresForwardingHeadersFromAnUntrustedDirectPeer() {
        var resolver = resolver("10.0.0.0/8");
        MockHttpServletRequest request = requestFrom("198.51.100.7");
        request.addHeader("X-Forwarded-For", "203.0.113.9");

        assertThat(resolver.resolve(request)).isEqualTo("198.51.100.7");
    }

    @Test
    void walksRightToLeftAcrossOnlyExplicitlyTrustedProxyHops() {
        var resolver = resolver("10.0.0.0/8", "2001:db8:100::/48");
        MockHttpServletRequest request = requestFrom("10.0.0.2");
        request.addHeader("X-Forwarded-For", "198.51.100.9, 10.1.2.3");

        assertThat(resolver.resolve(request)).isEqualTo("198.51.100.9");
    }

    @Test
    void stopsAtTheFirstUntrustedHopSoAClientCannotInjectALeftmostIdentity() {
        var resolver = resolver("10.0.0.0/8");
        MockHttpServletRequest request = requestFrom("10.0.0.2");
        request.addHeader("X-Forwarded-For", "192.0.2.10, 203.0.113.8");

        assertThat(resolver.resolve(request)).isEqualTo("203.0.113.8");
    }

    @Test
    void malformedOrOversizedForwardingChainsFailBackToTheTrustedPeerBucket() {
        var resolver = resolver("10.0.0.0/8");
        MockHttpServletRequest malformed = requestFrom("10.0.0.2");
        malformed.addHeader("X-Forwarded-For", "attacker.example");
        MockHttpServletRequest oversized = requestFrom("10.0.0.3");
        oversized.addHeader("X-Forwarded-For", "1".repeat(2_049));

        assertThat(resolver.resolve(malformed)).isEqualTo("10.0.0.2");
        assertThat(resolver.resolve(oversized)).isEqualTo("10.0.0.3");
    }

    @Test
    void configurationRejectsInvalidOrExcessiveNetworks() {
        assertThatThrownBy(() -> new ClientAddressProperties(List.of("10.0.0.0/99")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("out of range");
        assertThatThrownBy(() -> new ClientAddressProperties(
                        java.util.Collections.nCopies(65, "127.0.0.1")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("At most 64");
    }

    private static TrustedProxyClientAddressResolver resolver(String... networks) {
        return new TrustedProxyClientAddressResolver(
                new ClientAddressProperties(List.of(networks)));
    }

    private static MockHttpServletRequest requestFrom(String address) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr(address);
        return request;
    }
}
