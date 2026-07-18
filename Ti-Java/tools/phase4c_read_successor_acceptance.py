#!/usr/bin/env python3
"""Fixed trust root for historical checks that admit the Phase 4C read successor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    from tools.phase4c_http_entry_successor_acceptance import (
        accepted_sha256 as http_entry_accepted_sha256,
        successor_sha256 as http_entry_successor_sha256,
    )
    from tools.phase4c_http_implementation_successor_acceptance import (
        accepted_sha256 as http_implementation_accepted_sha256,
        successor_sha256 as http_implementation_successor_sha256,
    )
    from tools.phase4c_http_target_execution_successor_acceptance import (
        accepted_sha256 as http_target_execution_accepted_sha256,
        successor_sha256 as http_target_execution_successor_sha256,
    )
    from tools.phase4c_successor_acceptance import (
        SUCCESSOR_SOURCES as COMPOSITION_SUCCESSOR_SOURCES,
        successor_sha256 as composition_successor_sha256,
        validate_successor_contract as validate_composition_contract,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    from phase4c_http_entry_successor_acceptance import (
        accepted_sha256 as http_entry_accepted_sha256,
        successor_sha256 as http_entry_successor_sha256,
    )
    from phase4c_http_implementation_successor_acceptance import (
        accepted_sha256 as http_implementation_accepted_sha256,
        successor_sha256 as http_implementation_successor_sha256,
    )
    from phase4c_http_target_execution_successor_acceptance import (
        accepted_sha256 as http_target_execution_accepted_sha256,
        successor_sha256 as http_target_execution_successor_sha256,
    )
    from phase4c_successor_acceptance import (
        SUCCESSOR_SOURCES as COMPOSITION_SUCCESSOR_SOURCES,
        successor_sha256 as composition_successor_sha256,
        validate_successor_contract as validate_composition_contract,
    )


CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-read-contract"
CONTRACT_STATUS = "implemented_and_targeted_verified_http_aliases_deferred"
PREDECESSOR_CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-composition-contract"
)
PREDECESSOR_SHA256 = (
    "ba900795d92046693617d92f4de7599d604e389e7b60e1cc145d08a737518f6b"
)
CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json"
)
COMPOSITION_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json"
)

# Exact old/current hashes keep the read contract from becoming its own trust root.
PYTHON_SOURCES: dict[str, tuple[str, str]] = {
    "tools/test_phase4b_personal_bank_share_list_entry_contract.py": (
        "866b749cdc00fe22451e4a4663702d98e4917e0d546f996f0d6cac6326f39d75",
        "c60e4d9abb01c70001e703cf8c4c5eed77bd65445c506e99a9e3dd38dadab2ee",
    ),
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": (
        "114a07ce3ada1027c7e30a595b249c9f88244ffd0d0838b1507019f64711eb59",
        "2ed3c3d1168aeea07d863bcdd6c81522bc59e78d253242b9f36f3808b9ca0b40",
    ),
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": (
        "03a5cefe9ea73ad86ff8755019d88abbb84778488fdb117dd9c4517a91040b86",
        "f236ed8080a4e73d294d0eb96f1b19f8b3116ef0a51ba1be6d5d8e695dc558e0",
    ),
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": (
        "3459e74ed669e3f0aa6e4bc3e2e600f4a4b644a03fc7a382cd01a78ce873d254",
        "6869964c169b6970df0c9f762957664f2e711c2abb309a4e5a2a3689cb636f29",
    ),
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": (
        "5854e591041b8cb1892b805208903c5115027a8dbaeec56f8db8b98223301ada",
        "de1415897a0cef4e98266aaca699b162dd469caf17628dd2fde19bed691ef32c",
    ),
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": (
        "2251ab9b5c15c0badf59b782fd9e7f76030f1bef33f8943fcfbf459972abc4be",
        "90c77b28c1c08822d900f150e5c4c69fe4a7463b5dfc7a4ce021fc599c71a15a",
    ),
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": (
        "9fcd432a81f78eb78f0001e4e6d029e01f27047e56714c96d7fd47607d98c016",
        "590f4d62c45c4fc9fdde9332f2de376f62481b672120c72389071e4a8bf334a7",
    ),
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "c5c0a52d90553acc3699dab2534f6dc1ac0261940be6611f57ca293f3fb92207",
        "08e82154d66ab4a112091ee97b40bc1c155aae14a4bd9ca0b6afbb9032e71bdd",
    ),
}

JAVA_SOURCES: dict[str, tuple[str, str]] = {
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "ModuleContractParityTest.java"
    ): (
        "35e25fa5ed4d5771701f8c1819b615bee9af441a6c64cbf1386df168f16610cb",
        "02a4b9bfabe2f9e3789e94826b1f337e8a0986e5d36f42ac243cbe79060a82d2",
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankAllSharesContractParityTest.java"
    ): (
        "171c36f7c3cdd2d2ff97998cade67ec99c3d825ec3bce4191094a3bcf0095b48",
        "8946d000de7927cf258d6c8acaf025bcd85fe29c709b7b162b5dfade95115409",
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankShareListContractParityTest.java"
    ): (
        "1bc3ba26b932eba694d0aeb4762e7973d51a0fee5bd69d0454799c223d56248a",
        "d7e3be7430e5cfc1cd43988eb8cb42e05536286dac58d2d075b72ad32c8819b9",
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "PersonalBankUsageStatsContractParityTest.java"
    ): (
        "1b24e8a8f1861a5adad96de9f087abc684b73e9a4dd496ffb7f1d071ddc307bc",
        "07648bcf8c80c392b355df029893dac9411877a1d4adeb05e1ee83666b86ca42",
    ),
}

AUXILIARY_SOURCES: dict[str, tuple[str, str]] = {
    "docs/refactor/05-progress.md": (
        "47ec2b9a2178dee8db91f0461b9abffbbe9dea0a5ba4dd3694d4f33643735bbf",
        "71407c0fd99d1b8f982ea4e108e1dc5e0d9d472584824fb7a8ade325be65f1c2",
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_read_successor_contract(ti_java_root: Path) -> dict | None:
    path = ti_java_root / CONTRACT_RELATIVE
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        contract = json.load(handle)
    validate_read_successor_contract(contract, ti_java_root)
    return contract


def validate_read_successor_contract(contract: dict, ti_java_root: Path) -> None:
    if contract.get("contract_id") != CONTRACT_ID:
        raise AssertionError("unexpected Phase4C read successor contract id")
    if contract.get("status") != CONTRACT_STATUS:
        raise AssertionError("unexpected Phase4C read successor status")
    predecessor = contract.get("predecessor", {})
    if predecessor.get("contract_id") != PREDECESSOR_CONTRACT_ID:
        raise AssertionError("unexpected Phase4C read predecessor id")
    if predecessor.get("sha256") != PREDECESSOR_SHA256:
        raise AssertionError("Phase4C composition predecessor was not preserved")

    history = contract.get("historical_successor_acceptance", {})
    if not history.get("successor_allowlist_exact"):
        raise AssertionError("Phase4C read successor allowlist is not exact")
    if not history.get("arbitrary_source_hash_lookup_forbidden"):
        raise AssertionError("arbitrary Phase4C read successor lookup is not forbidden")
    python_sources = history.get("python_sources", {})
    if set(python_sources) != set(PYTHON_SOURCES):
        raise AssertionError("unexpected Phase4C read Python successor source set")
    java_sources = history.get("java_sources", {})
    if set(java_sources) != set(JAVA_SOURCES):
        raise AssertionError("unexpected Phase4C read Java successor source set")
    auxiliary_sources = history.get("auxiliary_sources", {})
    if set(auxiliary_sources) != set(AUXILIARY_SOURCES):
        raise AssertionError("unexpected Phase4C read auxiliary successor source set")

    root = ti_java_root.resolve(strict=True)
    for relative, (accepted_sha256, successor_hash) in {
        **PYTHON_SOURCES,
        **JAVA_SOURCES,
        **AUXILIARY_SOURCES,
    }.items():
        if relative in PYTHON_SOURCES:
            sources = python_sources
        elif relative in JAVA_SOURCES:
            sources = java_sources
        else:
            sources = auxiliary_sources
        reference = sources.get(relative, {})
        if reference.get("source") != relative:
            raise AssertionError(f"read successor source drift for {relative}")
        if reference.get("accepted_sha256") != accepted_sha256:
            raise AssertionError(f"read successor accepted hash drift for {relative}")
        if reference.get("successor_sha256") != successor_hash:
            raise AssertionError(f"read successor hash is not fixed for {relative}")
        path = root / relative
        cursor = root
        for part in Path(relative).parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise AssertionError(f"read successor path contains symlink: {relative}")
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            raise AssertionError(
                f"read successor path escaped or vanished: {relative}"
            ) from error
        physical_hash = successor_hash
        target_successor = http_target_execution_successor_sha256(root, relative)
        if target_successor is not None and (
                http_target_execution_accepted_sha256(relative) == successor_hash):
            physical_hash = target_successor
        else:
            http_successor = http_entry_successor_sha256(root, relative)
            if http_successor is not None:
                if http_entry_accepted_sha256(relative) != successor_hash:
                    raise AssertionError(
                        f"HTTP entry did not accept the exact read successor for {relative}"
                    )
                physical_hash = http_successor
            else:
                implementation_successor = http_implementation_successor_sha256(
                    root, relative
                )
                if implementation_successor is not None:
                    if http_implementation_accepted_sha256(relative) != successor_hash:
                        raise AssertionError(
                            "HTTP implementation did not accept the exact read "
                            f"successor for {relative}"
                        )
                    physical_hash = implementation_successor
        if not resolved.is_file() or _sha256(resolved) != physical_hash:
            raise AssertionError(f"read successor file hash drift for {relative}")


def load_composition_predecessor_contract(ti_java_root: Path) -> dict | None:
    read_contract = load_read_successor_contract(ti_java_root)
    if read_contract is None:
        return None
    path = ti_java_root / COMPOSITION_RELATIVE
    if not path.is_file() or _sha256(path) != PREDECESSOR_SHA256:
        raise AssertionError("Phase4C composition predecessor file drift")
    with path.open("r", encoding="utf-8") as handle:
        composition = json.load(handle)
    validate_composition_contract(composition)
    return composition


def successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    contract = load_read_successor_contract(ti_java_root)
    if contract is not None:
        fixed = {
            **PYTHON_SOURCES,
            **JAVA_SOURCES,
            **AUXILIARY_SOURCES,
        }.get(relative)
        target_successor = http_target_execution_successor_sha256(
            ti_java_root, relative
        )
        if target_successor is not None and fixed is not None and (
                http_target_execution_accepted_sha256(relative) == fixed[1]):
            return target_successor
        http_successor = http_entry_successor_sha256(ti_java_root, relative)
        if http_successor is not None:
            return http_successor
        implementation_successor = http_implementation_successor_sha256(
            ti_java_root, relative
        )
        if implementation_successor is not None:
            fixed = {
                **PYTHON_SOURCES,
                **JAVA_SOURCES,
                **AUXILIARY_SOURCES,
            }.get(relative)
            if fixed is None or (
                    http_implementation_accepted_sha256(relative) != fixed[1]):
                raise AssertionError(
                    "HTTP implementation did not accept the exact read "
                    f"successor for {relative}"
                )
            return implementation_successor
        if fixed is not None:
            return fixed[1]
        composition_fixed = COMPOSITION_SUCCESSOR_SOURCES.get(relative)
        if composition_fixed is None:
            return None
        load_composition_predecessor_contract(ti_java_root)
        return composition_fixed["successor_sha256"]
    return composition_successor_sha256(ti_java_root, relative)
