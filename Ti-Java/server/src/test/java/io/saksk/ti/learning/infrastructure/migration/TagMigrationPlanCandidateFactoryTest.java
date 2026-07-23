package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ApplyPrerequisiteBlocker;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.KeyClassification;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ReportingGroup;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.RowOutcome;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.SourceRow;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.Status;
import java.lang.reflect.Modifier;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class TagMigrationPlanCandidateFactoryTest {

    private final TagMigrationPlanCandidateFactory factory =
            new TagMigrationPlanCandidateFactory();

    @Test
    void createsDeterministicRedactedCandidateFromCanonicalInputs() {
        LegacyPersonalBankTagPreflightReport report =
                TagMigrationPlanCandidateTestFixture.report();
        RunBinding binding = TagMigrationPlanCandidateTestFixture.binding(report);

        TagMigrationPlanCandidate first = factory.create(
                TagMigrationPlanCandidateTestFixture.MIGRATION_ID,
                TagMigrationPlanCandidateTestFixture.RUN_ID,
                report,
                binding);
        TagMigrationPlanCandidate second = factory.create(
                TagMigrationPlanCandidateTestFixture.MIGRATION_ID,
                TagMigrationPlanCandidateTestFixture.RUN_ID,
                report,
                binding);

        assertThat(first).isEqualTo(second);
        assertThat(first.candidateSha256()).matches("[0-9a-f]{64}");
        assertThat(first.binding()).isEqualTo(binding);
        assertThat(first.freshPreflight()).isSameAs(report);
        assertThat(first.sourceCount()).isEqualTo(3);
        assertThat(first.migratedCount()).isEqualTo(1);
        assertThat(first.targetAlreadyPresentCount()).isEqualTo(1);
        assertThat(first.emptyNoopCount()).isEqualTo(1);
        assertThat(first.toString())
                .contains("redacted=true", first.candidateSha256())
                .doesNotContain(
                        TagMigrationPlanCandidateTestFixture.H1,
                        TagMigrationPlanCandidateTestFixture.H2,
                        "freshPreflight",
                        "binding=");
    }

    @Test
    void candidateDigestSeparatelyBindsMigrationRunAndEveryBindingRole() {
        LegacyPersonalBankTagPreflightReport report =
                TagMigrationPlanCandidateTestFixture.report();
        RunBinding binding = TagMigrationPlanCandidateTestFixture.binding(report);
        String base = factory.create(
                TagMigrationPlanCandidateTestFixture.MIGRATION_ID,
                TagMigrationPlanCandidateTestFixture.RUN_ID,
                report,
                binding).candidateSha256();

        assertThat(factory.create(
                UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
                TagMigrationPlanCandidateTestFixture.RUN_ID,
                report,
                binding).candidateSha256()).isNotEqualTo(base);
        assertThat(factory.create(
                TagMigrationPlanCandidateTestFixture.MIGRATION_ID,
                UUID.fromString("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
                report,
                binding).candidateSha256()).isNotEqualTo(base);

        List<RunBinding> changedBindings = List.of(
                new RunBinding(
                        TagMigrationPlanCandidateTestFixture.H9,
                        binding.clusterDatabaseIdentitySha256(),
                        binding.runIdentitySha256(),
                        binding.preflightDigestSha256(),
                        binding.sourceSetDigestSha256(),
                        binding.planSetDigestSha256(),
                        binding.preapplyTargetSetDigestSha256(),
                        binding.finalTargetSetDigestSha256(),
                        binding.membershipSetDigestSha256()),
                new RunBinding(
                        binding.backupManifestSha256(),
                        TagMigrationPlanCandidateTestFixture.H9,
                        binding.runIdentitySha256(),
                        binding.preflightDigestSha256(),
                        binding.sourceSetDigestSha256(),
                        binding.planSetDigestSha256(),
                        binding.preapplyTargetSetDigestSha256(),
                        binding.finalTargetSetDigestSha256(),
                        binding.membershipSetDigestSha256()),
                new RunBinding(
                        binding.backupManifestSha256(),
                        binding.clusterDatabaseIdentitySha256(),
                        TagMigrationPlanCandidateTestFixture.H9,
                        binding.preflightDigestSha256(),
                        binding.sourceSetDigestSha256(),
                        binding.planSetDigestSha256(),
                        binding.preapplyTargetSetDigestSha256(),
                        binding.finalTargetSetDigestSha256(),
                        binding.membershipSetDigestSha256()),
                new RunBinding(
                        binding.backupManifestSha256(),
                        binding.clusterDatabaseIdentitySha256(),
                        binding.runIdentitySha256(),
                        binding.preflightDigestSha256(),
                        TagMigrationPlanCandidateTestFixture.H9,
                        binding.planSetDigestSha256(),
                        binding.preapplyTargetSetDigestSha256(),
                        binding.finalTargetSetDigestSha256(),
                        binding.membershipSetDigestSha256()),
                new RunBinding(
                        binding.backupManifestSha256(),
                        binding.clusterDatabaseIdentitySha256(),
                        binding.runIdentitySha256(),
                        binding.preflightDigestSha256(),
                        binding.sourceSetDigestSha256(),
                        TagMigrationPlanCandidateTestFixture.H9,
                        binding.preapplyTargetSetDigestSha256(),
                        binding.finalTargetSetDigestSha256(),
                        binding.membershipSetDigestSha256()),
                new RunBinding(
                        binding.backupManifestSha256(),
                        binding.clusterDatabaseIdentitySha256(),
                        binding.runIdentitySha256(),
                        binding.preflightDigestSha256(),
                        binding.sourceSetDigestSha256(),
                        binding.planSetDigestSha256(),
                        TagMigrationPlanCandidateTestFixture.H9,
                        binding.finalTargetSetDigestSha256(),
                        binding.membershipSetDigestSha256()),
                new RunBinding(
                        binding.backupManifestSha256(),
                        binding.clusterDatabaseIdentitySha256(),
                        binding.runIdentitySha256(),
                        binding.preflightDigestSha256(),
                        binding.sourceSetDigestSha256(),
                        binding.planSetDigestSha256(),
                        binding.preapplyTargetSetDigestSha256(),
                        TagMigrationPlanCandidateTestFixture.H9,
                        binding.membershipSetDigestSha256()),
                new RunBinding(
                        binding.backupManifestSha256(),
                        binding.clusterDatabaseIdentitySha256(),
                        binding.runIdentitySha256(),
                        binding.preflightDigestSha256(),
                        binding.sourceSetDigestSha256(),
                        binding.planSetDigestSha256(),
                        binding.preapplyTargetSetDigestSha256(),
                        binding.finalTargetSetDigestSha256(),
                        TagMigrationPlanCandidateTestFixture.H9));
        assertThat(changedBindings)
                .extracting(changed -> factory.create(
                        TagMigrationPlanCandidateTestFixture.MIGRATION_ID,
                        TagMigrationPlanCandidateTestFixture.RUN_ID,
                        report,
                        changed).candidateSha256())
                .doesNotContain(base)
                .doesNotHaveDuplicates();
    }

    @Test
    void rejectsAggregateAndBindingMismatchBeforeCreatingCandidate() {
        LegacyPersonalBankTagPreflightReport report =
                TagMigrationPlanCandidateTestFixture.report();
        LegacyPersonalBankTagPreflightReport forgedAggregate =
                TagMigrationPlanCandidateTestFixture.report(
                        TagMigrationPlanCandidateTestFixture.H9);
        RunBinding binding = TagMigrationPlanCandidateTestFixture.binding(report);
        RunBinding wrongPreflightBinding = new RunBinding(
                binding.backupManifestSha256(),
                binding.clusterDatabaseIdentitySha256(),
                binding.runIdentitySha256(),
                TagMigrationPlanCandidateTestFixture.H9,
                binding.sourceSetDigestSha256(),
                binding.planSetDigestSha256(),
                binding.preapplyTargetSetDigestSha256(),
                binding.finalTargetSetDigestSha256(),
                binding.membershipSetDigestSha256());

        assertThatThrownBy(() -> factory.create(
                TagMigrationPlanCandidateTestFixture.MIGRATION_ID,
                TagMigrationPlanCandidateTestFixture.RUN_ID,
                forgedAggregate,
                binding)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> factory.create(
                TagMigrationPlanCandidateTestFixture.MIGRATION_ID,
                TagMigrationPlanCandidateTestFixture.RUN_ID,
                report,
                wrongPreflightBinding)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void factoryIsStatelessAndCandidateCannotBePubliclyForged() {
        assertThat(TagMigrationPlanCandidateFactory.class.getDeclaredFields())
                .allMatch(field -> Modifier.isStatic(field.getModifiers()));
        assertThat(TagMigrationPlanCandidate.class.getDeclaredConstructors())
                .noneMatch(constructor -> Modifier.isPublic(
                        constructor.getModifiers()));
        assertThat(Modifier.isFinal(
                TagMigrationPlanCandidate.class.getModifiers())).isTrue();
    }
}

final class TagMigrationPlanCandidateTestFixture {

    static final UUID MIGRATION_ID = UUID.fromString(
            "11111111-1111-4111-8111-111111111111");
    static final UUID RUN_ID = UUID.fromString(
            "22222222-2222-4222-8222-222222222222");
    static final String H0 = "0".repeat(64);
    static final String H1 = "1".repeat(64);
    static final String H2 = "2".repeat(64);
    static final String H3 = "3".repeat(64);
    static final String H4 = "4".repeat(64);
    static final String H5 = "5".repeat(64);
    static final String H6 = "6".repeat(64);
    static final String H7 = "7".repeat(64);
    static final String H8 = "8".repeat(64);
    static final String H9 = "9".repeat(64);

    private TagMigrationPlanCandidateTestFixture() {
    }

    static TagMigrationPlanCandidate candidate() {
        LegacyPersonalBankTagPreflightReport report = report();
        return new TagMigrationPlanCandidateFactory().create(
                MIGRATION_ID, RUN_ID, report, binding(report));
    }

    static RunBinding binding(LegacyPersonalBankTagPreflightReport report) {
        return new RunBinding(
                H0,
                H1,
                H2,
                report.aggregateDigest(),
                H4,
                H5,
                H6,
                H7,
                H8);
    }

    static LegacyPersonalBankTagPreflightReport report() {
        List<SourceRow> rows = rows();
        return report(aggregate(rows));
    }

    static LegacyPersonalBankTagPreflightReport report(String aggregate) {
        List<SourceRow> rows = rows();
        return new LegacyPersonalBankTagPreflightReport(
                "DRY_RUN",
                Status.COMPLETED,
                Instant.parse("2026-07-20T00:00:00Z"),
                Instant.parse("2026-07-20T00:00:01Z"),
                LegacyPersonalBankTagGlobalPreflight.advisoryLockKey(),
                Optional.of(1234),
                Optional.of(H3),
                Optional.of("18.4"),
                Optional.of("serializable"),
                true,
                true,
                rows.size(),
                rows.size(),
                0,
                0,
                rows,
                outcomeCounts(rows),
                reportingGroupCounts(rows),
                List.of(),
                0,
                aggregate,
                EnumSet.allOf(ApplyPrerequisiteBlocker.class),
                0,
                0);
    }

    private static List<SourceRow> rows() {
        return List.of(
                source(101, 201, 301, RowOutcome.MIGRATABLE),
                source(102, 202, 302, RowOutcome.TARGET_ALREADY_PRESENT),
                source(103, 203, 303, RowOutcome.EMPTY_NOOP));
    }

    private static SourceRow source(
            long sourceRowId,
            long userId,
            int bankId,
            RowOutcome outcome
    ) {
        boolean empty = outcome == RowOutcome.EMPTY_NOOP;
        return new SourceRow(
                sourceRowId,
                userId,
                KeyClassification.CANONICAL,
                Optional.of(bankId),
                H0,
                16,
                H1,
                32,
                Optional.of(H2),
                empty ? 0 : 1,
                empty ? 0 : 1,
                empty ? 0 : 1,
                Optional.of(H4),
                outcome == RowOutcome.TARGET_ALREADY_PRESENT ? 1 : 0,
                empty ? 0 : 1,
                Optional.of(H5),
                outcome,
                "NONE");
    }

    private static Map<RowOutcome, Long> outcomeCounts(List<SourceRow> rows) {
        EnumMap<RowOutcome, Long> counts = new EnumMap<>(RowOutcome.class);
        for (RowOutcome outcome : RowOutcome.values()) {
            counts.put(outcome, 0L);
        }
        rows.forEach(row -> counts.compute(
                row.outcome(), (ignored, count) -> count + 1L));
        return counts;
    }

    private static Map<ReportingGroup, Long> reportingGroupCounts(
            List<SourceRow> rows
    ) {
        EnumMap<ReportingGroup, Long> counts = new EnumMap<>(
                ReportingGroup.class);
        for (ReportingGroup group : ReportingGroup.values()) {
            counts.put(group, 0L);
        }
        rows.forEach(row -> counts.compute(
                row.reportingGroup(), (ignored, count) -> count + 1L));
        return counts;
    }

    private static String aggregate(List<SourceRow> rows) {
        MessageDigest digest = sha256Digest();
        updateNullableString(digest, "DRY_RUN");
        updateNullableString(digest, Status.COMPLETED.name());
        updateNullableString(digest, H3);
        for (SourceRow row : rows) {
            digest.update(ByteBuffer.allocate(Long.BYTES)
                    .putLong(row.sourceRowId()).array());
            updateNullableString(digest, row.keyDigest());
            updateNullableString(digest, row.sourceDigest());
            updateNullableString(digest, row.planDigest().orElse(null));
            updateNullableString(digest, row.targetDigest().orElse(null));
            updateNullableString(digest, row.membershipDigest().orElse(null));
            updateNullableString(digest, row.outcome().name());
            updateNullableString(digest, row.failureCode());
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private static void updateNullableString(MessageDigest digest, String value) {
        digest.update((byte) (value == null ? 0 : 1));
        if (value != null) {
            byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
            digest.update(ByteBuffer.allocate(Integer.BYTES)
                    .putInt(bytes.length).array());
            digest.update(bytes);
        }
    }

    private static MessageDigest sha256Digest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }
}
