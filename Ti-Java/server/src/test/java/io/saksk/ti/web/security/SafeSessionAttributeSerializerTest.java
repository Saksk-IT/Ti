package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.serializer.SerializationException;

class SafeSessionAttributeSerializerTest {

    private final SafeSessionAttributeSerializer serializer = new SafeSessionAttributeSerializer();

    @Test
    void roundTripsOnlyTheClosedScalarSet() {
        for (Object value : List.of("用户", 42L, 7, true, false)) {
            assertThat(serializer.deserialize(serializer.serialize(value))).isEqualTo(value);
        }
        assertThat(serializer.serialize(null)).isNull();
        assertThat(serializer.deserialize(null)).isNull();
        assertThat(serializer.deserialize(new byte[0])).isNull();
    }

    @Test
    void rejectsArbitraryObjectsAndOversizedOrMalformedPayloads() {
        assertThatThrownBy(() -> serializer.serialize(List.of("not", "allowed")))
                .isInstanceOf(SerializationException.class)
                .hasMessageContaining("Unsupported");
        assertThatThrownBy(() -> serializer.serialize("x".repeat(8 * 1024)))
                .isInstanceOf(SerializationException.class)
                .hasMessageContaining("size limit");
        assertThatThrownBy(() -> serializer.deserialize("x:value".getBytes(StandardCharsets.UTF_8)))
                .isInstanceOf(SerializationException.class)
                .hasMessageContaining("Unknown");
        assertThatThrownBy(() -> serializer.deserialize("b:true".getBytes(StandardCharsets.UTF_8)))
                .isInstanceOf(SerializationException.class)
                .hasMessageContaining("Boolean");
        assertThatThrownBy(() -> serializer.deserialize("i:nope".getBytes(StandardCharsets.UTF_8)))
                .isInstanceOf(SerializationException.class)
                .hasMessageContaining("numeric");
    }
}
