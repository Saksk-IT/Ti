#!/usr/bin/env python3
"""Build the Gitless Phase 4C tag-migration execution-protocol contract.

Ordinary construction reads only fixed regular files below ``Ti-Java``.  The
only Git-capable paths are the explicitly requested C2 replay and fixed-map
refresh commands; both are pinned to ``4c47d1e...`` and never inspect a live
ref or discover paths dynamically.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

try:
    from tools import build_phase4c_tag_migration_operator_core_contract as node_c
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_tag_migration_operator_core_contract",
    }:
        raise
    import build_phase4c_tag_migration_operator_core_contract as node_c


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-execution-protocol-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE
CONTRACT_ID = "ti.phase4c.personal-bank-tag-migration-execution-protocol-contract"
CAPTURED_AT = "2026-07-20T21:15:00+08:00"
SCOPE = "phase4c-learning-owned-personal-bank-tag-migration-execution-protocol"
STATUS = (
    "execution_protocol_crypto_verifier_and_local_disposable_rehearsal_closed_"
    "production_freeze_backup_apply_runtime_disable_and_cutover_unauthorized"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-operator-core-post-push-anchor-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-tag-migration-operator-core-"
    "post-push-anchor-contract"
)
PREDECESSOR_CAPTURED_AT = "2026-07-20T18:26:27+08:00"
PREDECESSOR_SCOPE = (
    "phase4c-personal-bank-tag-migration-operator-core-"
    "post-push-external-anchor"
)
PREDECESSOR_STATUS = (
    "operator_core_and_independent_acceptance_checkpoints_externally_anchored_"
    "production_schema_freeze_backup_apply_and_cutover_unauthorized"
)
PREDECESSOR_SHA256 = (
    "0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64"
)
PREDECESSOR_BYTE_COUNT = 84_461
PREDECESSOR_COMMIT = "4c47d1ea220ae9e310338bbf23b74d87d477e20f"
PREDECESSOR_INDEPENDENT_ACCEPTANCE_COMMIT = (
    "4ec9966f836378a33058b574fd1812d4d19cac10"
)

MIGRATION_MAIN_PREFIX = (
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
)
MIGRATION_TEST_PREFIX = (
    "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
)
WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-execution-protocol-worm-evidence.json"
)
WORM_PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-operator-core-worm-evidence.json"
)
WORM_PREDECESSOR_SHA256 = (
    "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f"
)
WORM_PREDECESSOR_BYTE_COUNT = 1_442
ACCEPTED_BUILD_CONTEXT_SHA256 = (
    "29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc"
)
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
BUILD_CONTEXT_SCRIPT_RELATIVE = "infra/phase2/hash-java-build-context.sh"

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol.md",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationExecutionProtocolContractParityTest.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationExecutionProtocolSuccessorAcceptance.java"
    ),
    "tools/build_phase4c_tag_migration_execution_protocol_contract.py",
    "tools/phase4c_tag_migration_execution_protocol_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_execution_protocol_contract.py",
)

IMPLEMENTATION_SOURCE_PATHS = (
    MIGRATION_MAIN_PREFIX + "Ed25519TagMigrationEvidenceVerifier.java",
    MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagMigrationExecutionProtocol.java",
    MIGRATION_MAIN_PREFIX + "TagMigrationPlanCandidate.java",
    MIGRATION_MAIN_PREFIX + "TagMigrationPlanCandidateFactory.java",
    MIGRATION_TEST_PREFIX + "Ed25519TagMigrationEvidenceVerifierTest.java",
    MIGRATION_TEST_PREFIX + "LegacyPersonalBankTagMigrationExecutionProtocolStaticTest.java",
    MIGRATION_TEST_PREFIX + "Phase4cLegacyPersonalBankTagMigrationExecutionProtocolIT.java",
    MIGRATION_TEST_PREFIX + "TagMigrationPlanCandidateFactoryTest.java",
    (
        "server/src/test/resources/db/phase4c/"
        "078-legacy-personal-bank-tag-migration-execution-protocol-schema.sql"
    ),
    (
        "server/src/test/resources/db/phase4c/"
        "079-legacy-personal-bank-tag-migration-execution-protocol-seed.sql"
    ),
    WORM_RELATIVE,
)

# Exact propagation allowlist.  It is intentionally a tuple, never a glob or a
# filesystem/Git diff result.
SOURCE_TRANSITION_PATHS = (
    "docs/refactor/05-progress.md",
    "docs/refactor/phase4c/README.md",
    "infra/phase2/README.md",
    "infra/phase2/verify-static.sh",
    "tools/phase2_wormhole_successor_acceptance.py",
    "tools/test_phase2_wormhole_successor_acceptance.py",
    "tools/phase4c_tag_migration_operator_core_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_operator_core_contract.py",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationOperatorCoreContractParityTest.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationOperatorCorePostPushAnchorContractParityTest.java"
    ),
    "tools/build_phase4c_tag_migration_global_preflight_contract.py",
    "tools/phase4c_tag_migration_global_preflight_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_global_preflight_contract.py",
    (
        "tools/test_phase4c_tag_migration_operator_core_"
        "post_push_anchor_contract.py"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationGlobalPreflightContractParityTest.java"
    ),
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py",
    "tools/phase4c_http_target_execution_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py",
    (
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_anchor_contract.py"
    ),
    "tools/phase4c_http_target_execution_anchor_successor_acceptance.py",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTypedNormalizationSuccessorAcceptance.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase6WebFoundationSourceSuccessorContractParityTest.java"
    ),
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py",
    "tools/test_phase4b_personal_bank_share_list_entry_contract.py",
    "tools/test_phase4b_personal_bank_share_list_read_contract.py",
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py",
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
)

# This one literal is mechanically refreshed with
# ``--emit-refreshed-fixed-map`` after all 37 propagation writers and Node 9
# have settled.  An empty object fails closed; no digest is guessed.
_FIXED_MAP: dict[str, Any] = json.loads(r'''{"accepted_learning_personalbank_main_file_count":50,"accepted_learning_personalbank_main_manifest_sha256":"3abdc97486bbb9ec62a2d426063157e0ef3a990a34ca4862fc9e18580b4f60e9","accepted_production_file_count":307,"accepted_production_manifest_sha256":"b1228337b60b752ff088c4e5b67ae21092ca75a07c437bae35cc67b39b1c8c25","current_build_context_sha256":"36978a808a327abfb3c7b3dfe138f5622000213a25bad762b59128c78894d7c7","current_learning_personalbank_main_file_count":54,"current_learning_personalbank_main_manifest_sha256":"66e7874b40dcbfc46fa349e7d4d8cd36025a82a03df009f985a6fc30d2edead6","current_production_file_count":311,"current_production_manifest_sha256":"053ffc0a6a6ecc02ffb7cd2a8545af339bef35ffd502dcdbfbc0de8b11977d4a","production_runtime_additions":{"server/src/main/java/io/saksk/ti/learning/infrastructure/migration/Ed25519TagMigrationEvidenceVerifier.java":"0db53a72f3ecbb5a72eefde3a4b042d3771727792cf9bc7b008b4dc7928c3573","server/src/main/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagMigrationExecutionProtocol.java":"9fbacb71fb333d4c6d90127255c12108321c2cec90666300e9bfbc5d7d82657c","server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationPlanCandidate.java":"e324adad954d337cfd92ec77f7fd5eb30db9d002b5be6a37d73c4a92e3161c8d","server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationPlanCandidateFactory.java":"336d24f66a57becafb0ac579f18d89391a935070510456de8626224672abcb54"},"source_files":{"docs/refactor/05-progress.md":["2fb55e0aaaeff28c3c3def877b5be51ae2ea6358272222f0e0f8232dec69867f",109911],"docs/refactor/phase4c/README.md":["ab5144697dfded1778d40209958a2c3fdcc7bfc1b08d5dde481cc6a8f009ed6e",31994],"docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-worm-evidence.json":["5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c",1442],"infra/phase2/README.md":["187895861b607be2cfddb63320b4ee52dc4efd7706e94afd5d56a07169832216",9031],"infra/phase2/verify-static.sh":["6878d027fc21c1564840771609f0f2e9dfa6eb2bb483b56b6abfd1e9386eb4a3",18597],"server/src/main/java/io/saksk/ti/learning/infrastructure/migration/Ed25519TagMigrationEvidenceVerifier.java":["0db53a72f3ecbb5a72eefde3a4b042d3771727792cf9bc7b008b4dc7928c3573",53495],"server/src/main/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagMigrationExecutionProtocol.java":["9fbacb71fb333d4c6d90127255c12108321c2cec90666300e9bfbc5d7d82657c",8972],"server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationPlanCandidate.java":["e324adad954d337cfd92ec77f7fd5eb30db9d002b5be6a37d73c4a92e3161c8d",5394],"server/src/main/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationPlanCandidateFactory.java":["336d24f66a57becafb0ac579f18d89391a935070510456de8626224672abcb54",8504],"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionSuccessorAcceptance.java":["ef55aee6c941c124653138a482769e19a85ab72b5e3ed83ee6d15803b15c2d6d",91381],"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java":["c20a6bd120b9c6eb2e930b8d1ac574814c2ac075b893de717991dce7e4af631e",80004],"server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java":["6ed99111749568ffeffe8f04e029cc273a9e60d59b6fdaf3e6eefe5e2a668ffb",18511],"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightContractParityTest.java":["849d3fe9b644f7811c13c4ba24a119170f1120a38c86635c3a6d5942e8cd44b9",46172],"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java":["f3046ce6749f6f0facc3db8b18ee3227c04f6ff0ced54f4df56871e1b7192677",102737],"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreContractParityTest.java":["9076e30366370c7ed61b962c0a987d1c2b1758e749bd1cc44f98f43387c4fd5b",28965],"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCorePostPushAnchorContractParityTest.java":["124d72fa07fcb3306e5476416afc124a2e2d51549406a1fee8483b757a7ab7bc",20374],"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java":["35a2352ba8218594919dd2b08108c644ada708b9885300ccfa22d1f17a931831",89356],"server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAnchorAcceptance.java":["e81298382c14c91689348997e3ab6b9a9d1722fa0decbbd8f4a525bf0a07db74",51293],"server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java":["57e45fe2031115551b8ae1035751a8cb2ef3e0de7de500511d02acff3400bd73",12204],"server/src/test/java/io/saksk/ti/learning/infrastructure/migration/Ed25519TagMigrationEvidenceVerifierTest.java":["dac1055f16b551fe934aea35d820fdf04c6a356ea74d31f58afeb744feb53da7",32990],"server/src/test/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagMigrationExecutionProtocolStaticTest.java":["f6f3227cdcae98dbf348691359e3dd13c4cd3a1af045a19234030d117a19c989",11445],"server/src/test/java/io/saksk/ti/learning/infrastructure/migration/Phase4cLegacyPersonalBankTagMigrationExecutionProtocolIT.java":["cfd4b4944e5f7b40c18b0ae10ebec8efaca0ef71a63446079ab776217037c1da",75966],"server/src/test/java/io/saksk/ti/learning/infrastructure/migration/TagMigrationPlanCandidateFactoryTest.java":["12d2bb0f0e6f99a7731d1315900dd28a06020d7e16e23e9943477beff3842795",17286],"server/src/test/resources/db/phase4c/078-legacy-personal-bank-tag-migration-execution-protocol-schema.sql":["b93e738bff82e4c5b19fa41570e73f807aad2c32f78e8e7a6e517c42db5d9c9b",4368],"server/src/test/resources/db/phase4c/079-legacy-personal-bank-tag-migration-execution-protocol-seed.sql":["c84d8511797d16b85025561f591b9248105a38b99d1944b6b04332dfc62588fe",2068],"tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py":["90ff8b73b778025b16de2c46ec1b4e789f0e677fccd03f67a9aeea546b90753a",36240],"tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py":["bf4b24b4e9568dde5d88ee0985cd765c063ee09e9ec2e5dc9a19f59ee6f66f0b",65798],"tools/build_phase4c_tag_migration_global_preflight_contract.py":["4efc2cf1a1e0e637dab550d44783e90082d597a18496e2fe63b15fff65b89e66",129994],"tools/phase2_wormhole_successor_acceptance.py":["fed88c98f558a70398181b68edfabf2b75f2ab62184793230cb17a7efce96acd",32082],"tools/phase4c_http_target_execution_anchor_successor_acceptance.py":["e002d6aefee761693087cf549d65f84f4887bb5b7146f8c19b36d9810f3a4cf7",36566],"tools/phase4c_http_target_execution_successor_acceptance.py":["39f997767d20c0e0382c6277da873ae8062a5823cd78910c0f4209823ad682a0",84585],"tools/phase4c_tag_migration_global_preflight_successor_acceptance.py":["d7a116cb3432e280b97a076347b1e659be4cfe9a811d879ead4c4eb886a2679d",33035],"tools/phase4c_tag_migration_operator_core_successor_acceptance.py":["6efd1cb559a6d7da470c2a454dc981db9d7ff670f8053b8b9b9597af270b18f3",25844],"tools/test_phase2_wormhole_successor_acceptance.py":["cf2e7f8023ee9036f94e2ff46a1464b8af1bbe5e20e8b5382f49198bb50b9313",55974],"tools/test_phase4b_personal_bank_all_shares_entry_contract.py":["612e5de6dffc85b20e19f7cfb882bf2caa36a796d29c500cb0598b308781cc4c",25488],"tools/test_phase4b_personal_bank_all_shares_read_contract.py":["46f08e7c6e57696609eda1f89eaaba9023dd6dbe6a3ec999dbfaca6dfed49a1e",20644],"tools/test_phase4b_personal_bank_share_list_entry_contract.py":["7d692b2c577f584ba2534e20c017d941129fe7db50b38bb5f1597d1da697f806",34561],"tools/test_phase4b_personal_bank_share_list_read_contract.py":["1f3dceccb6637949f197637b2ca1edf0f0a7269b202cecf0a0da4cbf12fe8e6b",46740],"tools/test_phase4b_personal_bank_usage_stats_entry_contract.py":["9b9fcfc637a62a7407a56557846284d60a3c03a65bd82ebcd4641e840c488b59",26791],"tools/test_phase4b_personal_bank_usage_stats_read_contract.py":["a34dfbeab04bbcbe66847c7f033e56a76e202dbdb71a669a25c8baf9f0cac884",35656],"tools/test_phase4b_personal_bank_user_counts_entry_contract.py":["08af86b0cf2b6fb8c59d531500ddc58ca5b0ffc003929e054eb0062f9e25e638",37521],"tools/test_phase4c_personal_bank_user_counts_composition_contract.py":["c405f432a55caaa7ede0375b18fbc8819b82b3ffeb62e29f10ff5f0793b45c20",60642],"tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py":["a05b7f0052e66d4233227a9995f0fc9ea1f34cba00269c1ea0999acaa60d801b",32398],"tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py":["6ebf44750d2eb5320c79351e9fa7a2e242207da3e4a4c400a0e9b110625546e3",34398],"tools/test_phase4c_personal_bank_user_counts_read_contract.py":["d8c745ff35f298f91afb8a723bc7676187c7da4a67000b02eb7ab2752a0d3522",24536],"tools/test_phase4c_tag_migration_global_preflight_contract.py":["f40cfec25a0cbcd5ef250ba3ba93408cf73c397e77e1a7dd7d03c67da0b1ed1a",40427],"tools/test_phase4c_tag_migration_operator_core_contract.py":["3c480aa1fd2378ed2c059965663c516c3ed5390c3c1e165f9a7e6855176df4b5",19902],"tools/test_phase4c_tag_migration_operator_core_post_push_anchor_contract.py":["ca947234c2ffe31f929cbd443101c01215b6a8a2d2ea7d454afa950a83a3f120",18632]},"source_transitions":{"docs/refactor/05-progress.md":{"accepted_byte_count":109838,"accepted_sha256":"71fc8bf98bc4fb50645df473ee79b2bc33856ca928f49da7aecc96a7d1040f9d","source":"docs/refactor/05-progress.md","successor_byte_count":109911,"successor_sha256":"2fb55e0aaaeff28c3c3def877b5be51ae2ea6358272222f0e0f8232dec69867f"},"docs/refactor/phase4c/README.md":{"accepted_byte_count":29918,"accepted_sha256":"f061ac5e2b240e3b8c367f9db817c84346a309e9872cfbdeeafe8d3ff8689230","source":"docs/refactor/phase4c/README.md","successor_byte_count":31994,"successor_sha256":"ab5144697dfded1778d40209958a2c3fdcc7bfc1b08d5dde481cc6a8f009ed6e"},"infra/phase2/README.md":{"accepted_byte_count":8018,"accepted_sha256":"d5c8647397016f93c8ea2b5e83b41818ea00498fd7e699cc1119930f1995e21b","source":"infra/phase2/README.md","successor_byte_count":9031,"successor_sha256":"187895861b607be2cfddb63320b4ee52dc4efd7706e94afd5d56a07169832216"},"infra/phase2/verify-static.sh":{"accepted_byte_count":17491,"accepted_sha256":"2a1a5a5453a1090f6132971081d4ac2448803023acb50d474ced491bafe8efc3","source":"infra/phase2/verify-static.sh","successor_byte_count":18597,"successor_sha256":"6878d027fc21c1564840771609f0f2e9dfa6eb2bb483b56b6abfd1e9386eb4a3"},"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionSuccessorAcceptance.java":{"accepted_byte_count":91381,"accepted_sha256":"9f929532d8c31f96f4e3e5cd24ee199220c82ad2aac46f5944ee0d54cd22dbb6","source":"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionSuccessorAcceptance.java","successor_byte_count":91381,"successor_sha256":"ef55aee6c941c124653138a482769e19a85ab72b5e3ed83ee6d15803b15c2d6d"},"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java":{"accepted_byte_count":79867,"accepted_sha256":"cb4cabfce2cded7cde291b54d2c2dd98cc397887d24141e5164250a8811fb369","source":"server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java","successor_byte_count":80004,"successor_sha256":"c20a6bd120b9c6eb2e930b8d1ac574814c2ac075b893de717991dce7e4af631e"},"server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java":{"accepted_byte_count":17439,"accepted_sha256":"137f3a9911d886610300aecc95a13f05d5621d18c19acf491194f1b8b741efe3","source":"server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java","successor_byte_count":18511,"successor_sha256":"6ed99111749568ffeffe8f04e029cc273a9e60d59b6fdaf3e6eefe5e2a668ffb"},"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightContractParityTest.java":{"accepted_byte_count":43784,"accepted_sha256":"bdb3ee1169dfe164016a2afc6a46e6e3fff7abe9b8602988ab9d0c0ecff86158","source":"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightContractParityTest.java","successor_byte_count":46172,"successor_sha256":"849d3fe9b644f7811c13c4ba24a119170f1120a38c86635c3a6d5942e8cd44b9"},"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java":{"accepted_byte_count":102527,"accepted_sha256":"e5471121ea2fc52f9e36712b222578e24323d5785dddf27b27a86799867fc99f","source":"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java","successor_byte_count":102737,"successor_sha256":"f3046ce6749f6f0facc3db8b18ee3227c04f6ff0ced54f4df56871e1b7192677"},"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreContractParityTest.java":{"accepted_byte_count":27467,"accepted_sha256":"f7dad6c7d51769669fda0cb2c26a7c3991ad3bfae27178c9c8a470f6addff361","source":"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreContractParityTest.java","successor_byte_count":28965,"successor_sha256":"9076e30366370c7ed61b962c0a987d1c2b1758e749bd1cc44f98f43387c4fd5b"},"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCorePostPushAnchorContractParityTest.java":{"accepted_byte_count":19496,"accepted_sha256":"486bbc757e44408dc9237eade44ec3f4e2cd60bd2d3360c1cc54bdaf426eacb1","source":"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCorePostPushAnchorContractParityTest.java","successor_byte_count":20374,"successor_sha256":"124d72fa07fcb3306e5476416afc124a2e2d51549406a1fee8483b757a7ab7bc"},"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java":{"accepted_byte_count":83287,"accepted_sha256":"83840dc07301be40828df8bd46f214bc2d50342bde6f8fb8412eca1ae3a7092c","source":"server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java","successor_byte_count":89356,"successor_sha256":"35a2352ba8218594919dd2b08108c644ada708b9885300ccfa22d1f17a931831"},"server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAnchorAcceptance.java":{"accepted_byte_count":51156,"accepted_sha256":"bd83bffe8851e2368f3d9280d213b7adac1b4073dbe2296bd1d6e1c6183a454e","source":"server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAnchorAcceptance.java","successor_byte_count":51293,"successor_sha256":"e81298382c14c91689348997e3ab6b9a9d1722fa0decbbd8f4a525bf0a07db74"},"server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java":{"accepted_byte_count":11762,"accepted_sha256":"ea9affd42829d4560c2b974e8d189bd6feac340112732cf15b89d797f7b4f7af","source":"server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java","successor_byte_count":12204,"successor_sha256":"57e45fe2031115551b8ae1035751a8cb2ef3e0de7de500511d02acff3400bd73"},"tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py":{"accepted_byte_count":36240,"accepted_sha256":"8d96674c8ea55f6050133945f0f58fe365ea9383d7660ba3c6d3423cf63bc7c5","source":"tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py","successor_byte_count":36240,"successor_sha256":"90ff8b73b778025b16de2c46ec1b4e789f0e677fccd03f67a9aeea546b90753a"},"tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py":{"accepted_byte_count":65798,"accepted_sha256":"c9d21809bd136ed131ee20ac6baabf0b6b67bcc85f03fab9fccedcd02c86f2c0","source":"tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py","successor_byte_count":65798,"successor_sha256":"bf4b24b4e9568dde5d88ee0985cd765c063ee09e9ec2e5dc9a19f59ee6f66f0b"},"tools/build_phase4c_tag_migration_global_preflight_contract.py":{"accepted_byte_count":129684,"accepted_sha256":"604c550ceb144c0bdca1d92e915a166d84c582cd53084f934bac71e171154ddf","source":"tools/build_phase4c_tag_migration_global_preflight_contract.py","successor_byte_count":129994,"successor_sha256":"4efc2cf1a1e0e637dab550d44783e90082d597a18496e2fe63b15fff65b89e66"},"tools/phase2_wormhole_successor_acceptance.py":{"accepted_byte_count":30285,"accepted_sha256":"afd967894036289ad3587fc740c97931d1ca5492a9208829536bf6745a840ebc","source":"tools/phase2_wormhole_successor_acceptance.py","successor_byte_count":32082,"successor_sha256":"fed88c98f558a70398181b68edfabf2b75f2ab62184793230cb17a7efce96acd"},"tools/phase4c_http_target_execution_anchor_successor_acceptance.py":{"accepted_byte_count":36566,"accepted_sha256":"810efb88c88efeb35b7a1f182214dc8873ca7099d8f6dfb8ce6b1af651dd3ecd","source":"tools/phase4c_http_target_execution_anchor_successor_acceptance.py","successor_byte_count":36566,"successor_sha256":"e002d6aefee761693087cf549d65f84f4887bb5b7146f8c19b36d9810f3a4cf7"},"tools/phase4c_http_target_execution_successor_acceptance.py":{"accepted_byte_count":84585,"accepted_sha256":"4048e962b5db2d332c0955099a77637c3542b77e58fd233b5460296c1f86abd9","source":"tools/phase4c_http_target_execution_successor_acceptance.py","successor_byte_count":84585,"successor_sha256":"39f997767d20c0e0382c6277da873ae8062a5823cd78910c0f4209823ad682a0"},"tools/phase4c_tag_migration_global_preflight_successor_acceptance.py":{"accepted_byte_count":32367,"accepted_sha256":"6fe3bf23d53ccaccd33f3ccaf31466cf0fc44df0f71bcc6f798765519fe12f95","source":"tools/phase4c_tag_migration_global_preflight_successor_acceptance.py","successor_byte_count":33035,"successor_sha256":"d7a116cb3432e280b97a076347b1e659be4cfe9a811d879ead4c4eb886a2679d"},"tools/phase4c_tag_migration_operator_core_successor_acceptance.py":{"accepted_byte_count":17419,"accepted_sha256":"c7e672f3a0d0ab959735de906c0e5131232c0dab17b698480f6a42cfb5871ee4","source":"tools/phase4c_tag_migration_operator_core_successor_acceptance.py","successor_byte_count":25844,"successor_sha256":"6efd1cb559a6d7da470c2a454dc981db9d7ff670f8053b8b9b9597af270b18f3"},"tools/test_phase2_wormhole_successor_acceptance.py":{"accepted_byte_count":54340,"accepted_sha256":"2c4881c5083c8e4ca2cf294ece486895e26d932d1f59d067f8da32ef544c63bc","source":"tools/test_phase2_wormhole_successor_acceptance.py","successor_byte_count":55974,"successor_sha256":"cf2e7f8023ee9036f94e2ff46a1464b8af1bbe5e20e8b5382f49198bb50b9313"},"tools/test_phase4b_personal_bank_all_shares_entry_contract.py":{"accepted_byte_count":24250,"accepted_sha256":"ab79ec3edc9f903a9917ae85450633982031f341aa219e75de08d69db0c63d26","source":"tools/test_phase4b_personal_bank_all_shares_entry_contract.py","successor_byte_count":25488,"successor_sha256":"612e5de6dffc85b20e19f7cfb882bf2caa36a796d29c500cb0598b308781cc4c"},"tools/test_phase4b_personal_bank_all_shares_read_contract.py":{"accepted_byte_count":19452,"accepted_sha256":"a308ba6b14bb9e960006378bdf165dc2dfece856bb09bf827d600a7a6f28e060","source":"tools/test_phase4b_personal_bank_all_shares_read_contract.py","successor_byte_count":20644,"successor_sha256":"46f08e7c6e57696609eda1f89eaaba9023dd6dbe6a3ec999dbfaca6dfed49a1e"},"tools/test_phase4b_personal_bank_share_list_entry_contract.py":{"accepted_byte_count":33266,"accepted_sha256":"3b59d4f9f4c3cafe84feb4bc0a902db1822455e73660f29461d2385370377122","source":"tools/test_phase4b_personal_bank_share_list_entry_contract.py","successor_byte_count":34561,"successor_sha256":"7d692b2c577f584ba2534e20c017d941129fe7db50b38bb5f1597d1da697f806"},"tools/test_phase4b_personal_bank_share_list_read_contract.py":{"accepted_byte_count":45548,"accepted_sha256":"49441844f63e05ca57e0b89c751cca3b1b574c984223e588d40bac9e7613501f","source":"tools/test_phase4b_personal_bank_share_list_read_contract.py","successor_byte_count":46740,"successor_sha256":"1f3dceccb6637949f197637b2ca1edf0f0a7269b202cecf0a0da4cbf12fe8e6b"},"tools/test_phase4b_personal_bank_usage_stats_entry_contract.py":{"accepted_byte_count":25599,"accepted_sha256":"9625aad3553408ef631d055735af33b4b21847aaaf8a57d540dd582cba025ab9","source":"tools/test_phase4b_personal_bank_usage_stats_entry_contract.py","successor_byte_count":26791,"successor_sha256":"9b9fcfc637a62a7407a56557846284d60a3c03a65bd82ebcd4641e840c488b59"},"tools/test_phase4b_personal_bank_usage_stats_read_contract.py":{"accepted_byte_count":34464,"accepted_sha256":"7c8a27ef4e97ed731dd4b0dd357942e32e75a45db3d9e482e7513b1e8c1820a4","source":"tools/test_phase4b_personal_bank_usage_stats_read_contract.py","successor_byte_count":35656,"successor_sha256":"a34dfbeab04bbcbe66847c7f033e56a76e202dbdb71a669a25c8baf9f0cac884"},"tools/test_phase4b_personal_bank_user_counts_entry_contract.py":{"accepted_byte_count":37035,"accepted_sha256":"409a2663e26f559108e815a805f42f566f2a7dfea8d1da8f9aab966efa0a14cb","source":"tools/test_phase4b_personal_bank_user_counts_entry_contract.py","successor_byte_count":37521,"successor_sha256":"08af86b0cf2b6fb8c59d531500ddc58ca5b0ffc003929e054eb0062f9e25e638"},"tools/test_phase4c_personal_bank_user_counts_composition_contract.py":{"accepted_byte_count":60156,"accepted_sha256":"18cdd0df59a7cfa6d052192ca85fe59cd50415fe263ae172133958d59df1f544","source":"tools/test_phase4c_personal_bank_user_counts_composition_contract.py","successor_byte_count":60642,"successor_sha256":"c405f432a55caaa7ede0375b18fbc8819b82b3ffeb62e29f10ff5f0793b45c20"},"tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py":{"accepted_byte_count":32398,"accepted_sha256":"17e77b5204bdec0b2deb43517354fada893802321a1cfa8f446151fcb5a2b0c9","source":"tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py","successor_byte_count":32398,"successor_sha256":"a05b7f0052e66d4233227a9995f0fc9ea1f34cba00269c1ea0999acaa60d801b"},"tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py":{"accepted_byte_count":34398,"accepted_sha256":"7e6039fd7288cd16980149b385f71faa79659092f5bd187c14d060a19c08fe84","source":"tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py","successor_byte_count":34398,"successor_sha256":"6ebf44750d2eb5320c79351e9fa7a2e242207da3e4a4c400a0e9b110625546e3"},"tools/test_phase4c_personal_bank_user_counts_read_contract.py":{"accepted_byte_count":24536,"accepted_sha256":"3aacc3a54b0ecc6314f0f84d51057f657e8c188d1f673d931092c40c3f39106b","source":"tools/test_phase4c_personal_bank_user_counts_read_contract.py","successor_byte_count":24536,"successor_sha256":"d8c745ff35f298f91afb8a723bc7676187c7da4a67000b02eb7ab2752a0d3522"},"tools/test_phase4c_tag_migration_global_preflight_contract.py":{"accepted_byte_count":38541,"accepted_sha256":"28548d878900d0aeba6b983ba307af077b4ebdd01a6b27f4c496bf6ae472c313","source":"tools/test_phase4c_tag_migration_global_preflight_contract.py","successor_byte_count":40427,"successor_sha256":"f40cfec25a0cbcd5ef250ba3ba93408cf73c397e77e1a7dd7d03c67da0b1ed1a"},"tools/test_phase4c_tag_migration_operator_core_contract.py":{"accepted_byte_count":18250,"accepted_sha256":"d3f89f0943d6aace6545f3f97ccc997d0c3aee9bc7175363bd47930281dfa42f","source":"tools/test_phase4c_tag_migration_operator_core_contract.py","successor_byte_count":19902,"successor_sha256":"3c480aa1fd2378ed2c059965663c516c3ed5390c3c1e165f9a7e6855176df4b5"},"tools/test_phase4c_tag_migration_operator_core_post_push_anchor_contract.py":{"accepted_byte_count":17715,"accepted_sha256":"2ddf897a07152d1a4a12f044ffe3d290591f86a3b21463aa1e25d74186345cb0","source":"tools/test_phase4c_tag_migration_operator_core_post_push_anchor_contract.py","successor_byte_count":18632,"successor_sha256":"ca947234c2ffe31f929cbd443101c01215b6a8a2d2ea7d454afa950a83a3f120"}},"worm_byte_count":1442,"worm_sha256":"5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c"}''')
SOURCE_FILES: dict[str, tuple[str, int]] = {
    relative: (str(descriptor[0]), int(descriptor[1]))
    for relative, descriptor in _FIXED_MAP.get("source_files", {}).items()
}
SOURCE_TRANSITIONS: dict[str, dict[str, Any]] = {
    relative: dict(descriptor)
    for relative, descriptor in _FIXED_MAP.get(
        "source_transitions", {}
    ).items()
}

PRODUCTION_RUNTIME_ADDITION_PATHS = (
    MIGRATION_MAIN_PREFIX + "Ed25519TagMigrationEvidenceVerifier.java",
    MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagMigrationExecutionProtocol.java",
    MIGRATION_MAIN_PREFIX + "TagMigrationPlanCandidate.java",
    MIGRATION_MAIN_PREFIX + "TagMigrationPlanCandidateFactory.java",
)
PRODUCTION_RUNTIME_ADDITIONS: dict[str, str] = {
    str(relative): str(digest)
    for relative, digest in _FIXED_MAP.get(
        "production_runtime_additions", {}
    ).items()
}
ACCEPTED_PRODUCTION_FILE_COUNT = 307
ACCEPTED_PRODUCTION_MANIFEST_SHA256 = (
    "b1228337b60b752ff088c4e5b67ae21092ca75a07c437bae35cc67b39b1c8c25"
)
CURRENT_PRODUCTION_FILE_COUNT = 311
CURRENT_PRODUCTION_MANIFEST_SHA256: str | None = _FIXED_MAP.get(
    "current_production_manifest_sha256"
)
ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT = 50
ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256 = (
    "3abdc97486bbb9ec62a2d426063157e0ef3a990a34ca4862fc9e18580b4f60e9"
)
CURRENT_LEARNING_PERSONALBANK_MAIN_FILE_COUNT = 54
CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256: str | None = (
    _FIXED_MAP.get("current_learning_personalbank_main_manifest_sha256")
)
WORM_SHA256: str | None = _FIXED_MAP.get("worm_sha256")
WORM_BYTE_COUNT: int | None = _FIXED_MAP.get("worm_byte_count")
CURRENT_BUILD_CONTEXT_SHA256: str | None = _FIXED_MAP.get(
    "current_build_context_sha256"
)

FIXED_NON_CONTROL_SOURCE_COUNT = 48
CONTROL_SOURCE_COUNT = 7
IMPLEMENTATION_SOURCE_COUNT = 11
SOURCE_TRANSITION_COUNT = 37
NEWLY_CLOSED_GATES = (
    "migration_execution_protocol_implemented",
    "cryptographic_evidence_verifier_implemented",
    "local_test_backup_restore_execution_rehearsal_closed",
)
ROUTE_STATE = {
    "migrated_operation_count": 13,
    "pending_operation_count": 598,
    "production_cutover_operation_count": 0,
    "total_operation_count": 611,
    "legacy_flask_remains_production_owner": True,
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def document_payload_sha256(document: Mapping[str, Any]) -> str:
    return sha256_json(
        {
            key: value
            for key, value in document.items()
            if key != "document_payload_sha256"
        }
    )


def serialized_contract(document: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in ("", ".", "..") for part in candidate.parts)
    ):
        raise AssertionError(
            f"execution-protocol path escapes fixed root: {relative}"
        )
    resolved_root = root.resolve(strict=True)
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(
                f"execution-protocol fixed source is a symlink: {relative}"
            )
    try:
        resolved = cursor.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, ValueError) as error:
        raise AssertionError(
            f"execution-protocol fixed source is absent or escaped: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(
            f"execution-protocol fixed source is not regular: {relative}"
        )
    return resolved


def _validated_json(
    root: Path,
    relative: str,
    sha256: str,
    byte_count: int,
    payload_sha256: str | None = None,
) -> dict[str, Any]:
    payload = fixed_regular_file(root, relative).read_bytes()
    if len(payload) != byte_count or sha256_bytes(payload) != sha256:
        raise AssertionError(
            f"execution-protocol fixed JSON bytes drifted: {relative}"
        )
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(
            f"execution-protocol fixed JSON is unreadable: {relative}"
        ) from error
    if not isinstance(document, dict):
        raise AssertionError(
            f"execution-protocol fixed JSON is not an object: {relative}"
        )
    if payload_sha256 is not None and (
        document.get("document_payload_sha256") != payload_sha256
        or document_payload_sha256(document) != payload_sha256
    ):
        raise AssertionError(
            f"execution-protocol fixed JSON payload drifted: {relative}"
        )
    return document


def load_predecessor(root: Path = ROOT) -> dict[str, Any]:
    document = _validated_json(
        root,
        PREDECESSOR_RELATIVE,
        PREDECESSOR_SHA256,
        PREDECESSOR_BYTE_COUNT,
        PREDECESSOR_PAYLOAD_SHA256,
    )
    if (
        document.get("contract_id") != PREDECESSOR_ID
        or document.get("captured_at") != PREDECESSOR_CAPTURED_AT
        or document.get("scope") != PREDECESSOR_SCOPE
        or document.get("status") != PREDECESSOR_STATUS
    ):
        raise AssertionError("execution-protocol predecessor identity drifted")
    checkpoint = document.get("independent_acceptance_checkpoint", {})
    if (
        checkpoint.get("commit_oid")
        != PREDECESSOR_INDEPENDENT_ACCEPTANCE_COMMIT
        or checkpoint.get("parent_is_implementation_checkpoint") is not True
        or checkpoint.get("exact_two_added_path_delta") is not True
        or document.get("acceptance", {}).get("c2_self_anchor_complete")
        is not False
        or document.get("current_node_trust_boundary", {}).get(
            "c2_commit_or_tree_identity_embedded"
        )
        is not False
    ):
        raise AssertionError("execution-protocol C2 checkpoint drifted")
    authorization = document.get("authorization", {})
    required_true = (
        "migration_global_preflight_evidence_closed",
        "migration_durable_ledger_freeze_design_evidence_closed",
        "operator_core_evidence_closed",
        "bounded_40001_40P01_retry_implemented",
        "operator_migration_implementation",
        "source_successor_external_git_anchor_complete",
        "semantic_successor_external_git_anchor_complete",
        "bootstrap_control_sources_external_git_anchor_complete",
        "operator_core_control_sources_external_git_anchor_complete",
        "independent_acceptance_control_sources_external_git_anchor_complete",
    )
    required_false = (
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
        "production_cutover",
        "current_node_control_sources_external_git_anchor_complete",
    )
    if (
        any(authorization.get(key) is not True for key in required_true)
        or any(authorization.get(key) is not False for key in required_false)
        or document.get("route_state") != ROUTE_STATE
    ):
        raise AssertionError("execution-protocol predecessor authority drifted")
    return document


def _require_fixed_maps() -> None:
    if (
        len(SOURCE_FILES) != FIXED_NON_CONTROL_SOURCE_COUNT
        or len(SOURCE_TRANSITIONS) != SOURCE_TRANSITION_COUNT
        or len(PRODUCTION_RUNTIME_ADDITIONS) != 4
        or CURRENT_PRODUCTION_MANIFEST_SHA256 is None
        or CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256 is None
        or WORM_SHA256 is None
        or WORM_BYTE_COUNT is None
        or CURRENT_BUILD_CONTEXT_SHA256 is None
    ):
        raise AssertionError(
            "execution-protocol fixed map requires explicit mechanical refresh"
        )


def validated_source(root: Path, relative: str) -> bytes:
    if relative not in SOURCE_FILES or relative in CONTROL_SOURCES:
        raise AssertionError(
            f"execution-protocol unknown or self-authority source: {relative}"
        )
    expected_sha256, expected_byte_count = SOURCE_FILES[relative]
    payload = fixed_regular_file(root, relative).read_bytes()
    if (
        len(payload) != expected_byte_count
        or sha256_bytes(payload) != expected_sha256
    ):
        raise AssertionError(
            f"execution-protocol fixed source bytes drifted: {relative}"
        )
    return payload


def _validate_sources(root: Path) -> None:
    _require_fixed_maps()
    if (
        len(CONTROL_SOURCES) != CONTROL_SOURCE_COUNT
        or len(set(CONTROL_SOURCES)) != CONTROL_SOURCE_COUNT
        or len(IMPLEMENTATION_SOURCE_PATHS) != IMPLEMENTATION_SOURCE_COUNT
        or len(set(IMPLEMENTATION_SOURCE_PATHS)) != IMPLEMENTATION_SOURCE_COUNT
        or len(SOURCE_TRANSITION_PATHS) != SOURCE_TRANSITION_COUNT
        or len(set(SOURCE_TRANSITION_PATHS)) != SOURCE_TRANSITION_COUNT
        or set(SOURCE_FILES)
        != set(IMPLEMENTATION_SOURCE_PATHS).union(SOURCE_TRANSITION_PATHS)
        or set(SOURCE_TRANSITIONS) != set(SOURCE_TRANSITION_PATHS)
        or set(SOURCE_FILES).intersection(CONTROL_SOURCES)
    ):
        raise AssertionError("execution-protocol source/control partition drifted")
    for relative in SOURCE_FILES:
        validated_source(root, relative)
    for relative, transition in SOURCE_TRANSITIONS.items():
        successor_sha256, successor_byte_count = SOURCE_FILES[relative]
        expected = {
            "source": relative,
            "accepted_sha256": transition["accepted_sha256"],
            "accepted_byte_count": transition["accepted_byte_count"],
            "successor_sha256": successor_sha256,
            "successor_byte_count": successor_byte_count,
        }
        if transition != expected:
            raise AssertionError(
                f"execution-protocol transition descriptor drifted: {relative}"
            )
        if (
            transition["accepted_sha256"] == successor_sha256
            and transition["accepted_byte_count"] == successor_byte_count
        ):
            raise AssertionError(
                f"execution-protocol transition is a no-op: {relative}"
            )


def _learning_personalbank_main(files: Mapping[str, str]) -> dict[str, str]:
    prefixes = (
        "server/src/main/java/io/saksk/ti/learning/",
        "server/src/main/java/io/saksk/ti/personalbank/",
    )
    return {
        relative: digest
        for relative, digest in sorted(files.items())
        if relative.startswith(prefixes)
    }


def production_runtime_manifests(
    root: Path = ROOT,
) -> tuple[dict[str, str], dict[str, str]]:
    _require_fixed_maps()
    # Node C reconstructs its 307-file manifest from fixed JSON and fixed
    # additions.  It is Gitless and does not discover the current runtime tree.
    _, accepted = node_c.production_runtime_manifests(root)
    if (
        len(accepted) != ACCEPTED_PRODUCTION_FILE_COUNT
        or sha256_json(accepted) != ACCEPTED_PRODUCTION_MANIFEST_SHA256
    ):
        raise AssertionError("execution-protocol accepted runtime drifted")
    if set(PRODUCTION_RUNTIME_ADDITIONS).intersection(accepted):
        raise AssertionError("execution-protocol runtime addition already existed")
    for relative, digest in PRODUCTION_RUNTIME_ADDITIONS.items():
        payload = fixed_regular_file(root, relative).read_bytes()
        if sha256_bytes(payload) != digest:
            raise AssertionError(
                f"execution-protocol runtime bytes drifted: {relative}"
            )
    current = dict(accepted)
    current.update(PRODUCTION_RUNTIME_ADDITIONS)
    current = dict(sorted(current.items()))
    if (
        len(current) != CURRENT_PRODUCTION_FILE_COUNT
        or sha256_json(current) != CURRENT_PRODUCTION_MANIFEST_SHA256
    ):
        raise AssertionError("execution-protocol current runtime drifted")
    return dict(sorted(accepted.items())), current


def _runtime_successor(root: Path) -> dict[str, Any]:
    accepted, current = production_runtime_manifests(root)
    accepted_main = _learning_personalbank_main(accepted)
    current_main = _learning_personalbank_main(current)
    if (
        len(accepted_main) != ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or sha256_json(accepted_main)
        != ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
        or len(current_main) != CURRENT_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or sha256_json(current_main)
        != CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
    ):
        raise AssertionError("execution-protocol learning runtime drifted")
    additions = dict(sorted(PRODUCTION_RUNTIME_ADDITIONS.items()))
    return {
        "accepted_file_count": ACCEPTED_PRODUCTION_FILE_COUNT,
        "accepted_manifest_sha256": ACCEPTED_PRODUCTION_MANIFEST_SHA256,
        "current_file_count": CURRENT_PRODUCTION_FILE_COUNT,
        "current_manifest_sha256": CURRENT_PRODUCTION_MANIFEST_SHA256,
        "unchanged_file_count": ACCEPTED_PRODUCTION_FILE_COUNT,
        "added_files": additions,
        "changed_files": {},
        "deleted_files": [],
        "exact_delta": "4A0M0D",
        "unknown_or_extra_files": "reject",
        "learning_personalbank_main": {
            "accepted_file_count": ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT,
            "accepted_manifest_sha256": (
                ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
            ),
            "current_file_count": CURRENT_LEARNING_PERSONALBANK_MAIN_FILE_COUNT,
            "current_manifest_sha256": (
                CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
            ),
            "unchanged_file_count": ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT,
            "added_files": additions,
            "changed_files": {},
            "deleted_files": [],
            "exact_delta": "4A0M0D",
        },
    }


def _validate_worm(root: Path) -> dict[str, Any]:
    _require_fixed_maps()
    predecessor = _validated_json(
        root,
        WORM_PREDECESSOR_RELATIVE,
        WORM_PREDECESSOR_SHA256,
        WORM_PREDECESSOR_BYTE_COUNT,
    )
    current = json.loads(validated_source(root, WORM_RELATIVE))
    if not isinstance(current, dict):
        raise AssertionError("execution-protocol Node 9 WORM is not an object")
    if (
        current.get("schemaVersion") != 1
        or current.get("source") != predecessor.get("source")
        or current.get("restore") != predecessor.get("restore")
        or current.get("readRole") != predecessor.get("readRole")
        or current.get("productionDatabaseVersion") != "unknown"
        or current.get("flywayBaselineCreated") is not False
    ):
        raise AssertionError("execution-protocol Node 9 WORM facts drifted")
    java = current.get("java", {})
    if (
        java.get("dockerfileSha256") != DOCKERFILE_SHA256
        or java.get("buildContextSha256") != CURRENT_BUILD_CONTEXT_SHA256
        or java.get("hibernateDdlAuto") != "validate"
        or java.get("startupPassed") is not True
        or java.get("readinessPassed") is not True
    ):
        raise AssertionError("execution-protocol Node 9 Java WORM drifted")
    return current


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    predecessor = load_predecessor(resolved_root)
    _validate_sources(resolved_root)
    worm = _validate_worm(resolved_root)
    runtime = _runtime_successor(resolved_root)
    source_descriptors = {
        relative: {
            "source": relative,
            "sha256": digest,
            "byte_count": byte_count,
        }
        for relative, (digest, byte_count) in sorted(SOURCE_FILES.items())
    }
    transitions = {
        relative: deepcopy(value)
        for relative, value in sorted(SOURCE_TRANSITIONS.items())
    }
    document: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "captured_at": CAPTURED_AT,
        "scope": SCOPE,
        "status": STATUS,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "contract_id": PREDECESSOR_ID,
            "captured_at": PREDECESSOR_CAPTURED_AT,
            "scope": PREDECESSOR_SCOPE,
            "status": PREDECESSOR_STATUS,
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "fixed_commit_oid": PREDECESSOR_COMMIT,
            "immutable": True,
        },
        "execution_protocol": {
            "owner": "learning",
            "entrypoint": (
                "io.saksk.ti.learning.infrastructure.migration."
                "LegacyPersonalBankTagMigrationExecutionProtocol"
            ),
            "candidate_factory": (
                "io.saksk.ti.learning.infrastructure.migration."
                "TagMigrationPlanCandidateFactory"
            ),
            "explicit_callable_only": True,
            "public_phases": ["prepare", "freeze", "apply", "recover"],
            "execute_all_force_reset_skip_or_rollback_entrypoint": False,
            "spring_bean_runner_scheduler_http_cli_registration": False,
            "environment_file_redis_kms_or_network_key_discovery": False,
            "candidate_requires_fresh_complete_data_eligible_preflight": True,
            "candidate_digest_binds_two_uuids_and_nine_run_binding_digests": True,
            "candidate_is_not_apply_authorization": True,
            "preverification_before_jdbc_or_membership_access": True,
            "same_verifier_and_evidence_reverified_by_operator_core": True,
            "one_explicit_phase_per_invocation": True,
            "core_result_returned_without_state_reinterpretation": True,
        },
        "cryptographic_evidence_verifier": {
            "algorithm": "pure-Ed25519",
            "canonical_binary_wire_version": 1,
            "purposes": ["PREPARE", "FREEZE", "APPLY", "RECOVERY"],
            "explicit_immutable_trust_snapshot": True,
            "raw_public_key_bytes": 32,
            "signature_bytes": 64,
            "purpose_domain_separation": True,
            "unknown_duplicate_optional_or_trailing_fields_rejected": True,
            "json_jwt_java_serialization_der_spki_wire_rejected": True,
            "dynamic_algorithm_dispatch": False,
            "bounded_clock_skew_and_evidence_lifetime": True,
            "key_validity_revocation_issuer_key_id_and_purpose_checked": True,
            "candidate_digest_recomputed_from_ids_and_binding": True,
            "prepare_and_apply_receipts_derived_from_verified_envelope": True,
            "writer_stop_receipts_pairwise_distinct": True,
            "durable_nonce_or_evidence_uuid_journal": False,
            "global_single_use_claimed": False,
        },
        "local_disposable_rehearsal": {
            "fixture_schema_scripts": [
                (
                    "server/src/test/resources/db/phase4c/"
                    "078-legacy-personal-bank-tag-migration-"
                    "execution-protocol-schema.sql"
                ),
                (
                    "server/src/test/resources/db/phase4c/"
                    "079-legacy-personal-bank-tag-migration-"
                    "execution-protocol-seed.sql"
                ),
            ],
            "postgresql_versions": ["16.14", "18.4"],
            "writer_identity_count": 6,
            "writer_domain_expectation_count": 18,
            "writer_sessions_drained_and_reconnections_rejected": True,
            "real_local_custom_dump_and_restore": True,
            "artifact_raw_sha256_and_separate_manifest_sha256": True,
            "corrupt_artifact_rejected_before_restore": True,
            "restored_database_identity_must_differ": True,
            "restored_business_and_schema_fingerprint_must_match": True,
            "fresh_preflight_before_candidate": True,
            "wrong_binding_rejected_before_dml": True,
            "four_explicit_phases_and_state_specific_zero_dml_replay": True,
            "source_fingerprint_unchanged": True,
            "disposable_database_role_dump_and_connection_residue": 0,
            "production_backup_restore_or_rollback_evidence": False,
            "production_writer_freeze_evidence": False,
        },
        "historical_source_successors": {
            "predecessor_checkpoint": PREDECESSOR_COMMIT,
            "override_count": len(transitions),
            "overrides": transitions,
            "accepted_bytes_replayable_only_by_explicit_fixed_commit": True,
            "successor_external_git_anchor_complete": False,
            "unknown_path": "reject",
        },
        "production_runtime_successor": runtime,
        "worm_successor": {
            "accepted_report": {
                "source": WORM_PREDECESSOR_RELATIVE,
                "sha256": WORM_PREDECESSOR_SHA256,
                "byte_count": WORM_PREDECESSOR_BYTE_COUNT,
            },
            "accepted_build_context_sha256": ACCEPTED_BUILD_CONTEXT_SHA256,
            "accepted_chain_node_count": 8,
            "current_report": {
                "source": WORM_RELATIVE,
                "sha256": WORM_SHA256,
                "byte_count": WORM_BYTE_COUNT,
                "captured_at": worm.get("capturedAt"),
            },
            "current_build_context_sha256": CURRENT_BUILD_CONTEXT_SHA256,
            "dockerfile_sha256": DOCKERFILE_SHA256,
            "current_chain_node_count": 9,
            "appended_node_count": 1,
            "historical_nodes_rewritten": False,
            "production_database_version": "unknown",
            "flyway_baseline_created": False,
        },
        "evidence": {
            "classification": (
                "test-only explicit protocol, canonical Ed25519 verifier and "
                "local disposable backup/restore rehearsal"
            ),
            "postgresql_versions": ["16.14", "18.4"],
            "production_connection_or_credentials_used": False,
            "production_data_read_or_mutated": False,
            "production_operator_executed": False,
            "production_receipt_or_private_key_issued": False,
            "user_compose_or_production_docker_mutated": False,
        },
        "authorization": {
            "newly_closed_gates": list(NEWLY_CLOSED_GATES),
            "migration_global_preflight_evidence_closed": True,
            "migration_durable_ledger_freeze_design_evidence_closed": True,
            "operator_core_evidence_closed": True,
            "bounded_40001_40P01_retry_implemented": True,
            "operator_migration_implementation": True,
            "migration_execution_protocol_implemented": True,
            "cryptographic_evidence_verifier_implemented": True,
            "local_test_backup_restore_execution_rehearsal_closed": True,
            "migration_design_closed": False,
            "production_durable_ledger_or_tombstone": False,
            "production_source_write_freeze_evidence_closed": False,
            "production_target_write_freeze_evidence_closed": False,
            "production_membership_write_freeze_or_digest_recheck_evidence_closed": False,
            "production_connection_drain_evidence_closed": False,
            "production_schema_or_index": False,
            "flyway_baseline_or_migration": False,
            "backup_and_rollback_evidence_closed": False,
            "real_data_migration_execution": False,
            "production_trust_roots_or_key_rotation_audit": False,
            "durable_evidence_nonce_journal": False,
            "operator_runtime_wiring": False,
            "legacy_runtime_permanently_disabled": False,
            "route_or_openapi_delta": False,
            "client_gateway_or_proxy_change": False,
            "production_cutover": False,
            "source_successor_external_git_anchor_complete": False,
            "semantic_successor_external_git_anchor_complete": False,
            "bootstrap_control_sources_external_git_anchor_complete": False,
            "current_node_control_sources_external_git_anchor_complete": False,
        },
        "route_state": deepcopy(ROUTE_STATE),
        "source_authority": {
            "fixed_non_control_source_count": len(source_descriptors),
            "implementation_source_count": len(IMPLEMENTATION_SOURCE_PATHS),
            "transition_source_count": len(SOURCE_TRANSITION_PATHS),
            "fixed_non_control_sources": source_descriptors,
            "control_source_count": len(CONTROL_SOURCES),
            "control_sources": list(CONTROL_SOURCES),
            "control_sources_excluded_from_self_authority": True,
            "current_control_sources_external_git_anchor_complete": False,
            "fixed_source_allowlist_exact": True,
            "dynamic_source_discovery": False,
            "ordinary_build_and_load_are_gitless": True,
            "live_head_main_or_origin_authority": False,
            "fixed_c2_commit_replay_is_explicit_only": True,
            "unknown_source": "reject",
            "absolute_parent_escape_or_symlink": "reject",
            "historical_contract_or_worm_overwrite": False,
        },
        "next_gate": {
            "required_next": (
                "externally anchor Node D, then separately authorize real "
                "production schema, writer freeze, backup and apply work"
            ),
            "node_d_is_production_apply_authorization": False,
            "production_execution_requires_explicit_user_authorization": True,
        },
    }
    if predecessor["operator_core_contract"]["sha256"] != (
        "2124d1b042f2df201ad3d8ca87fd19fa121b8d47cbaf51a60eb5271fe55b7fe8"
    ):
        raise AssertionError("execution-protocol transitive Node C contract drifted")
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def _run_fixed_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "main", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("execution-protocol live Git authority is forbidden")
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "LC_ALL": "C",
        }
    )
    try:
        completed = subprocess.run(
            ("git", "--no-optional-locks", *arguments),
            cwd=repository_root,
            env=environment,
            check=True,
            timeout=30,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise AssertionError(
            "execution-protocol fixed C2 Git replay failed"
        ) from error
    return completed.stdout


def validate_predecessor_git(repository_root: Path) -> None:
    """Explicitly replay accepted transition bytes from fixed C2 only."""
    root = repository_root.resolve(strict=True)
    top = _run_fixed_git(root, "rev-parse", "--show-toplevel").decode().strip()
    if Path(top).resolve() != root:
        raise AssertionError("execution-protocol Git replay root drifted")
    commit = _run_fixed_git(
        root, "rev-parse", "--verify", f"{PREDECESSOR_COMMIT}^{{commit}}"
    ).decode().strip()
    if commit != PREDECESSOR_COMMIT:
        raise AssertionError("execution-protocol fixed C2 commit drifted")
    _require_fixed_maps()
    for relative in SOURCE_TRANSITION_PATHS:
        payload = _run_fixed_git(
            root,
            "cat-file",
            "blob",
            f"{PREDECESSOR_COMMIT}:Ti-Java/{relative}",
        )
        transition = SOURCE_TRANSITIONS[relative]
        if (
            len(payload) != transition["accepted_byte_count"]
            or sha256_bytes(payload) != transition["accepted_sha256"]
        ):
            raise AssertionError(
                f"execution-protocol fixed C2 source drifted: {relative}"
            )


def refreshed_fixed_map(root: Path, repository_root: Path) -> dict[str, Any]:
    """Return fixed literals from two explicit allowlists; never discover paths."""
    resolved_root = root.resolve(strict=True)
    repository = repository_root.resolve(strict=True)
    commit = _run_fixed_git(
        repository,
        "rev-parse",
        "--verify",
        f"{PREDECESSOR_COMMIT}^{{commit}}",
    ).decode().strip()
    if commit != PREDECESSOR_COMMIT:
        raise AssertionError("execution-protocol refresh C2 commit drifted")

    sources: dict[str, list[Any]] = {}
    transitions: dict[str, dict[str, Any]] = {}
    for relative in (*IMPLEMENTATION_SOURCE_PATHS, *SOURCE_TRANSITION_PATHS):
        payload = fixed_regular_file(resolved_root, relative).read_bytes()
        sources[relative] = [sha256_bytes(payload), len(payload)]
    for relative in SOURCE_TRANSITION_PATHS:
        accepted = _run_fixed_git(
            repository,
            "cat-file",
            "blob",
            f"{PREDECESSOR_COMMIT}:Ti-Java/{relative}",
        )
        successor_sha256, successor_bytes = sources[relative]
        transitions[relative] = {
            "source": relative,
            "accepted_sha256": sha256_bytes(accepted),
            "accepted_byte_count": len(accepted),
            "successor_sha256": successor_sha256,
            "successor_byte_count": successor_bytes,
        }

    _, accepted_runtime = node_c.production_runtime_manifests(resolved_root)
    additions = {
        relative: sources[relative][0]
        for relative in PRODUCTION_RUNTIME_ADDITION_PATHS
    }
    current_runtime = dict(accepted_runtime)
    current_runtime.update(additions)
    current_runtime = dict(sorted(current_runtime.items()))
    accepted_main = _learning_personalbank_main(accepted_runtime)
    current_main = _learning_personalbank_main(current_runtime)

    script = fixed_regular_file(
        resolved_root, BUILD_CONTEXT_SCRIPT_RELATIVE
    )
    completed = subprocess.run(
        ("/bin/sh", str(script)),
        cwd=resolved_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError("execution-protocol build-context refresh failed")
    return {
        "source_files": dict(sorted(sources.items())),
        "source_transitions": dict(sorted(transitions.items())),
        "production_runtime_additions": dict(sorted(additions.items())),
        "accepted_production_file_count": len(accepted_runtime),
        "accepted_production_manifest_sha256": sha256_json(accepted_runtime),
        "current_production_file_count": len(current_runtime),
        "current_production_manifest_sha256": sha256_json(current_runtime),
        "accepted_learning_personalbank_main_file_count": len(accepted_main),
        "accepted_learning_personalbank_main_manifest_sha256": sha256_json(
            accepted_main
        ),
        "current_learning_personalbank_main_file_count": len(current_main),
        "current_learning_personalbank_main_manifest_sha256": sha256_json(
            current_main
        ),
        "worm_sha256": sources[WORM_RELATIVE][0],
        "worm_byte_count": sources[WORM_RELATIVE][1],
        "current_build_context_sha256": completed.stdout.strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--validate-c2-git",
        type=Path,
        help="explicit repository root for fixed 4c47d1e replay",
    )
    parser.add_argument(
        "--emit-refreshed-fixed-map",
        type=Path,
        metavar="REPOSITORY_ROOT",
        help=(
            "emit fixed literals from the exact 11+37 allowlists and fixed C2; "
            "does not write files"
        ),
    )
    arguments = parser.parse_args()
    if arguments.emit_refreshed_fixed_map is not None:
        print(
            json.dumps(
                refreshed_fixed_map(ROOT, arguments.emit_refreshed_fixed_map),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
        return
    if arguments.validate_c2_git is not None:
        validate_predecessor_git(arguments.validate_c2_git)
    payload = serialized_contract(build_contract())
    if arguments.write:
        arguments.output.write_bytes(payload)
    else:
        print(payload.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
