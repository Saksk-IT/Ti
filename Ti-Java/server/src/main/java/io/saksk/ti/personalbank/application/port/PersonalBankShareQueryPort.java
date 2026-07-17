package io.saksk.ti.personalbank.application.port;

import io.saksk.ti.personalbank.api.PersonalBankShareView;
import java.util.List;
import java.util.Optional;

/** Reads shares only after the legacy owner and active-status probe succeeds. */
public interface PersonalBankShareQueryPort {

    Optional<List<PersonalBankShareView>> findShares(long viewerId, int bankId);
}
