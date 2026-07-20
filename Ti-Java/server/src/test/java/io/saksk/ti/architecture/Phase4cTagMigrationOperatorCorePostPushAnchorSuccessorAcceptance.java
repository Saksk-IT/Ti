package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermission;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeMap;

/** Gitless Java acceptance for the Phase 4C operator-core C0+C1 anchor. */
final class Phase4cTagMigrationOperatorCorePostPushAnchorSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/personal-bank-tag-migration-operator-core-"
                    + "post-push-anchor-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-tag-migration-operator-core-"
                    + "post-push-anchor-contract";
    private static final String CONTRACT_CAPTURED_AT =
            "2026-07-20T18:26:27+08:00";
    private static final String CONTRACT_STATUS =
            "operator_core_and_independent_acceptance_checkpoints_externally_"
                    + "anchored_production_schema_freeze_backup_apply_and_"
                    + "cutover_unauthorized";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-tag-migration-operator-core-post-push-"
                    + "external-anchor";
    private static final String CONTRACT_SHA256 =
            "0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64";
    private static final long CONTRACT_BYTE_COUNT = 84_461L;

    private static final String OPERATOR_CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-operator-core-contract.json";
    private static final String OPERATOR_CONTRACT_ID =
            "ti.phase4c.personal-bank-tag-migration-operator-core-contract";
    private static final String OPERATOR_CONTRACT_SHA256 =
            "2124d1b042f2df201ad3d8ca87fd19fa121b8d47cbaf51a60eb5271fe55b7fe8";
    private static final String OPERATOR_CONTRACT_PAYLOAD_SHA256 =
            "28f0fa1a5ec1c2e795c60d472b47d0ccb16d1b838a30dd0e7ac69fe738f53778";
    private static final long OPERATOR_CONTRACT_BYTE_COUNT = 50_467L;

    private static final String EVIDENCE_RELATIVE =
            "docs/refactor/phase4c/personal-bank-tag-migration-operator-core-"
                    + "independent-acceptance-evidence.json";
    private static final String EVIDENCE_ID =
            "ti.phase4c.personal-bank-tag-migration-operator-core-"
                    + "independent-acceptance-evidence";
    private static final String EVIDENCE_SHA256 =
            "4262361fbcf55452bae3d8a50340c4fc2f103ee07b562fce8879500e38691003";
    private static final long EVIDENCE_BYTE_COUNT = 8_894L;
    private static final String RUNNER_RELATIVE =
            "tools/run_phase4c_tag_migration_operator_core_"
                    + "independent_acceptance.sh";
    private static final String RUNNER_SHA256 =
            "bcfa8b8a386579e7fddd212712fa045bf1d30a0bf7d6c7f8df5860b933de2774";
    private static final long RUNNER_BYTE_COUNT = 65_880L;
    private static final Set<PosixFilePermission> RUNNER_PERMISSIONS = Set.of(
            PosixFilePermission.OWNER_READ,
            PosixFilePermission.OWNER_WRITE,
            PosixFilePermission.OWNER_EXECUTE,
            PosixFilePermission.GROUP_READ,
            PosixFilePermission.GROUP_EXECUTE,
            PosixFilePermission.OTHERS_READ,
            PosixFilePermission.OTHERS_EXECUTE);

    private static final String C0_COMMIT =
            "a70c365959e123950d30bff05adb4fabbb72d640";
    private static final String C0_PARENT =
            "bbeb08efcccb0b9974dfefa2044aab43e0675f6f";
    private static final String C1_COMMIT =
            "4ec9966f836378a33058b574fd1812d4d19cac10";

    private static final List<String> C0_CONTROL_SOURCES = List.of(
            OPERATOR_CONTRACT_RELATIVE,
            "docs/refactor/phase4c/"
                    + "personal-bank-tag-migration-operator-core.md",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCoreContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java",
            "tools/build_phase4c_tag_migration_operator_core_contract.py",
            "tools/phase4c_tag_migration_operator_core_successor_acceptance.py",
            "tools/test_phase4c_tag_migration_operator_core_contract.py");

    private static final List<String> C1_CONTROL_SOURCES = List.of(
            EVIDENCE_RELATIVE, RUNNER_RELATIVE);

    private static final List<String> CURRENT_CONTROL_SOURCES = List.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCorePostPushAnchor"
                    + "ContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationOperatorCorePostPushAnchor"
                    + "SuccessorAcceptance.java",
            "tools/build_phase4c_tag_migration_operator_core_"
                    + "post_push_anchor_contract.py",
            "tools/phase4c_tag_migration_operator_core_"
                    + "post_push_anchor_successor_acceptance.py",
            "tools/test_phase4c_tag_migration_operator_core_"
                    + "post_push_anchor_contract.py");

    private static final List<String> AUTHORIZATION_TRUE_FIELDS = List.of(
            "migration_global_preflight_evidence_closed",
            "migration_durable_ledger_freeze_design_evidence_closed",
            "operator_core_evidence_closed",
            "bounded_40001_40P01_retry_implemented",
            "operator_migration_implementation",
            "operator_core_control_sources_external_git_anchor_complete",
            "independent_acceptance_control_sources_external_git_anchor_complete",
            "source_successor_external_git_anchor_complete",
            "semantic_successor_external_git_anchor_complete",
            "bootstrap_control_sources_external_git_anchor_complete");

    private static final List<String> AUTHORIZATION_FALSE_FIELDS = List.of(
            "current_node_control_sources_external_git_anchor_complete",
            "migration_design_closed",
            "production_durable_ledger_or_tombstone",
            "production_source_write_freeze_evidence_closed",
            "production_target_write_freeze_evidence_closed",
            "production_membership_write_freeze_or_digest_recheck_evidence_closed",
            "production_connection_drain_evidence_closed",
            "production_schema_or_index",
            "flyway_baseline_or_migration",
            "backup_and_rollback_evidence_closed",
            "real_data_migration_execution",
            "legacy_runtime_permanently_disabled",
            "route_or_openapi_delta",
            "client_gateway_or_proxy_change",
            "production_cutover");

    private Phase4cTagMigrationOperatorCorePostPushAnchorSuccessorAcceptance() {
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static String physicalSha256() {
        return CONTRACT_SHA256;
    }

    static String payloadSha256() {
        return CONTRACT_PAYLOAD_SHA256;
    }

    static long byteCount() {
        return CONTRACT_BYTE_COUNT;
    }

    static List<String> currentControlSources() {
        return CURRENT_CONTROL_SOURCES;
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = readFixedJson(
                root, CONTRACT_RELATIVE, CONTRACT_SHA256, CONTRACT_BYTE_COUNT);
        require(CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(contract)),
                "operator-core anchor contract payload drifted");
        JsonNode operator = readFixedJson(
                root, OPERATOR_CONTRACT_RELATIVE,
                OPERATOR_CONTRACT_SHA256, OPERATOR_CONTRACT_BYTE_COUNT);
        require(OPERATOR_CONTRACT_PAYLOAD_SHA256.equals(
                        operator.path("document_payload_sha256").asString())
                        && OPERATOR_CONTRACT_PAYLOAD_SHA256.equals(
                        documentPayloadSha256(operator)),
                "operator-core anchor C0 payload drifted");
        JsonNode evidence = readFixedJson(
                root, EVIDENCE_RELATIVE, EVIDENCE_SHA256, EVIDENCE_BYTE_COUNT);
        Path runnerPath = fixedRegularFile(root, RUNNER_RELATIVE);
        byte[] runner = Files.readAllBytes(runnerPath);
        require(runner.length == RUNNER_BYTE_COUNT
                        && RUNNER_SHA256.equals(sha256(runner)),
                "operator-core anchor runner fixed bytes drifted");
        validateRunnerMode(runnerPath);
        validate(contract, operator, evidence);
        return contract;
    }

    static String acceptedSha256(Path tiJavaRoot, String relative)
            throws IOException {
        try {
            JsonNode contract = load(tiJavaRoot);
            JsonNode artifact = contract.path("implementation_checkpoint")
                    .path("artifacts").path(relative);
            if (artifact.isMissingNode()) {
                artifact = contract.path("independent_acceptance_checkpoint")
                        .path("artifacts").path(relative);
            }
            if (artifact.isMissingNode()
                    || CURRENT_CONTROL_SOURCES.contains(relative)) {
                return null;
            }
            byte[] payload = Files.readAllBytes(
                    anchoredRegularFile(tiJavaRoot, relative));
            String expected = artifact.path("sha256").asString();
            return payload.length == artifact.path("byte_count").asLong()
                    && expected.equals(sha256(payload))
                    ? expected : null;
        } catch (AssertionError | IOException error) {
            return null;
        }
    }

    private static void validate(
            JsonNode contract,
            JsonNode operator,
            JsonNode evidence
    ) {
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at",
                        "status", "scope", "operator_core_contract",
                        "independent_acceptance_evidence",
                        "implementation_checkpoint",
                        "independent_acceptance_checkpoint",
                        "operator_core_authority_anchor",
                        "transitive_node_b_anchor",
                        "independent_copy_verification",
                        "production_and_worm_boundary", "authorization",
                        "route_state", "current_node_trust_boundary",
                        "acceptance", "document_payload_sha256"))
                        && CONTRACT_ID.equals(
                        contract.path("contract_id").asString())
                        && contract.path("schema_version").asInt() == 1
                        && CONTRACT_CAPTURED_AT.equals(
                        contract.path("captured_at").asString())
                        && CONTRACT_STATUS.equals(
                        contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(
                        contract.path("scope").asString()),
                "operator-core anchor identity/shape drifted");
        validateOperatorDescriptor(contract, operator);
        validateImplementationCheckpoint(contract, operator);
        validateIndependentCheckpoint(contract, evidence);
        validateTransitiveAnchor(contract, operator);
        validateIndependentEvidence(contract, evidence);
        validateProductionAndWorm(contract, operator);
        validateBoundaries(contract);
    }

    private static void validateOperatorDescriptor(
            JsonNode contract,
            JsonNode operator
    ) {
        JsonNode descriptor = contract.path("operator_core_contract");
        require(OPERATOR_CONTRACT_ID.equals(
                        operator.path("contract_id").asString())
                        && "2026-07-19T15:30:00+08:00".equals(
                        operator.path("captured_at").asString())
                        && OPERATOR_CONTRACT_RELATIVE.equals(
                        descriptor.path("source").asString())
                        && OPERATOR_CONTRACT_ID.equals(
                        descriptor.path("contract_id").asString())
                        && OPERATOR_CONTRACT_SHA256.equals(
                        descriptor.path("sha256").asString())
                        && descriptor.path("byte_count").asLong()
                        == OPERATOR_CONTRACT_BYTE_COUNT
                        && OPERATOR_CONTRACT_PAYLOAD_SHA256.equals(descriptor
                        .path("document_payload_sha256").asString())
                        && descriptor.path("immutable").asBoolean(),
                "operator-core anchor C0 descriptor drifted");
    }

    private static void validateImplementationCheckpoint(
            JsonNode contract,
            JsonNode operator
    ) {
        JsonNode checkpoint = contract.path("implementation_checkpoint");
        JsonNode artifacts = checkpoint.path("artifacts");
        require(C0_COMMIT.equals(checkpoint.path("commit_oid").asString())
                        && C0_PARENT.equals(
                        checkpoint.path("parent_oid").asString())
                        && "e23d0e8551dc8fd3338ba0682154eebe4a9e9f2f"
                        .equals(checkpoint.path("root_tree_oid").asString())
                        && "38f6aafbeb7888a5539d6ab3b4b6b8d9ae522194"
                        .equals(checkpoint.path("ti_java_tree_oid").asString())
                        && "c4243039f367f7f917a3f9c85c190ebc5233a0fb"
                        .equals(checkpoint.path("server_tree_oid").asString())
                        && "bdd88effe149c61fada2300a4ec85bb2a3fdaf1c"
                        .equals(checkpoint.path(
                                "server_src_main_tree_oid").asString())
                        && checkpoint.path("web_tree_oid").asString().equals(
                        checkpoint.path("parent_web_tree_oid").asString())
                        && checkpoint.path("miniprogram_tree_oid").asString()
                        .equals(checkpoint.path(
                                "parent_miniprogram_tree_oid").asString())
                        && checkpoint.path("changed_path_count").asInt() == 56
                        && checkpoint.path("added_count").asInt() == 22
                        && checkpoint.path("modified_count").asInt() == 34
                        && checkpoint.path("deleted_count").asInt() == 0
                        && checkpoint.path("non_ti_java_count").asInt() == 0
                        && checkpoint.path("exact_fifty_six_path_delta")
                        .asBoolean()
                        && artifacts.isObject() && artifacts.size() == 56,
                "operator-core anchor C0 checkpoint drifted");
        JsonNode diff = checkpoint.path("diff");
        require("6892e663c1d1b5572c28c8aa489fc5721af4b4dbe7771edbbef12cf870bd5371"
                        .equals(diff.path("standard_raw_sha256").asString())
                        && "a42f9a7d5da81d41b08204bd26ffdbfc4da728f2541d417967c107d2f14dd87c"
                        .equals(diff.path(
                                "standard_numstat_sha256").asString())
                        && "2de8de0fd74bc734fe8cd4acb93dd50471b8179eb87e148c7f66e57188565d1d"
                        .equals(diff.path(
                                "standard_name_status_sha256").asString())
                        && "ed145d808516678306ea1610fac1428244df90162371727ba9c1e4936381a196"
                        .equals(diff.path("nul_raw_sha256").asString())
                        && "f7b183cb1df7833418c014cd0a2d2a622dd0be43165e1dfa3dc6da5a7891d023"
                        .equals(diff.path("nul_numstat_sha256").asString())
                        && "22eb3e088ab24c2fcdb8defad142a01f6ba5a36bb81d9f0b5aec380a178c8725"
                        .equals(diff.path(
                                "nul_name_status_sha256").asString()),
                "operator-core anchor C0 diff identity drifted");
        validateC0Partition(
                contract.path("operator_core_authority_anchor"),
                operator, artifacts);
    }

    private static void validateC0Partition(
            JsonNode anchor,
            JsonNode operator,
            JsonNode artifacts
    ) {
        JsonNode sourceAuthority = operator.path("source_authority");
        JsonNode fixed = sourceAuthority.path("fixed_non_control_sources");
        JsonNode overrides = operator.path("historical_source_successors")
                .path("overrides");
        Set<String> controls = new LinkedHashSet<>(
                strings(sourceAuthority.path("control_sources")));
        Set<String> fixedPaths = propertyNames(fixed);
        Set<String> transitions = propertyNames(overrides);
        Set<String> artifactPaths = propertyNames(artifacts);
        Set<String> partition = new LinkedHashSet<>(controls);
        partition.addAll(fixedPaths);
        require(controls.equals(new LinkedHashSet<>(C0_CONTROL_SOURCES))
                        && sourceAuthority.path("control_source_count").asInt()
                        == 7
                        && sourceAuthority.path(
                                "fixed_non_control_source_count").asInt() == 49
                        && operator.path("historical_source_successors")
                        .path("override_count").asInt() == 34
                        && fixedPaths.size() == 49
                        && transitions.size() == 34
                        && fixedPaths.containsAll(transitions)
                        && disjoint(controls, fixedPaths)
                        && partition.equals(artifactPaths),
                "operator-core anchor C0 7+49 partition drifted");
        for (String relative : artifactPaths) {
            validateArtifact(relative, artifacts.path(relative));
        }
        for (String relative : controls) {
            require("A".equals(artifacts.path(relative)
                            .path("change_type").asString()),
                    "operator-core anchor C0 control is not added: "
                            + relative);
        }
        for (String relative : fixedPaths) {
            JsonNode source = fixed.path(relative);
            JsonNode artifact = artifacts.path(relative);
            require(relative.equals(source.path("source").asString())
                            && source.path("sha256").asString().equals(
                            artifact.path("sha256").asString())
                            && source.path("byte_count").asLong()
                            == artifact.path("byte_count").asLong(),
                    "operator-core anchor fixed C0 source drifted: "
                            + relative);
            if (!transitions.contains(relative)) {
                require("A".equals(
                                artifact.path("change_type").asString()),
                        "operator-core anchor non-transition was not added: "
                                + relative);
            }
        }
        for (String relative : transitions) {
            JsonNode transition = overrides.path(relative);
            JsonNode artifact = artifacts.path(relative);
            require("M".equals(artifact.path("change_type").asString())
                            && transition.path("successor_sha256").asString()
                            .equals(artifact.path("sha256").asString())
                            && transition.path("successor_byte_count").asLong()
                            == artifact.path("byte_count").asLong()
                            && transition.path("accepted_sha256").asString()
                            .equals(artifact.path(
                                    "previous_sha256").asString())
                            && transition.path("accepted_byte_count").asLong()
                            == artifact.path(
                                    "previous_byte_count").asLong(),
                    "operator-core anchor C0 transition drifted: "
                            + relative);
        }
        require(strings(anchor.path("implementation_control_sources"))
                        .equals(C0_CONTROL_SOURCES)
                        && new LinkedHashSet<>(strings(anchor.path(
                        "implementation_fixed_non_control_sources")))
                        .equals(fixedPaths)
                        && new LinkedHashSet<>(strings(anchor.path(
                        "implementation_transition_sources")))
                        .equals(transitions)
                        && anchor.path("implementation_control_source_count")
                        .asInt() == 7
                        && anchor.path(
                                "implementation_fixed_non_control_source_count")
                        .asInt() == 49
                        && anchor.path(
                                "implementation_transition_source_count")
                        .asInt() == 34
                        && "f9098c90c9ea2d75f3b5f2d08bb84ac075015c8f1b30160dd475d0d6d6e96f22"
                        .equals(anchor.path(
                                "implementation_control_path_manifest_sha256")
                                .asString())
                        && canonicalSha256(fixed).equals(anchor.path(
                                "implementation_fixed_manifest_sha256")
                                .asString())
                        && canonicalSha256(overrides).equals(anchor.path(
                                "implementation_transition_manifest_sha256")
                                .asString())
                        && canonicalSha256(artifacts).equals(anchor.path(
                                "implementation_artifact_manifest_sha256")
                                .asString())
                        && anchor.path(
                                "exact_disjoint_c0_7_plus_49_partition")
                        .asBoolean()
                        && anchor.path(
                                "all_34_transitions_are_exact_modified_commit_blobs")
                        .asBoolean(),
                "operator-core anchor C0 authority manifest drifted");
    }

    private static void validateIndependentCheckpoint(
            JsonNode contract,
            JsonNode evidence
    ) {
        JsonNode checkpoint = contract.path(
                "independent_acceptance_checkpoint");
        JsonNode artifacts = checkpoint.path("artifacts");
        require(C1_COMMIT.equals(checkpoint.path("commit_oid").asString())
                        && C0_COMMIT.equals(
                        checkpoint.path("parent_oid").asString())
                        && checkpoint.path("parent_is_implementation_checkpoint")
                        .asBoolean()
                        && "2cedbb629b02505ac378536bb30833cd46c3c0c4"
                        .equals(checkpoint.path("root_tree_oid").asString())
                        && checkpoint.path("parent_root_tree_oid").asString()
                        .equals(contract.path("implementation_checkpoint")
                                .path("root_tree_oid").asString())
                        && "23aa906d57ada83da307050c8104ce0d956d54f9"
                        .equals(checkpoint.path("ti_java_tree_oid").asString())
                        && checkpoint.path("server_tree_oid").asString()
                        .equals(checkpoint.path(
                                "parent_server_tree_oid").asString())
                        && checkpoint.path("server_src_main_tree_oid")
                        .asString().equals(checkpoint.path(
                                "parent_server_src_main_tree_oid").asString())
                        && checkpoint.path("web_tree_oid").asString().equals(
                        checkpoint.path("parent_web_tree_oid").asString())
                        && checkpoint.path("miniprogram_tree_oid").asString()
                        .equals(checkpoint.path(
                                "parent_miniprogram_tree_oid").asString())
                        && checkpoint.path("changed_path_count").asInt() == 2
                        && checkpoint.path("added_count").asInt() == 2
                        && checkpoint.path("modified_count").asInt() == 0
                        && checkpoint.path("deleted_count").asInt() == 0
                        && checkpoint.path("non_ti_java_count").asInt() == 0
                        && checkpoint.path("exact_two_added_path_delta")
                        .asBoolean()
                        && artifacts.size() == 2
                        && propertyNames(artifacts).equals(
                        new LinkedHashSet<>(C1_CONTROL_SOURCES)),
                "operator-core anchor C1 exact 2A checkpoint drifted");
        JsonNode evidenceArtifact = artifacts.path(EVIDENCE_RELATIVE);
        JsonNode runnerArtifact = artifacts.path(RUNNER_RELATIVE);
        validateAddedArtifact(
                EVIDENCE_RELATIVE, evidenceArtifact, "100644",
                EVIDENCE_SHA256, EVIDENCE_BYTE_COUNT);
        validateAddedArtifact(
                RUNNER_RELATIVE, runnerArtifact, "100755",
                RUNNER_SHA256, RUNNER_BYTE_COUNT);
        JsonNode anchor = contract.path("operator_core_authority_anchor");
        require(strings(anchor.path("independent_acceptance_control_sources"))
                        .equals(C1_CONTROL_SOURCES)
                        && anchor.path(
                                "independent_acceptance_control_source_count")
                        .asInt() == 2
                        && canonicalSha256(artifacts).equals(anchor.path(
                                "independent_acceptance_artifact_manifest_sha256")
                                .asString())
                        && anchor.path(
                                "c0_and_c1_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && anchor.path(
                                "ordinary_build_and_load_are_gitless")
                        .asBoolean()
                        && anchor.path(
                                "explicit_fixed_commit_git_replay_available")
                        .asBoolean()
                        && anchor.path("dynamic_source_discovery_forbidden")
                        .asBoolean()
                        && anchor.path("live_head_or_ref_authority_forbidden")
                        .asBoolean(),
                "operator-core anchor C1 authority drifted");
        require(EVIDENCE_ID.equals(evidence.path("contract_id").asString()),
                "operator-core anchor physical evidence identity drifted");
    }

    private static void validateTransitiveAnchor(
            JsonNode contract,
            JsonNode operator
    ) {
        JsonNode transitive = contract.path("transitive_node_b_anchor");
        JsonNode authority = transitive.path("git_authority");
        require(transitive.path("predecessor").equals(
                        operator.path("predecessor"))
                        && authority.equals(
                        operator.path("node_b_git_authority"))
                        && transitive.path("immutable").asBoolean()
                        && C0_PARENT.equals(authority
                        .path("external_anchor_checkpoint")
                        .path("commit_oid").asString())
                        && authority.path("external_anchor_artifact_count")
                        .asInt() == 6
                        && authority.path("external_anchor_artifacts")
                        .size() == 6
                        && !authority.path(
                                "ordinary_build_and_load_require_git")
                        .asBoolean()
                        && !authority.path(
                                "live_head_main_or_origin_authority")
                        .asBoolean(),
                "operator-core anchor transitive Node B drifted");
    }

    private static void validateIndependentEvidence(
            JsonNode contract,
            JsonNode evidence
    ) {
        JsonNode descriptor = contract.path(
                "independent_acceptance_evidence");
        JsonNode runner = evidence.path("independent_acceptance_runner");
        require(EVIDENCE_ID.equals(evidence.path("contract_id").asString())
                        && evidence.path("schema_version").asInt() == 1
                        && "passed".equals(
                        evidence.path("status").asString())
                        && EVIDENCE_RELATIVE.equals(
                        descriptor.path("source").asString())
                        && EVIDENCE_ID.equals(
                        descriptor.path("contract_id").asString())
                        && EVIDENCE_SHA256.equals(
                        descriptor.path("sha256").asString())
                        && descriptor.path("byte_count").asLong()
                        == EVIDENCE_BYTE_COUNT
                        && descriptor.path("runner").equals(runner)
                        && !descriptor.path(
                                "raw_report_required_for_gitless_build")
                        .asBoolean()
                        && descriptor.path("immutable").asBoolean(),
                "operator-core anchor independent evidence descriptor drifted");
        JsonNode authority = evidence.path("fixed_c0_authority");
        JsonNode authorityDiff = authority.path("diff");
        require(C0_COMMIT.equals(authority.path("commit_oid").asString())
                        && C0_PARENT.equals(
                        authority.path("parent_oid").asString())
                        && authorityDiff.path("changed_path_count").asInt()
                        == 56
                        && authorityDiff.path("added_path_count").asInt()
                        == 22
                        && authorityDiff.path("modified_path_count").asInt()
                        == 34
                        && authorityDiff.path("deleted_path_count").asInt()
                        == 0
                        && authorityDiff.path("control_source_count").asInt()
                        == 7
                        && authorityDiff.path("fixed_non_control_source_count")
                        .asInt() == 49,
                "operator-core anchor evidence C0 authority drifted");
        JsonNode c0Artifact = evidence.path("fixed_c0_artifacts")
                .path("operator_core_contract");
        require(OPERATOR_CONTRACT_RELATIVE.equals(
                        c0Artifact.path("path").asString())
                        && OPERATOR_CONTRACT_SHA256.equals(
                        c0Artifact.path("sha256").asString())
                        && c0Artifact.path("byte_count").asLong()
                        == OPERATOR_CONTRACT_BYTE_COUNT
                        && OPERATOR_CONTRACT_PAYLOAD_SHA256.equals(c0Artifact
                        .path("document_payload_sha256").asString()),
                "operator-core anchor evidence C0 contract drifted");
        JsonNode raw = runner.path("raw_report");
        require(RUNNER_RELATIVE.equals(runner.path("path").asString())
                        && RUNNER_SHA256.equals(
                        runner.path("sha256").asString())
                        && runner.path("byte_count").asLong()
                        == RUNNER_BYTE_COUNT
                        && "100755".equals(
                        runner.path("git_mode").asString())
                        && "45e8a3d0eaed833c6730aca1d2b05fccf5f145e51fb9e753aad283c652486d9d"
                        .equals(raw.path("sha256").asString())
                        && raw.path("byte_count").asLong() == 8_762L
                        && !raw.path("tracked").asBoolean()
                        && !raw.path("embedded").asBoolean()
                        && !raw.path(
                                "required_for_gitless_successor_acceptance")
                        .asBoolean(),
                "operator-core anchor runner/raw report drifted");
        JsonNode copy = contract.path("independent_copy_verification");
        require(copy.path("fixed_archive").equals(
                        evidence.path("fixed_archive"))
                        && copy.path("verification").equals(
                        evidence.path("verification"))
                        && copy.path("docker_and_host_trust_boundary").equals(
                        evidence.path("docker_and_host_trust_boundary"))
                        && copy.path("original_closure").equals(
                        evidence.path("closure")),
                "operator-core anchor independent evidence copy drifted");
        validateVerification(copy.path("verification"));
        JsonNode production = evidence.path("production_boundary");
        require(production.isObject() && production.size() == 9
                        && propertyNames(production).stream().allMatch(field ->
                        !production.path(field).asBoolean()),
                "operator-core anchor independent production boundary drifted");
        JsonNode closure = evidence.path("closure");
        require(closure.path("fixed_c0_independent_copy_acceptance_closed")
                        .asBoolean()
                        && C0_COMMIT.equals(
                        closure.path("proves_only_commit").asString())
                        && !closure.path(
                                "proves_c1_evidence_commit").asBoolean()
                        && !closure.path("proves_c2_anchor_commit").asBoolean()
                        && !closure.path(
                                "operator_core_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && !closure.path("self_hash_embedded").asBoolean(),
                "operator-core anchor original closure drifted");
    }

    private static void validateVerification(JsonNode verification) {
        require("UTC".equals(verification.path("timezone").asString())
                        && verification.path("phase1_passed").asBoolean()
                        && verification.path("phase2_static_passed").asBoolean()
                        && verification.path("phase3_static_passed").asBoolean()
                        && verification.path("phase3_topology_static_passed")
                        .asBoolean()
                        && verification.path("topology_data_plane_passed")
                        .asBoolean()
                        && verification.path("maven_cache_empty_at_start")
                        .asBoolean(),
                "operator-core anchor independent static gates drifted");
        validateTestSuite(
                verification.path("maven_full").path("surefire"), 860);
        validateTestSuite(
                verification.path("maven_full").path("failsafe"), 176);
        validateTestSuite(
                verification.path("focused_node_c").path("unit"), 83);
        validateTestSuite(verification.path("focused_node_c")
                .path("operator_integration"), 3);
        validateTestSuite(verification.path("focused_node_c")
                .path("retry_integration"), 2);
        JsonNode miniprogram = verification.path("miniprogram");
        require(miniprogram.path("tests").asInt() == 36
                        && miniprogram.path("passed").asInt() == 36
                        && miniprogram.path("failed").asInt() == 0,
                "operator-core anchor miniprogram evidence drifted");
        JsonNode discovery = verification.path("source_discovery");
        require(!discovery.path("executed_inside_independent_copy")
                        .asBoolean()
                        && discovery.path(
                                "claimed_independent_copy_test_count")
                        .asInt() == 0
                        && discovery.path("reason").asString().contains(
                                "outside the fixed Ti-Java archive"),
                "operator-core anchor source-discovery overclaim drifted");
        JsonNode image = verification.path("image");
        require(image.path("built").asBoolean()
                        && image.path("removed").asBoolean(),
                "operator-core anchor image lifecycle drifted");
        JsonNode compose = verification.path("compose");
        require(compose.path("service_count").asInt() == 3
                        && compose.path("healthy_service_count").asInt() == 3
                        && compose.path("restarted_service_count").asInt() == 3
                        && compose.path("all_services_healthy_after_restart")
                        .asBoolean()
                        && compose.path("api_restart_recovery_passed")
                        .asBoolean()
                        && compose.path("livez_status").asInt() == 200
                        && compose.path("readyz_status").asInt() == 200
                        && compose.path("unknown_status").asInt() == 401
                        && compose.path("external_metrics_status").asInt()
                        == 404
                        && compose.path("internal_metrics_status").asInt()
                        == 200
                        && compose.path("internal_metrics_after_restart_status")
                        .asInt() == 200
                        && compose.path("postgres_ready").asBoolean()
                        && compose.path("postgres_ready_after_restart")
                        .asBoolean()
                        && compose.path("read_only_bind_count").asInt() == 9
                        && compose.path("unique_bind_source_count").asInt()
                        == 7
                        && compose.path("source_worktree_bind_count").asInt()
                        == 0
                        && compose.path("exact_runtime_policy_service_count")
                        .asInt() == 3
                        && compose.path("read_only_rootfs_service_count")
                        .asInt() == 3
                        && compose.path("cap_drop_all_service_count").asInt()
                        == 3
                        && compose.path("no_new_privileges_service_count")
                        .asInt() == 3
                        && compose.path("init_service_count").asInt() == 3
                        && compose.path("environment_secret_value_count")
                        .asInt() == 0,
                "operator-core anchor Compose evidence drifted");
        JsonNode cleanup = verification.path("cleanup");
        require(cleanup.path("baseline_container_set_preserved").asBoolean()
                        && cleanup.path("baseline_network_set_preserved")
                        .asBoolean()
                        && cleanup.path("baseline_volume_set_preserved")
                        .asBoolean()
                        && List.of(
                                "container_residue", "network_residue",
                                "volume_residue", "image_residue",
                                "cache_volume_residue", "port_residue")
                        .stream().allMatch(field ->
                                cleanup.path(field).asInt() == 0)
                        && !cleanup.path(
                                "daemon_build_cache_preservation_claimed")
                        .asBoolean()
                        && !cleanup.path(
                                "daemon_image_set_preservation_claimed")
                        .asBoolean(),
                "operator-core anchor cleanup evidence drifted");
    }

    private static void validateProductionAndWorm(
            JsonNode contract,
            JsonNode operator
    ) {
        JsonNode boundary = contract.path("production_and_worm_boundary");
        JsonNode worm = operator.path("worm_successor");
        JsonNode runtime = operator.path("production_runtime_successor");
        require(boundary.path("worm").equals(worm)
                        && "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f"
                        .equals(worm.path("current_report")
                                .path("sha256").asString())
                        && worm.path("current_report").path("byte_count")
                        .asLong() == 1_442L
                        && worm.path("current_chain_node_count").asInt() == 8
                        && "29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc"
                        .equals(worm.path("current_build_context_sha256")
                                .asString())
                        && "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
                        .equals(worm.path("dockerfile_sha256").asString())
                        && boundary.path("accepted_runtime_file_count").asInt()
                        == runtime.path("accepted_file_count").asInt()
                        && boundary.path("current_runtime_file_count").asInt()
                        == runtime.path("current_file_count").asInt()
                        && boundary.path("accepted_runtime_manifest_sha256")
                        .asString().equals(runtime.path(
                                "accepted_manifest_sha256").asString())
                        && boundary.path("current_runtime_manifest_sha256")
                        .asString().equals(runtime.path(
                                "current_manifest_sha256").asString())
                        && boundary.path("runtime_added_files").equals(
                        runtime.path("added_files"))
                        && boundary.path("runtime_changed_files").equals(
                        runtime.path("changed_files"))
                        && boundary.path("runtime_added_files").size() == 7
                        && boundary.path("runtime_changed_files").size() == 1,
                "operator-core anchor WORM/runtime boundary drifted");
        for (String field : List.of(
                "production_schema_or_index_added",
                "production_connection_or_credentials_used",
                "production_data_read_or_mutated",
                "production_operator_executed",
                "user_compose_or_production_docker_mutated")) {
            require(!boundary.path(field).asBoolean(),
                    "operator-core anchor production boundary drifted: "
                            + field);
        }
        for (String field : List.of(
                "c1_server_tree_unchanged_from_c0",
                "c1_server_src_main_tree_unchanged_from_c0",
                "c1_web_tree_unchanged_from_c0",
                "c1_miniprogram_tree_unchanged_from_c0")) {
            require(boundary.path(field).asBoolean(),
                    "operator-core anchor C1 tree boundary drifted: " + field);
        }
    }

    private static void validateBoundaries(JsonNode contract) {
        JsonNode authorization = contract.path("authorization");
        Set<String> expectedFields = new LinkedHashSet<>(
                AUTHORIZATION_TRUE_FIELDS);
        expectedFields.addAll(AUTHORIZATION_FALSE_FIELDS);
        require(propertyNames(authorization).equals(expectedFields),
                "operator-core anchor authorization shape drifted");
        for (String field : AUTHORIZATION_TRUE_FIELDS) {
            require(authorization.path(field).asBoolean(),
                    "operator-core anchor closed authority drifted: " + field);
        }
        for (String field : AUTHORIZATION_FALSE_FIELDS) {
            require(!authorization.path(field).asBoolean(),
                    "operator-core anchor production overclaim: " + field);
        }
        JsonNode route = contract.path("route_state");
        require(route.path("migrated_operation_count").asInt() == 13
                        && route.path("pending_operation_count").asInt() == 598
                        && route.path("production_cutover_operation_count")
                        .asInt() == 0
                        && route.path("total_operation_count").asInt() == 611
                        && route.path(
                                "legacy_flask_remains_production_owner")
                        .asBoolean(),
                "operator-core anchor route boundary drifted");
        JsonNode current = contract.path("current_node_trust_boundary");
        Set<String> anchored = propertyNames(contract
                .path("implementation_checkpoint").path("artifacts"));
        anchored.addAll(propertyNames(contract
                .path("independent_acceptance_checkpoint").path("artifacts")));
        require(strings(current.path("control_sources"))
                        .equals(CURRENT_CONTROL_SOURCES)
                        && current.path("control_source_count").asInt() == 6
                        && current.path("control_source_allowlist_exact")
                        .asBoolean()
                        && current.path(
                                "control_sources_excluded_from_self_authority")
                        .asBoolean()
                        && !current.path(
                                "control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && !current.path("independently_signed_provenance")
                        .asBoolean()
                        && !current.path("c2_commit_or_tree_identity_embedded")
                        .asBoolean()
                        && CURRENT_CONTROL_SOURCES.stream()
                        .noneMatch(anchored::contains),
                "operator-core anchor current self-authority drifted");
        JsonNode acceptance = contract.path("acceptance");
        require(acceptance.path(
                                "implementation_checkpoint_changed_path_count")
                        .asInt() == 56
                        && acceptance.path(
                                "implementation_checkpoint_added_count")
                        .asInt() == 22
                        && acceptance.path(
                                "implementation_checkpoint_modified_count")
                        .asInt() == 34
                        && acceptance.path(
                                "independent_acceptance_checkpoint_changed_path_count")
                        .asInt() == 2
                        && acceptance.path(
                                "independent_acceptance_checkpoint_added_count")
                        .asInt() == 2
                        && acceptance.path("implementation_control_source_count")
                        .asInt() == 7
                        && acceptance.path(
                                "implementation_fixed_non_control_source_count")
                        .asInt() == 49
                        && acceptance.path("implementation_transition_count")
                        .asInt() == 34
                        && acceptance.path(
                                "independent_acceptance_control_source_count")
                        .asInt() == 2
                        && acceptance.path("current_control_source_count")
                        .asInt() == 6
                        && acceptance.path("anchor_closes_no_functional_gate")
                        .asBoolean()
                        && !acceptance.path("c2_self_anchor_complete")
                        .asBoolean()
                        && acceptance.path("migrated_operation_count").asInt()
                        == 13
                        && acceptance.path("pending_operation_count").asInt()
                        == 598
                        && acceptance.path(
                                "production_cutover_operation_count")
                        .asInt() == 0,
                "operator-core anchor acceptance boundary drifted");
    }

    private static void validateArtifact(String relative, JsonNode artifact) {
        require(propertyNames(artifact).equals(Set.of(
                        "repository_path", "ti_java_relative_path",
                        "change_type", "previous_mode", "mode",
                        "previous_git_blob_oid", "git_blob_oid",
                        "object_type", "previous_sha256",
                        "previous_byte_count", "sha256", "byte_count",
                        "inserted_line_count", "deleted_line_count"))
                        && relative.equals(artifact
                        .path("ti_java_relative_path").asString())
                        && ("Ti-Java/" + relative).equals(
                        artifact.path("repository_path").asString())
                        && "blob".equals(
                        artifact.path("object_type").asString())
                        && artifact.path("git_blob_oid").asString()
                        .length() == 40
                        && artifact.path("sha256").asString().length() == 64
                        && artifact.path("byte_count").asLong() > 0,
                "operator-core anchor artifact shape drifted: " + relative);
        String change = artifact.path("change_type").asString();
        if ("A".equals(change)) {
            require("000000".equals(
                            artifact.path("previous_mode").asString())
                            && "0".repeat(40).equals(artifact
                            .path("previous_git_blob_oid").asString())
                            && artifact.path("previous_sha256").isNull()
                            && artifact.path("previous_byte_count").asLong()
                            == 0L,
                    "operator-core anchor added artifact parent drifted: "
                            + relative);
        } else {
            require("M".equals(change)
                            && artifact.path("previous_git_blob_oid")
                            .asString().length() == 40
                            && artifact.path("previous_sha256").asString()
                            .length() == 64
                            && artifact.path("previous_byte_count").asLong()
                            > 0L,
                    "operator-core anchor modified artifact drifted: "
                            + relative);
        }
    }

    private static void validateAddedArtifact(
            String relative,
            JsonNode artifact,
            String mode,
            String expectedSha256,
            long expectedByteCount
    ) {
        validateArtifact(relative, artifact);
        require("A".equals(artifact.path("change_type").asString())
                        && mode.equals(artifact.path("mode").asString())
                        && expectedSha256.equals(
                        artifact.path("sha256").asString())
                        && artifact.path("byte_count").asLong()
                        == expectedByteCount,
                "operator-core anchor added artifact identity drifted: "
                        + relative);
    }

    private static void validateTestSuite(JsonNode suite, int tests) {
        require(suite.path("tests").asInt() == tests
                        && suite.path("failures").asInt() == 0
                        && suite.path("errors").asInt() == 0
                        && suite.path("skipped").asInt() == 0,
                "operator-core anchor test suite drifted: " + tests);
    }

    private static JsonNode readFixedJson(
            Path root,
            String relative,
            String expectedSha256,
            long expectedBytes
    ) throws IOException {
        Path path = fixedRegularFile(root, relative);
        byte[] payload = Files.readAllBytes(path);
        require(payload.length == expectedBytes
                        && expectedSha256.equals(sha256(payload)),
                "operator-core anchor fixed bytes drifted: " + relative);
        JsonNode value = JSON.readTree(payload);
        require(value.isObject(),
                "operator-core anchor fixed JSON must be an object");
        return value;
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Set<String> allowlist = Set.of(
                CONTRACT_RELATIVE, OPERATOR_CONTRACT_RELATIVE,
                EVIDENCE_RELATIVE, RUNNER_RELATIVE);
        require(allowlist.contains(relative),
                "operator-core anchor unknown or absolute source");
        return anchoredRegularFile(root, relative);
    }

    private static Path anchoredRegularFile(Path root, String relative)
            throws IOException {
        Path candidate;
        try {
            candidate = Path.of(relative);
        } catch (RuntimeException error) {
            throw new AssertionError(
                    "operator-core anchor invalid source path", error);
        }
        require(!candidate.isAbsolute() && candidate.getNameCount() > 0,
                "operator-core anchor absolute or empty source");
        Path base = root.toRealPath();
        Path cursor = base;
        for (Path part : candidate) {
            String value = part.toString();
            require(!value.isBlank() && !".".equals(value)
                            && !"..".equals(value),
                    "operator-core anchor path escapes root: " + relative);
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "operator-core anchor source is a symlink: " + relative);
        }
        Path resolved = base.resolve(candidate).toRealPath();
        require(resolved.startsWith(base)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "operator-core anchor source is not regular: " + relative);
        return resolved;
    }

    private static void validateRunnerMode(Path runner) {
        try {
            require(Files.getPosixFilePermissions(
                            runner, LinkOption.NOFOLLOW_LINKS)
                            .equals(RUNNER_PERMISSIONS),
                    "operator-core anchor runner mode drifted");
        } catch (IOException | UnsupportedOperationException error) {
            throw new AssertionError(
                    "operator-core anchor runner mode unavailable", error);
        }
    }

    private static String documentPayloadSha256(JsonNode document) {
        ObjectNode copy = (ObjectNode) document.deepCopy();
        copy.remove("document_payload_sha256");
        return canonicalSha256(copy);
    }

    private static String canonicalSha256(JsonNode value) {
        return sha256(JSON.writeValueAsBytes(canonicalNode(value)));
    }

    private static JsonNode canonicalNode(JsonNode value) {
        if (value.isObject()) {
            ObjectNode object = JSON.createObjectNode();
            TreeMap<String, JsonNode> sorted = new TreeMap<>();
            value.properties().forEach(entry ->
                    sorted.put(entry.getKey(), canonicalNode(entry.getValue())));
            sorted.forEach(object::set);
            return object;
        }
        if (value.isArray()) {
            ArrayNode array = JSON.createArrayNode();
            value.forEach(item -> array.add(canonicalNode(item)));
            return array;
        }
        return value;
    }

    private static Set<String> propertyNames(JsonNode object) {
        Set<String> names = new LinkedHashSet<>();
        object.properties().forEach(entry -> names.add(entry.getKey()));
        return names;
    }

    private static List<String> strings(JsonNode array) {
        List<String> result = new ArrayList<>();
        array.forEach(value -> result.add(value.asString()));
        return List.copyOf(result);
    }

    private static boolean disjoint(Set<String> left, Set<String> right) {
        return left.stream().noneMatch(right::contains);
    }

    private static String sha256(byte[] payload) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(payload));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }
}
