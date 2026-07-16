package io.saksk.ti.web.security;

import java.util.List;

/**
 * Authoritative Redis index for the bounded set of target Sessions owned by one identity.
 */
public interface TargetSessionRegistry {

    List<String> registerAndSelectEvictions(long identityId, String sessionId);

    boolean isActive(long identityId, String sessionId);

    void unregister(long identityId, String sessionId);
}
