package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceRejectedException;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceVerifier;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedApplyEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedFreezeEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedPrepareEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedRecoveryEvidence;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.SignedEvidence;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.FailureCode;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.State;
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.Proxy;
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;

class LegacyPersonalBankTagMigrationExecutionProtocolStaticTest {

    private static final Set<String> PHASE_METHODS = Set.of(
            "prepare", "freeze", "apply", "recover");

    @Test
    void publicApiRequiresConcreteVerifierAndEveryPhaseRequiresCandidate() {
        List<Constructor<?>> publicConstructors = Arrays.stream(
                        LegacyPersonalBankTagMigrationExecutionProtocol.class
                                .getDeclaredConstructors())
                .filter(constructor -> Modifier.isPublic(
                        constructor.getModifiers()))
                .toList();
        assertThat(publicConstructors).singleElement().satisfies(constructor ->
                assertThat(constructor.getParameterTypes()).containsExactly(
                        DataSource.class,
                        PersonalBankQuestionFactsApi.class,
                        Ed25519TagMigrationEvidenceVerifier.class));

        List<Method> phases = Arrays.stream(
                        LegacyPersonalBankTagMigrationExecutionProtocol.class
                                .getDeclaredMethods())
                .filter(method -> PHASE_METHODS.contains(method.getName()))
                .toList();
        assertThat(phases).hasSize(4).allSatisfy(method -> {
            assertThat(Modifier.isPublic(method.getModifiers())).isTrue();
            assertThat(method.getParameterTypes()).containsExactly(
                    TagMigrationPlanCandidate.class,
                    SignedEvidence.class);
            assertThat(method.getReturnType()).isEqualTo(TagMigrationResult.class);
        });
        assertThat(Arrays.stream(
                        LegacyPersonalBankTagMigrationExecutionProtocol.class
                                .getDeclaredMethods())
                .map(Method::getName))
                .doesNotContain("main", "executeAll", "run", "start");
    }

    @Test
    void arbitraryVerifierSeamIsNotPublic() {
        assertThat(Arrays.stream(
                        LegacyPersonalBankTagMigrationExecutionProtocol.class
                                .getDeclaredConstructors())
                .filter(constructor -> Arrays.asList(
                                constructor.getParameterTypes())
                        .contains(EvidenceVerifier.class)))
                .allMatch(constructor -> !Modifier.isPublic(
                        constructor.getModifiers()));
    }

    @Test
    void mismatchedBindingIsRejectedBeforeAnyCoreDatabaseAccess() {
        TagMigrationPlanCandidate candidate =
                TagMigrationPlanCandidateTestFixture.candidate();
        EvidenceVerifier verifier = new FixedVerifier(wrongBinding(candidate));
        LegacyPersonalBankTagMigrationExecutionProtocol protocol =
                new LegacyPersonalBankTagMigrationExecutionProtocol(
                        noConnectionDataSource(),
                        noMembershipAccess(),
                        verifier);
        SignedEvidence evidence = new SignedEvidence(
                "test-key:v1", new byte[] {1}, new byte[64]);

        assertEvidenceRejected(protocol.prepare(candidate, evidence), candidate);
        assertEvidenceRejected(protocol.freeze(candidate, evidence), candidate);
        assertEvidenceRejected(protocol.apply(candidate, evidence), candidate);
        assertEvidenceRejected(protocol.recover(candidate, evidence), candidate);
    }

    @Test
    void candidateFactoryAndProtocolHaveNoAutomaticOrExternalSurface() {
        List<Class<?>> types = List.of(
                TagMigrationPlanCandidate.class,
                TagMigrationPlanCandidateFactory.class,
                LegacyPersonalBankTagMigrationExecutionProtocol.class);
        assertThat(types).allSatisfy(type -> {
            assertThat(Arrays.stream(type.getDeclaredMethods())
                    .map(Method::getName))
                    .doesNotContain("main", "run", "start", "executeAll");
            assertThat(Arrays.stream(type.getAnnotations())
                    .map(annotation -> annotation.annotationType().getName()))
                    .noneMatch(name -> name.startsWith("org.springframework."));
        });
    }

