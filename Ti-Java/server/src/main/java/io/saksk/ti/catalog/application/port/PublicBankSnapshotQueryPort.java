package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.PublicBankBoardView;
import io.saksk.ti.catalog.api.PublicBankCardView;
import io.saksk.ti.catalog.api.PublicBankDetailView;
import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankHotQuery;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankSearchQuery;
import io.saksk.ti.catalog.api.PublicBankSummaryView;
import io.saksk.ti.catalog.domain.PublicBankPageSlice;
import io.saksk.ti.catalog.domain.PublicBankSnapshotResult;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.OptionalLong;

public interface PublicBankSnapshotQueryPort {

    PublicBankSnapshotResult<PublicBankPageSlice> search(
            PublicBankSearchQuery query,
            OptionalLong viewerIdentityId);

    PublicBankSnapshotResult<List<PublicBankBoardView>> boards(PublicBankFilter filter);

    PublicBankSnapshotResult<List<PublicBankCardView>> hot(PublicBankHotQuery query);

    PublicBankSnapshotResult<PublicBankSummaryView> summary(
            PublicBankFilter filter,
            Instant rollingSevenDayCutoff);

    PublicBankSnapshotResult<Optional<PublicBankDetailView>> detail(
            PublicBankRef ref,
            OptionalLong viewerIdentityId);
}
