package io.saksk.ti.learning.infrastructure.migration;

import java.util.Objects;
import java.util.UUID;
import java.util.regex.Pattern;

/** Opaque, explicit commands for the disabled-by-default legacy-tag operator. */
public sealed interface TagMigrationCommand permits
        TagMigrationCommand.PrepareCommand,
        TagMigrationCommand.FreezeCommand,
        TagMigrationCommand.ApplyCommand,
        TagMigrationCommand.RecoveryCommand {

    UUID migrationId();

    UUID migrationRunUuid();

    SignedEvidence signedEvidence();

    record PrepareCommand(
            UUID migrationId,
            UUID migrationRunUuid,
            LegacyPersonalBankTagPreflightReport freshPreflight,
            SignedEvidence signedEvidence
    ) implements TagMigrationCommand {
        public PrepareCommand {
            migrationId = requireUuid(migrationId, "migrationId");
            migrationRunUuid = requireUuid(migrationRunUuid, "migrationRunUuid");
            freshPreflight = Objects.requireNonNull(
                    freshPreflight, "freshPreflight");
            signedEvidence = Objects.requireNonNull(
                    signedEvidence, "signedEvidence");
            if (!freshPreflight.fullSweepComplete()
                    || !freshPreflight.isDataEligible()
                    || freshPreflight.reservedRowCount() == 0
                    || freshPreflight.blockingRowCount() != 0) {
                throw new IllegalArgumentException(
                        "prepare requires a complete non-empty data-eligible preflight");
            }
        }
    }

    record FreezeCommand(
            UUID migrationId,
            UUID migrationRunUuid,
            SignedEvidence signedEvidence
    ) implements TagMigrationCommand {
        public FreezeCommand {
            migrationId = requireUuid(migrationId, "migrationId");
            migrationRunUuid = requireUuid(migrationRunUuid, "migrationRunUuid");
            signedEvidence = Objects.requireNonNull(
                    signedEvidence, "signedEvidence");
        }
    }

    record ApplyCommand(
            UUID migrationId,
            UUID migrationRunUuid,
            SignedEvidence signedEvidence
    ) implements TagMigrationCommand {
        public ApplyCommand {
            migrationId = requireUuid(migrationId, "migrationId");
            migrationRunUuid = requireUuid(migrationRunUuid, "migrationRunUuid");
            signedEvidence = Objects.requireNonNull(
                    signedEvidence, "signedEvidence");
        }
    }

    record RecoveryCommand(
            UUID migrationId,
            UUID migrationRunUuid,
            SignedEvidence signedEvidence
    ) implements TagMigrationCommand {
        public RecoveryCommand {
            migrationId = requireUuid(migrationId, "migrationId");
            migrationRunUuid = requireUuid(migrationRunUuid, "migrationRunUuid");
            signedEvidence = Objects.requireNonNull(
                    signedEvidence, "signedEvidence");
        }
    }

    /**
     * Opaque signed bytes. The core never parses claims or trusts caller-provided
     * digests; its injected verifier must authenticate and bind every claim.
     */
    record SignedEvidence(
            String keyId,
            byte[] payload,
            byte[] signature
    ) {
        private static final Pattern KEY_ID =
                Pattern.compile("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}");
        private static final int MAX_PAYLOAD_BYTES = 65_536;
        private static final int MAX_SIGNATURE_BYTES = 8_192;

        public SignedEvidence {
            keyId = Objects.requireNonNull(keyId, "keyId");
            payload = Objects.requireNonNull(payload, "payload").clone();
            signature = Objects.requireNonNull(signature, "signature").clone();
            if (!KEY_ID.matcher(keyId).matches()) {
                throw new IllegalArgumentException("invalid evidence key id");
            }
            if (payload.length == 0 || payload.length > MAX_PAYLOAD_BYTES) {
                throw new IllegalArgumentException("invalid evidence payload size");
            }
            if (signature.length < 32 || signature.length > MAX_SIGNATURE_BYTES) {
                throw new IllegalArgumentException("invalid evidence signature size");
            }
        }

        @Override
        public byte[] payload() {
            return payload.clone();
        }

        @Override
        public byte[] signature() {
            return signature.clone();
        }
    }

    private static UUID requireUuid(UUID value, String name) {
        UUID required = Objects.requireNonNull(value, name);
        if (required.equals(new UUID(0L, 0L))) {
            throw new IllegalArgumentException(name + " must not be the nil UUID");
        }
        return required;
    }
}