    private static RunBinding wrongBinding(
            TagMigrationPlanCandidate candidate
    ) {
        RunBinding binding = candidate.binding();
        return new RunBinding(
                "f".repeat(64),
                binding.clusterDatabaseIdentitySha256(),
                binding.runIdentitySha256(),
                binding.preflightDigestSha256(),
                binding.sourceSetDigestSha256(),
                binding.planSetDigestSha256(),
                binding.preapplyTargetSetDigestSha256(),
                binding.finalTargetSetDigestSha256(),
                binding.membershipSetDigestSha256());
    }

    private static void assertEvidenceRejected(
            TagMigrationResult result,
            TagMigrationPlanCandidate candidate
    ) {
        assertThat(result.state()).isEqualTo(State.UNAVAILABLE);
        assertThat(result.failureCode()).contains(FailureCode.EVIDENCE_REJECTED);
        assertThat(result.migrationId()).isEqualTo(candidate.migrationId());
        assertThat(result.migrationRunUuid())
                .isEqualTo(candidate.migrationRunUuid());
        assertThat(result.transactionAttempts()).isZero();
    }

    private static DataSource noConnectionDataSource() {
        return (DataSource) Proxy.newProxyInstance(
                DataSource.class.getClassLoader(),
                new Class<?>[] {DataSource.class},
                (proxy, method, arguments) -> {
                    if (method.getName().equals("getConnection")) {
                        throw new AssertionError(
                                "binding mismatch reached the operator store");
                    }
                    if (method.getName().equals("isWrapperFor")) {
                        return false;
                    }
                    if (method.getName().equals("unwrap")) {
                        throw new UnsupportedOperationException();
                    }
                    return defaultValue(method.getReturnType());
                });
    }

    private static Object defaultValue(Class<?> type) {
        if (!type.isPrimitive()) {
            return null;
        }
        if (type == boolean.class) {
            return false;
        }
        if (type == int.class) {
            return 0;
        }
        if (type == long.class) {
            return 0L;
        }
        return null;
    }

    private static PersonalBankQuestionFactsApi noMembershipAccess() {
        return new PersonalBankQuestionFactsApi() {
            @Override
            public PersonalBankQuestionMembershipView inspectQuestionMembership(
                    int bankId,
                    List<Integer> questionIds
            ) {
                throw new AssertionError(
                        "binding mismatch reached membership facts");
            }

            @Override
            public PersonalBankQuestionAccessResult checkQuestionAccess(
                    AuthenticatedPersonalBankViewer viewer,
                    int bankId
            ) {
                throw new UnsupportedOperationException();
            }

            @Override
            public PersonalBankQuestionFactsResult summarizeQuestions(
                    AuthenticatedPersonalBankViewer viewer,
                    PersonalBankQuestionSelection selection
            ) {
                throw new UnsupportedOperationException();
            }
        };
    }

    private static final class FixedVerifier implements EvidenceVerifier {
        private final RunBinding binding;

        private FixedVerifier(RunBinding binding) {
            this.binding = binding;
        }

        @Override
        public VerifiedPrepareEvidence verifyPrepare(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            return new VerifiedPrepareEvidence(binding, hash(0));
        }

        @Override
        public VerifiedFreezeEvidence verifyFreeze(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            return new VerifiedFreezeEvidence(
                    binding,
                    hash(1), hash(2), hash(3), hash(4), hash(5), hash(6));
        }

        @Override
        public VerifiedApplyEvidence verifyApply(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            return new VerifiedApplyEvidence(
                    binding,
                    hash(1), hash(2), hash(3), hash(4),
                    hash(5), hash(6), hash(7), hash(8));
        }

        @Override
        public VerifiedRecoveryEvidence verifyRecovery(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            return new VerifiedRecoveryEvidence(
                    binding,
                    hash(1), hash(2), hash(3), hash(4),
                    hash(5), hash(6), hash(7), hash(8));
        }

        private static String hash(int value) {
            return Integer.toHexString(value).repeat(64).substring(0, 64);
        }
    }
}
