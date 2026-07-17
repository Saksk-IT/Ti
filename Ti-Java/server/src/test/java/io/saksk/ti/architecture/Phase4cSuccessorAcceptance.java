package io.saksk.ti.architecture;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import tools.jackson.databind.JsonNode;

/** Fixed Phase 4C trust root shared by historical Phase 4B parity tests. */
final class Phase4cSuccessorAcceptance {

    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-composition-contract";
    private static final String CONTRACT_STATUS =
            "composition_and_migration_primitives_closed_"
                    + "http_neutral_implementation_authorized";
    private static final String ACCEPTED_COMMIT =
            "2ca3e16d9585de55313fd2de9b1429a6351d9683";
    private static final String ACCEPTED_PREDECESSOR_SHA256 =
            "1ec41fde1e17dd1f09a9aa737aadd9ada1f64c41f4e44f1df87dbf0613c30ee6";
    private static final Map<String, FixedSource> SOURCES = fixedSources();

    private Phase4cSuccessorAcceptance() {
    }

    static void validate(JsonNode contract) {
        require(CONTRACT_ID.equals(contract.path("contract_id").asString()),
                "unexpected Phase4C contract id");
        require(CONTRACT_STATUS.equals(contract.path("status").asString()),
                "unexpected Phase4C contract status");
        JsonNode predecessor = contract.path("predecessor");
        require(ACCEPTED_COMMIT.equals(predecessor.path("accepted_commit").asString()),
                "unexpected accepted commit");
        require(ACCEPTED_PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString()),
                "Phase4B predecessor changed");

        JsonNode history = contract.path("historical_acceptance");
        require(ACCEPTED_COMMIT.equals(history.path("accepted_commit").asString()),
                "unexpected history commit");
        require(history.path("successor_allowlist_exact").asBoolean(),
                "successor allowlist is not exact");
        require(history.path("arbitrary_source_hash_lookup_forbidden").asBoolean(),
                "arbitrary successor lookup is not forbidden");
        require(propertyNames(history.path("successor_aware_test_files"))
                        .equals(SOURCES.keySet()),
                "unexpected successor source set");

        JsonNode accepted = history.path("accepted_file_sha256");
        JsonNode handoffs = history.path("successor_aware_test_files");
        JsonNode references = contract.path("source_contracts");
        for (Map.Entry<String, FixedSource> entry : SOURCES.entrySet()) {
            String relative = entry.getKey();
            FixedSource fixed = entry.getValue();
            JsonNode handoff = handoffs.path(relative);
            JsonNode reference = references.path(fixed.sourceKey());
            require(fixed.acceptedSha256().equals(accepted.path(relative).asString()),
                    "accepted hash changed for " + relative);
            require(fixed.acceptedSha256().equals(
                            handoff.path("accepted_sha256").asString()),
                    "handoff accepted hash changed for " + relative);
            require(fixed.sourceKey().equals(
                            handoff.path("source_contract_key").asString()),
                    "handoff key changed for " + relative);
            require(relative.equals(reference.path("source").asString()),
                    "successor source changed for " + relative);
            require(reference.path("sha256").asString().equals(
                            handoff.path("successor_sha256").asString()),
                    "successor hash disagreement for " + relative);
        }
    }

    static String successorHash(JsonNode contract, String relative) {
        FixedSource fixed = SOURCES.get(relative);
        if (fixed == null) {
            return null;
        }
        validate(contract);
        return contract.path("source_contracts")
                .path(fixed.sourceKey())
                .path("sha256")
                .asString();
    }

    private static Set<String> propertyNames(JsonNode node) {
        return node.propertyNames().stream().collect(java.util.stream.Collectors.toSet());
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static Map<String, FixedSource> fixedSources() {
        Map<String, FixedSource> sources = new LinkedHashMap<>();
        sources.put(
                "docs/refactor/05-progress.md",
                new FixedSource(
                        "progress",
                        "0d08ea5c4c6f0c61c6d8c2a722d1e95ce0bfe999d523db2c0b9cdca7bc213bb9"));
        sources.put(
                "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
                new FixedSource(
                        "all_shares_entry_successor_test",
                        "0c2be82c561aa7f02e6db4b71d4f91ebf1b772f92d4e193a3812e92722c2ba2a"));
        sources.put(
                "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
                new FixedSource(
                        "all_shares_read_successor_test",
                        "75e4235fad3bbe8edfd34829a82ff4a6cff8798fee1ac6cfeab072e6f2f81913"));
        sources.put(
                "tools/test_phase4b_personal_bank_share_list_read_contract.py",
                new FixedSource(
                        "share_list_acceptance_successor_test",
                        "65fe01833802612620ffa26e1771cd9215c5866d65a933bc34be4a806ee42c63"));
        sources.put(
                "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
                new FixedSource(
                        "usage_stats_entry_successor_test",
                        "0eb5fa3ae1eab5001e1a44e77d312ad425967d746370b8f6da6f18a202089f8d"));
        sources.put(
                "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
                new FixedSource(
                        "usage_stats_read_successor_test",
                        "60c6dc113f42093c2ff2ff21405cdebadb76fd99886fc94c1b15ab616955aac4"));
        sources.put(
                "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
                new FixedSource(
                        "phase4b_entry_contract_test",
                        "f5329e12eac3b18e2742c85d40d7c25591fb83fc2cdb3c0d215e240fa0566def"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankAllSharesContractParityTest.java",
                new FixedSource(
                        "all_shares_java_successor_test",
                        "0716fcfa788c530517f2da5ef87a943c3ed2d960e50e599d66756e6e84d29973"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankShareListContractParityTest.java",
                new FixedSource(
                        "share_list_java_successor_test",
                        "d6326b2aa91ceb2bb502bc8847d233c26a2741996a7bc3bf627c9731c6318523"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankUsageStatsContractParityTest.java",
                new FixedSource(
                        "usage_stats_java_successor_test",
                        "343b8b4cf4e9df575e1a5f14743d39c2d31e2b7b20f9c604bcab3f17081e6a1e"));
        return Map.copyOf(sources);
    }

    private record FixedSource(String sourceKey, String acceptedSha256) {
    }
}
