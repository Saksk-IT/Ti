package io.saksk.ti.personalbank.application.port;

import io.saksk.ti.personalbank.api.PersonalBankOwnedShareView;
import java.util.List;

/** Reads all legacy shares owned by one authenticated personal-bank viewer. */
public interface PersonalBankOwnedShareQueryPort {

    List<PersonalBankOwnedShareView> listOwnedShares(long viewerId);
}
