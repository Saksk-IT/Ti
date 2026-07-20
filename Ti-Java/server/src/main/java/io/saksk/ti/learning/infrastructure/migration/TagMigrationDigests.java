package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.TagRow;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import java.util.regex.Pattern;

/** Domain-separated canonical digests used by the operator and its store. */
final class TagMigrationDigests {

    static final String TARGET_FACTS_DOMAIN =
            "ti:phase4c:tag-migration:operator-target-facts:v1";
    private static final String CLUSTER_DATABASE_DOMAIN =
            "ti:phase4c:tag-migration:cluster-database:v1";
    private static final String RUN_IDENTITY_DOMAIN =
            "ti:phase4c:tag-migration:run-identity:v1";
    private static final String SOURCE_SET_DOMAIN =
            "ti:phase4c:tag-migration:operator-source-set:v1";
    private static final String PLAN_SET_DOMAIN =
            "ti:phase4c:tag-migration:operator-plan-set:v1";
    private static final String PREAPPLY_TARGET_SET_DOMAIN =
            "ti:phase4c:tag-migration:operator-preapply-target-set:v1";
    private static final String FINAL_TARGET_SET_DOMAIN =
            "ti:phase4c:tag-migration:operator-final-target-set:v1";
    private static final String MEMBERSHIP_SET_DOMAIN =
            "ti:phase4c:tag-migration:operator-membership-set:v1";
    private static final Pattern SHA256 = Pattern.compile("[0-9a-f]{64}");
    private static final Comparator<TagRow> TARGET_ORDER =
            Comparator.comparingInt(TagRow::questionId)
                    .thenComparing(TagRow::tag, TagMigrationDigests::compareUtf8);

    private TagMigrationDigests() {
    }

    static String sha256Utf8(String value) {
        return finish(digestWithDomain("ti:phase4c:tag-migration:utf8:v1"),
                digest -> updateString(digest, Objects.requireNonNull(value, "value")));
    }

    static String targetFacts(List<TagRow> rows) {
        Objects.requireNonNull(rows, "rows");
        MessageDigest digest = digestWithDomain(TARGET_FACTS_DOMAIN);
        rows.stream().distinct().sorted(TARGET_ORDER).forEach(row -> {
            digest.update(ByteBuffer.allocate(Integer.BYTES)
                    .putInt(row.questionId()).array());
            updateString(digest, row.tag());
        });
        return finish(digest);
    }

    static String legacyPreflightTargetFacts(List<RawTargetFact> rows) {
        Objects.requireNonNull(rows, "rows");
        MessageDigest digest = sha256Digest();
        rows.stream()
                .sorted(Comparator
                        .comparing(RawTargetFact::questionId,
                                Comparator.nullsFirst(Integer::compareTo))
                        .thenComparing(RawTargetFact::tag,
                                Comparator.nullsFirst(String::compareTo)))
                .forEach(row -> {
                    updateNullableInt(digest, row.questionId());
                    updateNullableString(digest, row.tag());
                });
        return finish(digest);
    }

    static TargetIdentity targetIdentity(
            String systemIdentifier,
            long databaseOid,
            String serverVersion,
            String serverAddress,
            String serverPort,
            String backupManifestSha256,
            UUID migrationRunUuid
    ) {
        requireSha256(backupManifestSha256, "backupManifestSha256");
        Objects.requireNonNull(migrationRunUuid, "migrationRunUuid");
        if (databaseOid <= 0) {
            throw new IllegalArgumentException("databaseOid must be positive");
        }
        String clusterDigest = sha256DomainFields(
                CLUSTER_DATABASE_DOMAIN,
                Objects.requireNonNull(systemIdentifier, "systemIdentifier"),
                Long.toString(databaseOid),
                Objects.requireNonNull(serverVersion, "serverVersion"),
                Objects.requireNonNull(serverAddress, "serverAddress"),
                Objects.requireNonNull(serverPort, "serverPort"));
        String runDigest = sha256DomainFields(
                RUN_IDENTITY_DOMAIN,
                backupManifestSha256,
                migrationRunUuid.toString(),
                clusterDigest);
        return new TargetIdentity(clusterDigest, runDigest);
    }

    static ManifestDigests manifestDigests(List<ManifestDigestRow> rows) {
        Objects.requireNonNull(rows, "rows");
        List<ManifestDigestRow> ordered = rows.stream()
                .sorted(Comparator.comparingLong(ManifestDigestRow::sourceRowId))
                .toList();
        if (ordered.stream().map(ManifestDigestRow::sourceRowId).distinct().count()
                != ordered.size()) {
            throw new IllegalArgumentException("manifest source IDs must be unique");
        }
        MessageDigest source = digestWithDomain(SOURCE_SET_DOMAIN);
        MessageDigest plan = digestWithDomain(PLAN_SET_DOMAIN);
        MessageDigest preapplyTarget = digestWithDomain(PREAPPLY_TARGET_SET_DOMAIN);
        MessageDigest finalTarget = digestWithDomain(FINAL_TARGET_SET_DOMAIN);
        MessageDigest membership = digestWithDomain(MEMBERSHIP_SET_DOMAIN);
        for (ManifestDigestRow row : ordered) {
            updateIdentity(source, row);
            updateSha(source, row.sourceDigestSha256());

            updateSourceId(plan, row.sourceRowId());
            updateSha(plan, row.planDigestSha256());

            updateSourceId(preapplyTarget, row.sourceRowId());
            updateSha(preapplyTarget, row.preapplyTargetDigestSha256());

            updateSourceId(finalTarget, row.sourceRowId());
            updateSha(finalTarget, row.expectedFinalTargetDigestSha256());

            updateSourceId(membership, row.sourceRowId());
            updateSha(membership, row.membershipDigestSha256());
        }
        return new ManifestDigests(
                finish(source), finish(plan), finish(preapplyTarget),
                finish(finalTarget), finish(membership));
    }

