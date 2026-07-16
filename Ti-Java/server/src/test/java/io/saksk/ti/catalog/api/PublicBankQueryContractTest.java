package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class PublicBankQueryContractTest {

    @Test
    void normalizesKeywordByStrippingLowercasingAndCollapsingWhitespace() {
        var filter = new PublicBankFilter(
                Optional.empty(),
                "  Data\t STRUCTURES \n And   Algorithms  ",
                Optional.empty());

        assertThat(filter.keyword()).isEqualTo("data structures and algorithms");
        assertThat(PublicBankFilter.normalizeKeyword(" \t\n ")).isEmpty();
    }

    @Test
    void boardIdPreservesPositiveLongValuesBeyondIntegerRange() {
        long largeBoardId = (long) Integer.MAX_VALUE + 1;

        var filter = new PublicBankFilter(
                Optional.of(largeBoardId),
                "",
                Optional.empty());

        assertThat(filter.boardId()).contains(largeBoardId);
    }

    @Test
    void boardIdRejectsZeroAndNegativeValues() {
        assertThatIllegalArgumentException().isThrownBy(() -> new PublicBankFilter(
                Optional.of(0L), "", Optional.empty()));
        assertThatIllegalArgumentException().isThrownBy(() -> new PublicBankFilter(
                Optional.of(-1L), "", Optional.empty()));
    }

    @Test
    void searchQueryAcceptsPageAndPageSizeBoundariesAndUsesLongOffset() {
        var first = new PublicBankSearchQuery(
                PublicBankFilter.all(), PublicBankSort.LATEST, 1, 1);
        var largest = new PublicBankSearchQuery(
                PublicBankFilter.all(), PublicBankSort.HOT, Integer.MAX_VALUE, 50);

        assertThat(first.offset()).isZero();
        assertThat(largest.offset()).isEqualTo(107_374_182_300L);
    }

    @Test
    void searchQueryRejectsInvalidPageAndPageSizeValues() {
        assertThatIllegalArgumentException().isThrownBy(() -> new PublicBankSearchQuery(
                PublicBankFilter.all(), PublicBankSort.LATEST, 0, 12));
        assertThatIllegalArgumentException().isThrownBy(() -> new PublicBankSearchQuery(
                PublicBankFilter.all(), PublicBankSort.LATEST, 1, 0));
        assertThatIllegalArgumentException().isThrownBy(() -> new PublicBankSearchQuery(
                PublicBankFilter.all(), PublicBankSort.LATEST, 1, 51));
    }

    @Test
    void hotQueryAcceptsOnlyLimitsFromOneThroughTen() {
        assertThat(new PublicBankHotQuery(PublicBankFilter.all(), 1).limit()).isEqualTo(1);
        assertThat(new PublicBankHotQuery(PublicBankFilter.all(), 10).limit()).isEqualTo(10);

        assertThatIllegalArgumentException().isThrownBy(() ->
                new PublicBankHotQuery(PublicBankFilter.all(), 0));
        assertThatIllegalArgumentException().isThrownBy(() ->
                new PublicBankHotQuery(PublicBankFilter.all(), 11));
    }

    @Test
    void relationViewDerivesEveryRelationFromItsTwoFlags() {
        assertThat(List.of(
                        PublicBankRelationView.fromFlags(false, false),
                        PublicBankRelationView.fromFlags(true, false),
                        PublicBankRelationView.fromFlags(false, true),
                        PublicBankRelationView.fromFlags(true, true)))
                .extracting(PublicBankRelationView::joinedVia, PublicBankRelationView::joined)
                .containsExactly(
                        org.assertj.core.groups.Tuple.tuple(PublicBankRelation.NONE, false),
                        org.assertj.core.groups.Tuple.tuple(PublicBankRelation.PUBLIC, true),
                        org.assertj.core.groups.Tuple.tuple(PublicBankRelation.SHARED, true),
                        org.assertj.core.groups.Tuple.tuple(PublicBankRelation.BOTH, true));
    }

    @Test
    void relationViewRejectsJoinedStateThatDisagreesWithRelation() {
        assertThatIllegalArgumentException().isThrownBy(() ->
                new PublicBankRelationView(PublicBankRelation.NONE, true));
        assertThatIllegalArgumentException().isThrownBy(() ->
                new PublicBankRelationView(PublicBankRelation.PUBLIC, false));
    }

    @Test
    void sourceIsAClosedBusinessClassificationWithoutPersistenceValues() {
        assertThat(PublicBankSource.values())
                .containsExactly(PublicBankSource.SYSTEM, PublicBankSource.USER_PUBLIC);
    }

    @Test
    void boardReferenceRequiresANameInsteadOfInventingAPresentationFallback() {
        assertThat(new PublicBankBoardRef(null, null, "Unassigned").name())
                .isEqualTo("Unassigned");
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new PublicBankBoardRef(null, null, "  "));
    }
}
