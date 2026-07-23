package io.saksk.ti.learning.application.port;

/** Learning-owned mutation boundary for one public-question favorite row. */
public interface FavoriteTogglePort {

    boolean toggle(long actorId, long questionId);
}