    static String requireSha256(String value, String name) {
        String required = Objects.requireNonNull(value, name);
        if (!SHA256.matcher(required).matches()) {
            throw new IllegalArgumentException(name + " must be lowercase SHA-256");
        }
        return required;
    }

    private static void updateIdentity(
            MessageDigest digest,
            ManifestDigestRow row
    ) {
        updateSourceId(digest, row.sourceRowId());
        digest.update(ByteBuffer.allocate(Long.BYTES).putLong(row.userId()).array());
        digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(row.bankId()).array());
    }

    private static int compareUtf8(String left, String right) {
        return java.util.Arrays.compareUnsigned(
                left.getBytes(StandardCharsets.UTF_8),
                right.getBytes(StandardCharsets.UTF_8));
    }

    private static void updateSourceId(MessageDigest digest, long sourceRowId) {
        digest.update(ByteBuffer.allocate(Long.BYTES).putLong(sourceRowId).array());
    }

    private static String sha256DomainFields(String domain, String... values) {
        MessageDigest digest = sha256Digest();
        digest.update(Objects.requireNonNull(domain, "domain")
                .getBytes(StandardCharsets.UTF_8));
        for (String value : values) {
            digest.update((byte) 0);
            digest.update(Objects.requireNonNull(value, "domain field")
                    .getBytes(StandardCharsets.UTF_8));
        }
        return finish(digest);
    }

    private static void updateSha(MessageDigest digest, String value) {
        requireSha256(value, "digest");
        digest.update(HexFormat.of().parseHex(value));
    }

    private static void updateString(MessageDigest digest, String value) {
        byte[] bytes = Objects.requireNonNull(value, "value")
                .getBytes(StandardCharsets.UTF_8);
        digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(bytes.length).array());
        digest.update(bytes);
    }

    private static void updateNullableInt(MessageDigest digest, Integer value) {
        digest.update((byte) (value == null ? 0 : 1));
        if (value != null) {
            digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(value).array());
        }
    }

    private static void updateNullableString(MessageDigest digest, String value) {
        digest.update((byte) (value == null ? 0 : 1));
        if (value != null) {
            byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
            digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(bytes.length).array());
            digest.update(bytes);
        }
    }

    private static MessageDigest digestWithDomain(String domain) {
        MessageDigest digest = sha256Digest();
        updateString(digest, domain);
        return digest;
    }

    private static String finish(
            MessageDigest digest,
            java.util.function.Consumer<MessageDigest> updates
    ) {
        updates.accept(digest);
        return finish(digest);
    }

    private static String finish(MessageDigest digest) {
        return HexFormat.of().formatHex(digest.digest());
    }

    private static MessageDigest sha256Digest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable", impossible);
        }
    }

    record TargetIdentity(
            String clusterDatabaseIdentitySha256,
            String runIdentitySha256
    ) {
        TargetIdentity {
            clusterDatabaseIdentitySha256 = requireSha256(
                    clusterDatabaseIdentitySha256,
                    "clusterDatabaseIdentitySha256");
            runIdentitySha256 = requireSha256(
                    runIdentitySha256, "runIdentitySha256");
        }
    }

    record ManifestDigests(
            String sourceSetDigestSha256,
            String planSetDigestSha256,
            String preapplyTargetSetDigestSha256,
            String finalTargetSetDigestSha256,
            String membershipSetDigestSha256
    ) {
        ManifestDigests {
            sourceSetDigestSha256 = requireSha256(
                    sourceSetDigestSha256, "sourceSetDigestSha256");
            planSetDigestSha256 = requireSha256(
                    planSetDigestSha256, "planSetDigestSha256");
            preapplyTargetSetDigestSha256 = requireSha256(
                    preapplyTargetSetDigestSha256,
                    "preapplyTargetSetDigestSha256");
            finalTargetSetDigestSha256 = requireSha256(
                    finalTargetSetDigestSha256, "finalTargetSetDigestSha256");
            membershipSetDigestSha256 = requireSha256(
                    membershipSetDigestSha256, "membershipSetDigestSha256");
        }
    }

    record ManifestDigestRow(
            long sourceRowId,
            long userId,
            int bankId,
            String sourceDigestSha256,
            String planDigestSha256,
            String preapplyTargetDigestSha256,
            String expectedFinalTargetDigestSha256,
            String membershipDigestSha256
    ) {
        ManifestDigestRow {
            if (sourceRowId <= 0 || userId <= 0 || bankId <= 0) {
                throw new IllegalArgumentException("manifest identity must be positive");
            }
            sourceDigestSha256 = requireSha256(
                    sourceDigestSha256, "sourceDigestSha256");
            planDigestSha256 = requireSha256(
                    planDigestSha256, "planDigestSha256");
            preapplyTargetDigestSha256 = requireSha256(
                    preapplyTargetDigestSha256,
                    "preapplyTargetDigestSha256");
            expectedFinalTargetDigestSha256 = requireSha256(
                    expectedFinalTargetDigestSha256,
                    "expectedFinalTargetDigestSha256");
            membershipDigestSha256 = requireSha256(
                    membershipDigestSha256, "membershipDigestSha256");
        }
    }

    record RawTargetFact(Integer questionId, String tag) {
    }
}
