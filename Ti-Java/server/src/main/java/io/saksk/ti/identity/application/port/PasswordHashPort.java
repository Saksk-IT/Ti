package io.saksk.ti.identity.application.port;

public interface PasswordHashPort {

    boolean matches(char[] password, String storedHash);

    boolean isTargetHash(String storedHash);

    String encodeTarget(char[] password);

    void performDummyVerification(char[] password);
}
