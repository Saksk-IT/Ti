package fixture.invalid.consumer;

import fixture.invalid.provider.domain.ProviderSecret;

/** Deliberately violates provider::api by importing provider.domain. */
public final class IllegalConsumer {

    private final ProviderSecret secret;

    public IllegalConsumer(ProviderSecret secret) {
        this.secret = secret;
    }

    public ProviderSecret leakedSecret() {
        return secret;
    }
}
