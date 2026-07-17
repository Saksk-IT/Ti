package io.saksk.ti.architecture;

import java.util.LinkedHashMap;
import java.util.HashSet;
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
    private static final Map<String, FixedAuxiliary> AUXILIARIES = fixedAuxiliaries();

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
            require(fixed.successorSha256().equals(
                            handoff.path("successor_sha256").asString()),
                    "successor hash is not fixed for " + relative);
            require(fixed.successorSha256().equals(reference.path("sha256").asString()),
                    "source contract hash is not fixed for " + relative);
            require(reference.path("sha256").asString().equals(
                            handoff.path("successor_sha256").asString()),
                    "successor hash disagreement for " + relative);
        }

        JsonNode forward = contract.path("forward_handoff");
        JsonNode overrides = forward.path("historical_hash_overrides");
        Set<String> additions = textValues(forward.path("forward_additions"));
        for (Map.Entry<String, FixedAuxiliary> entry : AUXILIARIES.entrySet()) {
            String relative = entry.getKey();
            FixedAuxiliary fixed = entry.getValue();
            JsonNode reference = references.path(fixed.sourceKey());
            require(relative.equals(reference.path("source").asString()),
                    "auxiliary successor source changed for " + relative);
            require(fixed.successorSha256().equals(reference.path("sha256").asString()),
                    "auxiliary successor hash is not fixed for " + relative);
            String forwardRelative = "Ti-Java/" + relative;
            if (fixed.historicalSha256() == null) {
                require(additions.contains(forwardRelative),
                        "new auxiliary successor is not admitted: " + relative);
                require(!propertyNames(overrides).contains(relative),
                        "new auxiliary successor has historical override: " + relative);
            } else {
                require(!additions.contains(forwardRelative),
                        "existing auxiliary is misclassified as new: " + relative);
                require(fixed.historicalSha256().equals(
                                overrides.path(relative).asString()),
                        "auxiliary historical hash changed for " + relative);
            }
        }
    }

    static String successorHash(JsonNode contract, String relative) {
        FixedSource fixed = SOURCES.get(relative);
        if (fixed == null) {
            return null;
        }
        validate(contract);
        return fixed.successorSha256();
    }

    private static Set<String> propertyNames(JsonNode node) {
        return node.propertyNames().stream().collect(java.util.stream.Collectors.toSet());
    }

    private static Set<String> textValues(JsonNode node) {
        Set<String> values = new HashSet<>();
        node.forEach(value -> values.add(value.asString()));
        return Set.copyOf(values);
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
                        "0d08ea5c4c6f0c61c6d8c2a722d1e95ce0bfe999d523db2c0b9cdca7bc213bb9",
                        "47ec2b9a2178dee8db91f0461b9abffbbe9dea0a5ba4dd3694d4f33643735bbf"));
        sources.put(
                "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
                new FixedSource(
                        "all_shares_entry_successor_test",
                        "0c2be82c561aa7f02e6db4b71d4f91ebf1b772f92d4e193a3812e92722c2ba2a",
                        "114a07ce3ada1027c7e30a595b249c9f88244ffd0d0838b1507019f64711eb59"));
        sources.put(
                "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
                new FixedSource(
                        "all_shares_read_successor_test",
                        "75e4235fad3bbe8edfd34829a82ff4a6cff8798fee1ac6cfeab072e6f2f81913",
                        "03a5cefe9ea73ad86ff8755019d88abbb84778488fdb117dd9c4517a91040b86"));
        sources.put(
                "tools/test_phase4b_personal_bank_share_list_read_contract.py",
                new FixedSource(
                        "share_list_acceptance_successor_test",
                        "65fe01833802612620ffa26e1771cd9215c5866d65a933bc34be4a806ee42c63",
                        "3459e74ed669e3f0aa6e4bc3e2e600f4a4b644a03fc7a382cd01a78ce873d254"));
        sources.put(
                "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
                new FixedSource(
                        "usage_stats_entry_successor_test",
                        "0eb5fa3ae1eab5001e1a44e77d312ad425967d746370b8f6da6f18a202089f8d",
                        "5854e591041b8cb1892b805208903c5115027a8dbaeec56f8db8b98223301ada"));
        sources.put(
                "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
                new FixedSource(
                        "usage_stats_read_successor_test",
                        "60c6dc113f42093c2ff2ff21405cdebadb76fd99886fc94c1b15ab616955aac4",
                        "2251ab9b5c15c0badf59b782fd9e7f76030f1bef33f8943fcfbf459972abc4be"));
        sources.put(
                "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
                new FixedSource(
                        "phase4b_entry_contract_test",
                        "f5329e12eac3b18e2742c85d40d7c25591fb83fc2cdb3c0d215e240fa0566def",
                        "9fcd432a81f78eb78f0001e4e6d029e01f27047e56714c96d7fd47607d98c016"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankAllSharesContractParityTest.java",
                new FixedSource(
                        "all_shares_java_successor_test",
                        "0716fcfa788c530517f2da5ef87a943c3ed2d960e50e599d66756e6e84d29973",
                        "171c36f7c3cdd2d2ff97998cade67ec99c3d825ec3bce4191094a3bcf0095b48"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankShareListContractParityTest.java",
                new FixedSource(
                        "share_list_java_successor_test",
                        "d6326b2aa91ceb2bb502bc8847d233c26a2741996a7bc3bf627c9731c6318523",
                        "1bc3ba26b932eba694d0aeb4762e7973d51a0fee5bd69d0454799c223d56248a"));
        sources.put(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "PersonalBankUsageStatsContractParityTest.java",
                new FixedSource(
                        "usage_stats_java_successor_test",
                        "343b8b4cf4e9df575e1a5f14743d39c2d31e2b7b20f9c604bcab3f17081e6a1e",
                        "1b24e8a8f1861a5adad96de9f087abc684b73e9a4dd496ffb7f1d071ddc307bc"));
        return Map.copyOf(sources);
    }

    private static Map<String, FixedAuxiliary> fixedAuxiliaries() {
        Map<String, FixedAuxiliary> sources = new LinkedHashMap<>();
        sources.put(
                "infra/phase2/README.md",
                new FixedAuxiliary(
                        "phase2_wormhole_readme",
                        "4dd7e88f99cb8639e91acd181c3f07749a1ff38dc95256eda6d6e55566623ef2",
                        "a8e60b2432a3dffa56a648f5e235d1cff8854584cdfee9a59a3c4a1571d32b54"));
        sources.put(
                "infra/phase2/verify-local-reference-wormhole.sh",
                new FixedAuxiliary(
                        "phase2_wormhole_runner",
                        "9aebdb8a7e477c464a6750b73c76f9336d1191230762ae8369ebe8cc1b82ad49",
                        "645ea7b35f66c26be93ab53314eeed1d3af68263b94c6c613e25935d8b864a8c"));
        sources.put(
                "infra/phase2/verify-static.sh",
                new FixedAuxiliary(
                        "phase2_static_verifier",
                        "5a9cd32fa094f25d32fcd71da6cd17d0fdc353d02fdfc6c2886ac5128777102d",
                        "7589dee01dd9af059ff3dd021e63dc7000e681d292cb748ab03318ebc3465ca5"));
        sources.put(
                "tools/validate_phase1.py",
                new FixedAuxiliary(
                        "phase1_validator",
                        "a38fce0e7f13530196ab424f7f7da75816c3e32ae6ac149986a5914875a62c5e",
                        "e343c9f72de83444c60268c8f328fa1626982ccf74ec96027c05485818541c6d"));
        sources.put(
                "tools/phase2_wormhole_successor_acceptance.py",
                new FixedAuxiliary(
                        "phase2_worm_successor_gate",
                        null,
                        "1e4dab89bfb58a2d9f10a63e812e26a4b2790a76a9bb02cd9d2d076596ee354e"));
        sources.put(
                "tools/test_phase2_wormhole_successor_acceptance.py",
                new FixedAuxiliary(
                        "phase2_worm_successor_test",
                        null,
                        "c3d6532757c5adf08689773827725e4753267d9d76231ea9fec5103bc1b96b49"));
        sources.put(
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-entry-worm-evidence.json",
                new FixedAuxiliary(
                        "phase4c_entry_worm_report",
                        null,
                        "cfb262319ded0840218fd9bfb4deff1e7bc9c66b5849e3ff05f49a459e686884"));
        return Map.copyOf(sources);
    }

    private record FixedSource(
            String sourceKey,
            String acceptedSha256,
            String successorSha256
    ) {
    }

    private record FixedAuxiliary(
            String sourceKey,
            String historicalSha256,
            String successorSha256
    ) {
    }
}
