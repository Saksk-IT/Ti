package io.saksk.ti.learning.api;

/** Public application boundary for Phase 4C learning-owned write operations. */
public interface LearningWriteApplicationApi {

    ToggleFavoriteResult toggleFavorite(ToggleFavoriteCommand command);
}
