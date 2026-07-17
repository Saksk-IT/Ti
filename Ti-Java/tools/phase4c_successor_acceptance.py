#!/usr/bin/env python3
"""Fixed trust root for Phase 4B tests that admit the Phase 4C successor."""

from __future__ import annotations

import json
from pathlib import Path


CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-composition-contract"
CONTRACT_STATUS = (
    "composition_and_migration_primitives_closed_"
    "http_neutral_implementation_authorized"
)
ACCEPTED_COMMIT = "2ca3e16d9585de55313fd2de9b1429a6351d9683"
ACCEPTED_PREDECESSOR_SHA256 = (
    "1ec41fde1e17dd1f09a9aa737aadd9ada1f64c41f4e44f1df87dbf0613c30ee6"
)
SUCCESSOR_SOURCES = {
    "docs/refactor/05-progress.md": {
        "source_key": "progress",
        "accepted_sha256": (
            "0d08ea5c4c6f0c61c6d8c2a722d1e95ce0bfe999d523db2c0b9cdca7bc213bb9"
        ),
    },
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": {
        "source_key": "all_shares_entry_successor_test",
        "accepted_sha256": (
            "0c2be82c561aa7f02e6db4b71d4f91ebf1b772f92d4e193a3812e92722c2ba2a"
        ),
    },
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": {
        "source_key": "all_shares_read_successor_test",
        "accepted_sha256": (
            "75e4235fad3bbe8edfd34829a82ff4a6cff8798fee1ac6cfeab072e6f2f81913"
        ),
    },
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": {
        "source_key": "share_list_acceptance_successor_test",
        "accepted_sha256": (
            "65fe01833802612620ffa26e1771cd9215c5866d65a933bc34be4a806ee42c63"
        ),
    },
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": {
        "source_key": "usage_stats_entry_successor_test",
        "accepted_sha256": (
            "0eb5fa3ae1eab5001e1a44e77d312ad425967d746370b8f6da6f18a202089f8d"
        ),
    },
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": {
        "source_key": "usage_stats_read_successor_test",
        "accepted_sha256": (
            "60c6dc113f42093c2ff2ff21405cdebadb76fd99886fc94c1b15ab616955aac4"
        ),
    },
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": {
        "source_key": "phase4b_entry_contract_test",
        "accepted_sha256": (
            "f5329e12eac3b18e2742c85d40d7c25591fb83fc2cdb3c0d215e240fa0566def"
        ),
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankAllSharesContractParityTest.java"
    ): {
        "source_key": "all_shares_java_successor_test",
        "accepted_sha256": (
            "0716fcfa788c530517f2da5ef87a943c3ed2d960e50e599d66756e6e84d29973"
        ),
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankShareListContractParityTest.java"
    ): {
        "source_key": "share_list_java_successor_test",
        "accepted_sha256": (
            "d6326b2aa91ceb2bb502bc8847d233c26a2741996a7bc3bf627c9731c6318523"
        ),
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ): {
        "source_key": "usage_stats_java_successor_test",
        "accepted_sha256": (
            "343b8b4cf4e9df575e1a5f14743d39c2d31e2b7b20f9c604bcab3f17081e6a1e"
        ),
    },
}


def load_successor_contract(ti_java_root: Path) -> dict | None:
    path = (
        ti_java_root
        / "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json"
    )
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        contract = json.load(handle)
    validate_successor_contract(contract)
    return contract


def validate_successor_contract(contract: dict) -> None:
    if contract.get("contract_id") != CONTRACT_ID:
        raise AssertionError("unexpected Phase4C successor contract id")
    if contract.get("status") != CONTRACT_STATUS:
        raise AssertionError("unexpected Phase4C successor status")
    predecessor = contract.get("predecessor", {})
    if predecessor.get("accepted_commit") != ACCEPTED_COMMIT:
        raise AssertionError("unexpected Phase4C accepted commit")
    if predecessor.get("sha256") != ACCEPTED_PREDECESSOR_SHA256:
        raise AssertionError("Phase4B predecessor was not preserved")
    history = contract.get("historical_acceptance", {})
    if history.get("accepted_commit") != ACCEPTED_COMMIT:
        raise AssertionError("unexpected historical acceptance commit")
    if not history.get("successor_allowlist_exact"):
        raise AssertionError("successor allowlist is not fail closed")
    if not history.get("arbitrary_source_hash_lookup_forbidden"):
        raise AssertionError("arbitrary successor lookup is not forbidden")
    handoffs = history.get("successor_aware_test_files", {})
    if set(handoffs) != set(SUCCESSOR_SOURCES):
        raise AssertionError("unexpected Phase4C successor source set")
    accepted = history.get("accepted_file_sha256", {})
    sources = contract.get("source_contracts", {})
    for relative, fixed in SUCCESSOR_SOURCES.items():
        handoff = handoffs.get(relative, {})
        if accepted.get(relative) != fixed["accepted_sha256"]:
            raise AssertionError(f"accepted hash drift for {relative}")
        if handoff.get("accepted_sha256") != fixed["accepted_sha256"]:
            raise AssertionError(f"handoff accepted hash drift for {relative}")
        if handoff.get("source_contract_key") != fixed["source_key"]:
            raise AssertionError(f"handoff source key drift for {relative}")
        reference = sources.get(fixed["source_key"], {})
        if reference.get("source") != relative:
            raise AssertionError(f"successor source drift for {relative}")
        if reference.get("sha256") != handoff.get("successor_sha256"):
            raise AssertionError(f"successor hash disagreement for {relative}")


def successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    fixed = SUCCESSOR_SOURCES.get(relative)
    if fixed is None:
        return None
    contract = load_successor_contract(ti_java_root)
    if contract is None:
        return None
    return contract["source_contracts"][fixed["source_key"]]["sha256"]
