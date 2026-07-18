#!/usr/bin/env python3
"""Build the fixed external Git anchor for Phase 4C typed normalization.

Ordinary construction is Gitless and validates only explicit regular files
below Ti-Java.  Optional replay fixes the immutable b0861d6 commit, its parent
and trees, the exact 26-path delta, and every committed blob.  The six sources
excluded from the predecessor's self-authority are thereby externally anchored;
this node's own six control sources remain explicitly excluded.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-anchor-contract.json"
)

CONTRACT_ID = (
    "ti.phase4c.personal-bank-user-counts-http-typed-normalization-anchor-contract"
)
CONTRACT_STATUS = (
    "typed_normalization_checkpoint_externally_anchored_routes_pending"
)
CONTRACT_SCOPE = (
    "phase4c-personal-bank-user-counts-http-typed-normalization-external-anchor"
)
CAPTURED_AT = "2026-07-18T18:18:23+08:00"
NEXT_GATE = (
    "pg16_pg18_termination_identity_sql_nine_table_fingerprints_then_real_"
    "tomcat_complete_response_headers_then_same_service_redis_refusal_"
    "interruption_and_recovery_before_route_migration"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-user-counts-http-typed-normalization-contract"
)
PREDECESSOR_STATUS = (
    "typed_normalization_executed_external_anchor_pending_routes_pending"
)
PREDECESSOR_SCOPE = "phase4c-personal-bank-user-counts-http-typed-normalization"
PREDECESSOR_CAPTURED_AT = "2026-07-18T15:28:17+08:00"
PREDECESSOR_SHA256 = (
    "ff1a751e1576916618422e0775c916e1d3b20122ffc141a04512119a6b5e99cd"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "eeb2b6dd9be091950867cfe8040c486b867179c49f0a0861c700864ec773eb99"
)
PREDECESSOR_BYTE_COUNT = 59_299

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "b0861d61438f649ed48d5d5e6806e02c804fa2e4"
GIT_ROOT_TREE_OID = "9d295380b565307dc5ebe0a5b9bf3d8589452dbf"
GIT_PARENT_OID = "c38defa703b358a280122a09019031c040c58ea7"
TI_JAVA_TREE_OID = "ff845fbf8b7e3b7a4823ebb00bf8dcb164fde019"
GIT_AUTHORED_AT = "2026-07-18T18:18:23+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "test(java): normalize user counts typed execution"
GIT_CAPTURE_REF = "origin/main"
GIT_RAW_DELTA_SHA256 = (
    "175dd8deb2cddb69e4bb6d6d985d312e041055699177d1054a8bb5ebef4f27c0"
)
ZERO_SHA256 = "0" * 64

TYPED_MANIFEST_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-typed-normalization-junit-manifest.json"
)
TYPED_MANIFEST_SHA256 = (
    "b6c619ee1ed4be44fd68903c2449188fd6a65ee39b7c855b1796c901d3a0268c"
)
TYPED_MANIFEST_PAYLOAD_SHA256 = (
    "08bdcc19ee0f3607d4e367a135d9a6544a5a9b5e5e999a2738180bc3258c8236"
)
TYPED_MANIFEST_PROOF_PAYLOAD_SHA256 = (
    "8ea42f371664c6a664b0cd8b408c292a8a2a57524215a718a71c634a0bc93047"
)
TYPED_RAW_REPORT_SHA256 = (
    "e1d5caebd6dfc7c792c8e4b4af337081246f718da5d1c4c82e072f46d6a1603b"
)
TYPED_RAW_REPORT_BYTE_COUNT = 51_169

WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
WORM_SHA256 = (
    "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39"
)
WORM_PREDECESSOR_SHA256 = (
    "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"
)
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
JAVA_BUILD_CONTEXT_SHA256 = (
    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
)
CANONICAL_SCHEMA_DUMP_SHA256 = (
    "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
)

_CHECKPOINT_LIST = json.loads(r'''[{"byte_count":37941,"change_type":"M","git_blob_oid":"73b4c3a334955ddf5684f8ad40cfeea563149394","mode":"100644","object_type":"blob","previous_git_blob_oid":"8f7c55c7d787fb6ba4067abd67e2bcd4906b24f5","previous_mode":"100644","repository_path":"Ti-Java/README.md","sha256":"1700589a3031071c71dad21e019165c0cb635be3362f85f36a4f4ce7d42ca0ea","ti_java_relative_path":"README.md"},{"byte_count":102736,"change_type":"M","git_blob_oid":"31c5619b46370ed0dc9a1b7e1f1514598e538d5b","mode":"100644","object_type":"blob","previous_git_blob_oid":"ede2a034c0121042c4053c1e585e9762ae1f8049","previous_mode":"100644","repository_path":"Ti-Java/docs/refactor/05-progress.md","sha256":"f37547e858db034361c23c7c886bf291f1783b343e98cd95a0efc328370b449a","ti_java_relative_path":"docs/refactor/05-progress.md"},{"byte_count":18266,"change_type":"M","git_blob_oid":"68fca94d05fc425f4c302d50e50054b060608868","mode":"100644","object_type":"blob","previous_git_blob_oid":"2a29318d27773ff40c2b4d7d63fbc52c09fbadb0","previous_mode":"100644","repository_path":"Ti-Java/docs/refactor/phase4c/README.md","sha256":"fbdbf32d9a3c488c890ce5d71689e59eb9a7458989843a45433e247dca2f6d98","ti_java_relative_path":"docs/refactor/phase4c/README.md"},{"byte_count":59299,"change_type":"A","git_blob_oid":"4d1b29ad082f17b59cd8262463f291f1c8c6c068","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/docs/refactor/phase4c/personal-bank-user-counts-http-typed-normalization-contract.json","sha256":"ff1a751e1576916618422e0775c916e1d3b20122ffc141a04512119a6b5e99cd","ti_java_relative_path":"docs/refactor/phase4c/personal-bank-user-counts-http-typed-normalization-contract.json"},{"byte_count":3730,"change_type":"A","git_blob_oid":"e74c2fe38d2bb39fa1d064ec26a48653e9b83f87","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/docs/refactor/phase4c/personal-bank-user-counts-typed-normalization-approved-difference.md","sha256":"3c6ecb59cae4e8a2f31e7dd0ed74bcca56e0cf61830339254523f3f824e652be","ti_java_relative_path":"docs/refactor/phase4c/personal-bank-user-counts-typed-normalization-approved-difference.md"},{"byte_count":9342,"change_type":"A","git_blob_oid":"42f686014b17b9a9535dbb24e2cbc9e60ced1a90","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/docs/refactor/phase4c/personal-bank-user-counts-typed-normalization-junit-manifest.json","sha256":"b6c619ee1ed4be44fd68903c2449188fd6a65ee39b7c855b1796c901d3a0268c","ti_java_relative_path":"docs/refactor/phase4c/personal-bank-user-counts-typed-normalization-junit-manifest.json"},{"byte_count":6850,"change_type":"M","git_blob_oid":"183ce4e90368e19f215fd54656e5da1b8733e260","mode":"100644","object_type":"blob","previous_git_blob_oid":"13dfe524febcdad3f0b7faedd8cd2c4b02d42e2a","previous_mode":"100644","repository_path":"Ti-Java/infra/phase2/README.md","sha256":"30950043edcca47aa42543065ca0b6b08d5c4c4a4839f2034af2cdde47174622","ti_java_relative_path":"infra/phase2/README.md"},{"byte_count":14323,"change_type":"M","git_blob_oid":"e69b9fda9d7030d66f5a9506d0774cce4e72f296","mode":"100755","object_type":"blob","previous_git_blob_oid":"eaa2f8c192de711747d55bffec1e81e1b57fcf2c","previous_mode":"100755","repository_path":"Ti-Java/infra/phase2/verify-static.sh","sha256":"78f6dd82e43d39f289b5962490aace65dba806581a16580903d32dbee4812752","ti_java_relative_path":"infra/phase2/verify-static.sh"},{"byte_count":55266,"change_type":"M","git_blob_oid":"964709792ad98337990b41614098774d512506dd","mode":"100644","object_type":"blob","previous_git_blob_oid":"67ad65a5d482128549df3b5d012e5314cd5cb173","previous_mode":"100644","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java","sha256":"b95ee58fd66698d129ee9562959d21ffc3a3e0c0b49339f21c379a8d0c356090","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java"},{"byte_count":75517,"change_type":"A","git_blob_oid":"e2b7960b89b2dddf9b68a634613f24df272ad43e","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java","sha256":"43a903c797ebc2af5aa85d65ca70709544eb068841dddca1505b2c95b3529d16","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java"},{"byte_count":19014,"change_type":"M","git_blob_oid":"1943c251a40877fd0d34aa7629220a67e860e8cc","mode":"100644","object_type":"blob","previous_git_blob_oid":"c275b712c210a21560bb2a91238ca4500eb4b907","previous_mode":"100644","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java","sha256":"bd2b0c554a19fb561919298bba1c23a9f35435390ff3a069e3ec8e7ec5959e12","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest.java"},{"byte_count":17241,"change_type":"M","git_blob_oid":"09a733afaf0675961f50f7d2e39125b985c1c579","mode":"100644","object_type":"blob","previous_git_blob_oid":"34312828552cd30ed62a4ec7b0e813aed2880d73","previous_mode":"100644","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java","sha256":"efa8bd66c5df68bdd9617415b156450ba2ae12dafb2c284df75dcc44e8edcd02","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java"},{"byte_count":27970,"change_type":"A","git_blob_oid":"e2a6bc27e46d5f1ab35d03591b8645ccbe021414","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java","sha256":"3da21589512652bf3a6f26f65e00d2a531d735218a5483613353e183f3eb1d25","ti_java_relative_path":"server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java"},{"byte_count":30716,"change_type":"A","git_blob_oid":"732c45c4d968dc761759d30449e4d79bce658517","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/server/src/test/java/io/saksk/ti/integration/LegacyPersonalBankUserCountsTypedNormalizationIT.java","sha256":"f9bd7dbd51e65abe8f01e80d0d564b9dfdba6856f95c4b06ad21b3705a2f025f","ti_java_relative_path":"server/src/test/java/io/saksk/ti/integration/LegacyPersonalBankUserCountsTypedNormalizationIT.java"},{"byte_count":363,"change_type":"A","git_blob_oid":"f11e49a60610901b81423ebae024d73764fe5998","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/server/src/test/resources/db/phase4c/072-personal-bank-user-counts-typed-normalization-seed.sql","sha256":"089b795d6e6a3efdb1af86641701bd1bf9d30e2c1a94c65a0a32865bdfca29c6","ti_java_relative_path":"server/src/test/resources/db/phase4c/072-personal-bank-user-counts-typed-normalization-seed.sql"},{"byte_count":39048,"change_type":"M","git_blob_oid":"f224874e62297680741004c967f35d4f083adc96","mode":"100644","object_type":"blob","previous_git_blob_oid":"70951075267e29b9cb354f7f03888b23adc504c9","previous_mode":"100644","repository_path":"Ti-Java/tools/build_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py","sha256":"342990a999fa0873b6c33a9a2f735f88fb7a453ee27d94832b81b14b9c8fa2a1","ti_java_relative_path":"tools/build_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py"},{"byte_count":40434,"change_type":"A","git_blob_oid":"5bec56940e2dd15ac71a20852b25a8489bce8d03","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/tools/build_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py","sha256":"46089a29a518c624dd87ceed6d464890acb9a530adfae3fc9eb46d26da81fd0a","ti_java_relative_path":"tools/build_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py"},{"byte_count":22318,"change_type":"A","git_blob_oid":"8201348aeecbb7061890070c62b49344e4c85654","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/tools/normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py","sha256":"3ff33e3ef1ad3171ea2ca97f9b70fc49db1c3dd92d97a5d8c634497d78285acc","ti_java_relative_path":"tools/normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py"},{"byte_count":24939,"change_type":"M","git_blob_oid":"a7ce09960adae56ff9aab156f3838532cd60d3c3","mode":"100644","object_type":"blob","previous_git_blob_oid":"d6de042c4c1f38aceb701045fce46777f5c9a83f","previous_mode":"100644","repository_path":"Ti-Java/tools/phase2_wormhole_successor_acceptance.py","sha256":"9e11c33623a10415b28a5aadf1cf0855ef4bdd1dc9a3d81eeeff41e76a98f735","ti_java_relative_path":"tools/phase2_wormhole_successor_acceptance.py"},{"byte_count":37853,"change_type":"M","git_blob_oid":"8cb03dba4c9feec82329bcbc8ad458faffc37d54","mode":"100644","object_type":"blob","previous_git_blob_oid":"2a5ec91d4709d11709571805786a8c641dfeba04","previous_mode":"100644","repository_path":"Ti-Java/tools/phase4c_http_target_execution_post_push_anchor_successor_acceptance.py","sha256":"c1abc55435cd3c3e1c62a72412dc5b62b300fb9f76b8ebc2b6c5482fe726403d","ti_java_relative_path":"tools/phase4c_http_target_execution_post_push_anchor_successor_acceptance.py"},{"byte_count":52080,"change_type":"A","git_blob_oid":"45a60e1194ba0fe292eb488160c66843cc4eef11","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/tools/phase4c_http_typed_normalization_successor_acceptance.py","sha256":"86de6fe3449a379c3ce960edd7a843768ccc0521ab7d9502c492c6ad1cf6a9f3","ti_java_relative_path":"tools/phase4c_http_typed_normalization_successor_acceptance.py"},{"byte_count":10366,"change_type":"A","git_blob_oid":"fa2b3b0b5816054594ca8d9cccc4fcb917e8c07b","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/tools/test_normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py","sha256":"51b316b9370da51b3c4f93b601ffb600451494d2743c0f08fbe17335e8d8bdcd","ti_java_relative_path":"tools/test_normalize_phase4c_personal_bank_user_counts_typed_normalization_junit.py"},{"byte_count":40416,"change_type":"M","git_blob_oid":"5ea0fd0a7294ce01ad169284cfad04c329116cb8","mode":"100644","object_type":"blob","previous_git_blob_oid":"eff3ddd92670bb00f094dcc80c96f4d6ec458edd","previous_mode":"100644","repository_path":"Ti-Java/tools/test_phase2_wormhole_successor_acceptance.py","sha256":"b273ae2f450238b709d409e07e6ab7c7f39fbe71d162563a18350f62adaca7ab","ti_java_relative_path":"tools/test_phase2_wormhole_successor_acceptance.py"},{"byte_count":19187,"change_type":"M","git_blob_oid":"3a5a859015906168ea57f0efd90dc95bbc1cb4e3","mode":"100644","object_type":"blob","previous_git_blob_oid":"368af3c122f52e35b66525f5e01362acbc956c20","previous_mode":"100644","repository_path":"Ti-Java/tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py","sha256":"b2f0feefd23f88c357c1bb6e72f417a4de212465e79577930a7c671c3138e47c","ti_java_relative_path":"tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py"},{"byte_count":12084,"change_type":"M","git_blob_oid":"0d4a88685aff51d0f37d7705bbceaa797fdbcc44","mode":"100644","object_type":"blob","previous_git_blob_oid":"72c87d9ab5c6555ee7ae52883def1916ece137ef","previous_mode":"100644","repository_path":"Ti-Java/tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py","sha256":"9bb6c53fd9c833ff2ed9d2bdcf09af80ae436a9bcfc4c2ee2d54c03f2274acca","ti_java_relative_path":"tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py"},{"byte_count":25364,"change_type":"A","git_blob_oid":"0f227599fd9c1674c018b474c84a752e1d2f3820","mode":"100644","object_type":"blob","previous_git_blob_oid":"0000000000000000000000000000000000000000","previous_mode":"000000","repository_path":"Ti-Java/tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py","sha256":"4203a585587b11bca41867c45d7a269f7ecb518f271fb6fd99919c9ba8a905bf","ti_java_relative_path":"tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py"}]''')
CHECKPOINT_CHANGES = {
    item["ti_java_relative_path"]: item
    for item in _CHECKPOINT_LIST
}

TYPED_SOURCE_PATHS = (
    PREDECESSOR_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_contract.py",
    "tools/phase4c_http_typed_normalization_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_contract.py",
)

CURRENT_ANCHOR_SOURCES = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-anchor-contract.json",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_anchor_contract.py",
    "tools/phase4c_http_typed_normalization_anchor_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_anchor_contract.py",
)

SUCCESSOR_PATHS = (
    "README.md",
    "docs/refactor/05-progress.md",
    "docs/refactor/phase4c/README.md",
    "infra/phase2/README.md",
    "infra/phase2/verify-static.sh",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java",
    "tools/phase2_wormhole_successor_acceptance.py",
    "tools/phase4c_http_typed_normalization_successor_acceptance.py",
    "tools/test_phase2_wormhole_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_anchor_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_contract.py",
)
SUCCESSOR_SHA256 = {
    "README.md": "524f03e89122b4d8a9af4ed805596a3b315a4859dac2777b0ab989ac25e82b47",
    "docs/refactor/05-progress.md": "62ff84e2cc3b525855f0a0eb07a1820c231ad50864956329d0da08a3d86b697c",
    "docs/refactor/phase4c/README.md": "dd0f41f78466636d09d3afa7669e507814aa78a04cb94d62bf7e96596c18e85a",
    "infra/phase2/README.md": "414901d53174c7875ea000c323652a1ddf046a2e97018bbbd1dc4c9a4b3bf988",
    "infra/phase2/verify-static.sh": "410108998f03e4d857d230c75687e854bd3bad99ba85d18c2fb090978ffa46d7",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java": "f78882b20e38857c420b750677e4e8dd52922a1f0c04c249db9ed0d4f3db4fd5",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java": "beaed12d8ec96782ce55969a0e511458d78f4040b3eccf65971ce38e2caaed27",
    "tools/phase2_wormhole_successor_acceptance.py": "1164b6c584f4905a8011c5320eac62591e039ad0526b5a0657908f7b82688480",
    "tools/phase4c_http_typed_normalization_successor_acceptance.py": "e71a5eec0e71ff824750f6eb20c4b310fdb0d8273fe89d83a23aee422ba282c5",
    "tools/test_phase2_wormhole_successor_acceptance.py": "ff3250a88eb6e16102fc91930beec627f79ed57720140a32e7ad4410d7856e9f",
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py": "3ded87895b33befb0f80905a1490d5f9207ae4e9ee26e939e5c00ebbd30a7874",
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py": "87078f6d01957dcbbb37b488048a6702bc2212850ee9b2b75aa9b68aba352057",
    "tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py": "72bd92b70d909c56598874328144835bc3e5a723c4f1e9f5bab041299d23be51",
}
SUCCESSOR_BYTE_COUNT = {
    "README.md": 38_265,
    "docs/refactor/05-progress.md": 103_256,
    "docs/refactor/phase4c/README.md": 19_511,
    "infra/phase2/README.md": 6_959,
    "infra/phase2/verify-static.sh": 14_719,
    "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java": 76_703,
    "server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationContractParityTest.java": 28_553,
    "tools/phase2_wormhole_successor_acceptance.py": 25_791,
    "tools/phase4c_http_typed_normalization_successor_acceptance.py": 54_168,
    "tools/test_phase2_wormhole_successor_acceptance.py": 44_809,
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py": 19_311,
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py": 12_208,
    "tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_contract.py": 25_018,
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def document_payload_sha256(document: dict[str, Any]) -> str:
    return sha256_json({
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    })


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"fixed typed anchor path escapes Ti-Java: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"fixed typed anchor path contains symlink: {relative}"
            )
    try:
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise AssertionError(
            f"fixed typed anchor path escaped or vanished: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(f"fixed typed anchor path is not a file: {relative}")
    return resolved


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    try:
        value = json.loads(
            fixed_regular_file(root, relative).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"cannot read fixed typed anchor JSON: {relative}") from error
    if not isinstance(value, dict):
        raise AssertionError(f"fixed typed anchor JSON is not an object: {relative}")
    return value


def _validate_predecessor(root: Path) -> dict[str, Any]:
    path = fixed_regular_file(root, PREDECESSOR_RELATIVE)
    payload = path.read_bytes()
    if len(payload) != PREDECESSOR_BYTE_COUNT:
        raise AssertionError("typed predecessor byte count drifted")
    if sha256_bytes(payload) != PREDECESSOR_SHA256:
        raise AssertionError("typed predecessor physical SHA-256 drifted")
    predecessor = _read_json(root, PREDECESSOR_RELATIVE)
    identity = {
        "contract_id": PREDECESSOR_ID,
        "status": PREDECESSOR_STATUS,
        "scope": PREDECESSOR_SCOPE,
        "captured_at": PREDECESSOR_CAPTURED_AT,
        "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
    }
    if {key: predecessor.get(key) for key in identity} != identity:
        raise AssertionError("typed predecessor identity drifted")
    if document_payload_sha256(predecessor) != PREDECESSOR_PAYLOAD_SHA256:
        raise AssertionError("typed predecessor payload is invalid")
    trust = predecessor.get("current_node_trust_boundary", {})
    if (
        trust.get("source_paths") != sorted(TYPED_SOURCE_PATHS)
        or trust.get("source_count") != 6
        or trust.get("source_path_allowlist_exact") is not True
        or trust.get("sources_excluded_from_self_authority") is not True
        or trust.get("source_bytes_external_git_anchor_complete") is not False
        or trust.get("post_push_external_anchor_required") is not True
    ):
        raise AssertionError("typed predecessor self-authority boundary drifted")
    authorization = predecessor.get("authorization", {})
    expected_false = (
        "current_node_sources_external_git_anchor_complete",
        "typed_parity_review_complete",
        "full_target_parity_closed",
        "route_migration_eligible",
        "two_legacy_get_routes_migrated",
        "production_cutover",
        "pg16_pg18_termination_fingerprints_complete",
        "real_tomcat_complete_response_header_matrix_complete",
        "same_service_redis_outage_and_recovery_complete",
    )
    if authorization.get("typed_execution_normalization_complete") is not True:
        raise AssertionError("typed predecessor lost executed normalization")
    for field in expected_false:
        if authorization.get(field) is not False:
            raise AssertionError(f"typed predecessor overclaims {field}")
    acceptance = predecessor.get("acceptance", {})
    if (
        acceptance.get("migrated_operation_count") != 11
        or acceptance.get("pending_operation_count") != 600
        or acceptance.get("production_cutover_operation_count") != 0
        or acceptance.get("logical_disposition_count") != 59
        or acceptance.get("http_execution_count") != 58
    ):
        raise AssertionError("typed predecessor acceptance counts drifted")
    return predecessor


def _validate_typed_manifest(root: Path) -> None:
    path = fixed_regular_file(root, TYPED_MANIFEST_RELATIVE)
    payload = path.read_bytes()
    if (
        len(payload) != 9_342
        or sha256_bytes(payload) != TYPED_MANIFEST_SHA256
    ):
        raise AssertionError("typed anchor JUnit manifest bytes drifted")
    manifest = _read_json(root, TYPED_MANIFEST_RELATIVE)
    if (
        manifest.get("document_payload_sha256") != TYPED_MANIFEST_PAYLOAD_SHA256
        or document_payload_sha256(manifest) != TYPED_MANIFEST_PAYLOAD_SHA256
        or manifest.get("result", {}).get("proof_payload_sha256")
        != TYPED_MANIFEST_PROOF_PAYLOAD_SHA256
    ):
        raise AssertionError("typed anchor JUnit manifest payload drifted")
    raw = manifest.get("raw_report", {})
    if (
        raw.get("sha256") != TYPED_RAW_REPORT_SHA256
        or raw.get("byte_count") != TYPED_RAW_REPORT_BYTE_COUNT
        or raw.get("tracked") is not False
        or raw.get("content_embedded") is not False
    ):
        raise AssertionError("typed anchor raw JUnit binding drifted")
    physical = manifest.get("result", {}).get("physical_evidence", {})
    effective = manifest.get("result", {}).get("effective_evidence", {})
    if (
        physical.get("aggregate_leaf_count") != 61
        or physical.get("failed_error_skipped_or_flaky") != 0
        or effective.get("selected_effective_proof_leaf_count") != 60
        or effective.get("logical_disposition_count") != 59
        or effective.get("superseded_leaf_double_counted") is not False
    ):
        raise AssertionError("typed anchor JUnit evidence counts drifted")


def _validate_worm(root: Path) -> None:
    payload = fixed_regular_file(root, WORM_RELATIVE).read_bytes()
    if sha256_bytes(payload) != WORM_SHA256:
        raise AssertionError("typed anchor fifth WORM hash drifted")
    worm = _read_json(root, WORM_RELATIVE)
    if (
        worm.get("java", {}).get("buildContextSha256")
        != JAVA_BUILD_CONTEXT_SHA256
        or worm.get("java", {}).get("dockerfileSha256") != DOCKERFILE_SHA256
        or worm.get("restore", {}).get("canonicalSchemaDumpSha256")
        != CANONICAL_SCHEMA_DUMP_SHA256
        or worm.get("flywayBaselineCreated") is not False
    ):
        raise AssertionError("typed anchor fifth WORM boundary drifted")


def successor_constants_settled() -> bool:
    return all(
        SUCCESSOR_SHA256.get(relative) not in (None, ZERO_SHA256)
        and SUCCESSOR_BYTE_COUNT.get(relative, 0) > 0
        for relative in SUCCESSOR_PATHS
    )


def _successor_descriptor(relative: str) -> dict[str, Any]:
    accepted = CHECKPOINT_CHANGES[relative]
    return {
        "source": relative,
        "repository_path": accepted["repository_path"],
        "accepted_git_commit_oid": GIT_COMMIT_OID,
        "accepted_git_blob_oid": accepted["git_blob_oid"],
        "accepted_sha256": accepted["sha256"],
        "accepted_byte_count": accepted["byte_count"],
        "mode": accepted["mode"],
        "successor_sha256": SUCCESSOR_SHA256[relative],
        "successor_byte_count": SUCCESSOR_BYTE_COUNT[relative],
    }


def _validate_local_successors(root: Path) -> None:
    if not successor_constants_settled():
        return
    for relative in SUCCESSOR_PATHS:
        payload = fixed_regular_file(root, relative).read_bytes()
        if (
            len(payload) != SUCCESSOR_BYTE_COUNT[relative]
            or sha256_bytes(payload) != SUCCESSOR_SHA256[relative]
        ):
            raise AssertionError(f"typed anchor successor drifted: {relative}")


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
            ["git", "--no-optional-locks", "-C", str(repository_root), *arguments],
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


def _expected_raw_delta() -> list[str]:
    return [
        (
            f":{descriptor['previous_mode']} {descriptor['mode']} "
            f"{descriptor['previous_git_blob_oid']} {descriptor['git_blob_oid']} "
            f"{descriptor['change_type']}\t{descriptor['repository_path']}"
        )
        for descriptor in CHECKPOINT_CHANGES.values()
    ]


def _validate_git_blob(root: Path, descriptor: dict[str, Any]) -> None:
    repository_path = descriptor["repository_path"]
    line = _git_text(root, "ls-tree", GIT_COMMIT_OID, "--", repository_path)
    parts = line.split(None, 3)
    if len(parts) != 4 or parts[:3] != [
        descriptor["mode"],
        "blob",
        descriptor["git_blob_oid"],
    ]:
        raise AssertionError(f"typed anchor tree entry drifted: {repository_path}")
    payload = _run_read_only_git(root, "cat-file", "blob", descriptor["git_blob_oid"])
    if (
        len(payload) != descriptor["byte_count"]
        or sha256_bytes(payload) != descriptor["sha256"]
    ):
        raise AssertionError(f"typed anchor blob bytes drifted: {repository_path}")
    previous_oid = descriptor["previous_git_blob_oid"]
    if previous_oid != "0" * 40:
        previous_payload = _run_read_only_git(root, "cat-file", "blob", previous_oid)
        if not previous_payload and descriptor["change_type"] == "M":
            raise AssertionError(f"typed anchor previous blob vanished: {repository_path}")


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    top = Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root:
        raise AssertionError("typed anchor repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("typed anchor Git object format drifted")
    if _git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit":
        raise AssertionError("typed anchor checkpoint is not a commit")
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
        GIT_COMMITTED_AT,
        GIT_SUBJECT,
    ]:
        raise AssertionError("typed anchor Git commit identity drifted")
    if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java") != TI_JAVA_TREE_OID:
        raise AssertionError("typed anchor Ti-Java subtree drifted")
    raw_bytes = _run_read_only_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--abbrev=40",
        "-r",
        GIT_COMMIT_OID,
    )
    if sha256_bytes(raw_bytes) != GIT_RAW_DELTA_SHA256:
        raise AssertionError("typed anchor raw delta digest drifted")
    if raw_bytes.decode("utf-8").splitlines() != _expected_raw_delta():
        raise AssertionError("typed anchor exact 26-path delta drifted")
    for descriptor in CHECKPOINT_CHANGES.values():
        _validate_git_blob(root, descriptor)


def build_contract(
    ti_java_root: Path = ROOT,
    *,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    _validate_predecessor(root)
    _validate_typed_manifest(root)
    _validate_worm(root)
    _validate_local_successors(root)
    if repository_root is not None:
        validate_git_checkpoint(repository_root)

    transitions_settled = successor_constants_settled()
    source_artifacts = {
        relative: deepcopy(CHECKPOINT_CHANGES[relative])
        for relative in sorted(TYPED_SOURCE_PATHS)
    }
    successor_overrides = {
        relative: _successor_descriptor(relative)
        for relative in sorted(SUCCESSOR_PATHS)
    }
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": CONTRACT_STATUS,
        "scope": CONTRACT_SCOPE,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "contract_id": PREDECESSOR_ID,
            "status": PREDECESSOR_STATUS,
            "scope": PREDECESSOR_SCOPE,
            "captured_at": PREDECESSOR_CAPTURED_AT,
            "immutable": True,
        },
        "git_checkpoint": {
            "object_format": GIT_OBJECT_FORMAT,
            "commit_oid": GIT_COMMIT_OID,
            "root_tree_oid": GIT_ROOT_TREE_OID,
            "parent_oid": GIT_PARENT_OID,
            "ti_java_tree_oid": TI_JAVA_TREE_OID,
            "authored_at": GIT_AUTHORED_AT,
            "committed_at": GIT_COMMITTED_AT,
            "subject": GIT_SUBJECT,
            "capture_ref_metadata": GIT_CAPTURE_REF,
            "capture_ref_is_validation_authority": False,
            "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
            "exact_changed_paths": [
                descriptor["repository_path"]
                for descriptor in CHECKPOINT_CHANGES.values()
            ],
            "diff": {
                "added_count": 12,
                "modified_count": 14,
                "deleted_count": 0,
                "non_ti_java_count": 0,
                "inserted_line_count": 8_182,
                "deleted_line_count": 32,
                "current_total_bytes": 802_663,
                "added_total_bytes": 357_499,
                "modified_current_total_bytes": 445_164,
                "modified_parent_total_bytes": 428_047,
                "net_byte_increase": 374_616,
                "exact_twenty_six_path_delta": True,
            },
            "artifacts": deepcopy(CHECKPOINT_CHANGES),
        },
        "typed_normalization_source_anchor": {
            "accepted_checkpoint_commit_oid": GIT_COMMIT_OID,
            "source_paths": sorted(TYPED_SOURCE_PATHS),
            "source_path_allowlist_exact": True,
            "source_count": 6,
            "source_total_bytes": 280_664,
            "artifacts": source_artifacts,
            "predecessor_current_sources_external_git_anchor_complete": True,
            "predecessor_false_claim_preserved": True,
            "whole_commit_root_parent_and_ti_java_tree_fixed": True,
            "exact_twenty_six_change_blobs_fixed": True,
            "arbitrary_git_object_lookup_forbidden": True,
            "dynamic_source_discovery_forbidden": True,
            "current_anchor_sources": sorted(CURRENT_ANCHOR_SOURCES),
            "current_anchor_sources_excluded_from_self_authority": True,
            "current_anchor_source_bytes_external_git_anchor_complete": False,
            "independently_signed_provenance": False,
            "tamper_evident_scope": "fixed_git_commit_tree_delta_and_explicit_blobs",
        },
        "historical_source_successors": {
            "accepted_checkpoint_commit_oid": GIT_COMMIT_OID,
            "successor_allowlist_count": len(SUCCESSOR_PATHS),
            "successor_allowlist": sorted(SUCCESSOR_PATHS),
            "successor_allowlist_exact": True,
            "arbitrary_source_lookup_forbidden": True,
            "accepted_hashes_from_fixed_git_blobs": True,
            "successor_hashes_code_fixed": True,
            "successor_transitions_settled": transitions_settled,
            "overrides": successor_overrides,
            "current_successor_bytes_external_git_anchor_complete": False,
        },
        "junit_execution": {
            "source": TYPED_MANIFEST_RELATIVE,
            "sha256": TYPED_MANIFEST_SHA256,
            "document_payload_sha256": TYPED_MANIFEST_PAYLOAD_SHA256,
            "proof_payload_sha256": TYPED_MANIFEST_PROOF_PAYLOAD_SHA256,
            "raw_report_sha256": TYPED_RAW_REPORT_SHA256,
            "raw_report_byte_count": TYPED_RAW_REPORT_BYTE_COUNT,
            "aggregate_physical_leaf_count": 61,
            "selected_effective_leaf_count": 60,
            "logical_disposition_count": 59,
            "failures_errors_skipped_or_flaky": 0,
            "raw_report_tracked": False,
            "raw_report_embedded": False,
        },
        "worm_evidence": {
            "source": WORM_RELATIVE,
            "sha256": WORM_SHA256,
            "predecessor_sha256": WORM_PREDECESSOR_SHA256,
            "fixed_chain_node_count": 5,
            "reused": True,
            "new_worm_report_created": False,
            "java_build_context_sha256": JAVA_BUILD_CONTEXT_SHA256,
            "dockerfile_sha256": DOCKERFILE_SHA256,
            "canonical_schema_dump_sha256": CANONICAL_SCHEMA_DUMP_SHA256,
        },
        "authorization": {
            "typed_execution_normalization_complete": True,
            "typed_normalization_checkpoint_and_six_excluded_sources_"
            "external_git_anchor_complete": True,
            "historical_successor_transitions_settled": transitions_settled,
            "current_anchor_source_bytes_external_git_anchor_complete": False,
            "typed_parity_review_complete": False,
            "pg16_pg18_termination_fingerprints_complete": False,
            "real_tomcat_complete_response_header_matrix_complete": False,
            "same_service_redis_outage_and_recovery_complete": False,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "two_legacy_get_routes_migrated": False,
            "derived_head_and_options_count_as_migrated": False,
            "operator_migration_implementation": False,
            "production_schema_or_index": False,
            "real_data_migration_execution": False,
            "client_change": False,
            "gateway_or_proxy_change": False,
            "production_cutover": False,
        },
        "acceptance": {
            "checkpoint_changed_path_count": 26,
            "checkpoint_added_count": 12,
            "checkpoint_modified_count": 14,
            "checkpoint_current_total_bytes": 802_663,
            "typed_source_anchor_count": 6,
            "typed_source_anchor_total_bytes": 280_664,
            "junit_physical_leaf_count": 61,
            "junit_selected_effective_leaf_count": 60,
            "logical_disposition_count": 59,
            "http_execution_count": 58,
            "mocked_application_result_case_count": 0,
            "bound_only_case_count": 0,
            "typed_execution_normalization_complete": True,
            "typed_parity_review_complete": False,
            "full_target_parity_closed": False,
            "route_migration_eligible": False,
            "implemented_pending_get_count": 2,
            "migrated_operation_count": 11,
            "pending_operation_count": 600,
            "production_cutover_operation_count": 0,
            "production_cutover": False,
            "current_anchor_is_successor_bootstrap": True,
            "next_gate": NEXT_GATE,
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(serialized_contract(document))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-sha256", action="store_true")
    parser.add_argument("--print-payload-sha256", action="store_true")
    args = parser.parse_args()
    document = build_contract(
        args.ti_java_root,
        repository_root=args.repository_root,
    )
    payload = serialized_contract(document)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != payload:
            raise AssertionError("typed-normalization anchor contract is stale")
    else:
        _write_json(args.output, document)
    if args.print_sha256:
        print(sha256_bytes(payload))
    if args.print_payload_sha256:
        print(document["document_payload_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
