#!/usr/bin/env python3
"""Fail-closed acceptance for the Phase 4C typed-normalization node.

Ordinary ``load`` needs only a fixed set of regular files below ``Ti-Java``;
it neither discovers sources dynamically nor consults Git.  Callers may opt in
to replay the immutable ``c38defa`` checkpoint that externally anchors this
node's predecessor.  This module intentionally imports neither the builder nor
any earlier acceptance/validator.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-contract.json"
)
CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-http-typed-normalization-contract"
)
CONTRACT_STATUS = (
    "typed_normalization_executed_external_anchor_pending_routes_pending"
)
CONTRACT_SCOPE = "phase4c-personal-bank-user-counts-http-typed-normalization"
CONTRACT_CAPTURED_AT = "2026-07-18T15:28:17+08:00"
CONTRACT_SHA256 = (
    "ff1a751e1576916618422e0775c916e1d3b20122ffc141a04512119a6b5e99cd"
)
CONTRACT_PAYLOAD_SHA256 = (
    "eeb2b6dd9be091950867cfe8040c486b867179c49f0a0861c700864ec773eb99"
)
CONTRACT_BYTE_COUNT = 59_299

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-anchor-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-target-execution-"
    "post-push-anchor-contract"
)
PREDECESSOR_STATUS = (
    "target_execution_post_push_checkpoint_externally_anchored_"
    "typed_parity_pending_routes_pending"
)
PREDECESSOR_SCOPE = (
    "phase4c-personal-bank-user-counts-http-target-execution-"
    "post-push-external-anchor"
)
PREDECESSOR_CAPTURED_AT = "2026-07-18T14:04:12+08:00"
PREDECESSOR_SHA256 = (
    "1aa86e7cd8fe4f6c6c808eee166ff0ed30f7e228e707941efde87323b9ae057a"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "b38abd80403536c7e6db2ec9b8a8920dc06e9f740ed9c065941e483a0b5a30e2"
)
PREDECESSOR_BYTE_COUNT = 32_763

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "c38defa703b358a280122a09019031c040c58ea7"
GIT_ROOT_TREE_OID = "5ac75d896171039f34650c92829282d8a5e3c3f8"
GIT_PARENT_OID = "1dae013e11c76ad858d6695f166a32631eb1525e"
GIT_TI_JAVA_TREE_OID = "07086dc62157018ec1c989832e5e63bfefbae0f0"
GIT_AUTHORED_AT = "2026-07-18T15:06:30+08:00"
GIT_SUBJECT = "test(java): externally anchor user counts handoff"
GIT_RAW_DELTA_SHA256 = (
    "66bb02a32b94b858606b965b55c01cc1f09c7c6ded72ff7dcc639bb7c8284f72"
)
GIT_PATHS = (
    "Ti-Java/README.md",
    "Ti-Java/docs/refactor/05-progress.md",
    "Ti-Java/docs/refactor/phase4c/README.md",
    "Ti-Java/docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-anchor-contract.json",
    "Ti-Java/infra/phase2/README.md",
    "Ti-Java/infra/phase2/verify-static.sh",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java",
    "Ti-Java/tools/"
    "build_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py",
    "Ti-Java/tools/"
    "build_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py",
    "Ti-Java/tools/phase2_wormhole_successor_acceptance.py",
    "Ti-Java/tools/"
    "phase4c_http_target_execution_post_push_anchor_successor_acceptance.py",
    "Ti-Java/tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
    "Ti-Java/tools/test_phase2_wormhole_successor_acceptance.py",
    "Ti-Java/tools/"
    "test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py",
    "Ti-Java/tools/"
    "test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py",
)


def _anchored_source(
    relative: str,
    blob_oid: str,
    sha256: str,
    byte_count: int,
) -> dict[str, Any]:
    return {
        "ti_java_relative_path": relative,
        "repository_path": f"Ti-Java/{relative}",
        "git_blob_oid": blob_oid,
        "sha256": sha256,
        "byte_count": byte_count,
        "mode": "100644",
    }


ANCHORED_PREDECESSOR_SOURCES = {
    PREDECESSOR_RELATIVE: _anchored_source(
        PREDECESSOR_RELATIVE,
        "a010939ba208dd03387595ba191807eca5612ee8",
        PREDECESSOR_SHA256,
        PREDECESSOR_BYTE_COUNT,
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java"
    ): _anchored_source(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
        "67ad65a5d482128549df3b5d012e5314cd5cb173",
        "0042ca6deb05498b2d363c81843d7ec39e3f2cb6af2d43376b24b1d24b03940a",
        54_058,
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java"
    ): _anchored_source(
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java",
        "c275b712c210a21560bb2a91238ca4500eb4b907",
        "4824d1aa3ecb5208277066731b16efe33eadf2748348071f04e43c6e5887b520",
        18_477,
    ),
    (
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py"
    ): _anchored_source(
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py",
        "70951075267e29b9cb354f7f03888b23adc504c9",
        "4f97c2fcdfd36ac943fce4a1e948d99bf52cb8418519602141d40614ce78af44",
        37_163,
    ),
    (
        "tools/phase4c_http_target_execution_post_push_anchor_"
        "successor_acceptance.py"
    ): _anchored_source(
        "tools/phase4c_http_target_execution_post_push_anchor_"
        "successor_acceptance.py",
        "2a5ec91d4709d11709571805786a8c641dfeba04",
        "fe074402bcb58cfd3a681769050dd80174c584a082b462047d9684950b60e363",
        35_451,
    ),
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py"
    ): _anchored_source(
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py",
        "368af3c122f52e35b66525f5e01362acbc956c20",
        "f51784ae1831b54e630150af2af12d3692397f3191d74314f3f0816b847cdfae",
        18_683,
    ),
}


def _source(sha256: str, byte_count: int) -> dict[str, Any]:
    return {"sha256": sha256, "byte_count": byte_count}


# This allowlist is intentionally literal.  Adding a source requires editing
# this acceptance rather than discovering it from the contract or filesystem.
LOCAL_SOURCES = {
    "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json": _source(
        "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1",
        1_200_690,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-golden-target-execution-evidence.json"
    ): _source(
        "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002",
        173_397,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-http-implementation-worm-evidence.json"
    ): _source(
        "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
        1_442,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-target-execution-junit-manifest.json"
    ): _source(
        "64ff60cd56bf60f585af3d55b4ed4b4f7ee30b6a4c9e3e840688a1caaa45664b",
        33_246,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-typed-normalization-approved-difference.md"
    ): _source(
        "3c6ecb59cae4e8a2f31e7dd0ed74bcca56e0cf61830339254523f3f824e652be",
        3_730,
    ),
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-typed-normalization-junit-manifest.json"
    ): _source(
        "b6c619ee1ed4be44fd68903c2449188fd6a65ee39b7c855b1796c901d3a0268c",
        9_342,
    ),
    "docs/refactor/phase4c/route-parity-delta.csv": _source(
        "40ead5f703f1a589989fd524107f1fc31994662fb7d3e3be54fe22705025b52b",
        2_230,
    ),
    "infra/phase2/verify-in-maven-container.sh": _source(
        "2a9fa5d2e7b17f2f8d691b3d8e9e7e615e6c960c12c351525baae4251a56090e",
        3_131,
    ),
    "openapi/phase4c-personal-bank-user-counts.openapi.json": _source(
        "076957f391fd9aed65861d0633ad4b21d88b391df5217b10e2105b88b56605c9",
        87_401,
    ),
    "server/.mvn/wrapper/maven-wrapper.properties": _source(
        "ec15e462d862b9ba5dc9d8cdf249576bfdad7c70ccd441d64117d9abcd808dab",
        446,
    ),
    "server/Dockerfile": _source(
        "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499",
        1_850,
    ),
    "server/pom.xml": _source(
        "24b45d68c44c64a6b2fda2fbf6f342889640f7c3dbc088015703cd1a68ff916b",
        9_582,
    ),
    (
        "server/src/test/java/io/saksk/ti/integration/"
        "LegacyPersonalBankUserCountsTypedNormalizationIT.java"
    ): _source(
        "f9bd7dbd51e65abe8f01e80d0d564b9dfdba6856f95c4b06ad21b3705a2f025f",
        30_716,
    ),
    "server/src/test/java/io/saksk/ti/support/Phase2ContainerImages.java": _source(
        "c3bcd6b78ed2606ddc1e7a685774b9d0c2969c93502b6983d5f8352e27c29f50",
        1_220,
    ),
    "server/src/test/java/io/saksk/ti/support/Phase2PostgresContainers.java": _source(
        "c5ecf36dc5e943f9baa34b61be65bf73cf4502b1e8bdccc0a012a8db55c29ffe",
        1_698,
    ),
    (
        "server/src/test/java/io/saksk/ti/support/"
        "Phase4cUserCountsFaultInjectingDataSource.java"
    ): _source(
        "83f381e0766ebeb0c71aa3b8f3f024d9af1a0099776b2d8923082947d6116dae",
        20_783,
    ),
    "server/src/test/resources/db/phase3/030-auth-schema.sql": _source(
        "9f9546be5f32bd1babcb9a4711c2cc9b3641e4c22ff051738ba9d735a150c87e",
        934,
    ),
    "server/src/test/resources/db/phase4b/062-personal-bank-share-list-schema.sql": _source(
        "d0e51e7cd16d0275611a82c984a52538beb14b10b19c50925646dd48a4d1c29d",
        1_654,
    ),
    "server/src/test/resources/db/phase4b/065-personal-bank-usage-stats-schema.sql": _source(
        "90d94b6c90c09586908e3108626ddbace04a83b56ed2018a55709ccdc7a2f684",
        1_291,
    ),
    "server/src/test/resources/db/phase4b/067-personal-bank-user-counts-schema.sql": _source(
        "32367c8795654e0ae2f5e2f1d6d4e42fb70e354f745a7f06894e28ac4a45f934",
        2_951,
    ),
    (
        "server/src/test/resources/db/phase4c/"
        "071-personal-bank-user-counts-golden-target-seed.sql"
    ): _source(
        "5fbdc1da8e15072995baffba15b3a430b1ddd93e4788237a44bc3a5965e7556e",
        9_672,
    ),
    (
        "server/src/test/resources/db/phase4c/"
        "072-personal-bank-user-counts-typed-normalization-seed.sql"
    ): _source(
        "089b795d6e6a3efdb1af86641701bd1bf9d30e2c1a94c65a0a32865bdfca29c6",
        363,
    ),
    "tools/normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py": _source(
        "3ff33e3ef1ad3171ea2ca97f9b70fc49db1c3dd92d97a5d8c634497d78285acc",
        22_318,
    ),
    "tools/test_normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py": _source(
        "51b316b9370da51b3c4f93b601ffb600451494d2743c0f08fbe17335e8d8bdcd",
        10_366,
    ),
}

HISTORICAL_MANIFEST = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-target-execution-junit-manifest.json"
)
TYPED_MANIFEST = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-typed-normalization-junit-manifest.json"
)
WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
CURRENT_NODE_SOURCES = (
    CONTRACT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py",
    "tools/phase4c_http_typed_normalization_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py",
)

# The only third-hop transitions this node is allowed to expose.  The accepted
# hashes are the bytes in the immutable c38 checkpoint; successor hashes bind
# the current typed-normalization wiring.  These files deliberately remain
# outside ordinary ``load`` so a minimal Gitless evidence copy stays sufficient.
THIRD_HOP_SOURCES = {
    "README.md": {
        "accepted_git_blob_oid": "8f7c55c7d787fb6ba4067abd67e2bcd4906b24f5",
        "mode": "100644",
        "accepted_sha256": (
            "9008df17aa8eba4945fde525a304c4d891da20004f18ab86ceda485fffab2b57"
        ),
        "accepted_byte_count": 37_622,
        "successor_sha256": (
            "1700589a3031071c71dad21e019165c0cb635be3362f85f36a4f4ce7d42ca0ea"
        ),
        "successor_byte_count": 37_941,
    },
    "docs/refactor/05-progress.md": {
        "accepted_git_blob_oid": "ede2a034c0121042c4053c1e585e9762ae1f8049",
        "mode": "100644",
        "accepted_sha256": (
            "477d2dc0fce4946e511faa2c143fc76367ae6231a932ae204b6858ca5787e1bf"
        ),
        "accepted_byte_count": 101_162,
        "successor_sha256": (
            "f37547e858db034361c23c7c886bf291f1783b343e98cd95a0efc328370b449a"
        ),
        "successor_byte_count": 102_736,
    },
    "docs/refactor/phase4c/README.md": {
        "accepted_git_blob_oid": "2a29318d27773ff40c2b4d7d63fbc52c09fbadb0",
        "mode": "100644",
        "accepted_sha256": (
            "50f1ee46eddac681b49281c3b348e4017fe6893ec38051a5485317cd766c2f61"
        ),
        "accepted_byte_count": 15_524,
        "successor_sha256": (
            "fbdbf32d9a3c488c890ce5d71689e59eb9a7458989843a45433e247dca2f6d98"
        ),
        "successor_byte_count": 18_266,
    },
    "infra/phase2/README.md": {
        "accepted_git_blob_oid": "13dfe524febcdad3f0b7faedd8cd2c4b02d42e2a",
        "mode": "100644",
        "accepted_sha256": (
            "7ae3e8a5bb36920039649ffa8a2aef2bd9bb59782fa03f50e4174cee9063b56f"
        ),
        "accepted_byte_count": 6_786,
        "successor_sha256": (
            "30950043edcca47aa42543065ca0b6b08d5c4c4a4839f2034af2cdde47174622"
        ),
        "successor_byte_count": 6_850,
    },
    "infra/phase2/verify-static.sh": {
        "accepted_git_blob_oid": "eaa2f8c192de711747d55bffec1e81e1b57fcf2c",
        "mode": "100755",
        "accepted_sha256": (
            "92a3a1ee30ddbb2b5c854dbff7fac23da37e5804e0628211e85725ba4523d835"
        ),
        "accepted_byte_count": 13_955,
        "successor_sha256": (
            "78f6dd82e43d39f289b5962490aace65dba806581a16580903d32dbee4812752"
        ),
        "successor_byte_count": 14_323,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java"
    ): {
        "accepted_git_blob_oid": "67ad65a5d482128549df3b5d012e5314cd5cb173",
        "mode": "100644",
        "accepted_sha256": (
            "0042ca6deb05498b2d363c81843d7ec39e3f2cb6af2d43376b24b1d24b03940a"
        ),
        "accepted_byte_count": 54_058,
        "successor_sha256": (
            "b95ee58fd66698d129ee9562959d21ffc3a3e0c0b49339f21c379a8d0c356090"
        ),
        "successor_byte_count": 55_266,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java"
    ): {
        "accepted_git_blob_oid": "c275b712c210a21560bb2a91238ca4500eb4b907",
        "mode": "100644",
        "accepted_sha256": (
            "4824d1aa3ecb5208277066731b16efe33eadf2748348071f04e43c6e5887b520"
        ),
        "accepted_byte_count": 18_477,
        "successor_sha256": (
            "bd2b0c554a19fb561919298bba1c23a9f35435390ff3a069e3ec8e7ec5959e12"
        ),
        "successor_byte_count": 19_014,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java"
    ): {
        "accepted_git_blob_oid": "34312828552cd30ed62a4ec7b0e813aed2880d73",
        "mode": "100644",
        "accepted_sha256": (
            "a8e81f0758928eb69c527a9d6bbcf00517160221ea7b1aca4b901b7d5a26cf48"
        ),
        "accepted_byte_count": 16_704,
        "successor_sha256": (
            "efa8bd66c5df68bdd9617415b156450ba2ae12dafb2c284df75dcc44e8edcd02"
        ),
        "successor_byte_count": 17_241,
    },
    (
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py"
    ): {
        "accepted_git_blob_oid": "70951075267e29b9cb354f7f03888b23adc504c9",
        "mode": "100644",
        "accepted_sha256": (
            "4f97c2fcdfd36ac943fce4a1e948d99bf52cb8418519602141d40614ce78af44"
        ),
        "accepted_byte_count": 37_163,
        "successor_sha256": (
            "342990a999fa0873b6c33a9a2f735f88fb7a453ee27d94832b81b14b9c8fa2a1"
        ),
        "successor_byte_count": 39_048,
    },
    "tools/phase2_wormhole_successor_acceptance.py": {
        "accepted_git_blob_oid": "d6de042c4c1f38aceb701045fce46777f5c9a83f",
        "mode": "100644",
        "accepted_sha256": (
            "868d5cebbcc695136083ac892e572483ffc40829f487cb8d9d2b407c2fc763d1"
        ),
        "accepted_byte_count": 24_199,
        "successor_sha256": (
            "9e11c33623a10415b28a5aadf1cf0855ef4bdd1dc9a3d81eeeff41e76a98f735"
        ),
        "successor_byte_count": 24_939,
    },
    (
        "tools/phase4c_http_target_execution_post_push_anchor_"
        "successor_acceptance.py"
    ): {
        "accepted_git_blob_oid": "2a5ec91d4709d11709571805786a8c641dfeba04",
        "mode": "100644",
        "accepted_sha256": (
            "fe074402bcb58cfd3a681769050dd80174c584a082b462047d9684950b60e363"
        ),
        "accepted_byte_count": 35_451,
        "successor_sha256": (
            "c1abc55435cd3c3e1c62a72412dc5b62b300fb9f76b8ebc2b6c5482fe726403d"
        ),
        "successor_byte_count": 37_853,
    },
    "tools/test_phase2_wormhole_successor_acceptance.py": {
        "accepted_git_blob_oid": "eff3ddd92670bb00f094dcc80c96f4d6ec458edd",
        "mode": "100644",
        "accepted_sha256": (
            "691198f36292c460b6bb516e9deb4e4efe064ae12fe60efb85280a52753cb5cb"
        ),
        "accepted_byte_count": 36_539,
        "successor_sha256": (
            "b273ae2f450238b709d409e07e6ab7c7f39fbe71d162563a18350f62adaca7ab"
        ),
        "successor_byte_count": 40_416,
    },
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py"
    ): {
        "accepted_git_blob_oid": "368af3c122f52e35b66525f5e01362acbc956c20",
        "mode": "100644",
        "accepted_sha256": (
            "f51784ae1831b54e630150af2af12d3692397f3191d74314f3f0816b847cdfae"
        ),
        "accepted_byte_count": 18_683,
        "successor_sha256": (
            "b2f0feefd23f88c357c1bb6e72f417a4de212465e79577930a7c671c3138e47c"
        ),
        "successor_byte_count": 19_187,
    },
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py"
    ): {
        "accepted_git_blob_oid": "72c87d9ab5c6555ee7ae52883def1916ece137ef",
        "mode": "100644",
        "accepted_sha256": (
            "d99d36f8b17e5072dcd130c4570ac074096a3c9ee2b9bf4f0f49fd2b1cd907e6"
        ),
        "accepted_byte_count": 11_724,
        "successor_sha256": (
            "9bb6c53fd9c833ff2ed9d2bdcf09af80ae436a9bcfc4c2ee2d54c03f2274acca"
        ),
        "successor_byte_count": 12_084,
    },
}

TOP_LEVEL_KEYS = {
    "acceptance",
    "authorization",
    "captured_at",
    "contract_id",
    "current_node_trust_boundary",
    "disposition_ledger",
    "document_payload_sha256",
    "junit_execution",
    "malformed_typed_rejection",
    "predecessor",
    "predecessor_external_git_anchor",
    "production_surface",
    "schema_version",
    "scope",
    "source_contracts",
    "status",
    "typed_normalization",
    "worm_evidence",
}
EXPECTED_SUMMARY = {
    "logical_disposition_count": 59,
    "http_execution_count": 58,
    "business_jdbc_reached_http_count": 50,
    "pre_business_jdbc_termination_http_count": 8,
    "non_fault_http_execution_count": 47,
    "postgres_abort_http_execution_count": 11,
    "typed_rejection_count": 1,
    "api_alias_http_execution_count": 44,
    "web_alias_http_execution_count": 14,
    "http_status_counts": {
        "200": 35,
        "302": 5,
        "401": 3,
        "403": 10,
        "500": 5,
    },
    "execution_disposition_counts": {
        "EXECUTED_FULL_CONTEXT_HTTP": 47,
        "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT": 11,
        "EXECUTED_TYPED_REJECTION": 1,
    },
    "bound_only_case_count": 0,
    "mocked_application_result_case_count": 0,
}
EXPECTED_RUNTIME_SCOPE = {
    "typed_cast_compatibility": {
        "postgresql_versions": ["16.14", "18.4"],
        "session_time_zones": ["UTC", "America/Los_Angeles"],
        "positive_offset_input": "2026-07-17T13:00:00+08:00",
        "negative_offset_input": "2026-07-17T13:00:00-05:00",
        "canonical_local_datetime": "2026-07-17T13:00:00",
        "cross_version_equal": True,
        "session_timezone_independent": True,
    },
    "full_filter_http": {
        "postgresql_version": "18.4",
        "redis_version": "7.4.7",
        "fixture_origin": (
            "java_string_bind_explicit_cast_insert_before_request_trace"
        ),
        "fixture_sql_literal_seeded": False,
        "fixture_dml_before_request_trace": True,
    },
}
NEXT_GATE = (
    "pg16_pg18_termination_identity_sql_nine_table_fingerprints_then_real_"
    "tomcat_complete_response_headers_then_same_service_redis_refusal_"
    "interruption_and_recovery_before_route_migration"
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _payload_sha256(document: dict[str, Any]) -> str:
    return _sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def _fixed_regular_file(root: Path, relative: str) -> Path:
    try:
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AssertionError("typed-normalization Ti-Java root is unavailable") from error
    if not resolved_root.is_dir():
        raise AssertionError("typed-normalization Ti-Java root is not a directory")
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        raise AssertionError(
            f"fixed typed-normalization path escapes Ti-Java: {relative}"
        )
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"fixed typed-normalization path contains symlink: {relative}"
            )
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as error:
        raise AssertionError(
            f"fixed typed-normalization path escaped or vanished: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(
            f"fixed typed-normalization path is not a regular file: {relative}"
        )
    return resolved


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    try:
        document = json.loads(
            _fixed_regular_file(root, relative).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"cannot read fixed JSON: {relative}") from error
    if not isinstance(document, dict):
        raise AssertionError(f"fixed JSON is not an object: {relative}")
    return document


def _expected_source_contracts() -> dict[str, dict[str, Any]]:
    return {
        relative: {"path": relative, **descriptor}
        for relative, descriptor in sorted(LOCAL_SOURCES.items())
    }


def _validate_local_inputs(root: Path) -> None:
    for relative, descriptor in LOCAL_SOURCES.items():
        payload = _fixed_regular_file(root, relative).read_bytes()
        if (
            len(payload) != descriptor["byte_count"]
            or _sha256_bytes(payload) != descriptor["sha256"]
        ):
            raise AssertionError(f"typed-normalization source drifted: {relative}")

    predecessor_raw = _fixed_regular_file(root, PREDECESSOR_RELATIVE).read_bytes()
    predecessor = _read_json(root, PREDECESSOR_RELATIVE)
    if (
        len(predecessor_raw) != PREDECESSOR_BYTE_COUNT
        or _sha256_bytes(predecessor_raw) != PREDECESSOR_SHA256
        or predecessor.get("contract_id") != PREDECESSOR_ID
        or predecessor.get("status") != PREDECESSOR_STATUS
        or predecessor.get("scope") != PREDECESSOR_SCOPE
        or predecessor.get("captured_at") != PREDECESSOR_CAPTURED_AT
        or predecessor.get("document_payload_sha256")
        != PREDECESSOR_PAYLOAD_SHA256
        or _payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256
        or predecessor.get("post_push_source_anchor", {}).get(
            "current_anchor_source_bytes_external_git_anchor_complete"
        ) is not False
        or predecessor.get("authorization", {}).get("route_migration_eligible")
        is not False
    ):
        raise AssertionError("typed-normalization predecessor boundary drifted")

    historical = _read_json(root, HISTORICAL_MANIFEST)
    if (
        historical.get("document_payload_sha256")
        != "9f53234730888c5e3bcd682390093331daca61814c1111c195ea3def4fbe543c"
        or _payload_sha256(historical)
        != historical.get("document_payload_sha256")
        or len(historical.get("result", {}).get("leaves", [])) != 60
    ):
        raise AssertionError("historical JUnit manifest boundary drifted")

    typed = _read_json(root, TYPED_MANIFEST)
    if (
        typed.get("document_payload_sha256")
        != "08bdcc19ee0f3607d4e367a135d9a6544a5a9b5e5e999a2738180bc3258c8236"
        or _payload_sha256(typed) != typed.get("document_payload_sha256")
        or typed.get("result", {}).get("proof_payload_sha256")
        != "8ea42f371664c6a664b0cd8b408c292a8a2a57524215a718a71c634a0bc93047"
        or typed.get("raw_report", {}).get("sha256")
        != "e1d5caebd6dfc7c792c8e4b4af337081246f718da5d1c4c82e072f46d6a1603b"
        or typed.get("raw_report", {}).get("byte_count") != 51_169
        or typed.get("result", {}).get("runtime_scope") != EXPECTED_RUNTIME_SCOPE
    ):
        raise AssertionError("typed-normalization JUnit manifest boundary drifted")

    worm = _read_json(root, WORM_RELATIVE)
    if (
        worm.get("java", {}).get("buildContextSha256")
        != "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
        or worm.get("java", {}).get("dockerfileSha256")
        != "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
        or worm.get("restore", {}).get("canonicalSchemaDumpSha256")
        != "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
        or worm.get("flywayBaselineCreated") is not False
    ):
        raise AssertionError("typed-normalization WORM boundary drifted")


def _validate_git_anchor(document: dict[str, Any]) -> None:
    expected = {
        "object_format": GIT_OBJECT_FORMAT,
        "commit_oid": GIT_COMMIT_OID,
        "root_tree_oid": GIT_ROOT_TREE_OID,
        "parent_oid": GIT_PARENT_OID,
        "ti_java_tree_oid": GIT_TI_JAVA_TREE_OID,
        "authored_at": GIT_AUTHORED_AT,
        "committed_at": GIT_AUTHORED_AT,
        "subject": GIT_SUBJECT,
        "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
        "exact_changed_paths": list(GIT_PATHS),
        "changed_path_count": 18,
        "added_path_count": 6,
        "modified_path_count": 12,
        "deleted_path_count": 0,
        "non_ti_java_path_count": 0,
        "inserted_line_count": 4_544,
        "deleted_line_count": 40,
        "anchored_source_count": 6,
        "anchored_source_total_bytes": 196_595,
        "anchored_sources": ANCHORED_PREDECESSOR_SOURCES,
        "predecessor_current_anchor_sources_external_git_anchor_complete": True,
        "mutable_ref_is_validation_authority": False,
        "ordinary_contract_load_requires_git": False,
        "explicit_git_replay_supported": True,
    }
    if document.get("predecessor_external_git_anchor") != expected:
        raise AssertionError("typed-normalization predecessor Git anchor drifted")


def _validate_ledger(document: dict[str, Any]) -> None:
    ledger = document.get("disposition_ledger")
    if not isinstance(ledger, dict):
        raise AssertionError("typed-normalization ledger is not an object")
    rows = ledger.get("rows")
    if not isinstance(rows, list) or len(rows) != 59:
        raise AssertionError("typed-normalization ledger must contain 59 rows")
    if {
        key: value for key, value in ledger.items() if key != "rows"
    } != {
        "ordered_by": "canonical_case_ordinal",
        "ordered_case_ids_sha256": (
            "d8c9aa1c8fdcfd833f2d7bbba3e21adcc3e696954b8756ace69405428bbdfad8"
        ),
        "ledger_payload_sha256": (
            "332953b40ac71157e20ff322a37e8abf8fc308b12d5997bd0343b5674f0c0654"
        ),
        "case_id_set_equal_to_historical_predecessor": True,
        "single_effective_override_case_id": (
            "access-shared-aware-expiry-type-error"
        ),
        "summary": EXPECTED_SUMMARY,
    }:
        raise AssertionError("typed-normalization ledger metadata drifted")
    if _sha256_json(rows) != ledger["ledger_payload_sha256"]:
        raise AssertionError("typed-normalization ledger payload drifted")

    required_row_keys = {
        "alias",
        "business_jdbc_reached",
        "canonical_case_ordinal",
        "case_id",
        "execution_disposition",
        "execution_ordinal",
        "http_execution",
        "proof",
        "route_id",
        "target_status",
    }
    if any(not isinstance(row, dict) or set(row) != required_row_keys for row in rows):
        raise AssertionError("typed-normalization ledger row shape drifted")
    if [row["canonical_case_ordinal"] for row in rows] != list(range(1, 60)):
        raise AssertionError("typed-normalization canonical row order drifted")
    case_ids = [row["case_id"] for row in rows]
    if len(set(case_ids)) != 59 or _sha256_json(case_ids) != ledger[
        "ordered_case_ids_sha256"
    ]:
        raise AssertionError("typed-normalization case-id set/order drifted")

    http_rows = [row for row in rows if row["http_execution"] is True]
    typed_rows = [
        row
        for row in rows
        if row["execution_disposition"] == "EXECUTED_TYPED_REJECTION"
    ]
    disposition_counts = Counter(row["execution_disposition"] for row in rows)
    status_counts = Counter(str(row["target_status"]) for row in http_rows)
    alias_counts = Counter(row["alias"] for row in http_rows)
    business_count = sum(row["business_jdbc_reached"] is True for row in http_rows)
    if (
        len(http_rows) != 58
        or len(typed_rows) != 1
        or disposition_counts
        != Counter({
            "EXECUTED_FULL_CONTEXT_HTTP": 47,
            "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT": 11,
            "EXECUTED_TYPED_REJECTION": 1,
        })
        or status_counts
        != Counter({"200": 35, "302": 5, "401": 3, "403": 10, "500": 5})
        or alias_counts != Counter({"api": 44, "web": 14})
        or business_count != 50
    ):
        raise AssertionError("typed-normalization 58 HTTP plus one rejection drifted")

    typed_row = typed_rows[0]
    if typed_row != {
        "alias": "api",
        "business_jdbc_reached": False,
        "canonical_case_ordinal": 37,
        "case_id": "access-shared-malformed-expiry-value-error",
        "execution_disposition": "EXECUTED_TYPED_REJECTION",
        "execution_ordinal": 58,
        "http_execution": False,
        "proof": {
            "manifest": HISTORICAL_MANIFEST,
            "suite_leaf_ordinal": 59,
            "xml_name": (
                "rejectsTheMalformedExpiryTypedDispositionWithoutPersistingARow"
            ),
        },
        "route_id": "6858f6fa506f",
        "target_status": None,
    }:
        raise AssertionError("malformed typed-rejection ledger row drifted")

    aware_rows = [
        row
        for row in rows
        if row["case_id"] == "access-shared-aware-expiry-type-error"
    ]
    if aware_rows != [{
        "alias": "api",
        "business_jdbc_reached": True,
        "canonical_case_ordinal": 38,
        "case_id": "access-shared-aware-expiry-type-error",
        "execution_disposition": "EXECUTED_FULL_CONTEXT_HTTP",
        "execution_ordinal": 59,
        "http_execution": True,
        "proof": {
            "manifest": TYPED_MANIFEST,
            "replaces_historical_leaf_ordinal": 60,
            "suite_leaf_ordinal": 1,
            "xml_name": "executesAwareExpiryAsARealFullFilterChainHttpRead",
        },
        "route_id": "6858f6fa506f",
        "target_status": 200,
    }]:
        raise AssertionError("aware-expiry replacement ledger row drifted")

    historical_ordinals = {
        row["proof"].get("suite_leaf_ordinal")
        for row in rows
        if row["proof"].get("manifest") == HISTORICAL_MANIFEST
    }
    typed_proofs = [
        row["proof"]
        for row in rows
        if row["proof"].get("manifest") == TYPED_MANIFEST
    ]
    if historical_ordinals != set(range(2, 60)) or len(typed_proofs) != 1:
        raise AssertionError("typed-normalization selected proof leaves drifted")


def _validate_semantic_sections(document: dict[str, Any]) -> None:
    expected_junit = {
        "historical_manifest": HISTORICAL_MANIFEST,
        "typed_normalization_manifest": TYPED_MANIFEST,
        "historical_physical_leaf_count": 60,
        "new_physical_leaf_count": 1,
        "aggregate_physical_leaf_count": 61,
        "selected_effective_proof_leaf_count": 60,
        "logical_disposition_leaf_count": 59,
        "supplementary_authentication_leaf_count": 1,
        "superseded_historical_representation_leaf_count": 1,
        "replacement_leaf_count": 1,
        "superseded_leaf_double_counted": False,
        "new_raw_report_sha256": (
            "e1d5caebd6dfc7c792c8e4b4af337081246f718da5d1c4c82e072f46d6a1603b"
        ),
        "new_raw_report_byte_count": 51_169,
        "new_manifest_document_payload_sha256": (
            "08bdcc19ee0f3607d4e367a135d9a6544a5a9b5e5e999a2738180bc3258c8236"
        ),
        "new_manifest_proof_payload_sha256": (
            "8ea42f371664c6a664b0cd8b408c292a8a2a57524215a718a71c634a0bc93047"
        ),
        "failed_error_skipped_or_flaky_leaf_count": 0,
    }
    if document.get("junit_execution") != expected_junit:
        raise AssertionError("typed-normalization 61-to-60 JUnit accounting drifted")

    expected_typed = {
        "difference_id": "P4C-LEARNING-013",
        "difference_document": (
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-typed-normalization-approved-difference.md"
        ),
        "behavior_difference_decision": (
            "documented_local_adr_pending_current_node_external_git_anchor"
        ),
        "case_id": "access-shared-aware-expiry-type-error",
        "source_status": 500,
        "historical_disposition": "EXECUTED_TYPED_COLLAPSE",
        "effective_disposition": "EXECUTED_FULL_CONTEXT_HTTP",
        "target_status": 200,
        "business_jdbc_reached": True,
        "input_kind": "string_bind_explicit_cast",
        "input": "2026-07-17T13:00:00+08:00",
        "negative_offset_input": "2026-07-17T13:00:00-05:00",
        "postgresql_type": "timestamp without time zone",
        "canonical_local_datetime": "2026-07-17T13:00:00",
        "offset_provenance_erased": True,
        "cast_compatibility_versions": ["16.14", "18.4"],
        "cast_session_time_zones": ["UTC", "America/Los_Angeles"],
        "cross_version_equal": True,
        "session_timezone_independent": True,
        "full_filter_http_version": "18.4",
        "http_fixture_origin": (
            "java_string_bind_explicit_cast_insert_before_request_trace"
        ),
        "http_fixture_sql_literal_seeded": False,
        "fixture_share_id": 99_661,
        "fixture_share_record_id": 99_681,
        "target_data": {
            "total": 9,
            "favorites": 0,
            "mistakes": 0,
            "types": [
                "判断题", "简答题", "填空题", "多选题",
                "选择题", "选择题", "简答题",
            ],
            "shuffle_options_available": False,
        },
        "proof_scope": (
            "Java String CAST compatibility on PostgreSQL 16.14 and 18.4 "
            "across UTC and America/Los_Angeles; full production filter "
            "chain MockMvc HTTP on PostgreSQL 18.4 and Redis 7.4.7; not "
            "random-port Tomcat network evidence"
        ),
        "request_interval_assertions": {
            "authority_users_sql_count": 1,
            "bank_access_sql_count": 5,
            "share_access_sql_count": 5,
            "favorite_membership_sql_count": 1,
            "mistake_membership_sql_count": 1,
            "question_summary_sql_count": 2,
            "tag_membership_sql_count": 0,
            "write_dml_count": 0,
            "users_last_active_write_dml_count": 0,
            "schema_mutation_count": 0,
            "nine_table_fingerprint_unchanged": True,
            "hmac_route_rate_key_count": 3,
            "each_route_rate_key_value": 1,
        },
        "fixture_and_session_exchange_occur_before_request_trace": True,
        "whole_test_lifecycle_zero_dml_claimed": False,
    }
    if document.get("typed_normalization") != expected_typed:
        raise AssertionError("aware-expiry typed-normalization semantics drifted")

    if document.get("malformed_typed_rejection") != {
        "case_id": "access-shared-malformed-expiry-value-error",
        "execution_disposition": "EXECUTED_TYPED_REJECTION",
        "http_execution": False,
        "target_status": None,
        "sqlstate": "22007",
        "persisted_bank_share_row_count": 0,
        "no_row_http_forbidden_from_claiming_malformed_semantics": True,
    }:
        raise AssertionError("malformed typed-rejection semantics drifted")

    if document.get("worm_evidence") != {
        "source": WORM_RELATIVE,
        "sha256": LOCAL_SOURCES[WORM_RELATIVE]["sha256"],
        "fixed_chain_node_count": 5,
        "predecessor_sha256": (
            "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"
        ),
        "java_build_context_sha256": (
            "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
        ),
        "dockerfile_sha256": LOCAL_SOURCES["server/Dockerfile"]["sha256"],
        "canonical_schema_dump_sha256": (
            "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
        ),
        "new_worm_report_created": False,
        "reused": True,
    }:
        raise AssertionError("typed-normalization WORM contract drifted")


def _validate_closed_boundaries(document: dict[str, Any]) -> None:
    if document.get("production_surface") != {
        "production_source_changed": False,
        "production_build_context_changed": False,
        "production_schema_or_index_changed": False,
        "operator_changed": False,
        "client_changed": False,
        "gateway_or_proxy_changed": False,
        "openapi_sha256": LOCAL_SOURCES[
            "openapi/phase4c-personal-bank-user-counts.openapi.json"
        ]["sha256"],
        "route_delta_sha256": LOCAL_SOURCES[
            "docs/refactor/phase4c/route-parity-delta.csv"
        ]["sha256"],
    }:
        raise AssertionError("typed-normalization production surface drifted")

    expected_authorization = {
        "typed_execution_normalization_complete": True,
        "behavior_difference_adr_documented": True,
        "current_node_sources_external_git_anchor_complete": False,
        "typed_parity_review_complete": False,
        "pg16_pg18_termination_fingerprints_complete": False,
        "real_tomcat_complete_response_header_matrix_complete": False,
        "same_service_redis_outage_and_recovery_complete": False,
        "full_target_parity_closed": False,
        "route_migration_eligible": False,
        "two_legacy_get_routes_migrated": False,
        "derived_head_and_options_count_as_migrated": False,
        "production_cutover": False,
    }
    if document.get("authorization") != expected_authorization:
        raise AssertionError("typed-normalization authorization overclaim")

    expected_acceptance = {
        **EXPECTED_SUMMARY,
        "junit_physical_leaf_count": 61,
        "junit_selected_effective_leaf_count": 60,
        "implemented_pending_get_count": 2,
        "migrated_operation_count": 11,
        "pending_operation_count": 600,
        "production_cutover_operation_count": 0,
        "route_migration_eligible": False,
        "typed_parity_review_complete": False,
        "full_target_parity_closed": False,
        "production_cutover": False,
        "next_gate": NEXT_GATE,
    }
    if document.get("acceptance") != expected_acceptance:
        raise AssertionError("typed-normalization acceptance boundary drifted")

    expected_trust = {
        "source_paths": sorted(CURRENT_NODE_SOURCES),
        "source_path_allowlist_exact": True,
        "source_count": 6,
        "sources_excluded_from_self_authority": True,
        "source_bytes_external_git_anchor_complete": False,
        "post_push_external_anchor_required": True,
        "dynamic_source_discovery_forbidden": True,
        "independently_signed_provenance": False,
    }
    if document.get("current_node_trust_boundary") != expected_trust:
        raise AssertionError("typed-normalization current-node trust boundary drifted")


def validate_contract(document: dict[str, Any], ti_java_root: Path) -> None:
    if not isinstance(document, dict) or set(document) != TOP_LEVEL_KEYS:
        raise AssertionError("typed-normalization contract top-level shape drifted")
    if {
        "contract_id": document.get("contract_id"),
        "schema_version": document.get("schema_version"),
        "captured_at": document.get("captured_at"),
        "status": document.get("status"),
        "scope": document.get("scope"),
    } != {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CONTRACT_CAPTURED_AT,
        "status": CONTRACT_STATUS,
        "scope": CONTRACT_SCOPE,
    }:
        raise AssertionError("typed-normalization contract identity drifted")

    if document.get("predecessor") != {
        "source": PREDECESSOR_RELATIVE,
        "sha256": PREDECESSOR_SHA256,
        "byte_count": PREDECESSOR_BYTE_COUNT,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "scope": PREDECESSOR_SCOPE,
        "captured_at": PREDECESSOR_CAPTURED_AT,
        "immutable": True,
    }:
        raise AssertionError("typed-normalization predecessor descriptor drifted")
    if document.get("source_contracts") != _expected_source_contracts():
        raise AssertionError("typed-normalization source allowlist drifted")

    _validate_git_anchor(document)
    _validate_ledger(document)
    _validate_semantic_sections(document)
    _validate_closed_boundaries(document)
    payload_sha256 = _payload_sha256(document)
    if (
        document.get("document_payload_sha256") != payload_sha256
        or payload_sha256 != CONTRACT_PAYLOAD_SHA256
    ):
        raise AssertionError("typed-normalization fixed payload SHA-256 drifted")
    _validate_local_inputs(ti_java_root.resolve(strict=True))


def load(
    ti_java_root: Path,
    *,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    path = _validate_contract_physical_bytes(root)
    document = _read_json(root, CONTRACT_RELATIVE)
    validate_contract(document, root)
    if repository_root is not None:
        validate_git_checkpoint(repository_root)
    return document


def _validate_contract_physical_bytes(root: Path) -> Path:
    """Bind the exact canonical contract without recursively validating its inputs."""

    path = _fixed_regular_file(root, CONTRACT_RELATIVE)
    payload = path.read_bytes()
    if (
        len(payload) != CONTRACT_BYTE_COUNT
        or _sha256_bytes(payload) != CONTRACT_SHA256
    ):
        raise AssertionError("typed-normalization contract physical bytes drifted")
    return path


def accepted_sha256(relative: str) -> str | None:
    """Return the c38 hash for one of the nine fixed third-hop paths."""

    descriptor = THIRD_HOP_SOURCES.get(relative)
    return None if descriptor is None else descriptor["accepted_sha256"]


def _load_typed_normalization_anchor_successor_acceptance() -> object:
    """Lazily import the sole fixed successor for post-b086 bytes."""

    qualified_name = (
        "tools.phase4c_http_typed_normalization_anchor_successor_acceptance"
    )
    direct_name = "phase4c_http_typed_normalization_anchor_successor_acceptance"
    try:
        return importlib.import_module(qualified_name)
    except ModuleNotFoundError as error:
        if error.name not in {"tools", qualified_name}:
            raise
    try:
        return importlib.import_module(direct_name)
    except ModuleNotFoundError as error:
        if error.name != direct_name:
            raise
        raise AssertionError(
            "fixed HTTP typed-normalization anchor successor is required"
        ) from error


def _current_or_typed_normalization_anchor_successor_sha256(
        root: Path,
        relative: str,
        declared_sha256: str,
        physical_sha256: str,
) -> str:
    """Accept b086 bytes directly or one exact code-fixed anchor successor."""

    if declared_sha256 == physical_sha256:
        return physical_sha256
    anchor = _load_typed_normalization_anchor_successor_acceptance()
    accepted_lookup = getattr(anchor, "accepted_sha256", None)
    successor_lookup = getattr(anchor, "successor_sha256", None)
    if not callable(accepted_lookup) or not callable(successor_lookup):
        raise AssertionError("typed-normalization anchor successor API is incomplete")
    if accepted_lookup(relative) != declared_sha256:
        raise AssertionError(
            "typed-normalization anchor does not accept historical source: "
            f"{relative}"
        )
    if successor_lookup(root, relative) != physical_sha256:
        raise AssertionError(
            "typed-normalization anchor does not bind current source: "
            f"{relative}"
        )
    return physical_sha256


def successor_sha256(ti_java_root: Path, relative: str) -> str | None:
    """Bind the canonical contract and one current third-hop path.

    Full evidence validation remains the responsibility of :func:`load`, which
    Phase 2 invokes once as a fixed terminal acceptance.  Re-running that full
    validation for each historical path made one top-level gate recursively
    parse the 1.2 MiB golden hundreds of times.  This lookup keeps no cache: it
    re-hashes both the canonical contract and requested physical path on every
    call, so byte tampering remains visible without quadratic successor walks.
    """

    descriptor = THIRD_HOP_SOURCES.get(relative)
    if descriptor is None:
        return None
    root = ti_java_root.resolve(strict=True)
    _validate_contract_physical_bytes(root)
    payload = _fixed_regular_file(root, relative).read_bytes()
    physical = _sha256_bytes(payload)
    transitioned = _current_or_typed_normalization_anchor_successor_sha256(
        root,
        relative,
        descriptor["successor_sha256"],
        physical,
    )
    if physical == descriptor["successor_sha256"] and (
        len(payload) != descriptor["successor_byte_count"]
    ):
        raise AssertionError(
            f"typed-normalization third-hop successor drifted: {relative}"
        )
    return transitioned


def _run_read_only_git(repository_root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    try:
        completed = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-C",
                str(repository_root),
                *arguments,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AssertionError(f"read-only Git command failed: {arguments[0]}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1000:].strip()
        raise AssertionError(f"read-only Git command rejected: {detail}")
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_read_only_git(repository_root, *arguments).decode("utf-8").strip()


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    top = Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root:
        raise AssertionError("typed-normalization repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("typed-normalization Git object format drifted")
    if _git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit":
        raise AssertionError("typed-normalization predecessor anchor is not a commit")
    facts = _git_text(
        root,
        "show",
        "-s",
        "--format=%T%n%P%n%aI%n%cI%n%s",
        GIT_COMMIT_OID,
    ).splitlines()
    if facts != [
        GIT_ROOT_TREE_OID,
        GIT_PARENT_OID,
        GIT_AUTHORED_AT,
        GIT_AUTHORED_AT,
        GIT_SUBJECT,
    ]:
        raise AssertionError("typed-normalization Git commit identity drifted")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java") != (
        GIT_TI_JAVA_TREE_OID
    ):
        raise AssertionError("typed-normalization Ti-Java subtree drifted")

    raw_delta = _run_read_only_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--abbrev=40",
        "-r",
        GIT_COMMIT_OID,
    )
    if _sha256_bytes(raw_delta) != GIT_RAW_DELTA_SHA256:
        raise AssertionError("typed-normalization exact Git delta drifted")
    lines = raw_delta.decode("utf-8").splitlines()
    paths = tuple(line.split("\t", 1)[1] for line in lines)
    statuses = Counter(line.split("\t", 1)[0].rsplit(" ", 1)[-1] for line in lines)
    if paths != GIT_PATHS or statuses != Counter({"A": 6, "M": 12}):
        raise AssertionError("typed-normalization changed-path allowlist drifted")

    for descriptor in ANCHORED_PREDECESSOR_SOURCES.values():
        repository_path = descriptor["repository_path"]
        entry = _git_text(root, "ls-tree", GIT_COMMIT_OID, "--", repository_path)
        parts = entry.split(None, 3)
        if len(parts) != 4 or parts[:3] != [
            descriptor["mode"],
            "blob",
            descriptor["git_blob_oid"],
        ]:
            raise AssertionError(f"anchored tree entry drifted: {repository_path}")
        payload = _run_read_only_git(
            root, "cat-file", "blob", descriptor["git_blob_oid"]
        )
        if (
            len(payload) != descriptor["byte_count"]
            or _sha256_bytes(payload) != descriptor["sha256"]
        ):
            raise AssertionError(f"anchored source bytes drifted: {repository_path}")

    for relative, descriptor in THIRD_HOP_SOURCES.items():
        repository_path = f"Ti-Java/{relative}"
        entry = _git_text(root, "ls-tree", GIT_COMMIT_OID, "--", repository_path)
        parts = entry.split(None, 3)
        if len(parts) != 4 or parts[:3] != [
            descriptor["mode"],
            "blob",
            descriptor["accepted_git_blob_oid"],
        ]:
            raise AssertionError(
                f"third-hop accepted tree entry drifted: {repository_path}"
            )
        payload = _run_read_only_git(
            root, "cat-file", "blob", descriptor["accepted_git_blob_oid"]
        )
        if (
            len(payload) != descriptor["accepted_byte_count"]
            or _sha256_bytes(payload) != descriptor["accepted_sha256"]
        ):
            raise AssertionError(
                f"third-hop accepted bytes drifted: {repository_path}"
            )
