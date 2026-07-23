package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceRejectedException;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceVerifier;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedApplyEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedFreezeEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedPrepareEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedRecoveryEvidence;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.SignedEvidence;
import java.io.ByteArrayOutputStream;
import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.interfaces.EdECPublicKey;
import java.security.spec.EdECPoint;
import java.security.spec.NamedParameterSpec;
import java.time.Clock;
import java.time.DateTimeException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;
import org.bouncycastle.math.ec.rfc8032.Ed25519;
import org.bouncycastle.math.ec.rfc8032.Ed25519.PublicPoint;

/**
 * Strict, explicitly constructed verifier for legacy-tag migration evidence.
 *
 * <p>The verifier has no key discovery, private-key, filesystem, environment,
 * network, Spring, or database integration. Every trusted key, policy value,
 * and clock is supplied by its caller. Wire payloads use one canonical binary
 * encoding and pure Ed25519 with a method-selected domain; no algorithm value
 * from the wire is ever dispatched.</p>
 */
public final class Ed25519TagMigrationEvidenceVerifier
        implements EvidenceVerifier {

    private static final byte[] MAGIC = {'T', 'I', 'T', 'M'};
    private static final int FORMAT_VERSION = 1;
    private static final int MAX_CANONICAL_PAYLOAD_BYTES = 1_024;
    private static final int RAW_PUBLIC_KEY_BYTES = Ed25519.PUBLIC_KEY_SIZE;
    private static final int SIGNATURE_BYTES = Ed25519.SIGNATURE_SIZE;
    private static final int SHA256_BYTES = 32;
    private static final String ZERO_SHA256 = "0".repeat(64);
    private static final UUID NIL_UUID = new UUID(0L, 0L);

    private static final Duration MAX_ALLOWED_CLOCK_SKEW =
            Duration.ofMinutes(5);
    private static final Duration MAX_ALLOWED_EVIDENCE_LIFETIME =
            Duration.ofHours(1);

    private static final Pattern IDENTIFIER = Pattern.compile(
            "[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?");

    private static final String RECEIPT_DOMAIN =
            "ti:phase4c:legacy-personal-bank-tag-migration:"
                    + "signed-evidence-receipt:sha256:v1";

    private static final int MIGRATION_ID_TAG = 0x10;
    private static final int RUN_UUID_TAG = 0x11;
    private static final int EVIDENCE_UUID_TAG = 0x12;
    private static final int ISSUED_AT_TAG = 0x13;
    private static final int EXPIRES_AT_TAG = 0x14;
    private static final int PLAN_CANDIDATE_DIGEST_TAG = 0x15;

    private static final int BACKUP_MANIFEST_TAG = 0x20;
    private static final int CLUSTER_DATABASE_IDENTITY_TAG = 0x21;
    private static final int RUN_IDENTITY_TAG = 0x22;
    private static final int PREFLIGHT_DIGEST_TAG = 0x23;
    private static final int SOURCE_SET_DIGEST_TAG = 0x24;
    private static final int PLAN_SET_DIGEST_TAG = 0x25;
    private static final int PREAPPLY_TARGET_SET_DIGEST_TAG = 0x26;
    private static final int FINAL_TARGET_SET_DIGEST_TAG = 0x27;
    private static final int MEMBERSHIP_SET_DIGEST_TAG = 0x28;

    private static final int SOURCE_WRITER_STOP_TAG = 0x40;
    private static final int TARGET_WRITER_STOP_TAG = 0x41;
    private static final int MEMBERSHIP_WRITER_STOP_TAG = 0x42;
    private static final int CONNECTION_DRAIN_TAG = 0x43;
    private static final int CONNECTION_REJECTION_TAG = 0x44;
    private static final int RESTORED_BACKUP_TAG = 0x45;
    private static final int APPLY_AUTHORIZATION_TAG = 0x46;
    private static final int LEGACY_RUNTIME_DISABLED_TAG = 0x47;

    private static final int FIXED_COMMON_PAYLOAD_BYTES =
            MAGIC.length
                    + 1 // format version
                    + 1 // phase
                    + 1 // issuer byte length
                    + 1 // key-id byte length
                    + 3 * (1 + 16) // tagged UUIDs
                    + 2 * (1 + Long.BYTES) // tagged epoch seconds
                    + 1 + SHA256_BYTES // tagged plan-candidate digest
                    + 9 * (1 + SHA256_BYTES); // tagged run binding

    private final Map<String, KeyMaterial> trustedKeys;
    private final Clock clock;
    private final Duration allowedClockSkew;
    private final Duration maximumEvidenceLifetime;

    /**
     * Creates an immutable verifier from an explicit trust snapshot.
     *
     * @param trustedKeys trusted raw Ed25519 keys; key IDs and key material
     *                    must both be unique
     * @param clock explicit verification clock
     * @param allowedClockSkew non-negative skew, at most five minutes
     * @param maximumEvidenceLifetime positive lifetime, at most one hour
     */
    public Ed25519TagMigrationEvidenceVerifier(
            List<TrustedKey> trustedKeys,
            Clock clock,
            Duration allowedClockSkew,
            Duration maximumEvidenceLifetime
    ) {
        List<TrustedKey> keys = List.copyOf(Objects.requireNonNull(
                trustedKeys, "trustedKeys"));
        if (keys.isEmpty()) {
            throw new IllegalArgumentException("trustedKeys must not be empty");
        }
        this.clock = Objects.requireNonNull(clock, "clock");
        this.allowedClockSkew = requireDuration(
                allowedClockSkew,
                Duration.ZERO,
                MAX_ALLOWED_CLOCK_SKEW,
                true,
                "allowedClockSkew");
        this.maximumEvidenceLifetime = requireDuration(
                maximumEvidenceLifetime,
                Duration.ZERO,
                MAX_ALLOWED_EVIDENCE_LIFETIME,
                false,
                "maximumEvidenceLifetime");

        Map<String, KeyMaterial> byId = new LinkedHashMap<>();
        Set<String> publicKeyFingerprints = new HashSet<>();
        for (TrustedKey trustedKey : keys) {
            TrustedKey key = Objects.requireNonNull(
                    trustedKey, "trusted key entry");
            byte[] rawPublicKey = key.rawPublicKey();
            PublicPoint publicPoint;
            try {
                publicPoint = Ed25519.validatePublicKeyFullExport(
                        rawPublicKey, 0);
            } catch (RuntimeException invalidKey) {
                throw new IllegalArgumentException(
                        "trusted key is not a strict Ed25519 public key");
            }
            if (publicPoint == null) {
                throw new IllegalArgumentException(
                        "trusted key is not a strict Ed25519 public key");
            }
            String fingerprint = sha256Hex(rawPublicKey);
            if (!publicKeyFingerprints.add(fingerprint)) {
                throw new IllegalArgumentException(
                        "trusted Ed25519 public keys must be unique");
            }
            if (byId.putIfAbsent(
                    key.keyId(), new KeyMaterial(key, publicPoint)) != null) {
                throw new IllegalArgumentException(
                        "trusted key IDs must be unique");
            }
        }
        this.trustedKeys = Map.copyOf(byId);
    }

    @Override
    public VerifiedPrepareEvidence verifyPrepare(
            UUID migrationId,
            UUID migrationRunUuid,
            SignedEvidence signedEvidence
    ) throws EvidenceRejectedException {
        try {
            VerifiedEnvelope verified = verifyEnvelope(
                    Purpose.PREPARE,
                    migrationId,
                    migrationRunUuid,
                    signedEvidence);
            return new VerifiedPrepareEvidence(
                    verified.payload().common().binding(),
                    envelopeReceiptSha256(verified));
        } catch (EvidenceRejectedException rejected) {
            throw rejected;
        } catch (RuntimeException rejected) {
            throw rejectedEvidence();
        }
    }

    @Override
    public VerifiedFreezeEvidence verifyFreeze(
            UUID migrationId,
            UUID migrationRunUuid,
            SignedEvidence signedEvidence
    ) throws EvidenceRejectedException {
        try {
            DecodedPayload payload = verifyEnvelope(
                    Purpose.FREEZE,
                    migrationId,
                    migrationRunUuid,
                    signedEvidence).payload();
            FreezeReceiptClaims receipts = Objects.requireNonNull(
                    payload.freezeReceipts(), "freeze receipts");
            return new VerifiedFreezeEvidence(
                    payload.common().binding(),
                    receipts.sourceWriterStopReceiptSha256(),
                    receipts.targetWriterStopReceiptSha256(),
                    receipts.membershipWriterStopReceiptSha256(),
                    receipts.connectionDrainReceiptSha256(),
                    receipts.connectionRejectionReceiptSha256(),
                    receipts.restoredBackupReceiptSha256());
        } catch (EvidenceRejectedException rejected) {
            throw rejected;
        } catch (RuntimeException rejected) {
            throw rejectedEvidence();
        }
    }

    @Override
    public VerifiedApplyEvidence verifyApply(
            UUID migrationId,
            UUID migrationRunUuid,
            SignedEvidence signedEvidence
    ) throws EvidenceRejectedException {
        try {
            VerifiedEnvelope verified = verifyEnvelope(
                    Purpose.APPLY,
                    migrationId,
                    migrationRunUuid,
                    signedEvidence);
            DecodedPayload payload = verified.payload();
            FreezeReceiptClaims receipts = Objects.requireNonNull(
                    payload.freezeReceipts(), "freeze receipts");
            String applyAuthorizationReceiptSha256 =
                    envelopeReceiptSha256(verified);
            String legacyRuntimeDisabledReceiptSha256 =
                    Objects.requireNonNull(
                            payload.legacyRuntimeDisabledReceiptSha256(),
                            "legacy runtime receipt");
            requireReceiptDistinctness(
                    receipts,
                    List.of(
                            applyAuthorizationReceiptSha256,
                            legacyRuntimeDisabledReceiptSha256));
            return new VerifiedApplyEvidence(
                    payload.common().binding(),
                    receipts.sourceWriterStopReceiptSha256(),
                    receipts.targetWriterStopReceiptSha256(),
                    receipts.membershipWriterStopReceiptSha256(),
                    receipts.connectionDrainReceiptSha256(),
                    receipts.connectionRejectionReceiptSha256(),
                    receipts.restoredBackupReceiptSha256(),
                    applyAuthorizationReceiptSha256,
                    legacyRuntimeDisabledReceiptSha256);
        } catch (EvidenceRejectedException rejected) {
            throw rejected;
        } catch (RuntimeException rejected) {
            throw rejectedEvidence();
        }
    }

    @Override
    public VerifiedRecoveryEvidence verifyRecovery(
            UUID migrationId,
            UUID migrationRunUuid,
            SignedEvidence signedEvidence
    ) throws EvidenceRejectedException {
        try {
            DecodedPayload payload = verifyEnvelope(
                    Purpose.RECOVERY,
                    migrationId,
                    migrationRunUuid,
                    signedEvidence).payload();
            FreezeReceiptClaims receipts = Objects.requireNonNull(
                    payload.freezeReceipts(), "freeze receipts");
            return new VerifiedRecoveryEvidence(
                    payload.common().binding(),
                    receipts.sourceWriterStopReceiptSha256(),
                    receipts.targetWriterStopReceiptSha256(),
                    receipts.membershipWriterStopReceiptSha256(),
                    receipts.connectionDrainReceiptSha256(),
                    receipts.connectionRejectionReceiptSha256(),
                    receipts.restoredBackupReceiptSha256(),
                    Objects.requireNonNull(
                            payload.applyAuthorizationReceiptSha256(),
                            "apply authorization receipt"),
                    Objects.requireNonNull(
                            payload.legacyRuntimeDisabledReceiptSha256(),
                            "legacy runtime receipt"));
        } catch (EvidenceRejectedException rejected) {
            throw rejected;
        } catch (RuntimeException rejected) {
            throw rejectedEvidence();
        }
    }

    /** Encodes canonical PREPARE claims for an external signer. */
    public static byte[] encodePreparePayload(PrepareClaims claims) {
        PrepareClaims required = Objects.requireNonNull(claims, "claims");
        return encodePayload(
                Purpose.PREPARE,
                required.common(),
                null,
                null,
                null);
    }

    /** Encodes canonical FREEZE claims for an external signer. */
    public static byte[] encodeFreezePayload(FreezeClaims claims) {
        FreezeClaims required = Objects.requireNonNull(claims, "claims");
        return encodePayload(
                Purpose.FREEZE,
                required.common(),
                required.receipts(),
                null,
                null);
    }

    /** Encodes canonical APPLY claims for an external signer. */
    public static byte[] encodeApplyPayload(ApplyClaims claims) {
        ApplyClaims required = Objects.requireNonNull(claims, "claims");
        return encodePayload(
                Purpose.APPLY,
                required.common(),
                required.receipts(),
                null,
                required.legacyRuntimeDisabledReceiptSha256());
    }

    /** Encodes canonical RECOVERY claims for an external signer. */
    public static byte[] encodeRecoveryPayload(RecoveryClaims claims) {
        RecoveryClaims required = Objects.requireNonNull(claims, "claims");
        return encodePayload(
                Purpose.RECOVERY,
                required.common(),
                required.receipts(),
                required.applyAuthorizationReceiptSha256(),
                required.legacyRuntimeDisabledReceiptSha256());
    }

    /**
     * Returns the exact bytes that an external pure-Ed25519 signer must sign.
     */
    public static byte[] signatureInput(
            Purpose purpose,
            byte[] canonicalPayload
    ) {
        Purpose requiredPurpose = Objects.requireNonNull(purpose, "purpose");
        byte[] payload = Objects.requireNonNull(
                canonicalPayload, "canonicalPayload").clone();
        if (payload.length == 0
                || payload.length > MAX_CANONICAL_PAYLOAD_BYTES) {
            throw new IllegalArgumentException(
                    "invalid canonical evidence payload size");
        }
        byte[] domain = requiredPurpose.domainBytes();
        CanonicalWriter writer = new CanonicalWriter();
        writer.writeUnsignedShort(domain.length);
        writer.writeBytes(domain);
        writer.writeBytes(payload);
        return writer.toByteArray();
    }

    private VerifiedEnvelope verifyEnvelope(
            Purpose expectedPurpose,
            UUID migrationId,
            UUID migrationRunUuid,
            SignedEvidence signedEvidence
    ) throws EvidenceRejectedException {
        requireNonNilUuid(migrationId);
        requireNonNilUuid(migrationRunUuid);
        SignedEvidence evidence = Objects.requireNonNull(
                signedEvidence, "signedEvidence");
        KeyMaterial key = trustedKeys.get(evidence.keyId());
        if (key == null || key.trustedKey().purpose() != expectedPurpose) {
            throw rejectedEvidence();
        }

        byte[] payload = evidence.payload();
        byte[] signature = evidence.signature();
        if (signature.length != SIGNATURE_BYTES
                || payload.length != expectedPayloadBytes(
                        expectedPurpose, key.trustedKey())) {
            throw rejectedEvidence();
        }

        byte[] input = signatureInput(expectedPurpose, payload);
        boolean authentic;
        try {
            authentic = Ed25519.verify(
                    signature,
                    0,
                    key.publicPoint(),
                    input,
                    0,
                    input.length);
        } catch (RuntimeException verificationFailure) {
            throw rejectedEvidence();
        }
        if (!authentic) {
            throw rejectedEvidence();
        }

        DecodedPayload decoded = decodePayload(expectedPurpose, payload);
        CommonClaims common = decoded.common();
        TrustedKey trustedKey = key.trustedKey();
        if (!common.keyId().equals(evidence.keyId())
                || !common.keyId().equals(trustedKey.keyId())
                || !common.issuer().equals(trustedKey.issuer())
                || !common.migrationId().equals(migrationId)
                || !common.migrationRunUuid().equals(migrationRunUuid)) {
            throw rejectedEvidence();
        }
        requireActiveWindow(common, trustedKey);
        return new VerifiedEnvelope(
                expectedPurpose,
                decoded,
                common.keyId(),
                payload,
                signature);
    }

    private void requireActiveWindow(
            CommonClaims claims,
            TrustedKey trustedKey
    ) throws EvidenceRejectedException {
        if (trustedKey.revoked()) {
            throw rejectedEvidence();
        }
        Instant now;
        Instant earliestAcceptedExpiry;
        Instant latestAcceptedIssuance;
        Duration lifetime;
        try {
            now = Objects.requireNonNull(clock.instant(), "clock instant");
            earliestAcceptedExpiry = now.minus(allowedClockSkew);
            latestAcceptedIssuance = now.plus(allowedClockSkew);
            lifetime = Duration.between(
                    claims.issuedAt(), claims.expiresAt());
        } catch (DateTimeException | ArithmeticException failure) {
            throw rejectedEvidence();
        }
        if (now.isBefore(trustedKey.validFrom())
                || !now.isBefore(trustedKey.validUntil())
                || claims.issuedAt().isBefore(trustedKey.validFrom())
                || claims.expiresAt().isAfter(trustedKey.validUntil())
                || claims.issuedAt().isAfter(latestAcceptedIssuance)
                || !claims.expiresAt().isAfter(earliestAcceptedExpiry)
                || lifetime.isZero()
                || lifetime.isNegative()
                || lifetime.compareTo(maximumEvidenceLifetime) > 0) {
            throw rejectedEvidence();
        }
    }

    private static int expectedPayloadBytes(
            Purpose purpose,
            TrustedKey key
    ) {
        int receiptBytes = switch (purpose) {
            case PREPARE -> 0;
            case FREEZE -> 6 * (1 + SHA256_BYTES);
            case APPLY -> 7 * (1 + SHA256_BYTES);
            case RECOVERY -> 8 * (1 + SHA256_BYTES);
        };
        return Math.addExact(
                FIXED_COMMON_PAYLOAD_BYTES + receiptBytes,
                Math.addExact(
                        asciiBytes(key.issuer()).length,
                        asciiBytes(key.keyId()).length));
    }

    private static byte[] encodePayload(
            Purpose purpose,
            CommonClaims common,
            FreezeReceiptClaims freezeReceipts,
            String applyAuthorizationReceiptSha256,
            String legacyRuntimeDisabledReceiptSha256
    ) {
        Purpose requiredPurpose = Objects.requireNonNull(purpose, "purpose");
        CommonClaims requiredCommon = Objects.requireNonNull(common, "common");
        requireTailShape(
                requiredPurpose,
                freezeReceipts,
                applyAuthorizationReceiptSha256,
                legacyRuntimeDisabledReceiptSha256);

        CanonicalWriter writer = new CanonicalWriter();
        writer.writeBytes(MAGIC);
        writer.writeByte(FORMAT_VERSION);
        writer.writeByte(requiredPurpose.wireCode());
        writer.writeAscii(requiredCommon.issuer());
        writer.writeAscii(requiredCommon.keyId());

        writer.writeTaggedUuid(
                MIGRATION_ID_TAG, requiredCommon.migrationId());
        writer.writeTaggedUuid(
                RUN_UUID_TAG, requiredCommon.migrationRunUuid());
        writer.writeTaggedUuid(
                EVIDENCE_UUID_TAG, requiredCommon.evidenceUuid());
        writer.writeTaggedLong(
                ISSUED_AT_TAG, requiredCommon.issuedAt().getEpochSecond());
        writer.writeTaggedLong(
                EXPIRES_AT_TAG, requiredCommon.expiresAt().getEpochSecond());
        writer.writeTaggedSha(
                PLAN_CANDIDATE_DIGEST_TAG,
                TagMigrationPlanCandidateFactory.candidateDigest(
                        requiredCommon.migrationId(),
                        requiredCommon.migrationRunUuid(),
                        requiredCommon.binding()));

        RunBinding binding = requiredCommon.binding();
        writer.writeTaggedSha(
                BACKUP_MANIFEST_TAG, binding.backupManifestSha256());
        writer.writeTaggedSha(
                CLUSTER_DATABASE_IDENTITY_TAG,
                binding.clusterDatabaseIdentitySha256());
        writer.writeTaggedSha(
                RUN_IDENTITY_TAG, binding.runIdentitySha256());
        writer.writeTaggedSha(
                PREFLIGHT_DIGEST_TAG, binding.preflightDigestSha256());
        writer.writeTaggedSha(
                SOURCE_SET_DIGEST_TAG, binding.sourceSetDigestSha256());
        writer.writeTaggedSha(
                PLAN_SET_DIGEST_TAG, binding.planSetDigestSha256());
        writer.writeTaggedSha(
                PREAPPLY_TARGET_SET_DIGEST_TAG,
                binding.preapplyTargetSetDigestSha256());
        writer.writeTaggedSha(
                FINAL_TARGET_SET_DIGEST_TAG,
                binding.finalTargetSetDigestSha256());
        writer.writeTaggedSha(
                MEMBERSHIP_SET_DIGEST_TAG,
                binding.membershipSetDigestSha256());

        if (freezeReceipts != null) {
            writer.writeTaggedSha(
                    SOURCE_WRITER_STOP_TAG,
                    freezeReceipts.sourceWriterStopReceiptSha256());
            writer.writeTaggedSha(
                    TARGET_WRITER_STOP_TAG,
                    freezeReceipts.targetWriterStopReceiptSha256());
            writer.writeTaggedSha(
                    MEMBERSHIP_WRITER_STOP_TAG,
                    freezeReceipts.membershipWriterStopReceiptSha256());
            writer.writeTaggedSha(
                    CONNECTION_DRAIN_TAG,
                    freezeReceipts.connectionDrainReceiptSha256());
            writer.writeTaggedSha(
                    CONNECTION_REJECTION_TAG,
                    freezeReceipts.connectionRejectionReceiptSha256());
            writer.writeTaggedSha(
                    RESTORED_BACKUP_TAG,
                    freezeReceipts.restoredBackupReceiptSha256());
        }
        if (applyAuthorizationReceiptSha256 != null) {
            writer.writeTaggedSha(
                    APPLY_AUTHORIZATION_TAG,
                    applyAuthorizationReceiptSha256);
        }
        if (legacyRuntimeDisabledReceiptSha256 != null) {
            writer.writeTaggedSha(
                    LEGACY_RUNTIME_DISABLED_TAG,
                    legacyRuntimeDisabledReceiptSha256);
        }

        byte[] payload = writer.toByteArray();
        if (payload.length > MAX_CANONICAL_PAYLOAD_BYTES) {
            throw new IllegalArgumentException(
                    "canonical evidence payload is too large");
        }
        return payload;
    }

    private static void requireTailShape(
            Purpose purpose,
            FreezeReceiptClaims freezeReceipts,
            String applyAuthorizationReceiptSha256,
            String legacyRuntimeDisabledReceiptSha256
    ) {
        switch (purpose) {
            case PREPARE -> {
                if (freezeReceipts != null
                        || applyAuthorizationReceiptSha256 != null
                        || legacyRuntimeDisabledReceiptSha256 != null) {
                    throw new IllegalArgumentException(
                            "prepare evidence has an invalid receipt tail");
                }
            }
            case FREEZE -> {
                Objects.requireNonNull(freezeReceipts, "freezeReceipts");
                if (applyAuthorizationReceiptSha256 != null
                        || legacyRuntimeDisabledReceiptSha256 != null) {
                    throw new IllegalArgumentException(
                            "freeze evidence has an invalid receipt tail");
                }
            }
            case APPLY -> {
                Objects.requireNonNull(freezeReceipts, "freezeReceipts");
                if (applyAuthorizationReceiptSha256 != null) {
                    throw new IllegalArgumentException(
                            "apply authorization receipt must be derived");
                }
                requireArtifactSha256(
                        legacyRuntimeDisabledReceiptSha256,
                        "legacyRuntimeDisabledReceiptSha256");
                requireReceiptDistinctness(
                        freezeReceipts,
                        List.of(legacyRuntimeDisabledReceiptSha256));
            }
            case RECOVERY -> {
                Objects.requireNonNull(freezeReceipts, "freezeReceipts");
                requireArtifactSha256(
                        applyAuthorizationReceiptSha256,
                        "applyAuthorizationReceiptSha256");
                requireArtifactSha256(
                        legacyRuntimeDisabledReceiptSha256,
                        "legacyRuntimeDisabledReceiptSha256");
                requireReceiptDistinctness(
                        freezeReceipts,
                        List.of(
                                applyAuthorizationReceiptSha256,
                                legacyRuntimeDisabledReceiptSha256));
            }
        }
    }

    private static DecodedPayload decodePayload(
            Purpose expectedPurpose,
            byte[] payload
    ) {
        CanonicalCursor cursor = new CanonicalCursor(payload);
        cursor.expectBytes(MAGIC);
        cursor.expectByte(FORMAT_VERSION);
        cursor.expectByte(expectedPurpose.wireCode());
        String issuer = cursor.readAscii();
        String keyId = cursor.readAscii();
        UUID migrationId = cursor.readTaggedUuid(MIGRATION_ID_TAG);
        UUID migrationRunUuid = cursor.readTaggedUuid(RUN_UUID_TAG);
        UUID evidenceUuid = cursor.readTaggedUuid(EVIDENCE_UUID_TAG);
        Instant issuedAt = Instant.ofEpochSecond(
                cursor.readTaggedLong(ISSUED_AT_TAG));
        Instant expiresAt = Instant.ofEpochSecond(
                cursor.readTaggedLong(EXPIRES_AT_TAG));
        String encodedCandidateDigest = cursor.readTaggedSha(
                PLAN_CANDIDATE_DIGEST_TAG);

        RunBinding binding = new RunBinding(
                cursor.readTaggedSha(BACKUP_MANIFEST_TAG),
                cursor.readTaggedSha(CLUSTER_DATABASE_IDENTITY_TAG),
                cursor.readTaggedSha(RUN_IDENTITY_TAG),
                cursor.readTaggedSha(PREFLIGHT_DIGEST_TAG),
                cursor.readTaggedSha(SOURCE_SET_DIGEST_TAG),
                cursor.readTaggedSha(PLAN_SET_DIGEST_TAG),
                cursor.readTaggedSha(PREAPPLY_TARGET_SET_DIGEST_TAG),
                cursor.readTaggedSha(FINAL_TARGET_SET_DIGEST_TAG),
                cursor.readTaggedSha(MEMBERSHIP_SET_DIGEST_TAG));
        CommonClaims common = new CommonClaims(
                issuer,
                keyId,
                migrationId,
                migrationRunUuid,
                evidenceUuid,
                issuedAt,
                expiresAt,
                binding);
        String recomputedCandidateDigest =
                TagMigrationPlanCandidateFactory.candidateDigest(
                        migrationId, migrationRunUuid, binding);
        if (!MessageDigest.isEqual(
                HexFormat.of().parseHex(encodedCandidateDigest),
                HexFormat.of().parseHex(recomputedCandidateDigest))) {
            throw new IllegalArgumentException(
                    "plan-candidate digest does not match its bound inputs");
        }

        FreezeReceiptClaims freezeReceipts = null;
        String applyAuthorizationReceiptSha256 = null;
        String legacyRuntimeDisabledReceiptSha256 = null;
        if (expectedPurpose != Purpose.PREPARE) {
            freezeReceipts = new FreezeReceiptClaims(
                    cursor.readTaggedSha(SOURCE_WRITER_STOP_TAG),
                    cursor.readTaggedSha(TARGET_WRITER_STOP_TAG),
                    cursor.readTaggedSha(MEMBERSHIP_WRITER_STOP_TAG),
                    cursor.readTaggedSha(CONNECTION_DRAIN_TAG),
                    cursor.readTaggedSha(CONNECTION_REJECTION_TAG),
                    cursor.readTaggedSha(RESTORED_BACKUP_TAG));
        }
        if (expectedPurpose == Purpose.RECOVERY) {
            applyAuthorizationReceiptSha256 = cursor.readTaggedSha(
                    APPLY_AUTHORIZATION_TAG);
        }
        if (expectedPurpose == Purpose.APPLY
                || expectedPurpose == Purpose.RECOVERY) {
            legacyRuntimeDisabledReceiptSha256 = cursor.readTaggedSha(
                    LEGACY_RUNTIME_DISABLED_TAG);
        }
        cursor.requireEnd();
        requireTailShape(
                expectedPurpose,
                freezeReceipts,
                applyAuthorizationReceiptSha256,
                legacyRuntimeDisabledReceiptSha256);

        DecodedPayload decoded = new DecodedPayload(
                common,
                freezeReceipts,
                applyAuthorizationReceiptSha256,
                legacyRuntimeDisabledReceiptSha256);
        byte[] canonical = switch (expectedPurpose) {
            case PREPARE -> encodePreparePayload(
                    new PrepareClaims(common));
            case FREEZE -> encodeFreezePayload(
                    new FreezeClaims(common, freezeReceipts));
            case APPLY -> encodeApplyPayload(
                    new ApplyClaims(
                            common,
                            freezeReceipts,
                            legacyRuntimeDisabledReceiptSha256));
            case RECOVERY -> encodeRecoveryPayload(
                    new RecoveryClaims(
                            common,
                            freezeReceipts,
                            applyAuthorizationReceiptSha256,
                            legacyRuntimeDisabledReceiptSha256));
        };
        if (!MessageDigest.isEqual(payload, canonical)) {
            throw new IllegalArgumentException(
                    "evidence payload is not canonical");
        }
        return decoded;
    }

    private static String envelopeReceiptSha256(VerifiedEnvelope envelope) {
        byte[] receiptDomain = asciiBytes(RECEIPT_DOMAIN);
        byte[] keyId = asciiBytes(envelope.keyId());
        CanonicalWriter writer = new CanonicalWriter();
        writer.writeUnsignedShort(receiptDomain.length);
        writer.writeBytes(receiptDomain);
        writer.writeByte(envelope.purpose().wireCode());
        writer.writeByte(keyId.length);
        writer.writeBytes(keyId);
        writer.writeInt(envelope.payloadBytes().length);
        writer.writeBytes(envelope.payloadBytes());
        writer.writeUnsignedShort(envelope.signatureBytes().length);
        writer.writeBytes(envelope.signatureBytes());
        return sha256Hex(writer.toByteArray());
    }

    private static Duration requireDuration(
            Duration value,
            Duration minimum,
            Duration maximum,
            boolean minimumInclusive,
            String name
    ) {
        Duration required = Objects.requireNonNull(value, name);
        int minimumComparison = required.compareTo(minimum);
        if ((minimumInclusive
                ? minimumComparison < 0
                : minimumComparison <= 0)
                || required.compareTo(maximum) > 0) {
            throw new IllegalArgumentException(name + " is outside its fixed bound");
        }
        return required;
    }

    private static String requireIdentifier(String value, String name) {
        String required = Objects.requireNonNull(value, name);
        if (!IDENTIFIER.matcher(required).matches()
                || asciiBytes(required).length > 64) {
            throw new IllegalArgumentException(name + " is not canonical ASCII");
        }
        return required;
    }

    private static UUID requireNonNilUuid(UUID value) {
        UUID required = Objects.requireNonNull(value, "UUID");
        if (required.equals(NIL_UUID)) {
            throw new IllegalArgumentException("UUID must not be nil");
        }
        return required;
    }

    private static Instant requireSecondPrecision(
            Instant value,
            String name
    ) {
        Instant required = Objects.requireNonNull(value, name);
        if (required.getNano() != 0) {
            throw new IllegalArgumentException(name + " must use epoch-second precision");
        }
        return required;
    }

    private static RunBinding requireNonZeroBinding(RunBinding binding) {
        RunBinding required = Objects.requireNonNull(binding, "binding");
        requireArtifactSha256(
                required.backupManifestSha256(), "backupManifestSha256");
        requireArtifactSha256(
                required.clusterDatabaseIdentitySha256(),
                "clusterDatabaseIdentitySha256");
        requireArtifactSha256(
                required.runIdentitySha256(), "runIdentitySha256");
        requireArtifactSha256(
                required.preflightDigestSha256(), "preflightDigestSha256");
        requireArtifactSha256(
                required.sourceSetDigestSha256(), "sourceSetDigestSha256");
        requireArtifactSha256(
                required.planSetDigestSha256(), "planSetDigestSha256");
        requireArtifactSha256(
                required.preapplyTargetSetDigestSha256(),
                "preapplyTargetSetDigestSha256");
        requireArtifactSha256(
                required.finalTargetSetDigestSha256(),
                "finalTargetSetDigestSha256");
        requireArtifactSha256(
                required.membershipSetDigestSha256(),
                "membershipSetDigestSha256");
        return required;
    }

    private static String requireArtifactSha256(String value, String name) {
        String required = TagMigrationDigests.requireSha256(value, name);
        if (ZERO_SHA256.equals(required)) {
            throw new IllegalArgumentException(name + " must not be all zero");
        }
        return required;
    }

    private static void requireReceiptDistinctness(
            FreezeReceiptClaims freezeReceipts,
            List<String> additionalReceipts
    ) {
        FreezeReceiptClaims freeze = Objects.requireNonNull(
                freezeReceipts, "freezeReceipts");
        List<String> receipts = new ArrayList<>(List.of(
                freeze.sourceWriterStopReceiptSha256(),
                freeze.targetWriterStopReceiptSha256(),
                freeze.membershipWriterStopReceiptSha256(),
                freeze.connectionDrainReceiptSha256(),
                freeze.connectionRejectionReceiptSha256(),
                freeze.restoredBackupReceiptSha256()));
        receipts.addAll(Objects.requireNonNull(
                additionalReceipts, "additionalReceipts"));
        if (new HashSet<>(receipts).size() != receipts.size()) {
            throw new IllegalArgumentException(
                    "receipt digests must be pairwise distinct");
        }
    }

    private static byte[] rawPublicKey(EdECPublicKey publicKey) {
        EdECPublicKey key = Objects.requireNonNull(publicKey, "publicKey");
        NamedParameterSpec params = Objects.requireNonNull(
                key.getParams(), "public key parameters");
        if (!NamedParameterSpec.ED25519.getName().equals(params.getName())) {
            throw new IllegalArgumentException(
                    "public key parameters must be Ed25519");
        }
        EdECPoint point = Objects.requireNonNull(
                key.getPoint(), "public key point");
        BigInteger y = Objects.requireNonNull(point.getY(), "public key y");
        if (y.signum() < 0 || y.bitLength() > 255) {
            throw new IllegalArgumentException("public key point is not canonical");
        }
        byte[] bigEndian = y.toByteArray();
        if (bigEndian.length > RAW_PUBLIC_KEY_BYTES) {
            throw new IllegalArgumentException("public key point is not canonical");
        }
        byte[] encoded = new byte[RAW_PUBLIC_KEY_BYTES];
        for (int index = 0; index < bigEndian.length; index++) {
            encoded[index] = bigEndian[bigEndian.length - 1 - index];
        }
        if (point.isXOdd()) {
            encoded[RAW_PUBLIC_KEY_BYTES - 1] |= (byte) 0x80;
        }
        return encoded;
    }

    private static byte[] asciiBytes(String value) {
        String required = Objects.requireNonNull(value, "ASCII value");
        byte[] encoded = required.getBytes(StandardCharsets.US_ASCII);
        if (!required.equals(new String(encoded, StandardCharsets.US_ASCII))) {
            throw new IllegalArgumentException("value is not ASCII");
        }
        return encoded;
    }

    private static byte[] shaBytes(String value) {
        String required = requireArtifactSha256(value, "SHA-256");
        return HexFormat.of().parseHex(required);
    }

    private static String sha256Hex(byte[] value) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(value));
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable", impossible);
        }
    }

    private static EvidenceRejectedException rejectedEvidence() {
        return new EvidenceRejectedException();
    }

    /** The four independently keyed and domain-separated evidence purposes. */
    public enum Purpose {
        PREPARE(0x01, "prepare"),
        FREEZE(0x02, "freeze"),
        APPLY(0x03, "apply"),
        RECOVERY(0x04, "recovery");

        private static final String DOMAIN_PREFIX =
                "ti:phase4c:legacy-personal-bank-tag-migration:"
                        + "evidence:ed25519:";

        private final int wireCode;
        private final String signatureDomain;

        Purpose(int wireCode, String domainPurpose) {
            this.wireCode = wireCode;
            this.signatureDomain = DOMAIN_PREFIX + domainPurpose + ":v1";
        }

        public int wireCode() {
            return wireCode;
        }

        public String signatureDomain() {
            return signatureDomain;
        }

        private byte[] domainBytes() {
            return asciiBytes(signatureDomain);
        }
    }

    /** Immutable, single-purpose public-key trust entry. */
    public record TrustedKey(
            String keyId,
            String issuer,
            Purpose purpose,
            byte[] rawPublicKey,
            Instant validFrom,
            Instant validUntil,
            boolean revoked
    ) {
        public TrustedKey {
            keyId = requireIdentifier(keyId, "keyId");
            issuer = requireIdentifier(issuer, "issuer");
            purpose = Objects.requireNonNull(purpose, "purpose");
            rawPublicKey = Objects.requireNonNull(
                    rawPublicKey, "rawPublicKey").clone();
            validFrom = Objects.requireNonNull(validFrom, "validFrom");
            validUntil = Objects.requireNonNull(validUntil, "validUntil");
            if (rawPublicKey.length != RAW_PUBLIC_KEY_BYTES) {
                throw new IllegalArgumentException(
                        "raw Ed25519 public key must contain 32 bytes");
            }
            if (!validFrom.isBefore(validUntil)) {
                throw new IllegalArgumentException(
                        "trusted key validity interval is empty");
            }
        }

        /** Convenience overload for an explicitly supplied JDK Ed25519 key. */
        public TrustedKey(
                String keyId,
                String issuer,
                Purpose purpose,
                EdECPublicKey publicKey,
                Instant validFrom,
                Instant validUntil,
                boolean revoked
        ) {
            this(
                    keyId,
                    issuer,
                    purpose,
                    Ed25519TagMigrationEvidenceVerifier.rawPublicKey(
                            publicKey),
                    validFrom,
                    validUntil,
                    revoked);
        }

        @Override
        public byte[] rawPublicKey() {
            return rawPublicKey.clone();
        }
    }

    /** Claims shared by every signed operator phase. */
    public record CommonClaims(
            String issuer,
            String keyId,
            UUID migrationId,
            UUID migrationRunUuid,
            UUID evidenceUuid,
            Instant issuedAt,
            Instant expiresAt,
            RunBinding binding
    ) {
        public CommonClaims {
            issuer = requireIdentifier(issuer, "issuer");
            keyId = requireIdentifier(keyId, "keyId");
            migrationId = requireNonNilUuid(migrationId);
            migrationRunUuid = requireNonNilUuid(migrationRunUuid);
            evidenceUuid = requireNonNilUuid(evidenceUuid);
            issuedAt = requireSecondPrecision(issuedAt, "issuedAt");
            expiresAt = requireSecondPrecision(expiresAt, "expiresAt");
            binding = requireNonZeroBinding(binding);
            if (!issuedAt.isBefore(expiresAt)) {
                throw new IllegalArgumentException(
                        "evidence validity interval is empty");
            }
        }
    }

    /** Six independent freeze receipts, including three writer-stop domains. */
    public record FreezeReceiptClaims(
            String sourceWriterStopReceiptSha256,
            String targetWriterStopReceiptSha256,
            String membershipWriterStopReceiptSha256,
            String connectionDrainReceiptSha256,
            String connectionRejectionReceiptSha256,
            String restoredBackupReceiptSha256
    ) {
        public FreezeReceiptClaims {
            sourceWriterStopReceiptSha256 = requireArtifactSha256(
                    sourceWriterStopReceiptSha256,
                    "sourceWriterStopReceiptSha256");
            targetWriterStopReceiptSha256 = requireArtifactSha256(
                    targetWriterStopReceiptSha256,
                    "targetWriterStopReceiptSha256");
            membershipWriterStopReceiptSha256 = requireArtifactSha256(
                    membershipWriterStopReceiptSha256,
                    "membershipWriterStopReceiptSha256");
            connectionDrainReceiptSha256 = requireArtifactSha256(
                    connectionDrainReceiptSha256,
                    "connectionDrainReceiptSha256");
            connectionRejectionReceiptSha256 = requireArtifactSha256(
                    connectionRejectionReceiptSha256,
                    "connectionRejectionReceiptSha256");
            restoredBackupReceiptSha256 = requireArtifactSha256(
                    restoredBackupReceiptSha256,
                    "restoredBackupReceiptSha256");
            Set<String> distinct = Set.of(
                    sourceWriterStopReceiptSha256,
                    targetWriterStopReceiptSha256,
                    membershipWriterStopReceiptSha256,
                    connectionDrainReceiptSha256,
                    connectionRejectionReceiptSha256,
                    restoredBackupReceiptSha256);
            if (distinct.size() != 6) {
                throw new IllegalArgumentException(
                        "freeze receipt digests must be pairwise distinct");
            }
        }
    }

    public record PrepareClaims(CommonClaims common) {
        public PrepareClaims {
            common = Objects.requireNonNull(common, "common");
        }
    }

    public record FreezeClaims(
            CommonClaims common,
            FreezeReceiptClaims receipts
    ) {
        public FreezeClaims {
            common = Objects.requireNonNull(common, "common");
            receipts = Objects.requireNonNull(receipts, "receipts");
        }
    }

    public record ApplyClaims(
            CommonClaims common,
            FreezeReceiptClaims receipts,
            String legacyRuntimeDisabledReceiptSha256
    ) {
        public ApplyClaims {
            common = Objects.requireNonNull(common, "common");
            receipts = Objects.requireNonNull(receipts, "receipts");
            legacyRuntimeDisabledReceiptSha256 = requireArtifactSha256(
                    legacyRuntimeDisabledReceiptSha256,
                    "legacyRuntimeDisabledReceiptSha256");
            requireReceiptDistinctness(
                    receipts,
                    List.of(legacyRuntimeDisabledReceiptSha256));
        }
    }

    public record RecoveryClaims(
            CommonClaims common,
            FreezeReceiptClaims receipts,
            String applyAuthorizationReceiptSha256,
            String legacyRuntimeDisabledReceiptSha256
    ) {
        public RecoveryClaims {
            common = Objects.requireNonNull(common, "common");
            receipts = Objects.requireNonNull(receipts, "receipts");
            applyAuthorizationReceiptSha256 = requireArtifactSha256(
                    applyAuthorizationReceiptSha256,
                    "applyAuthorizationReceiptSha256");
            legacyRuntimeDisabledReceiptSha256 = requireArtifactSha256(
                    legacyRuntimeDisabledReceiptSha256,
                    "legacyRuntimeDisabledReceiptSha256");
            requireReceiptDistinctness(
                    receipts,
                    List.of(
                            applyAuthorizationReceiptSha256,
                            legacyRuntimeDisabledReceiptSha256));
        }
    }

    private record KeyMaterial(
            TrustedKey trustedKey,
            PublicPoint publicPoint
    ) {
    }

    private record DecodedPayload(
            CommonClaims common,
            FreezeReceiptClaims freezeReceipts,
            String applyAuthorizationReceiptSha256,
            String legacyRuntimeDisabledReceiptSha256
    ) {
    }

    private record VerifiedEnvelope(
            Purpose purpose,
            DecodedPayload payload,
            String keyId,
            byte[] payloadBytes,
            byte[] signatureBytes
    ) {
        private VerifiedEnvelope {
            payloadBytes = payloadBytes.clone();
            signatureBytes = signatureBytes.clone();
        }

        @Override
        public byte[] payloadBytes() {
            return payloadBytes.clone();
        }

        @Override
        public byte[] signatureBytes() {
            return signatureBytes.clone();
        }
    }

    private static final class CanonicalWriter {
        private final ByteArrayOutputStream output = new ByteArrayOutputStream();

        private void writeByte(int value) {
            output.write(value & 0xff);
        }

        private void writeUnsignedShort(int value) {
            if (value < 0 || value > 0xffff) {
                throw new IllegalArgumentException(
                        "unsigned-short value is out of range");
            }
            writeByte(value >>> 8);
            writeByte(value);
        }

        private void writeInt(int value) {
            writeBytes(ByteBuffer.allocate(Integer.BYTES)
                    .order(ByteOrder.BIG_ENDIAN)
                    .putInt(value)
                    .array());
        }

        private void writeLong(long value) {
            writeBytes(ByteBuffer.allocate(Long.BYTES)
                    .order(ByteOrder.BIG_ENDIAN)
                    .putLong(value)
                    .array());
        }

        private void writeBytes(byte[] bytes) {
            output.writeBytes(Objects.requireNonNull(bytes, "bytes"));
        }

        private void writeAscii(String value) {
            byte[] bytes = asciiBytes(requireIdentifier(value, "identifier"));
            writeByte(bytes.length);
            writeBytes(bytes);
        }

        private void writeTaggedUuid(int tag, UUID value) {
            UUID uuid = requireNonNilUuid(value);
            writeByte(tag);
            writeLong(uuid.getMostSignificantBits());
            writeLong(uuid.getLeastSignificantBits());
        }

        private void writeTaggedLong(int tag, long value) {
            writeByte(tag);
            writeLong(value);
        }

        private void writeTaggedSha(int tag, String value) {
            writeByte(tag);
            writeBytes(shaBytes(value));
        }

        private byte[] toByteArray() {
            return output.toByteArray();
        }
    }

    private static final class CanonicalCursor {
        private final byte[] bytes;
        private int offset;

        private CanonicalCursor(byte[] bytes) {
            this.bytes = Objects.requireNonNull(bytes, "bytes").clone();
        }

        private int readUnsignedByte() {
            requireRemaining(1);
            return bytes[offset++] & 0xff;
        }

        private void expectByte(int expected) {
            if (readUnsignedByte() != expected) {
                throw new IllegalArgumentException(
                        "unexpected canonical field tag");
            }
        }

        private void expectBytes(byte[] expected) {
            byte[] actual = readBytes(expected.length);
            if (!MessageDigest.isEqual(actual, expected)) {
                throw new IllegalArgumentException(
                        "unexpected canonical prefix");
            }
        }

        private byte[] readBytes(int length) {
            if (length < 0) {
                throw new IllegalArgumentException("negative field length");
            }
            requireRemaining(length);
            byte[] value = Arrays.copyOfRange(bytes, offset, offset + length);
            offset += length;
            return value;
        }

        private long readLong() {
            return ByteBuffer.wrap(readBytes(Long.BYTES))
                    .order(ByteOrder.BIG_ENDIAN)
                    .getLong();
        }

        private String readAscii() {
            int length = readUnsignedByte();
            if (length == 0 || length > 64) {
                throw new IllegalArgumentException(
                        "canonical ASCII length is invalid");
            }
            byte[] encoded = readBytes(length);
            for (byte value : encoded) {
                if ((value & 0x80) != 0) {
                    throw new IllegalArgumentException(
                            "canonical identifier is not ASCII");
                }
            }
            String decoded = new String(encoded, StandardCharsets.US_ASCII);
            return requireIdentifier(decoded, "identifier");
        }

        private UUID readTaggedUuid(int tag) {
            expectByte(tag);
            return requireNonNilUuid(new UUID(readLong(), readLong()));
        }

        private long readTaggedLong(int tag) {
            expectByte(tag);
            return readLong();
        }

        private String readTaggedSha(int tag) {
            expectByte(tag);
            String value = HexFormat.of().formatHex(readBytes(SHA256_BYTES));
            return requireArtifactSha256(value, "SHA-256 field");
        }

        private void requireEnd() {
            if (offset != bytes.length) {
                throw new IllegalArgumentException(
                        "canonical evidence contains trailing bytes");
            }
        }

        private void requireRemaining(int length) {
            if (length > bytes.length - offset) {
                throw new IllegalArgumentException(
                        "canonical evidence is truncated");
            }
        }
    }
}
