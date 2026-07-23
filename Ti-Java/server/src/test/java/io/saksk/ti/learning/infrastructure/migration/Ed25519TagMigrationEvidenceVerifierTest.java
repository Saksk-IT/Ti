package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.ApplyClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.CommonClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.FreezeClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.FreezeReceiptClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.PrepareClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.Purpose;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.RecoveryClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.TrustedKey;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceRejectedException;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.SignedEvidence;
import java.math.BigInteger;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.EdECPublicKey;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;
import java.util.stream.Stream;
import org.bouncycastle.math.ec.rfc8032.Ed25519;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class Ed25519TagMigrationEvidenceVerifierTest {

    private static final HexFormat HEX = HexFormat.of();
    private static final Instant NOW = Instant.parse("2026-07-20T00:00:00Z");
    private static final Duration SKEW = Duration.ofSeconds(30);
    private static final Duration MAX_LIFETIME = Duration.ofMinutes(5);
    private static final String ISSUER = "ti-operator";

    private static final UUID MIGRATION_ID =
            UUID.fromString("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee");
    private static final UUID RUN_UUID =
            UUID.fromString("11111111-2222-4333-8444-555555555555");
    private static final UUID OTHER_RUN_UUID =
            UUID.fromString("22222222-3333-4444-8555-666666666666");

    // RFC 8032, section 7.1, test vector 1 seed and public key.
    private static final byte[] PREPARE_SEED = HEX.parseHex(
            "9d61b19deffd5a60ba844af492ec2cc4"
                    + "4449c5697b326919703bac031cae7f60");
    private static final byte[] RFC_PUBLIC_KEY = HEX.parseHex(
            "d75a980182b10ab7d54bfed3c964073a"
                    + "0ee172f3daa62325af021a68f707511a");
    private static final byte[] FREEZE_SEED = HEX.parseHex("11".repeat(32));
    private static final byte[] APPLY_SEED = HEX.parseHex("22".repeat(32));
    private static final byte[] RECOVERY_SEED = HEX.parseHex("33".repeat(32));

    private static final String PREPARE_KEY_ID = "prepare-key-v1";
    private static final String FREEZE_KEY_ID = "freeze-key-v1";
    private static final String APPLY_KEY_ID = "apply-key-v1";
    private static final String RECOVERY_KEY_ID = "recovery-key-v1";

    private static final RunBinding BINDING = new RunBinding(
            "01".repeat(32),
            "02".repeat(32),
            "03".repeat(32),
            "04".repeat(32),
            "05".repeat(32),
            "06".repeat(32),
            "07".repeat(32),
            "08".repeat(32),
            "09".repeat(32));

    private static final FreezeReceiptClaims FREEZE_RECEIPTS =
            new FreezeReceiptClaims(
                    "11".repeat(32),
                    "12".repeat(32),
                    "13".repeat(32),
                    "14".repeat(32),
                    "15".repeat(32),
                    "16".repeat(32));
    private static final String LEGACY_RUNTIME_DISABLED = "17".repeat(32);

    @Test
    void rfc8032GoldenAndCanonicalPrepareReceiptAreDeterministic()
            throws Exception {
        assertThat(publicKey(PREPARE_SEED)).containsExactly(RFC_PUBLIC_KEY);
        byte[] rfcSignature = new byte[64];
        Ed25519.sign(
                PREPARE_SEED,
                0,
                new byte[0],
                0,
                0,
                rfcSignature,
                0);
        assertThat(HEX.formatHex(rfcSignature)).isEqualTo(
                "e5564300c360ac729086e2cc806e828a"
                        + "84877f1eb8e5d974d873e06522490155"
                        + "5fb8821590a33bacc61e39701cf9b46b"
                        + "d25bf5f0595bbe24655141438e7a100b");

        PrepareClaims claims = new PrepareClaims(common(
                PREPARE_KEY_ID,
                UUID.fromString("99999999-8888-4777-8666-555555555555"),
                NOW.minusSeconds(10),
                NOW.plusSeconds(240)));
        byte[] payload = Ed25519TagMigrationEvidenceVerifier
                .encodePreparePayload(claims);
        byte[] signature = sign(Purpose.PREPARE, payload, PREPARE_SEED);

        assertThat(payload)
                .hasSize(432)
                .startsWith(
                        (byte) 'T',
                        (byte) 'I',
                        (byte) 'T',
                        (byte) 'M',
                        (byte) 1,
                        (byte) 1);
        assertThat(signature).hasSize(64).containsExactly(
                sign(Purpose.PREPARE, payload, PREPARE_SEED));

        var verified = verifier().verifyPrepare(
                MIGRATION_ID,
                RUN_UUID,
                new SignedEvidence(PREPARE_KEY_ID, payload, signature));

        assertThat(verified.binding()).isEqualTo(BINDING);
        assertThat(verified.prepareEvidenceReceiptSha256())
                .matches("[0-9a-f]{64}")
                .isEqualTo(verifier().verifyPrepare(
                        MIGRATION_ID,
                        RUN_UUID,
                        new SignedEvidence(
                                PREPARE_KEY_ID,
                                payload,
                                signature))
                        .prepareEvidenceReceiptSha256());
    }

    @Test
    void allFourPurposesVerifyAndApplyReceiptFeedsRecovery() throws Exception {
        Ed25519TagMigrationEvidenceVerifier verifier = verifier();

        CommonClaims freezeCommon = common(
                FREEZE_KEY_ID,
                UUID.fromString("10000000-0000-4000-8000-000000000002"),
                NOW.minusSeconds(5),
                NOW.plusSeconds(120));
        byte[] freezePayload = Ed25519TagMigrationEvidenceVerifier
                .encodeFreezePayload(new FreezeClaims(
                        freezeCommon, FREEZE_RECEIPTS));
        var freeze = verifier.verifyFreeze(
                MIGRATION_ID,
                RUN_UUID,
                signed(FREEZE_KEY_ID, Purpose.FREEZE, freezePayload, FREEZE_SEED));
        assertThat(freeze.binding()).isEqualTo(BINDING);
        assertThat(freeze.sourceWriterStopReceiptSha256())
                .isEqualTo(FREEZE_RECEIPTS.sourceWriterStopReceiptSha256());
        assertThat(freeze.targetWriterStopReceiptSha256())
                .isEqualTo(FREEZE_RECEIPTS.targetWriterStopReceiptSha256());
        assertThat(freeze.membershipWriterStopReceiptSha256())
                .isEqualTo(FREEZE_RECEIPTS.membershipWriterStopReceiptSha256());

        CommonClaims applyCommon = common(
                APPLY_KEY_ID,
                UUID.fromString("10000000-0000-4000-8000-000000000003"),
                NOW.minusSeconds(5),
                NOW.plusSeconds(120));
        byte[] applyPayload = Ed25519TagMigrationEvidenceVerifier
                .encodeApplyPayload(new ApplyClaims(
                        applyCommon,
                        FREEZE_RECEIPTS,
                        LEGACY_RUNTIME_DISABLED));
        SignedEvidence applyEvidence = signed(
                APPLY_KEY_ID, Purpose.APPLY, applyPayload, APPLY_SEED);
        var firstApply = verifier.verifyApply(
                MIGRATION_ID, RUN_UUID, applyEvidence);
        var replayedApply = verifier.verifyApply(
                MIGRATION_ID, RUN_UUID, applyEvidence);

        assertThat(firstApply).isEqualTo(replayedApply);
        assertThat(firstApply.applyAuthorizationReceiptSha256())
                .matches("[0-9a-f]{64}")
                .isNotEqualTo(LEGACY_RUNTIME_DISABLED)
                .isNotIn(
                        FREEZE_RECEIPTS.sourceWriterStopReceiptSha256(),
                        FREEZE_RECEIPTS.targetWriterStopReceiptSha256(),
                        FREEZE_RECEIPTS.membershipWriterStopReceiptSha256());

        CommonClaims recoveryCommon = common(
                RECOVERY_KEY_ID,
                UUID.fromString("10000000-0000-4000-8000-000000000004"),
                NOW.minusSeconds(5),
                NOW.plusSeconds(120));
        byte[] recoveryPayload = Ed25519TagMigrationEvidenceVerifier
                .encodeRecoveryPayload(new RecoveryClaims(
                        recoveryCommon,
                        FREEZE_RECEIPTS,
                        firstApply.applyAuthorizationReceiptSha256(),
                        LEGACY_RUNTIME_DISABLED));
        var recovery = verifier.verifyRecovery(
                MIGRATION_ID,
                RUN_UUID,
                signed(
                        RECOVERY_KEY_ID,
                        Purpose.RECOVERY,
                        recoveryPayload,
                        RECOVERY_SEED));

        assertThat(recovery.binding()).isEqualTo(BINDING);
        assertThat(recovery.applyAuthorizationReceiptSha256())
                .isEqualTo(firstApply.applyAuthorizationReceiptSha256());
        assertThat(recovery.legacyRuntimeDisabledReceiptSha256())
                .isEqualTo(LEGACY_RUNTIME_DISABLED);
    }

    @Test
    void purposeDomainsKeysAndWirePhaseAreNotInterchangeable() {
        byte[] preparePayload = Ed25519TagMigrationEvidenceVerifier
                .encodePreparePayload(new PrepareClaims(common(
                        PREPARE_KEY_ID,
                        UUID.fromString("20000000-0000-4000-8000-000000000001"),
                        NOW.minusSeconds(1),
                        NOW.plusSeconds(60))));

        assertRejected(() -> verifier().verifyPrepare(
                MIGRATION_ID,
                RUN_UUID,
                signed(
                        PREPARE_KEY_ID,
                        Purpose.FREEZE,
                        preparePayload,
                        PREPARE_SEED)));
        assertRejected(() -> verifier().verifyFreeze(
                MIGRATION_ID,
                RUN_UUID,
                signed(
                        PREPARE_KEY_ID,
                        Purpose.PREPARE,
                        preparePayload,
                        PREPARE_SEED)));

        byte[] wrongPhase = preparePayload.clone();
        wrongPhase[5] = (byte) Purpose.FREEZE.wireCode();
        assertRejected(() -> verifier().verifyPrepare(
                MIGRATION_ID,
                RUN_UUID,
                signed(
                        PREPARE_KEY_ID,
                        Purpose.PREPARE,
                        wrongPhase,
                        PREPARE_SEED)));
    }

    @Test
    void canonicalParserRejectsTruncationTailTagIdentityAndIdentifierDrift()
            throws Exception {
        byte[] payload = Ed25519TagMigrationEvidenceVerifier
                .encodePreparePayload(new PrepareClaims(common(
                        PREPARE_KEY_ID,
                        UUID.fromString("30000000-0000-4000-8000-000000000001"),
                        NOW.minusSeconds(1),
                        NOW.plusSeconds(60))));

        List<byte[]> malformed = new ArrayList<>();
        malformed.add(Arrays.copyOf(payload, payload.length - 1));
        malformed.add(Arrays.copyOf(payload, payload.length + 1));

        for (int index : List.of(0, 4, 5, commonFirstTagOffset())) {
            byte[] changed = payload.clone();
            changed[index] ^= 0x01;
            malformed.add(changed);
        }
        byte[] wrongCandidateDigest = payload.clone();
        wrongCandidateDigest[candidateDigestValueOffset()] ^= 0x01;
        malformed.add(wrongCandidateDigest);

        byte[] wrongIssuer = payload.clone();
        wrongIssuer[8] = 'x';
        malformed.add(wrongIssuer);

        int keyStart = 8 + ISSUER.length();
        byte[] wrongKeyId = payload.clone();
        wrongKeyId[keyStart] = 'x';
        malformed.add(wrongKeyId);

        for (byte[] candidate : malformed) {
            SignedEvidence evidence = signed(
                    PREPARE_KEY_ID,
                    Purpose.PREPARE,
                    candidate,
                    PREPARE_SEED);
            assertRejected(() -> verifier().verifyPrepare(
                    MIGRATION_ID, RUN_UUID, evidence));
        }

        SignedEvidence valid = signed(
                PREPARE_KEY_ID, Purpose.PREPARE, payload, PREPARE_SEED);
        assertRejected(() -> verifier().verifyPrepare(
                MIGRATION_ID, OTHER_RUN_UUID, valid));
        assertRejected(() -> verifier().verifyPrepare(
                UUID.fromString("bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"),
                RUN_UUID,
                valid));
    }

    @ParameterizedTest(name = "signature size {0}")
    @MethodSource("invalidSignatureSizes")
    void rejectsEveryNonEd25519SignatureSize(int size) {
        byte[] payload = Ed25519TagMigrationEvidenceVerifier
                .encodePreparePayload(new PrepareClaims(common(
                        PREPARE_KEY_ID,
                        UUID.fromString("40000000-0000-4000-8000-000000000001"),
                        NOW.minusSeconds(1),
                        NOW.plusSeconds(60))));
        SignedEvidence evidence = new SignedEvidence(
                PREPARE_KEY_ID, payload, new byte[size]);
        assertRejected(() -> verifier().verifyPrepare(
                MIGRATION_ID, RUN_UUID, evidence));
    }

    static Stream<Arguments> invalidSignatureSizes() {
        return Stream.of(32, 63, 65, 8_192).map(Arguments::of);
    }

    @Test
    void rejectsScalarMalleabilityNonCanonicalRAndMissingDomain() {
        byte[] payload = Ed25519TagMigrationEvidenceVerifier
                .encodePreparePayload(new PrepareClaims(common(
                        PREPARE_KEY_ID,
                        UUID.fromString("50000000-0000-4000-8000-000000000001"),
                        NOW.minusSeconds(1),
                        NOW.plusSeconds(60))));
        byte[] signature = sign(Purpose.PREPARE, payload, PREPARE_SEED);

        byte[] malleable = signature.clone();
        byte[] increasedS = littleEndian32(
                littleEndianInteger(signature, 32)
                        .add(HEX_BIG_INTEGER_L));
        System.arraycopy(increasedS, 0, malleable, 32, 32);
        assertRejected(() -> verifier().verifyPrepare(
                MIGRATION_ID,
                RUN_UUID,
                new SignedEvidence(PREPARE_KEY_ID, payload, malleable)));

        byte[] nonCanonicalR = signature.clone();
        byte[] fieldPrime = littleEndian32(
                BigInteger.TWO.pow(255).subtract(BigInteger.valueOf(19)));
        System.arraycopy(fieldPrime, 0, nonCanonicalR, 0, 32);
        assertRejected(() -> verifier().verifyPrepare(
                MIGRATION_ID,
                RUN_UUID,
                new SignedEvidence(PREPARE_KEY_ID, payload, nonCanonicalR)));

        byte[] rawPayloadSignature = new byte[64];
        Ed25519.sign(
                PREPARE_SEED,
                0,
                payload,
                0,
                payload.length,
                rawPayloadSignature,
                0);
        assertRejected(() -> verifier().verifyPrepare(
                MIGRATION_ID,
                RUN_UUID,
                new SignedEvidence(
                        PREPARE_KEY_ID, payload, rawPayloadSignature)));
    }

    private static final BigInteger HEX_BIG_INTEGER_L = new BigInteger(
            "10000000000000000000000000000000"
                    + "14def9dea2f79cd65812631a5cf5d3ed",
            16);

    @Test
    void signedCollapsedFreezeReceiptsFailClosed() {
        byte[] payload = Ed25519TagMigrationEvidenceVerifier
                .encodeFreezePayload(new FreezeClaims(
                        common(
                                FREEZE_KEY_ID,
                                UUID.fromString(
                                        "60000000-0000-4000-8000-000000000001"),
                                NOW.minusSeconds(1),
                                NOW.plusSeconds(60)),
                        FREEZE_RECEIPTS));
        int tail = payload.length - 6 * 33;
        byte[] collapsed = payload.clone();
        System.arraycopy(
                collapsed,
                tail + 1,
                collapsed,
                tail + 33 + 1,
                32);
        assertRejected(() -> verifier().verifyFreeze(
                MIGRATION_ID,
                RUN_UUID,
                signed(
                        FREEZE_KEY_ID,
                        Purpose.FREEZE,
                        collapsed,
                        FREEZE_SEED)));

        assertThatThrownBy(() -> new FreezeReceiptClaims(
                "11".repeat(32),
                "11".repeat(32),
                "13".repeat(32),
                "14".repeat(32),
                "15".repeat(32),
                "16".repeat(32)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void evidenceTimeWindowEnforcesSkewLifetimeAndExclusiveExpiry()
            throws Exception {
        CommonClaims exactBoundary = common(
                PREPARE_KEY_ID,
                UUID.fromString("70000000-0000-4000-8000-000000000001"),
                NOW.plus(SKEW),
                NOW.plus(SKEW).plus(MAX_LIFETIME));
        byte[] exactPayload = Ed25519TagMigrationEvidenceVerifier
                .encodePreparePayload(new PrepareClaims(exactBoundary));
        assertThat(verifier().verifyPrepare(
                MIGRATION_ID,
                RUN_UUID,
                signed(
                        PREPARE_KEY_ID,
                        Purpose.PREPARE,
                        exactPayload,
                        PREPARE_SEED))).isNotNull();

        for (CommonClaims invalid : List.of(
                common(
                        PREPARE_KEY_ID,
                        UUID.fromString(
                                "70000000-0000-4000-8000-000000000002"),
                        NOW.plus(SKEW).plusSeconds(1),
                        NOW.plus(SKEW).plusSeconds(61)),
                common(
                        PREPARE_KEY_ID,
                        UUID.fromString(
                                "70000000-0000-4000-8000-000000000003"),
                        NOW.minusSeconds(100),
                        NOW.minus(SKEW)),
                common(
                        PREPARE_KEY_ID,
                        UUID.fromString(
                                "70000000-0000-4000-8000-000000000004"),
                        NOW.minusSeconds(1),
                        NOW.minusSeconds(1).plus(MAX_LIFETIME).plusSeconds(1)))) {
            byte[] invalidPayload = Ed25519TagMigrationEvidenceVerifier
                    .encodePreparePayload(new PrepareClaims(invalid));
            assertRejected(() -> verifier().verifyPrepare(
                    MIGRATION_ID,
                    RUN_UUID,
                    signed(
                            PREPARE_KEY_ID,
                            Purpose.PREPARE,
                            invalidPayload,
                            PREPARE_SEED)));
        }
    }

    @Test
    void keyValidityAndHardRevocationAreFailClosed() {
        CommonClaims common = common(
                PREPARE_KEY_ID,
                UUID.fromString("80000000-0000-4000-8000-000000000001"),
                NOW.minusSeconds(1),
                NOW.plusSeconds(60));
        byte[] payload = Ed25519TagMigrationEvidenceVerifier
                .encodePreparePayload(new PrepareClaims(common));
        SignedEvidence evidence = signed(
                PREPARE_KEY_ID, Purpose.PREPARE, payload, PREPARE_SEED);

        for (TrustedKey key : List.of(
                trusted(
                        PREPARE_KEY_ID,
                        Purpose.PREPARE,
                        PREPARE_SEED,
                        NOW.minusSeconds(60),
                        NOW.plusSeconds(60),
                        true),
                trusted(
                        PREPARE_KEY_ID,
                        Purpose.PREPARE,
                        PREPARE_SEED,
                        NOW.plusSeconds(1),
                        NOW.plusSeconds(120),
                        false),
                trusted(
                        PREPARE_KEY_ID,
                        Purpose.PREPARE,
                        PREPARE_SEED,
                        NOW.minusSeconds(120),
                        NOW,
                        false))) {
            Ed25519TagMigrationEvidenceVerifier verifier = verifier(List.of(key));
            assertRejected(() -> verifier.verifyPrepare(
                    MIGRATION_ID, RUN_UUID, evidence));
        }
    }

    @Test
    void trustSnapshotRejectsDuplicateIdsKeyReuseAndInvalidPublicPoints()
            throws Exception {
        TrustedKey prepare = trusted(
                PREPARE_KEY_ID,
                Purpose.PREPARE,
                PREPARE_SEED,
                NOW.minusSeconds(60),
                NOW.plusSeconds(600),
                false);
        TrustedKey duplicateId = trusted(
                PREPARE_KEY_ID,
                Purpose.FREEZE,
                FREEZE_SEED,
                NOW.minusSeconds(60),
                NOW.plusSeconds(600),
                false);
        TrustedKey reusedRawKey = new TrustedKey(
                "different-key-v1",
                ISSUER,
                Purpose.FREEZE,
                prepare.rawPublicKey(),
                NOW.minusSeconds(60),
                NOW.plusSeconds(600),
                false);

        assertThatThrownBy(() -> verifier(List.of(prepare, duplicateId)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> verifier(List.of(prepare, reusedRawKey)))
                .isInstanceOf(IllegalArgumentException.class);

        byte[] identityPoint = new byte[32];
        identityPoint[0] = 1;
        TrustedKey invalidPoint = new TrustedKey(
                "invalid-key-v1",
                ISSUER,
                Purpose.PREPARE,
                identityPoint,
                NOW.minusSeconds(60),
                NOW.plusSeconds(600),
                false);
        assertThatThrownBy(() -> verifier(List.of(invalidPoint)))
                .isInstanceOf(IllegalArgumentException.class);

        assertThatThrownBy(() -> new TrustedKey(
                "spki-key-v1",
                ISSUER,
                Purpose.PREPARE,
                jdkEd25519KeyPair().getPublic().getEncoded(),
                NOW.minusSeconds(60),
                NOW.plusSeconds(600),
                false))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("32 bytes");
    }

    @Test
    void jdkEdEcPublicKeyOverloadProducesStrictRawKeyAndDefensiveCopies()
            throws Exception {
        KeyPair pair = jdkEd25519KeyPair();
        TrustedKey key = new TrustedKey(
                "jdk-key-v1",
                ISSUER,
                Purpose.PREPARE,
                (EdECPublicKey) pair.getPublic(),
                NOW.minusSeconds(60),
                NOW.plusSeconds(600),
                false);
        byte[] first = key.rawPublicKey();
        byte[] second = key.rawPublicKey();

        assertThat(first).hasSize(32).isNotSameAs(second);
        first[0] ^= 0x7f;
        assertThat(key.rawPublicKey()).containsExactly(second);
        assertThat(new Ed25519TagMigrationEvidenceVerifier(
                List.of(key),
                Clock.fixed(NOW, ZoneOffset.UTC),
                SKEW,
                MAX_LIFETIME)).isNotNull();
    }

    @Test
    void constructionRejectsPoliciesThatCouldDisableTimeValidation() {
        List<TrustedKey> keys = trustedKeys();
        assertThatThrownBy(() -> new Ed25519TagMigrationEvidenceVerifier(
                keys,
                Clock.fixed(NOW, ZoneOffset.UTC),
                Duration.ofSeconds(-1),
                MAX_LIFETIME))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Ed25519TagMigrationEvidenceVerifier(
                keys,
                Clock.fixed(NOW, ZoneOffset.UTC),
                Duration.ofMinutes(5).plusNanos(1),
                MAX_LIFETIME))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Ed25519TagMigrationEvidenceVerifier(
                keys,
                Clock.fixed(NOW, ZoneOffset.UTC),
                SKEW,
                Duration.ZERO))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Ed25519TagMigrationEvidenceVerifier(
                keys,
                Clock.fixed(NOW, ZoneOffset.UTC),
                SKEW,
                Duration.ofHours(1).plusNanos(1)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void claimsRejectNilIdsSubsecondTimesZeroDigestsAndReceiptReuse() {
        assertThatThrownBy(() -> new CommonClaims(
                ISSUER,
                PREPARE_KEY_ID,
                new UUID(0L, 0L),
                RUN_UUID,
                UUID.randomUUID(),
                NOW,
                NOW.plusSeconds(1),
                BINDING)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CommonClaims(
                ISSUER,
                PREPARE_KEY_ID,
                MIGRATION_ID,
                RUN_UUID,
                UUID.randomUUID(),
                NOW.plusNanos(1),
                NOW.plusSeconds(1),
                BINDING)).isInstanceOf(IllegalArgumentException.class);

        RunBinding zeroBinding = new RunBinding(
                "00".repeat(32),
                "02".repeat(32),
                "03".repeat(32),
                "04".repeat(32),
                "05".repeat(32),
                "06".repeat(32),
                "07".repeat(32),
                "08".repeat(32),
                "09".repeat(32));
        assertThatThrownBy(() -> new CommonClaims(
                ISSUER,
                PREPARE_KEY_ID,
                MIGRATION_ID,
                RUN_UUID,
                UUID.randomUUID(),
                NOW,
                NOW.plusSeconds(1),
                zeroBinding)).isInstanceOf(IllegalArgumentException.class);

        assertThatThrownBy(() -> new ApplyClaims(
                common(
                        APPLY_KEY_ID,
                        UUID.randomUUID(),
                        NOW,
                        NOW.plusSeconds(1)),
                FREEZE_RECEIPTS,
                FREEZE_RECEIPTS.connectionDrainReceiptSha256()))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static Ed25519TagMigrationEvidenceVerifier verifier() {
        return verifier(trustedKeys());
    }

    private static Ed25519TagMigrationEvidenceVerifier verifier(
            List<TrustedKey> keys
    ) {
        return new Ed25519TagMigrationEvidenceVerifier(
                keys,
                Clock.fixed(NOW, ZoneOffset.UTC),
                SKEW,
                MAX_LIFETIME);
    }

    private static List<TrustedKey> trustedKeys() {
        Instant validFrom = NOW.minusSeconds(600);
        Instant validUntil = NOW.plusSeconds(600);
        return List.of(
                trusted(
                        PREPARE_KEY_ID,
                        Purpose.PREPARE,
                        PREPARE_SEED,
                        validFrom,
                        validUntil,
                        false),
                trusted(
                        FREEZE_KEY_ID,
                        Purpose.FREEZE,
                        FREEZE_SEED,
                        validFrom,
                        validUntil,
                        false),
                trusted(
                        APPLY_KEY_ID,
                        Purpose.APPLY,
                        APPLY_SEED,
                        validFrom,
                        validUntil,
                        false),
                trusted(
                        RECOVERY_KEY_ID,
                        Purpose.RECOVERY,
                        RECOVERY_SEED,
                        validFrom,
                        validUntil,
                        false));
    }

    private static TrustedKey trusted(
            String keyId,
            Purpose purpose,
            byte[] seed,
            Instant validFrom,
            Instant validUntil,
            boolean revoked
    ) {
        return new TrustedKey(
                keyId,
                ISSUER,
                purpose,
                publicKey(seed),
                validFrom,
                validUntil,
                revoked);
    }

    private static CommonClaims common(
            String keyId,
            UUID evidenceUuid,
            Instant issuedAt,
            Instant expiresAt
    ) {
        return new CommonClaims(
                ISSUER,
                keyId,
                MIGRATION_ID,
                RUN_UUID,
                evidenceUuid,
                issuedAt,
                expiresAt,
                BINDING);
    }

    private static SignedEvidence signed(
            String keyId,
            Purpose purpose,
            byte[] payload,
            byte[] seed
    ) {
        return new SignedEvidence(keyId, payload, sign(purpose, payload, seed));
    }

    private static byte[] sign(
            Purpose purpose,
            byte[] payload,
            byte[] seed
    ) {
        byte[] input = Ed25519TagMigrationEvidenceVerifier.signatureInput(
                purpose, payload);
        byte[] signature = new byte[64];
        Ed25519.sign(seed, 0, input, 0, input.length, signature, 0);
        return signature;
    }

    private static byte[] publicKey(byte[] seed) {
        byte[] publicKey = new byte[32];
        Ed25519.generatePublicKey(seed, 0, publicKey, 0);
        return publicKey;
    }

    private static KeyPair jdkEd25519KeyPair() throws Exception {
        return KeyPairGenerator.getInstance("Ed25519").generateKeyPair();
    }

    private static int commonFirstTagOffset() {
        return 8 + ISSUER.length() + PREPARE_KEY_ID.length();
    }

    private static int candidateDigestValueOffset() {
        return commonFirstTagOffset()
                + 3 * (1 + 16)
                + 2 * (1 + Long.BYTES)
                + 1;
    }

    private static BigInteger littleEndianInteger(byte[] bytes, int offset) {
        byte[] bigEndian = Arrays.copyOfRange(bytes, offset, offset + 32);
        reverse(bigEndian);
        return new BigInteger(1, bigEndian);
    }

    private static byte[] littleEndian32(BigInteger value) {
        byte[] bigEndian = value.toByteArray();
        if (bigEndian.length == 33 && bigEndian[0] == 0) {
            bigEndian = Arrays.copyOfRange(bigEndian, 1, bigEndian.length);
        }
        if (bigEndian.length > 32) {
            throw new IllegalArgumentException("value does not fit in 32 bytes");
        }
        byte[] littleEndian = new byte[32];
        for (int index = 0; index < bigEndian.length; index++) {
            littleEndian[index] = bigEndian[bigEndian.length - 1 - index];
        }
        return littleEndian;
    }

    private static void reverse(byte[] value) {
        for (int left = 0, right = value.length - 1;
                left < right;
                left++, right--) {
            byte swap = value[left];
            value[left] = value[right];
            value[right] = swap;
        }
    }

    private static void assertRejected(ThrowingVerification verification) {
        assertThatThrownBy(verification::verify)
                .isExactlyInstanceOf(EvidenceRejectedException.class)
                .hasMessage("tag migration evidence was rejected")
                .hasNoCause();
    }

    @FunctionalInterface
    private interface ThrowingVerification {
        void verify() throws Exception;
    }
}
