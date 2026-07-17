#!/usr/bin/env python3
"""Fixed trust root for Phase 4B tests that admit the Phase 4C successor."""

from __future__ import annotations

import hashlib
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
        "successor_sha256": (
            "47ec2b9a2178dee8db91f0461b9abffbbe9dea0a5ba4dd3694d4f33643735bbf"
        ),
    },
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": {
        "source_key": "all_shares_entry_successor_test",
        "accepted_sha256": (
            "0c2be82c561aa7f02e6db4b71d4f91ebf1b772f92d4e193a3812e92722c2ba2a"
        ),
        "successor_sha256": (
            "114a07ce3ada1027c7e30a595b249c9f88244ffd0d0838b1507019f64711eb59"
        ),
    },
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": {
        "source_key": "all_shares_read_successor_test",
        "accepted_sha256": (
            "75e4235fad3bbe8edfd34829a82ff4a6cff8798fee1ac6cfeab072e6f2f81913"
        ),
        "successor_sha256": (
            "03a5cefe9ea73ad86ff8755019d88abbb84778488fdb117dd9c4517a91040b86"
        ),
    },
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": {
        "source_key": "share_list_acceptance_successor_test",
        "accepted_sha256": (
            "65fe01833802612620ffa26e1771cd9215c5866d65a933bc34be4a806ee42c63"
        ),
        "successor_sha256": (
            "3459e74ed669e3f0aa6e4bc3e2e600f4a4b644a03fc7a382cd01a78ce873d254"
        ),
    },
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": {
        "source_key": "usage_stats_entry_successor_test",
        "accepted_sha256": (
            "0eb5fa3ae1eab5001e1a44e77d312ad425967d746370b8f6da6f18a202089f8d"
        ),
        "successor_sha256": (
            "5854e591041b8cb1892b805208903c5115027a8dbaeec56f8db8b98223301ada"
        ),
    },
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": {
        "source_key": "usage_stats_read_successor_test",
        "accepted_sha256": (
            "60c6dc113f42093c2ff2ff21405cdebadb76fd99886fc94c1b15ab616955aac4"
        ),
        "successor_sha256": (
            "2251ab9b5c15c0badf59b782fd9e7f76030f1bef33f8943fcfbf459972abc4be"
        ),
    },
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": {
        "source_key": "phase4b_entry_contract_test",
        "accepted_sha256": (
            "f5329e12eac3b18e2742c85d40d7c25591fb83fc2cdb3c0d215e240fa0566def"
        ),
        "successor_sha256": (
            "9fcd432a81f78eb78f0001e4e6d029e01f27047e56714c96d7fd47607d98c016"
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
        "successor_sha256": (
            "171c36f7c3cdd2d2ff97998cade67ec99c3d825ec3bce4191094a3bcf0095b48"
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
        "successor_sha256": (
            "1bc3ba26b932eba694d0aeb4762e7973d51a0fee5bd69d0454799c223d56248a"
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
        "successor_sha256": (
            "1b24e8a8f1861a5adad96de9f087abc684b73e9a4dd496ffb7f1d071ddc307bc"
        ),
    },
}

FIXED_AUXILIARY_SUCCESSORS = {
    "infra/phase2/README.md": {
        "source_key": "phase2_wormhole_readme",
        "historical_sha256": (
            "4dd7e88f99cb8639e91acd181c3f07749a1ff38dc95256eda6d6e55566623ef2"
        ),
        "successor_sha256": (
            "a8e60b2432a3dffa56a648f5e235d1cff8854584cdfee9a59a3c4a1571d32b54"
        ),
    },
    "infra/phase2/verify-local-reference-wormhole.sh": {
        "source_key": "phase2_wormhole_runner",
        "historical_sha256": (
            "9aebdb8a7e477c464a6750b73c76f9336d1191230762ae8369ebe8cc1b82ad49"
        ),
        "successor_sha256": (
            "645ea7b35f66c26be93ab53314eeed1d3af68263b94c6c613e25935d8b864a8c"
        ),
    },
    "infra/phase2/verify-static.sh": {
        "source_key": "phase2_static_verifier",
        "historical_sha256": (
            "5a9cd32fa094f25d32fcd71da6cd17d0fdc353d02fdfc6c2886ac5128777102d"
        ),
        "successor_sha256": (
            "7589dee01dd9af059ff3dd021e63dc7000e681d292cb748ab03318ebc3465ca5"
        ),
    },
    "tools/validate_phase1.py": {
        "source_key": "phase1_validator",
        "historical_sha256": (
            "a38fce0e7f13530196ab424f7f7da75816c3e32ae6ac149986a5914875a62c5e"
        ),
        "successor_sha256": (
            "e343c9f72de83444c60268c8f328fa1626982ccf74ec96027c05485818541c6d"
        ),
    },
    "tools/phase2_wormhole_successor_acceptance.py": {
        "source_key": "phase2_worm_successor_gate",
        "historical_sha256": None,
        "successor_sha256": (
            "1e4dab89bfb58a2d9f10a63e812e26a4b2790a76a9bb02cd9d2d076596ee354e"
        ),
    },
    "tools/test_phase2_wormhole_successor_acceptance.py": {
        "source_key": "phase2_worm_successor_test",
        "historical_sha256": None,
        "successor_sha256": (
            "c3d6532757c5adf08689773827725e4753267d9d76231ea9fec5103bc1b96b49"
        ),
    },
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-entry-worm-evidence.json"
    ): {
        "source_key": "phase4c_entry_worm_report",
        "historical_sha256": None,
        "successor_sha256": (
            "cfb262319ded0840218fd9bfb4deff1e7bc9c66b5849e3ff05f49a459e686884"
        ),
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_fixed_files(ti_java_root: Path) -> None:
    root = ti_java_root.resolve(strict=True)
    for relative, fixed in {
        **SUCCESSOR_SOURCES,
        **FIXED_AUXILIARY_SUCCESSORS,
    }.items():
        path = root / relative
        cursor = root
        for part in Path(relative).parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise AssertionError(f"fixed successor path contains symlink: {relative}")
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            raise AssertionError(f"fixed successor path escaped or vanished: {relative}") from error
        if not resolved.is_file():
            raise AssertionError(f"fixed successor is not a file: {relative}")
        if _sha256(resolved) != fixed["successor_sha256"]:
            raise AssertionError(f"fixed successor file hash drift for {relative}")


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
    _validate_fixed_files(ti_java_root)
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
        if handoff.get("successor_sha256") != fixed["successor_sha256"]:
            raise AssertionError(f"successor hash is not fixed for {relative}")
        reference = sources.get(fixed["source_key"], {})
        if reference.get("source") != relative:
            raise AssertionError(f"successor source drift for {relative}")
        if reference.get("sha256") != fixed["successor_sha256"]:
            raise AssertionError(f"source contract hash is not fixed for {relative}")
        if reference.get("sha256") != handoff.get("successor_sha256"):
            raise AssertionError(f"successor hash disagreement for {relative}")

    forward = contract.get("forward_handoff", {})
    additions = set(forward.get("forward_additions", []))
    overrides = forward.get("historical_hash_overrides", {})
    for relative, fixed in FIXED_AUXILIARY_SUCCESSORS.items():
        reference = sources.get(fixed["source_key"], {})
        if reference.get("source") != relative:
            raise AssertionError(f"auxiliary successor source drift for {relative}")
        if reference.get("sha256") != fixed["successor_sha256"]:
            raise AssertionError(f"auxiliary successor hash is not fixed for {relative}")
        historical = fixed["historical_sha256"]
        forward_relative = f"Ti-Java/{relative}"
        if historical is None:
            if forward_relative not in additions:
                raise AssertionError(f"new auxiliary successor is not admitted: {relative}")
            if relative in overrides:
                raise AssertionError(f"new auxiliary successor has historical override: {relative}")
        else:
            if forward_relative in additions:
                raise AssertionError(f"existing auxiliary misclassified as new: {relative}")
            if overrides.get(relative) != historical:
                raise AssertionError(f"auxiliary historical hash drift for {relative}")


def successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    fixed = SUCCESSOR_SOURCES.get(relative)
    if fixed is None:
        return None
    contract = load_successor_contract(ti_java_root)
    if contract is None:
        return None
    return fixed["successor_sha256"]
