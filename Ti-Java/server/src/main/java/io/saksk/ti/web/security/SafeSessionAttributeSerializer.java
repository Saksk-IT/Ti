package io.saksk.ti.web.security;

import java.nio.charset.StandardCharsets;
import org.springframework.data.redis.serializer.RedisSerializer;
import org.springframework.data.redis.serializer.SerializationException;

/**
 * Closed scalar serializer for target HttpSession attributes.
 *
 * <p>Java native serialization and polymorphic JSON are deliberately excluded.</p>
 */
final class SafeSessionAttributeSerializer implements RedisSerializer<Object> {

    private static final int MAX_SERIALIZED_BYTES = 8 * 1024;

    @Override
    public byte[] serialize(Object value) throws SerializationException {
        if (value == null) {
            return null;
        }

        String encoded;
        if (value instanceof String text) {
            encoded = "s:" + text;
        } else if (value instanceof Long number) {
            encoded = "l:" + number;
        } else if (value instanceof Integer number) {
            encoded = "i:" + number;
        } else if (value instanceof Boolean flag) {
            encoded = flag ? "b:1" : "b:0";
        } else {
            throw new SerializationException(
                    "Unsupported target-session attribute type: " + value.getClass().getName());
        }

        byte[] bytes = encoded.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_SERIALIZED_BYTES) {
            throw new SerializationException("Target-session attribute exceeds the safe size limit");
        }
        return bytes;
    }

    @Override
    public Object deserialize(byte[] bytes) throws SerializationException {
        if (bytes == null || bytes.length == 0) {
            return null;
        }
        if (bytes.length > MAX_SERIALIZED_BYTES) {
            throw new SerializationException("Target-session attribute exceeds the safe size limit");
        }

        String encoded = new String(bytes, StandardCharsets.UTF_8);
        if (encoded.length() < 2 || encoded.charAt(1) != ':') {
            throw new SerializationException("Malformed target-session attribute");
        }

        String value = encoded.substring(2);
        try {
            return switch (encoded.charAt(0)) {
                case 's' -> value;
                case 'l' -> Long.valueOf(value);
                case 'i' -> Integer.valueOf(value);
                case 'b' -> switch (value) {
                    case "1" -> Boolean.TRUE;
                    case "0" -> Boolean.FALSE;
                    default -> throw new SerializationException("Malformed Boolean session attribute");
                };
                default -> throw new SerializationException("Unknown target-session attribute type");
            };
        } catch (NumberFormatException exception) {
            throw new SerializationException("Malformed numeric target-session attribute", exception);
        }
    }
}
