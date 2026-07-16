package io.saksk.ti.identity.domain;

import java.util.Objects;

/** Current authentication-relevant state loaded by primary key from PostgreSQL. */
public final class AuthoritativeIdentityState {

    private final long id;
    private final String username;
    private final String openid;
    private final boolean administrator;
    private final boolean locked;
    private final int sessionVersion;
    private final boolean subjectAdministrator;
    private final boolean notificationAdministrator;

    public AuthoritativeIdentityState(
            long id,
            String username,
            String openid,
            boolean administrator,
            boolean locked,
            int sessionVersion,
            boolean subjectAdministrator,
            boolean notificationAdministrator
    ) {
        if (id <= 0 || sessionVersion < 0) {
            throw new IllegalArgumentException("Invalid authoritative identity state");
        }
        this.id = id;
        this.username = Objects.requireNonNull(username, "username");
        if (username.isBlank()) {
            throw new IllegalArgumentException("Authoritative username must not be blank");
        }
        this.openid = openid;
        this.administrator = administrator;
        this.locked = locked;
        this.sessionVersion = sessionVersion;
        this.subjectAdministrator = subjectAdministrator;
        this.notificationAdministrator = notificationAdministrator;
    }

    public long id() {
        return id;
    }

    public boolean locked() {
        return locked;
    }

    public int sessionVersion() {
        return sessionVersion;
    }

    /**
     * Applies the observed Flask compatibility rule for a JWT binding claim.
     *
     * <p>A null claim is malformed and fails closed. After Python-compatible whitespace trimming,
     * an empty claim is the observed non-WeChat bearer-token form and intentionally performs no
     * binding check. A non-empty claim must equal the current, likewise-trimmed database binding;
     * therefore both an unbind and a rebind invalidate that token.</p>
     */
    public boolean acceptsLegacyJwtOpenid(String claimedOpenid) {
        if (claimedOpenid == null) {
            return false;
        }
        String normalizedClaim = stripLikePython(claimedOpenid);
        if (normalizedClaim.isEmpty()) {
            return true;
        }
        return normalizedClaim.equals(stripLikePython(openid == null ? "" : openid));
    }

    public AuthorizedLegacyIdentity authorize() {
        return new AuthorizedLegacyIdentity(
                id,
                username,
                administrator,
                subjectAdministrator,
                notificationAdministrator,
                sessionVersion);
    }

    @Override
    public String toString() {
        return "AuthoritativeIdentityState[redacted]";
    }

    private static String stripLikePython(String value) {
        int start = 0;
        int end = value.length();
        while (start < end) {
            int codePoint = value.codePointAt(start);
            if (!isPythonWhitespace(codePoint)) {
                break;
            }
            start += Character.charCount(codePoint);
        }
        while (end > start) {
            int codePoint = value.codePointBefore(end);
            if (!isPythonWhitespace(codePoint)) {
                break;
            }
            end -= Character.charCount(codePoint);
        }
        return value.substring(start, end);
    }

    private static boolean isPythonWhitespace(int codePoint) {
        return Character.isWhitespace(codePoint)
                || Character.isSpaceChar(codePoint)
                || codePoint == 0x0085;
    }
}
