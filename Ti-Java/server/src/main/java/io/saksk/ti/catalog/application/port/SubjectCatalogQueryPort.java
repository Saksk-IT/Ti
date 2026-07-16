package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.domain.SubjectCatalogEntry;
import java.util.List;

/** Constant-query catalog read for unlocked subjects and their question counts. */
public interface SubjectCatalogQueryPort {

    List<SubjectCatalogEntry> findUnlockedWithQuestionCounts();
}
