package io.saksk.ti.web.security;

import jakarta.servlet.http.HttpServletRequest;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.List;

final class TrustedProxyClientAddressResolver implements ClientAddressResolver {

    private static final int MAXIMUM_FORWARDING_HEADER_BYTES = 2_048;
    private static final int MAXIMUM_FORWARDING_HOPS = 32;
    private static final String FORWARDED_FOR = "X-Forwarded-For";
    private static final String INVALID_PEER = "invalid-peer";

    private final List<Cidr> trustedProxies;

    TrustedProxyClientAddressResolver(ClientAddressProperties properties) {
        trustedProxies = properties.trustedProxyCidrs().stream().map(Cidr::parse).toList();
    }

    static void validateCidr(String value) {
        Cidr.parse(value);
    }

    @Override
    public String resolve(HttpServletRequest request) {
        InetAddress peer = parseAddress(request.getRemoteAddr());
        if (peer == null) {
            return INVALID_PEER;
        }
        if (!isTrusted(peer)) {
            return peer.getHostAddress();
        }

        List<InetAddress> forwarded = parseForwardedFor(request.getHeaders(FORWARDED_FOR));
        if (forwarded.isEmpty()) {
            return peer.getHostAddress();
        }

        InetAddress candidate = peer;
        for (int index = forwarded.size() - 1; index >= 0 && isTrusted(candidate); index--) {
            candidate = forwarded.get(index);
        }
        return candidate.getHostAddress();
    }

    private boolean isTrusted(InetAddress address) {
        return trustedProxies.stream().anyMatch(cidr -> cidr.contains(address));
    }

    private static List<InetAddress> parseForwardedFor(Enumeration<String> headerValues) {
        if (headerValues == null) {
            return List.of();
        }
        List<String> values = Collections.list(headerValues);
        int bytes = values.stream().mapToInt(String::length).sum();
        if (bytes == 0 || bytes > MAXIMUM_FORWARDING_HEADER_BYTES) {
            return List.of();
        }

        List<InetAddress> addresses = new ArrayList<>();
        for (String value : values) {
            for (String part : value.split(",", -1)) {
                if (addresses.size() == MAXIMUM_FORWARDING_HOPS) {
                    return List.of();
                }
                InetAddress address = parseAddress(part.strip());
                if (address == null) {
                    return List.of();
                }
                addresses.add(address);
            }
        }
        return List.copyOf(addresses);
    }

    private static InetAddress parseAddress(String value) {
        if (value == null
                || value.isBlank()
                || value.length() > 64
                || !value.matches("[0-9A-Fa-f:.]+")) {
            return null;
        }
        try {
            return InetAddress.getByName(value);
        } catch (UnknownHostException exception) {
            return null;
        }
    }

    private record Cidr(byte[] network, int prefixBits) {

        private static Cidr parse(String value) {
            if (value == null || value.isBlank() || value.length() > 80) {
                throw new IllegalArgumentException("Trusted proxy CIDR must not be blank");
            }
            String[] parts = value.split("/", -1);
            if (parts.length > 2) {
                throw new IllegalArgumentException("Invalid trusted proxy CIDR");
            }
            InetAddress address = parseAddress(parts[0]);
            if (address == null) {
                throw new IllegalArgumentException("Invalid trusted proxy network address");
            }
            int maximumBits = address.getAddress().length * Byte.SIZE;
            int prefix = maximumBits;
            if (parts.length == 2) {
                try {
                    prefix = Integer.parseInt(parts[1]);
                } catch (NumberFormatException exception) {
                    throw new IllegalArgumentException("Invalid trusted proxy prefix", exception);
                }
            }
            if (prefix < 0 || prefix > maximumBits) {
                throw new IllegalArgumentException("Trusted proxy prefix is out of range");
            }

            byte[] network = address.getAddress().clone();
            mask(network, prefix);
            return new Cidr(network, prefix);
        }

        private boolean contains(InetAddress candidate) {
            byte[] address = candidate.getAddress().clone();
            if (address.length != network.length) {
                return false;
            }
            mask(address, prefixBits);
            return java.util.Arrays.equals(network, address);
        }

        private static void mask(byte[] value, int prefixBits) {
            int completeBytes = prefixBits / Byte.SIZE;
            int remainder = prefixBits % Byte.SIZE;
            if (completeBytes < value.length && remainder != 0) {
                int mask = 0xff << (Byte.SIZE - remainder);
                value[completeBytes] = (byte) (value[completeBytes] & mask);
                completeBytes++;
            }
            java.util.Arrays.fill(value, completeBytes, value.length, (byte) 0);
        }
    }
}
