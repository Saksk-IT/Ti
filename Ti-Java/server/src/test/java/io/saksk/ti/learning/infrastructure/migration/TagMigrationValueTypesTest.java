package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedApplyEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedFreezeEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedRecoveryEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.TagRow;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ApplyPrerequisiteBlocker;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.KeyClassification;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ReportingGroup;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.RowOutcome;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.SourceRow;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.Status;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.SignedEvidence;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.ManifestDigestRow;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.ManifestDigests;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.FailureCode;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.Outcome;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.State;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.time.Instant;
import java.util.Arrays;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Stream;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class TagMigrationValueTypesTest {

    private static final UUID MIGRATION_ID =
            UUID.fromString("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee");
    private static final UUID RUN_ID =
            UUID.fromString("11111111-2222-3333-4444-555555555555");
    private static final UUID NIL_UUID = new UUID(0L, 0L);

    private static final String H0 = "00".repeat(32);
    private static final String H1 = "11".repeat(32);
    private static final String H2 = "22".repeat(32);
    private static final String H3 = "33".repeat(32);
    private static final String H4 = "44".repeat(32);
    private static final String H5 = "55".repeat(32);
    private static final String H6 = "66".repeat(32);
    private static final String H7 = "77".repeat(32);
    private static final String H8 = "88".repeat(32);
    private static final String H9 = "99".repeat(32);

    @Test
    void signedEvidenceDefensivelyCopiesInputsAndAccessorResults() {
        byte[] payload = {1, 2, 3};
        byte[] signature = filledBytes(32, (byte) 7);

        SignedEvidence evidence = new SignedEvidence("operator-key:v1", payload, signature);
        payload[0] = 99;
        signature[0] = 99;

        assertThat(evidence.payload()).containsExactly(1, 2, 3);
        assertThat(evidence.signature()).containsOnly((byte) 7);

        byte[] exposedPayload = evidence.payload();
        byte[] exposedSignature = evidence.signature();
        exposedPayload[1] = 88;
        exposedSignature[1] = 88;

        assertThat(evidence.payload()).containsExactly(1, 2, 3);
        assertThat(evidence.signature()).containsOnly((byte) 7);
        assertThat(evidence.payload()).isNotSameAs(evidence.payload());
        assertThat(evidence.signature()).isNotSameAs(evidence.signature());
    }

    @Test
    void signedEvidenceEnforcesIdentifierAndByteBoundaries() {
        assertThat(new SignedEvidence("k", new byte[1], new byte[32])).isNotNull();
        assertThat(new SignedEvidence(
                "k" + "a".repeat(127), new byte[65_536], new byte[8_192]))
                .isNotNull();

        for (String invalidKeyId : List.of(
                "",
                "-leading-punctuation",
                "contains whitespace",
                "contains/slash",
                "密钥",
                "jdbc:postgresql://db.example/prod",
                "-----BEGIN-PRIVATE-KEY-----",
                "a".repeat(129))) {
            assertThatThrownBy(() -> new SignedEvidence(
                    invalidKeyId, new byte[1], new byte[32]))
                    .as("invalid key id %s", invalidKeyId)
                    .isInstanceOf(IllegalArgumentException.class);
        }

        assertThatThrownBy(() -> new SignedEvidence(null, new byte[1], new byte[32]))
                .isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> new SignedEvidence("key", null, new byte[32]))
                .isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> new SignedEvidence("key", new byte[1], null))
                .isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> new SignedEvidence("key", new byte[0], new byte[32]))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new SignedEvidence(
                "key", new byte[65_537], new byte[32]))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new SignedEvidence("key", new byte[1], new byte[31]))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new SignedEvidence(
                "key", new byte[1], new byte[8_193]))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void verifiedEvidenceRejectsEveryCollapsedWriterStopReceiptPair() {
        RunBinding binding = new RunBinding(
                H0, H1, H2, H3, H4, H5, H6, H7, H8);
        assertThat(new VerifiedFreezeEvidence(
                binding, H0, H1, H2, H3, H4, H5)).isNotNull();
        assertThat(new VerifiedApplyEvidence(
                binding, H0, H1, H2, H3, H4, H5, H6, H7)).isNotNull();
        assertThat(new VerifiedRecoveryEvidence(
                binding, H0, H1, H2, H3, H4, H5, H6, H7)).isNotNull();

        for (List<String> writerReceipts : List.of(
                List.of(H0, H0, H1),
                List.of(H0, H1, H0),
                List.of(H0, H1, H1),
                List.of(H0, H0, H0))) {
            String source = writerReceipts.get(0);
            String target = writerReceipts.get(1);
            String membership = writerReceipts.get(2);
            assertThatThrownBy(() -> new VerifiedFreezeEvidence(
                    binding, source, target, membership, H3, H4, H5))
                    .as("freeze rejects collapsed writer receipts %s", writerReceipts)
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("pairwise distinct");
            assertThatThrownBy(() -> new VerifiedApplyEvidence(
                    binding, source, target, membership,
                    H3, H4, H5, H6, H7))
                    .as("apply rejects collapsed writer receipts %s", writerReceipts)
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("pairwise distinct");
            assertThatThrownBy(() -> new VerifiedRecoveryEvidence(
                    binding, source, target, membership,
                    H3, H4, H5, H6, H7))
                    .as("recovery rejects collapsed writer receipts %s", writerReceipts)
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("pairwise distinct");
        }
    }

    @Test
    void commandsExposeOpaqueEvidenceInsteadOfDatabaseOrCredentialParameters() {
        assertThat(TagMigrationCommand.class.getPermittedSubclasses()).hasSize(4);
        for (Class<?> commandType : TagMigrationCommand.class.getPermittedSubclasses()) {
            assertThat(commandType.isRecord()).isTrue();
            for (RecordComponent component : commandType.getRecordComponents()) {
                String name = component.getName().toLowerCase(Locale.ROOT);
                assertThat(name)
                        .doesNotContain("jdbc", "url", "password", "secret",
                                "privatekey", "credential", "token");
                assertThat(component.getType())
                        .isNotIn(String.class, byte[].class,
                                DataSource.class, Connection.class);
                assertThat(component.getType().getPackageName())
                        .doesNotStartWith("java.sql");
            }
        }

        assertThat(Arrays.stream(SignedEvidence.class.getRecordComponents())
                .map(RecordComponent::getName))
                .containsExactly("keyId", "payload", "signature");

        String opaqueClaims = "jdbc:postgresql://prod.example/ti?password=hunter2;"
                + "private-key=do-not-log";
        SignedEvidence evidence = new SignedEvidence(
                "operator-key:v1",
                opaqueClaims.getBytes(StandardCharsets.UTF_8),
                filledBytes(64, (byte) 9));
        TagMigrationCommand command = new TagMigrationCommand.FreezeCommand(
                MIGRATION_ID, RUN_ID, evidence);

        assertThat(evidence.toString())
                .doesNotContain("jdbc:postgresql", "hunter2", "do-not-log");
        assertThat(command.toString())
                .doesNotContain("jdbc:postgresql", "hunter2", "do-not-log");
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("commandFactories")
    void everyCommandRequiresNonNilIdsAndSignedEvidence(
            String ignoredName,
            CommandFactory factory
    ) {
        LegacyPersonalBankTagPreflightReport preflight = validPreflight();
        SignedEvidence evidence = evidence();

        assertThat(factory.create(MIGRATION_ID, RUN_ID, preflight, evidence)).isNotNull();
        assertThatThrownBy(() -> factory.create(null, RUN_ID, preflight, evidence))
                .isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> factory.create(NIL_UUID, RUN_ID, preflight, evidence))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> factory.create(MIGRATION_ID, null, preflight, evidence))
                .isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> factory.create(MIGRATION_ID, NIL_UUID, preflight, evidence))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> factory.create(MIGRATION_ID, RUN_ID, preflight, null))
                .isInstanceOf(NullPointerException.class);
    }

    static Stream<Arguments> commandFactories() {
        return Stream.of(
                Arguments.of("prepare", (CommandFactory) TagMigrationCommand.PrepareCommand::new),
                Arguments.of("freeze", (CommandFactory) (migrationId, runId, ignored, evidence) ->
                        new TagMigrationCommand.FreezeCommand(
                                migrationId, runId, evidence)),
                Arguments.of("apply", (CommandFactory) (migrationId, runId, ignored, evidence) ->
                        new TagMigrationCommand.ApplyCommand(
                                migrationId, runId, evidence)),
                Arguments.of("recovery", (CommandFactory) (migrationId, runId, ignored, evidence) ->
                        new TagMigrationCommand.RecoveryCommand(
                                migrationId, runId, evidence)));
    }

    @Test
    void prepareRequiresFreshCompleteNonEmptyDataEligiblePreflight() {
        assertThat(new TagMigrationCommand.PrepareCommand(
                MIGRATION_ID, RUN_ID, validPreflight(), evidence())).isNotNull();

        assertThatThrownBy(() -> new TagMigrationCommand.PrepareCommand(
                MIGRATION_ID, RUN_ID, null, evidence()))
                .isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> new TagMigrationCommand.PrepareCommand(
                MIGRATION_ID, RUN_ID, emptyCompletedPreflight(), evidence()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new TagMigrationCommand.PrepareCommand(
                MIGRATION_ID, RUN_ID, blockingPreflight(), evidence()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new TagMigrationCommand.PrepareCommand(
                MIGRATION_ID, RUN_ID, incompletePreflight(), evidence()))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @ParameterizedTest(name = "{0}/{1}/v{2}")
    @MethodSource("validResultStates")
    void resultAcceptsOnlyTheDocumentedOutcomeStateVersions(
            Outcome outcome,
            State state,
            int version
    ) {
        Optional<FailureCode> failure = outcome == Outcome.BLOCKED
                ? Optional.of(FailureCode.SOURCE_DRIFT)
                : Optional.empty();

        TagMigrationResult result = result(
                outcome, state, version, 3, 1, 1, 1, 2, 1, failure);

        assertThat(result.outcome()).isEqualTo(outcome);
        assertThat(result.state()).isEqualTo(state);
        assertThat(result.version()).isEqualTo(version);
    }

    static Stream<Arguments> validResultStates() {
        return Stream.of(
                Arguments.of(Outcome.PREPARED, State.PLANNED, 0),
                Arguments.of(Outcome.ALREADY_PREPARED_ZERO_DML, State.PLANNED, 0),
                Arguments.of(Outcome.FROZEN, State.FROZEN, 1),
                Arguments.of(Outcome.ALREADY_FROZEN_ZERO_DML, State.FROZEN, 1),
                Arguments.of(Outcome.APPLIED, State.APPLIED, 3),
                Arguments.of(Outcome.ALREADY_APPLIED_ZERO_DML, State.APPLIED, 3),
                Arguments.of(Outcome.BLOCKED, State.UNAVAILABLE, -1),
                Arguments.of(Outcome.BLOCKED, State.PLANNED, 0),
                Arguments.of(Outcome.BLOCKED, State.FROZEN, 1),
                Arguments.of(Outcome.BLOCKED, State.APPLYING, 2),
                Arguments.of(Outcome.BLOCKED, State.APPLIED, 3),
                Arguments.of(Outcome.BLOCKED, State.BLOCKED, 1),
                Arguments.of(Outcome.BLOCKED, State.BLOCKED, 2),
                Arguments.of(Outcome.BLOCKED, State.BLOCKED, 3));
    }

    @Test
    void resultRejectsEveryUndocumentedOutcomeStateCombination() {
        for (Outcome outcome : Outcome.values()) {
            for (State state : State.values()) {
                if (isDocumentedOutcomeState(outcome, state)) {
                    continue;
                }
                Optional<FailureCode> failure = outcome == Outcome.BLOCKED
                        ? Optional.of(FailureCode.ILLEGAL_STATE)
                        : Optional.empty();
                assertThatThrownBy(() -> result(
                        outcome, state, acceptedVersion(state),
                        3, 1, 1, 1, 1, 0, failure))
                        .as("%s must not be emitted with %s", outcome, state)
                        .isInstanceOf(IllegalArgumentException.class);
            }
        }
    }

    @ParameterizedTest(name = "{0}/{1}/v{2}")
    @MethodSource("invalidStateVersions")
    void resultRejectsStateVersionBoundaryViolations(
            Outcome outcome,
            State state,
            int invalidVersion
    ) {
        Optional<FailureCode> failure = outcome == Outcome.BLOCKED
                ? Optional.of(FailureCode.ILLEGAL_STATE)
                : Optional.empty();

        assertThatThrownBy(() -> result(
                outcome, state, invalidVersion,
                3, 1, 1, 1, 1, 0, failure))
                .isInstanceOf(IllegalArgumentException.class);
    }

    static Stream<Arguments> invalidStateVersions() {
        return Stream.of(
                Arguments.of(Outcome.PREPARED, State.PLANNED, -1),
                Arguments.of(Outcome.PREPARED, State.PLANNED, 1),
                Arguments.of(Outcome.FROZEN, State.FROZEN, 0),
                Arguments.of(Outcome.FROZEN, State.FROZEN, 2),
                Arguments.of(Outcome.BLOCKED, State.APPLYING, 1),
                Arguments.of(Outcome.BLOCKED, State.APPLYING, 3),
                Arguments.of(Outcome.APPLIED, State.APPLIED, 2),
                Arguments.of(Outcome.APPLIED, State.APPLIED, 4),
                Arguments.of(Outcome.BLOCKED, State.UNAVAILABLE, -2),
                Arguments.of(Outcome.BLOCKED, State.UNAVAILABLE, 0),
                Arguments.of(Outcome.BLOCKED, State.BLOCKED, -1),
                Arguments.of(Outcome.BLOCKED, State.BLOCKED, 0),
                Arguments.of(Outcome.BLOCKED, State.BLOCKED, 4));
    }

    @Test
    void resultFailureCodeIsRequiredOnlyForBlockedOutcomes() {
        assertThatThrownBy(() -> result(
                Outcome.BLOCKED, State.UNAVAILABLE, -1,
                0, 0, 0, 0, 0, 0, Optional.empty()))
                .isInstanceOf(IllegalArgumentException.class);

        for (Outcome outcome : Outcome.values()) {
            if (outcome == Outcome.BLOCKED) {
                continue;
            }
            State state = switch (outcome) {
                case PREPARED, ALREADY_PREPARED_ZERO_DML -> State.PLANNED;
                case FROZEN, ALREADY_FROZEN_ZERO_DML -> State.FROZEN;
                case APPLIED, ALREADY_APPLIED_ZERO_DML -> State.APPLIED;
                case BLOCKED -> throw new AssertionError("handled above");
            };
            assertThatThrownBy(() -> result(
                    outcome, state, acceptedVersion(state),
                    3, 1, 1, 1, 0, 0,
                    Optional.of(FailureCode.SQL_FAILURE)))
                    .as("%s must not carry a failure", outcome)
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void resultRejectsNegativeCountsRetryInversionAndDispositionOverflow() {
        List<int[]> invalidCounts = List.of(
                new int[] {-1, 0, 0, 0, 0, 0},
                new int[] {0, -1, 0, 0, 0, 0},
                new int[] {0, 0, -1, 0, 0, 0},
                new int[] {0, 0, 0, -1, 0, 0},
                new int[] {0, 0, 0, 0, -1, 0},
                new int[] {0, 0, 0, 0, 0, -1},
                new int[] {0, 0, 0, 0, 1, 2});

        for (int[] counts : invalidCounts) {
            assertThatThrownBy(() -> result(
                    Outcome.PREPARED, State.PLANNED, 0,
                    counts[0], counts[1], counts[2], counts[3],
                    counts[4], counts[5], Optional.empty()))
                    .isInstanceOf(IllegalArgumentException.class);
        }

        assertThatThrownBy(() -> result(
                Outcome.PREPARED, State.PLANNED, 0,
                Integer.MAX_VALUE, Integer.MAX_VALUE, 1, 0,
                0, 0, Optional.empty()))
                .isInstanceOf(ArithmeticException.class);
    }

    @Test
    void appliedResultsRequireExactlyOneDispositionPerSource() {
        for (Outcome applied : List.of(
                Outcome.APPLIED, Outcome.ALREADY_APPLIED_ZERO_DML)) {
            assertThatThrownBy(() -> result(
                    applied, State.APPLIED, 3,
                    3, 1, 1, 0, 1, 0, Optional.empty()))
                    .as("under-counted %s", applied)
                    .isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(() -> result(
                    applied, State.APPLIED, 3,
                    2, 1, 1, 1, 1, 0, Optional.empty()))
                    .as("over-counted %s", applied)
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void resultHasNoSecretBearingFieldAndItsStringFormIsRedacted() {
        for (RecordComponent component : TagMigrationResult.class.getRecordComponents()) {
            assertThat(component.getType()).isNotIn(String.class, byte[].class);
        }

        TagMigrationResult result = result(
                Outcome.BLOCKED, State.UNAVAILABLE, -1,
                0, 0, 0, 0, 2, 1,
                Optional.of(FailureCode.EVIDENCE_REJECTED));

        assertThat(result.toString())
                .contains("BLOCKED", "EVIDENCE_REJECTED")
                .doesNotContain("jdbc:postgresql", "password=", "private-key");
    }

    @Test
    void targetIdentityV1MatchesIndependentFixedVectorAndRejectsBadBoundaries() {
        TagMigrationDigests.TargetIdentity identity = TagMigrationDigests.targetIdentity(
                "741852963",
                16_384L,
                "18.4",
                "127.0.0.1",
                "5432",
                "ab".repeat(32),
                RUN_ID);

        assertThat(identity.clusterDatabaseIdentitySha256()).isEqualTo(
                "1481a173be5a29e7151195f8ce154a2f516c11c199cb70777e8aa513ff30d97c");
        assertThat(identity.runIdentitySha256()).isEqualTo(
                "1a8e43ef56afd6abdc866b4245150d4bbcadec2d1e85da9fd694f6ad4787a256");

        assertThatThrownBy(() -> TagMigrationDigests.targetIdentity(
                "741852963", 0, "18.4", "127.0.0.1", "5432",
                "ab".repeat(32), RUN_ID))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TagMigrationDigests.targetIdentity(
                "741852963", -1, "18.4", "127.0.0.1", "5432",
                "ab".repeat(32), RUN_ID))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TagMigrationDigests.targetIdentity(
                "741852963", 1, "18.4", "127.0.0.1", "5432",
                "AB".repeat(32), RUN_ID))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TagMigrationDigests.targetIdentity(
                "741852963", 1, "18.4", "127.0.0.1", "5432",
                H0, null))
                .isInstanceOf(NullPointerException.class);
    }

    @Test
    void manifestDigestsAreOrderIndependentAndRejectDuplicateSourceIds() {
        ManifestDigestRow first = manifestRow(
                1, 101, 201, H0, H1, H2, H3, H4);
        ManifestDigestRow second = manifestRow(
                2, 102, 202, H5, H6, H7, H8, H9);

        assertThat(TagMigrationDigests.manifestDigests(List.of(first, second)))
                .isEqualTo(TagMigrationDigests.manifestDigests(List.of(second, first)));

        ManifestDigestRow duplicateId = manifestRow(
                1, 999, 999, H9, H8, H7, H6, H5);
        assertThatThrownBy(() -> TagMigrationDigests.manifestDigests(
                List.of(first, duplicateId)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void preapplyFinalAndMembershipDigestsAreSeparatelyDomainBound() {
        ManifestDigestRow baseRow = manifestRow(
                1, 101, 201, H0, H1, H2, H3, H4);
        ManifestDigests base = TagMigrationDigests.manifestDigests(List.of(baseRow));

        ManifestDigests changedPreapply = TagMigrationDigests.manifestDigests(List.of(
                manifestRow(1, 101, 201, H0, H1, H5, H3, H4)));
        assertOnlyChanged(base, changedPreapply, DigestSlot.PREAPPLY);

        ManifestDigests changedFinal = TagMigrationDigests.manifestDigests(List.of(
                manifestRow(1, 101, 201, H0, H1, H2, H5, H4)));
        assertOnlyChanged(base, changedFinal, DigestSlot.FINAL);

        ManifestDigests changedMembership = TagMigrationDigests.manifestDigests(List.of(
                manifestRow(1, 101, 201, H0, H1, H2, H3, H5)));
        assertOnlyChanged(base, changedMembership, DigestSlot.MEMBERSHIP);

        ManifestDigests sameInputBytes = TagMigrationDigests.manifestDigests(List.of(
                manifestRow(9, 109, 209, H0, H0, H0, H0, H0)));
        assertThat(new HashSet<>(List.of(
                sameInputBytes.sourceSetDigestSha256(),
                sameInputBytes.planSetDigestSha256(),
                sameInputBytes.preapplyTargetSetDigestSha256(),
                sameInputBytes.finalTargetSetDigestSha256(),
                sameInputBytes.membershipSetDigestSha256())))
                .as("all five manifest roles use distinct v1 domains")
                .hasSize(5);
    }

    @Test
    void supplementaryUnicodeTargetDigestUsesUnsignedUtf8ByteOrderFixedVector() {
        String firstSupplementary = "\uD800\uDC00";
        String privateUseBmp = "\uE000";
        String emoji = "\uD83D\uDE00";
        List<TagRow> rows = List.of(
                new TagRow(7, emoji),
                new TagRow(8, "é"),
                new TagRow(7, firstSupplementary),
                new TagRow(8, "e\u0301"),
                new TagRow(7, privateUseBmp),
                new TagRow(7, emoji));

        assertThat(firstSupplementary.compareTo(privateUseBmp)).isNegative();
        assertThat(Arrays.compareUnsigned(
                firstSupplementary.getBytes(StandardCharsets.UTF_8),
                privateUseBmp.getBytes(StandardCharsets.UTF_8)))
                .isPositive();

        assertThat(TagMigrationDigests.targetFacts(rows)).isEqualTo(
                "f47ff060b3d959391bdfc7ed70340c2d7d5e49de6f022536bc68d70e23ee8c8c");
        assertThat(TagMigrationDigests.targetFacts(List.of(
                new TagRow(8, "e\u0301"),
                new TagRow(7, privateUseBmp),
                new TagRow(7, emoji),
                new TagRow(8, "é"),
                new TagRow(7, firstSupplementary))))
                .isEqualTo(TagMigrationDigests.targetFacts(rows));
    }

    private static boolean isDocumentedOutcomeState(Outcome outcome, State state) {
        return switch (outcome) {
            case PREPARED, ALREADY_PREPARED_ZERO_DML -> state == State.PLANNED;
            case FROZEN, ALREADY_FROZEN_ZERO_DML -> state == State.FROZEN;
            case APPLIED, ALREADY_APPLIED_ZERO_DML -> state == State.APPLIED;
            case BLOCKED -> state == State.UNAVAILABLE
                    || state == State.PLANNED
                    || state == State.FROZEN
                    || state == State.APPLYING
                    || state == State.APPLIED
                    || state == State.BLOCKED;
        };
    }

    private static int acceptedVersion(State state) {
        return switch (state) {
            case PLANNED -> 0;
            case FROZEN, BLOCKED -> 1;
            case APPLYING -> 2;
            case APPLIED -> 3;
            case UNAVAILABLE -> -1;
        };
    }

    private static TagMigrationResult result(
            Outcome outcome,
            State state,
            int version,
            int sourceCount,
            int migratedCount,
            int targetAlreadyPresentCount,
            int emptyNoopCount,
            int transactionAttempts,
            int transactionRetries,
            Optional<FailureCode> failureCode
    ) {
        return new TagMigrationResult(
                outcome,
                state,
                version,
                MIGRATION_ID,
                RUN_ID,
                sourceCount,
                migratedCount,
                targetAlreadyPresentCount,
                emptyNoopCount,
                transactionAttempts,
                transactionRetries,
                failureCode);
    }

    private static SignedEvidence evidence() {
        return new SignedEvidence("operator-key:v1", new byte[] {1}, new byte[32]);
    }

    private static LegacyPersonalBankTagPreflightReport validPreflight() {
        return completedPreflight(List.of(new SourceRow(
                1,
                2,
                KeyClassification.CANONICAL,
                Optional.of(3),
                H0,
                11,
                H1,
                22,
                Optional.of(H2),
                1,
                1,
                1,
                Optional.of(H3),
                0,
                1,
                Optional.of(H4),
                RowOutcome.MIGRATABLE,
                "NONE")), 1, 0);
    }

    private static LegacyPersonalBankTagPreflightReport emptyCompletedPreflight() {
        return completedPreflight(List.of(), 0, 0);
    }

    private static LegacyPersonalBankTagPreflightReport blockingPreflight() {
        return completedPreflight(List.of(new SourceRow(
                1,
                2,
                KeyClassification.NEAR_MISS,
                Optional.empty(),
                H0,
                11,
                H1,
                22,
                Optional.empty(),
                0,
                0,
                0,
                Optional.empty(),
                0,
                0,
                Optional.empty(),
                RowOutcome.INVALID_KEY,
                "INVALID_KEY")), 0, 1);
    }

    private static LegacyPersonalBankTagPreflightReport completedPreflight(
            List<SourceRow> rows,
            int canonicalRows,
            int nearMissRows
    ) {
        return preflight(Status.COMPLETED, rows, canonicalRows, nearMissRows);
    }

    private static LegacyPersonalBankTagPreflightReport incompletePreflight() {
        return preflight(Status.LOCK_BUSY, List.of(), 0, 0);
    }

    private static LegacyPersonalBankTagPreflightReport preflight(
            Status status,
            List<SourceRow> rows,
            int canonicalRows,
            int nearMissRows
    ) {
        return new LegacyPersonalBankTagPreflightReport(
                "DRY_RUN",
                status,
                Instant.parse("2026-07-19T00:00:00Z"),
                Instant.parse("2026-07-19T00:00:01Z"),
                7L,
                Optional.of(1234),
                Optional.of(H5),
                Optional.of("18.4"),
                Optional.of("serializable"),
                true,
                true,
                rows.size(),
                canonicalRows,
                nearMissRows,
                0,
                rows,
                outcomeCounts(rows),
                reportingGroupCounts(rows),
                List.of(),
                rows.stream().filter(SourceRow::blocksDataApply).count(),
                H6,
                EnumSet.allOf(ApplyPrerequisiteBlocker.class),
                0,
                0);
    }

    private static Map<RowOutcome, Long> outcomeCounts(List<SourceRow> rows) {
        EnumMap<RowOutcome, Long> counts = new EnumMap<>(RowOutcome.class);
        for (RowOutcome outcome : RowOutcome.values()) {
            counts.put(outcome, 0L);
        }
        for (SourceRow row : rows) {
            counts.compute(row.outcome(), (ignored, count) -> count + 1L);
        }
        return counts;
    }

    private static Map<ReportingGroup, Long> reportingGroupCounts(List<SourceRow> rows) {
        EnumMap<ReportingGroup, Long> counts = new EnumMap<>(ReportingGroup.class);
        for (ReportingGroup group : ReportingGroup.values()) {
            counts.put(group, 0L);
        }
        for (SourceRow row : rows) {
            counts.compute(row.reportingGroup(), (ignored, count) -> count + 1L);
        }
        return counts;
    }

    private static ManifestDigestRow manifestRow(
            long sourceRowId,
            long userId,
            int bankId,
            String source,
            String plan,
            String preapply,
            String expectedFinal,
            String membership
    ) {
        return new ManifestDigestRow(
                sourceRowId,
                userId,
                bankId,
                source,
                plan,
                preapply,
                expectedFinal,
                membership);
    }

    private static void assertOnlyChanged(
            ManifestDigests base,
            ManifestDigests changed,
            DigestSlot changedSlot
    ) {
        assertDigestSlot(base.sourceSetDigestSha256(), changed.sourceSetDigestSha256(),
                changedSlot == DigestSlot.SOURCE);
        assertDigestSlot(base.planSetDigestSha256(), changed.planSetDigestSha256(),
                changedSlot == DigestSlot.PLAN);
        assertDigestSlot(
                base.preapplyTargetSetDigestSha256(),
                changed.preapplyTargetSetDigestSha256(),
                changedSlot == DigestSlot.PREAPPLY);
        assertDigestSlot(
                base.finalTargetSetDigestSha256(),
                changed.finalTargetSetDigestSha256(),
                changedSlot == DigestSlot.FINAL);
        assertDigestSlot(
                base.membershipSetDigestSha256(),
                changed.membershipSetDigestSha256(),
                changedSlot == DigestSlot.MEMBERSHIP);
    }

    private static void assertDigestSlot(
            String base,
            String changed,
            boolean shouldChange
    ) {
        if (shouldChange) {
            assertThat(changed).isNotEqualTo(base);
        } else {
            assertThat(changed).isEqualTo(base);
        }
    }

    private static byte[] filledBytes(int size, byte value) {
        byte[] bytes = new byte[size];
        Arrays.fill(bytes, value);
        return bytes;
    }

    private enum DigestSlot {
        SOURCE,
        PLAN,
        PREAPPLY,
        FINAL,
        MEMBERSHIP
    }

    @FunctionalInterface
    private interface CommandFactory {
        TagMigrationCommand create(
                UUID migrationId,
                UUID migrationRunUuid,
                LegacyPersonalBankTagPreflightReport preflight,
                SignedEvidence evidence);
    }
}
