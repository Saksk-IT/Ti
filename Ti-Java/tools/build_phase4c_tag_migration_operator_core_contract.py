#!/usr/bin/env python3
"""Build the gitless Phase 4C tag-migration operator-core contract."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-operator-core-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE
CONTRACT_ID = "ti.phase4c.personal-bank-tag-migration-operator-core-contract"
CAPTURED_AT = "2026-07-19T15:30:00+08:00"
SCOPE = "phase4c-learning-owned-personal-bank-tag-migration-operator-core"
STATUS = (
    "operator_core_and_bounded_retry_evidence_closed_"
    "production_schema_freeze_backup_apply_and_cutover_unauthorized"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-durable-ledger-freeze-design-"
    "post-push-anchor-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-tag-migration-durable-ledger-freeze-design-"
    "post-push-anchor-contract"
)
PREDECESSOR_CAPTURED_AT = "2026-07-19T13:33:45+08:00"
PREDECESSOR_SCOPE = (
    "phase4c-personal-bank-tag-migration-durable-ledger-freeze-design-"
    "post-push-external-anchor"
)
PREDECESSOR_STATUS = (
    "durable_ledger_freeze_design_checkpoint_externally_anchored_"
    "production_schema_operator_apply_backup_and_cutover_unauthorized"
)
PREDECESSOR_SHA256 = (
    "2d65af0c4fd725dceef5d99d2b2dd06804f78f0250f0136a662ca6fb184ccaa6"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "840d8e06a755fc6c01f5357411023fd875ec5dd87e322608252782b1bbc39542"
)
PREDECESSOR_BYTE_COUNT = 15_550

GLOBAL_PREFLIGHT_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-global-preflight-contract.json"
)
GLOBAL_PREFLIGHT_CONTRACT_SHA256 = (
    "65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e"
)
GLOBAL_PREFLIGHT_CONTRACT_PAYLOAD_SHA256 = (
    "c7a94e88772a2453743f9821b165ae10f52650a41bf6dab78006d7058951159e"
)
GLOBAL_PREFLIGHT_CONTRACT_BYTE_COUNT = 102_931
HISTORICAL_RUNTIME_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-contract.json"
)
HISTORICAL_RUNTIME_CONTRACT_SHA256 = (
    "9f6c37c4217da83199403da8207ed4f89a3999fafd149f069afb520dee4d2460"
)
HISTORICAL_RUNTIME_CONTRACT_PAYLOAD_SHA256 = (
    "331c82ad941f4eeb3e07d1701271310f2b1dea91132794e4e5d1eb1b466fc458"
)
HISTORICAL_RUNTIME_CONTRACT_BYTE_COUNT = 74_597

NODE_B_ANCHOR_COMMIT = "bbeb08efcccb0b9974dfefa2044aab43e0675f6f"
NODE_B_IMPLEMENTATION_COMMIT = "ea894b3a02787a91b688d7295cace37139f7f486"
NODE_B_ANCHOR_CHECKPOINT = {
    "object_format": "sha1",
    "commit_oid": NODE_B_ANCHOR_COMMIT,
    "parent_oid": NODE_B_IMPLEMENTATION_COMMIT,
    "root_tree_oid": "2df48a21e622d0e5e3731fe2617ddaedbf466866",
    "parent_root_tree_oid": "57cfc3b195600b38a73e09673267143de346474d",
    "ti_java_tree_oid": "ce2c2035763ac4512fa2bcaaa73cacb255212756",
    "parent_ti_java_tree_oid": "cd5de2cb7f73400cd3d3fe2aa2d7bf48db21a3c8",
    "server_tree_oid": "931e1268a43465023e23b31d903d5d7b3219981d",
    "parent_server_tree_oid": "fd7ccc66962e691eaaadc31e3dad409dbe392273",
    "server_src_main_tree_oid": "21fe4902d57a11998502e63041b5a56fb039a090",
    "parent_server_src_main_tree_oid": "21fe4902d57a11998502e63041b5a56fb039a090",
    "web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "parent_web_tree_oid": "a75f69a8205a56843feb055656ddb015ec5b5215",
    "authored_at": "2026-07-19T13:53:33+08:00",
    "committed_at": "2026-07-19T13:53:33+08:00",
    "subject": "test(java): anchor tag migration ledger freeze design",
    "raw_delta_sha256": (
        "01857633c569bbc92da8ff6cb7387c21e75db59c35f55165683114ba5ff6a072"
    ),
    "numstat_sha256": (
        "267db667ace02ac39b697109114ecc30def477c1d2eb6f7db9da185f4290c0b1"
    ),
    "changed_path_count": 6,
    "added_count": 6,
    "modified_count": 0,
    "deleted_count": 0,
    "inserted_line_count": 2_051,
    "deleted_line_count": 0,
    "added_total_bytes": 108_700,
}
NODE_B_ANCHOR_ARTIFACTS = {
    PREDECESSOR_RELATIVE: {
        "git_blob_oid": "8b8ecd6b6b59cf753aef1ca2b9322a3c45e489d6",
        "sha256": PREDECESSOR_SHA256,
        "byte_count": PREDECESSOR_BYTE_COUNT,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorContractParityTest.java"
    ): {
        "git_blob_oid": "93af26843b459ad2766f22b2cfbcae53367eea0b",
        "sha256": "4fff40991c24fa0052c35178c2117f9e58d25e4fcf09571431636a8dc439b3dc",
        "byte_count": 13_774,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance.java"
    ): {
        "git_blob_oid": "46a992352737bc42b534dfa982a79928fabcd238",
        "sha256": "989a81d6a5abec0f910603a19022d53754062b074dad80efdd38d6642393f3be",
        "byte_count": 22_247,
    },
    (
        "tools/build_phase4c_tag_migration_durable_ledger_freeze_design_"
        "post_push_anchor_contract.py"
    ): {
        "git_blob_oid": "e75ec97a16de094519d83e7e51dbfa8c727f08d0",
        "sha256": "46677e31ff369b13de500b719c27f0ebf5e2bb4fbef8c66048ac0b1489d5a832",
        "byte_count": 29_621,
    },
    (
        "tools/phase4c_tag_migration_durable_ledger_freeze_design_"
        "post_push_anchor_successor_acceptance.py"
    ): {
        "git_blob_oid": "3a82c7edc9e80b3b5a99698349e7c4a209c0e8c8",
        "sha256": "14267487e304afa0dee932d8e5ff652e51a2da092f3c171cbbaf5b103bd6202c",
        "byte_count": 15_583,
    },
    (
        "tools/test_phase4c_tag_migration_durable_ledger_freeze_design_"
        "post_push_anchor_contract.py"
    ): {
        "git_blob_oid": "6ac7770fa57120619f8ff49ace5ef9ec6b75be2a",
        "sha256": "d48955b0b7d8ee1892fcbfd4ad9881ece1581c8875542d39bcd13ad030bcd13c",
        "byte_count": 11_925,
    },
}

MIGRATION_MAIN_PREFIX = (
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
)
GLOBAL_PREFLIGHT_MAIN_RELATIVE = (
    MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagGlobalPreflight.java"
)
PRODUCTION_RUNTIME_ADDITIONS = {
    MIGRATION_MAIN_PREFIX + "BoundedSqlRetry.java": (
        "4f3a37fc45d5fbeab21e4092de79d2e01dbb4c3db516d69a7e39ec6e486de2d6"
    ),
    MIGRATION_MAIN_PREFIX + "JdbcTagMigrationStore.java": (
        "8adf102211041e33243f6e76bab1eda9100cc3e44ee54d9a5468a6c7cdb4c242"
    ),
    MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagMigrationOperatorCore.java": (
        "2a70c9e9cc7e5acdb1aa5059114fdb34e910a9f4c7d124dc17f62ad06360987b"
    ),
    MIGRATION_MAIN_PREFIX + "TagMigrationCommand.java": (
        "4d1d2a059a6ca2874cd8a787dee860482f035bad9cdb8ea62451b80fd41445a0"
    ),
    MIGRATION_MAIN_PREFIX + "TagMigrationDigests.java": (
        "92520a2abb405024fcfb760c0d710b2bf50e0f6ad4c22d2dd2b7f25547f8a7ec"
    ),
    MIGRATION_MAIN_PREFIX + "TagMigrationResult.java": (
        "eb9c6ccdae328a9bbff331e05ca324af2bce1e008d8ab6fddad442a9af7cbd81"
    ),
    MIGRATION_MAIN_PREFIX + "TagMigrationSchemaVerifier.java": (
        "7b28cd9ac19d328166f124052c2d0d8ba57ea7bbc1257e8aad399cb2c1d2750f"
    ),
}
PRODUCTION_RUNTIME_CHANGES = {
    GLOBAL_PREFLIGHT_MAIN_RELATIVE: (
        "c6dd412fcfa23f8e59ccf6e2a0d7c741e1cc684015b73e92cfb77cab3300e746"
    )
}
ACCEPTED_PRODUCTION_FILE_COUNT = 300
ACCEPTED_PRODUCTION_MANIFEST_SHA256 = (
    "8d28a382447c8756b2ec4cfc4107bc55fd744587d81a8835b71eee1f1942fbb3"
)
CURRENT_PRODUCTION_FILE_COUNT = 307
CURRENT_PRODUCTION_MANIFEST_SHA256 = (
    "b1228337b60b752ff088c4e5b67ae21092ca75a07c437bae35cc67b39b1c8c25"
)
ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT = 43
ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256 = (
    "2cc855057a4b3b6b5693ad717404ea6b9828de3aa73ef9be8a9a1a62b177f751"
)
CURRENT_LEARNING_PERSONALBANK_MAIN_FILE_COUNT = 50
CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256 = (
    "3abdc97486bbb9ec62a2d426063157e0ef3a990a34ca4862fc9e18580b4f60e9"
)
EXPECTED_CATALOG_SHA256 = (
    "f4361024a36e4e509f1ca4203c2dca5ecfd5bf1eded036e462bbbb20f395f99c"
)

WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-operator-core-worm-evidence.json"
)
WORM_SHA256 = "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f"
WORM_BYTE_COUNT = 1_442
WORM_PREDECESSOR_SHA256 = (
    "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344"
)
ACCEPTED_BUILD_CONTEXT_SHA256 = (
    "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17"
)
CURRENT_BUILD_CONTEXT_SHA256 = (
    "29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc"
)
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "docs/refactor/phase4c/personal-bank-tag-migration-operator-core.md",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationOperatorCoreContractParityTest.java"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationOperatorCoreSuccessorAcceptance.java"
    ),
    "tools/build_phase4c_tag_migration_operator_core_contract.py",
    "tools/phase4c_tag_migration_operator_core_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_operator_core_contract.py",
)

# These are the only non-control physical inputs authorized by this node.
SOURCE_FILES: dict[str, tuple[str, int]] = {
    MIGRATION_MAIN_PREFIX + "BoundedSqlRetry.java": (
        PRODUCTION_RUNTIME_ADDITIONS[MIGRATION_MAIN_PREFIX + "BoundedSqlRetry.java"],
        9_021,
    ),
    MIGRATION_MAIN_PREFIX + "JdbcTagMigrationStore.java": (
        PRODUCTION_RUNTIME_ADDITIONS[MIGRATION_MAIN_PREFIX + "JdbcTagMigrationStore.java"],
        68_333,
    ),
    MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagMigrationOperatorCore.java": (
        PRODUCTION_RUNTIME_ADDITIONS[
            MIGRATION_MAIN_PREFIX + "LegacyPersonalBankTagMigrationOperatorCore.java"
        ],
        78_742,
    ),
    MIGRATION_MAIN_PREFIX + "TagMigrationCommand.java": (
        PRODUCTION_RUNTIME_ADDITIONS[MIGRATION_MAIN_PREFIX + "TagMigrationCommand.java"],
        4_822,
    ),
    MIGRATION_MAIN_PREFIX + "TagMigrationDigests.java": (
        PRODUCTION_RUNTIME_ADDITIONS[MIGRATION_MAIN_PREFIX + "TagMigrationDigests.java"],
        12_330,
    ),
    MIGRATION_MAIN_PREFIX + "TagMigrationResult.java": (
        PRODUCTION_RUNTIME_ADDITIONS[MIGRATION_MAIN_PREFIX + "TagMigrationResult.java"],
        4_785,
    ),
    MIGRATION_MAIN_PREFIX + "TagMigrationSchemaVerifier.java": (
        PRODUCTION_RUNTIME_ADDITIONS[
            MIGRATION_MAIN_PREFIX + "TagMigrationSchemaVerifier.java"
        ],
        54_778,
    ),
    (
        "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
        "BoundedSqlRetryTest.java"
    ): ("8e0e5f522b76e3569ff8bf1ef59949cc0830a72e17a7d62f85af465fd409a2b8", 20_398),
    (
        "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
        "LegacyPersonalBankTagMigrationOperatorCoreStaticTest.java"
    ): ("d828e25633e5029d10a781f171a1eb719ddc565954928ed77f6375f20b89e3a3", 17_734),
    (
        "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
        "Phase4cBoundedSqlRetryPostgresIT.java"
    ): ("105b8cd83b4c3beb043c3d98cda0da160c4f496919846ae9c7ffdf8b32f00263", 19_658),
    (
        "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
        "Phase4cLegacyPersonalBankTagOperatorCoreIT.java"
    ): ("891bbac391e21454ad309ac568bf2f3cc5f5fa82c0ea3da9936005308b70197c", 96_139),
    (
        "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
        "TagMigrationValueTypesTest.java"
    ): ("ba9d21a78bc58afc5627b217ad255cba6dcfc5d94d4732140b2d6494faec8857", 34_019),
    (
        "server/src/test/resources/db/phase4c/"
        "076-legacy-personal-bank-tag-operator-core-schema.sql"
    ): ("c6cf2ec3c0d0c43a7032305f3180163cb78ec933b01edbc8ad877db07d96d173", 39_696),
    (
        "server/src/test/resources/db/phase4c/"
        "077-legacy-personal-bank-tag-operator-core-seed.sql"
    ): ("4d0ead5c5bff645b67bffba46272bb5564d9f37d60d3a3a0e6f1e7dd744beccf", 2_982),
    WORM_RELATIVE: (WORM_SHA256, WORM_BYTE_COUNT),
    "infra/phase2/README.md": (
        "d5c8647397016f93c8ea2b5e83b41818ea00498fd7e699cc1119930f1995e21b",
        8_018,
    ),
    "infra/phase2/verify-static.sh": (
        "2a1a5a5453a1090f6132971081d4ac2448803023acb50d474ced491bafe8efc3",
        17_491,
    ),
    "tools/phase2_wormhole_successor_acceptance.py": (
        "afd967894036289ad3587fc740c97931d1ca5492a9208829536bf6745a840ebc",
        30_285,
    ),
    "tools/test_phase2_wormhole_successor_acceptance.py": (
        "2c4881c5083c8e4ca2cf294ece486895e26d932d1f59d067f8da32ef544c63bc",
        54_340,
    ),
    "docs/refactor/05-progress.md": (
        "71fc8bf98bc4fb50645df473ee79b2bc33856ca928f49da7aecc96a7d1040f9d",
        109_838,
    ),
    "docs/refactor/phase4c/README.md": (
        "f061ac5e2b240e3b8c367f9db817c84346a309e9872cfbdeeafe8d3ff8689230",
        29_918,
    ),
    "tools/build_phase4c_tag_migration_global_preflight_contract.py": (
        "604c550ceb144c0bdca1d92e915a166d84c582cd53084f934bac71e171154ddf",
        129_684,
    ),
    "tools/phase4c_tag_migration_global_preflight_successor_acceptance.py": (
        "6fe3bf23d53ccaccd33f3ccaf31466cf0fc44df0f71bcc6f798765519fe12f95",
        32_367,
    ),
    "tools/test_phase4c_tag_migration_global_preflight_contract.py": (
        "28548d878900d0aeba6b983ba307af077b4ebdd01a6b27f4c496bf6ae472c313",
        38_541,
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java"
    ): ("e5471121ea2fc52f9e36712b222578e24323d5785dddf27b27a86799867fc99f", 102_527),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationGlobalPreflightContractParityTest.java"
    ): ("bdb3ee1169dfe164016a2afc6a46e6e3fff7abe9b8602988ab9d0c0ecff86158", 43_784),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "ModuleContractParityTest.java"
    ): ("9f32b0d204ea8d7d78b3ca5e0112cb4bd70bc31ce98cf16c032afd7545d67c61", 182_760),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTypedNormalizationSuccessorAcceptance.java"
    ): ("cb4cabfce2cded7cde291b54d2c2dd98cc397887d24141e5164250a8811fb369", 79_867),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java"
    ): ("bd83bffe8851e2368f3d9280d213b7adac1b4073dbe2296bd1d6e1c6183a454e", 51_156),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java"
    ): ("137f3a9911d886610300aecc95a13f05d5621d18c19acf491194f1b8b741efe3", 17_439),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase6WebFoundationSourceSuccessorContractParityTest.java"
    ): ("ea9affd42829d4560c2b974e8d189bd6feac340112732cf15b89d797f7b4f7af", 11_762),
    GLOBAL_PREFLIGHT_MAIN_RELATIVE: (
        PRODUCTION_RUNTIME_CHANGES[GLOBAL_PREFLIGHT_MAIN_RELATIVE],
        36_070,
    ),
    (
        "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
        "LegacyPersonalBankTagGlobalPreflightTest.java"
    ): ("ff4ff3dee678874b5acb0d9d2d380aee01fbcc5454c82746c1e0564113c40aaf", 34_622),
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "18cdd0df59a7cfa6d052192ca85fe59cd50415fe263ae172133958d59df1f544",
        60_156,
    ),
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": (
        "ab79ec3edc9f903a9917ae85450633982031f341aa219e75de08d69db0c63d26",
        24_250,
    ),
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": (
        "a308ba6b14bb9e960006378bdf165dc2dfece856bb09bf827d600a7a6f28e060",
        19_452,
    ),
    "tools/test_phase4b_personal_bank_share_list_entry_contract.py": (
        "3b59d4f9f4c3cafe84feb4bc0a902db1822455e73660f29461d2385370377122",
        33_266,
    ),
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": (
        "49441844f63e05ca57e0b89c751cca3b1b574c984223e588d40bac9e7613501f",
        45_548,
    ),
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": (
        "409a2663e26f559108e815a805f42f566f2a7dfea8d1da8f9aab966efa0a14cb",
        37_035,
    ),
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": (
        "9625aad3553408ef631d055735af33b4b21847aaaf8a57d540dd582cba025ab9",
        25_599,
    ),
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": (
        "7c8a27ef4e97ed731dd4b0dd357942e32e75a45db3d9e482e7513b1e8c1820a4",
        34_464,
    ),
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": (
        "3aacc3a54b0ecc6314f0f84d51057f657e8c188d1f673d931092c40c3f39106b",
        24_536,
    ),
    "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py": (
        "17e77b5204bdec0b2deb43517354fada893802321a1cfa8f446151fcb5a2b0c9",
        32_398,
    ),
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py": (
        "c9d21809bd136ed131ee20ac6baabf0b6b67bcc85f03fab9fccedcd02c86f2c0",
        65_798,
    ),
    "tools/phase4c_http_target_execution_successor_acceptance.py": (
        "4048e962b5db2d332c0955099a77637c3542b77e58fd233b5460296c1f86abd9",
        84_585,
    ),
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py": (
        "7e6039fd7288cd16980149b385f71faa79659092f5bd187c14d060a19c08fe84",
        34_398,
    ),
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py": (
        "8d96674c8ea55f6050133945f0f58fe365ea9383d7660ba3c6d3423cf63bc7c5",
        36_240,
    ),
    "tools/phase4c_http_target_execution_anchor_successor_acceptance.py": (
        "810efb88c88efeb35b7a1f182214dc8873ca7099d8f6dfb8ce6b1af651dd3ecd",
        36_566,
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): ("9f929532d8c31f96f4e3e5cd24ee199220c82ad2aac46f5944ee0d54cd22dbb6", 91_381),
}

SOURCE_TRANSITIONS: dict[str, dict[str, Any]] = {
    GLOBAL_PREFLIGHT_MAIN_RELATIVE: {
        "accepted_sha256": "cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76",
        "accepted_byte_count": 35_830,
    },
    (
        "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
        "LegacyPersonalBankTagGlobalPreflightTest.java"
    ): {
        "accepted_sha256": "8fc30419dee8be99b8081f873d38921fdedb2beea42a7c1b4c8e2241e844ce3f",
        "accepted_byte_count": 34_570,
    },
    "infra/phase2/README.md": {
        "accepted_sha256": "a0c467bfc8aa0f0b64b4d520f9cda60ff081a340f016647e1da934c73b7b99d5",
        "accepted_byte_count": 7_474,
    },
    "infra/phase2/verify-static.sh": {
        "accepted_sha256": "893ca920d0ed1bd62e16509893fa30bbfc72b88368d66d96c2ebc5c2fbae38dc",
        "accepted_byte_count": 16_417,
    },
    "tools/phase2_wormhole_successor_acceptance.py": {
        "accepted_sha256": "5c93b9aa00d3faec19ebc8d6472bd9e8ab1903a7116d487ff8a711fc60fd8d20",
        "accepted_byte_count": 28_590,
    },
    "tools/test_phase2_wormhole_successor_acceptance.py": {
        "accepted_sha256": "e61ed72335bba631cf34ebfe06fae8d391e7828622eba17d0240f59efed379a3",
        "accepted_byte_count": 52_825,
    },
    "docs/refactor/05-progress.md": {
        "accepted_sha256": "8478e44622fc666fdb9a377b15ced624e34d104d1fcbb9b36a4913cfb3ddedf0",
        "accepted_byte_count": 107_912,
    },
    "docs/refactor/phase4c/README.md": {
        "accepted_sha256": "4d75ba666d7d45d620a4fba4574e4c2640b754c5a6beadbdbfdee5498aa3cc48",
        "accepted_byte_count": 26_858,
    },
    "tools/build_phase4c_tag_migration_global_preflight_contract.py": {
        "accepted_sha256": "fa5fb43b5caa24006c5d08b94a12eeafaa25be927165f14ae4cf170ff59c03d5",
        "accepted_byte_count": 124_466,
    },
    "tools/phase4c_tag_migration_global_preflight_successor_acceptance.py": {
        "accepted_sha256": "258ba0903f318aae40ebeba1b693bd97fe13ea534e1afcb423f1a373b9e05a44",
        "accepted_byte_count": 27_736,
    },
    "tools/test_phase4c_tag_migration_global_preflight_contract.py": {
        "accepted_sha256": "3644acb20bb3ddf220d1c088c2e52778742892d8bae843c697314372fa858b87",
        "accepted_byte_count": 35_696,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java"
    ): {
        "accepted_sha256": "4a7a9ee5338b8a2dc3b57fd660b3ca9dc30b81e0fcb68d06437bd0f53d3a58b0",
        "accepted_byte_count": 94_373,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cTagMigrationGlobalPreflightContractParityTest.java"
    ): {
        "accepted_sha256": "15dd2e02d5230970358d1761a8298cf44b837c7beda7459d4c4a69173c42f472",
        "accepted_byte_count": 38_080,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "ModuleContractParityTest.java"
    ): {
        "accepted_sha256": "984863bff3762adc8e375f0073559bb1e0e1d0ed16c368147087fdc3ca4efcd1",
        "accepted_byte_count": 182_577,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTypedNormalizationSuccessorAcceptance.java"
    ): {
        "accepted_sha256": "ec7c98b04a26f25940fd5b9ec4120ebd478aa41798d4040f1cce97336898d6d2",
        "accepted_byte_count": 79_735,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java"
    ): {
        "accepted_sha256": "e5ccdf547d1c11edaf58298a2759241c64731c048bc1bef67f5be046237c01aa",
        "accepted_byte_count": 51_024,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java"
    ): {
        "accepted_sha256": "faff2f55f48cdaa8bab92530347cda47a0f3ba4dc4227c86242afb94d78aebc0",
        "accepted_byte_count": 17_295,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase6WebFoundationSourceSuccessorContractParityTest.java"
    ): {
        "accepted_sha256": "e61b445cbedddd5b71efe7dda22811128414b58089bf1525aaa4017485f6675d",
        "accepted_byte_count": 11_762,
    },
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": {
        "accepted_sha256": "51ab42d0a220f3e91ac07a9b3ab1f6a2ca6c366b994de200effae31a074a766b",
        "accepted_byte_count": 60_156,
    },
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py": {
        "accepted_sha256": "31dec8b10fad1f044ecbca4a76da0d4f1f97ffbbe32e075895e050372ff8ba4a",
        "accepted_byte_count": 24_249,
    },
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py": {
        "accepted_sha256": "7afd91f0e0048cba029d38965c900da670d5f327b8b9541b0962533b1b1f09eb",
        "accepted_byte_count": 19_451,
    },
    "tools/test_phase4b_personal_bank_share_list_entry_contract.py": {
        "accepted_sha256": "32b4d8e625f452ba20852fe64805086a6d878f3f8518298e7340122ff6120943",
        "accepted_byte_count": 33_265,
    },
    "tools/test_phase4b_personal_bank_share_list_read_contract.py": {
        "accepted_sha256": "047563af77f5786b0af24eeb20f8d287163df44778aad1ee56d1805a05207ec4",
        "accepted_byte_count": 45_547,
    },
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py": {
        "accepted_sha256": "162e057e07d6d0d0f73b6ee8bf9210fd98c492369222ce649a4f5bd5418b16b4",
        "accepted_byte_count": 37_033,
    },
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py": {
        "accepted_sha256": "4f3c9ab19370eabd6dbe6dbea047d1e176c3a4e8ed947035a54dc210b75e2057",
        "accepted_byte_count": 25_598,
    },
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py": {
        "accepted_sha256": "0a980e05a5fd4204e5db630447c7b018d54e2e89b64e7f069eb1329f85a5d372",
        "accepted_byte_count": 34_463,
    },
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": {
        "accepted_sha256": "6c302395dca0d7d319233e6463ed65b26aa3ea103c90511752ae4cac710dbaad",
        "accepted_byte_count": 24_536,
    },
    "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py": {
        "accepted_sha256": "fcc4eee103b33604addfd17e453793dd41c498de62fe0538e873520dbd285b26",
        "accepted_byte_count": 32_398,
    },
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py": {
        "accepted_sha256": "3064c164d300499d958947068d3acd50c8823c741d9a0144860b5f3b1b532f7d",
        "accepted_byte_count": 65_798,
    },
    "tools/phase4c_http_target_execution_successor_acceptance.py": {
        "accepted_sha256": "daca285575123c6b3d690c52977bbf8797fa46d5db75862b774805acb586a230",
        "accepted_byte_count": 84_585,
    },
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py": {
        "accepted_sha256": "469c46bde8e339ef28a461f3fd2a34ee7e02bfa12cb75eec4f881454049e7957",
        "accepted_byte_count": 34_398,
    },
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py": {
        "accepted_sha256": "624d741b383866ce1bb8ec49c24445164665096cdf5b9ab679b2561c61ab7e9a",
        "accepted_byte_count": 36_240,
    },
    "tools/phase4c_http_target_execution_anchor_successor_acceptance.py": {
        "accepted_sha256": "e91c56e91cdeff3bf069407d8e43d7d1b76fb131c875cf536e561976fe395141",
        "accepted_byte_count": 36_566,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): {
        "accepted_sha256": "10d19deb68495db02f9113dd58bdf7bbf7dfa67a8885c49f7dd88685f574ff78",
        "accepted_byte_count": 91_381,
    },
}
for _relative, _transition in SOURCE_TRANSITIONS.items():
    _successor_sha256, _successor_byte_count = SOURCE_FILES[_relative]
    _transition.update(
        {
            "source": _relative,
            "successor_sha256": _successor_sha256,
            "successor_byte_count": _successor_byte_count,
        }
    )

ROUTE_STATE = {
    "migrated_operation_count": 13,
    "pending_operation_count": 598,
    "production_cutover_operation_count": 0,
    "total_operation_count": 611,
    "legacy_flask_remains_production_owner": True,
}
FIXED_NON_CONTROL_SOURCE_COUNT = 49
CONTROL_SOURCE_COUNT = 7
SOURCE_TRANSITION_COUNT = 34
NEWLY_CLOSED_GATES = (
    "operator_core_evidence_closed",
    "bounded_40001_40P01_retry_implemented",
    "operator_migration_implementation",
)


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
        raise AssertionError(f"operator-core path escapes fixed root: {relative}")
    resolved_root = root.resolve(strict=True)
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"operator-core fixed source is a symlink: {relative}")
    try:
        resolved = cursor.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, ValueError) as error:
        raise AssertionError(
            f"operator-core fixed source is absent or escaped: {relative}"
        ) from error
    if not resolved.is_file():
        raise AssertionError(
            f"operator-core fixed source is not a regular file: {relative}"
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
        raise AssertionError(f"operator-core fixed JSON bytes drifted: {relative}")
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"operator-core fixed JSON is unreadable: {relative}") from error
    if not isinstance(document, dict):
        raise AssertionError(f"operator-core fixed JSON is not an object: {relative}")
    if payload_sha256 is not None and (
        document.get("document_payload_sha256") != payload_sha256
        or document_payload_sha256(document) != payload_sha256
    ):
        raise AssertionError(f"operator-core fixed JSON payload drifted: {relative}")
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
        raise AssertionError("operator-core predecessor identity drifted")
    checkpoint = document.get("git_checkpoint", {})
    if (
        checkpoint.get("commit_oid") != NODE_B_IMPLEMENTATION_COMMIT
        or checkpoint.get("changed_path_count") != 8
        or checkpoint.get("added_count") != 8
        or checkpoint.get("modified_count") != 0
        or checkpoint.get("deleted_count") != 0
        or checkpoint.get("server_src_main_tree_unchanged_from_parent") is not True
        or checkpoint.get("web_tree_unchanged_from_parent") is not True
    ):
        raise AssertionError("operator-core Node B implementation checkpoint drifted")
    trust = document.get("current_node_trust_boundary", {})
    if (
        trust.get("control_source_count") != 6
        or trust.get("control_sources_external_git_anchor_complete") is not False
        or trust.get("control_source_allowlist_exact") is not True
    ):
        raise AssertionError("operator-core Node B external anchor drifted")
    node_b_controls = document.get("node_b_control_source_anchor", {})
    if (
        node_b_controls.get("control_source_count") != 8
        or node_b_controls.get("predecessor_control_sources_external_git_anchor_complete")
        is not True
        or node_b_controls.get("all_controls_are_exact_commit_delta_blobs")
        is not True
    ):
        raise AssertionError("operator-core Node B control anchor drifted")
    inherited = document.get("inherited_evidence_and_authorization", {})
    if (
        inherited.get("migration_global_preflight_evidence_closed") is not True
        or inherited.get("migration_durable_ledger_freeze_design_evidence_closed")
        is not True
        or inherited.get("bounded_40001_40P01_retry_implemented") is not False
        or inherited.get("operator_migration_implementation") is not False
        or inherited.get("migration_design_closed") is not False
        or inherited.get("production_cutover") is not False
    ):
        raise AssertionError("operator-core predecessor authorization drifted")
    if document.get("route_state") != ROUTE_STATE:
        raise AssertionError("operator-core predecessor route state drifted")
    return document


def _load_global_preflight(root: Path) -> dict[str, Any]:
    document = _validated_json(
        root,
        GLOBAL_PREFLIGHT_CONTRACT_RELATIVE,
        GLOBAL_PREFLIGHT_CONTRACT_SHA256,
        GLOBAL_PREFLIGHT_CONTRACT_BYTE_COUNT,
        GLOBAL_PREFLIGHT_CONTRACT_PAYLOAD_SHA256,
    )
    successor = document.get("historical_semantic_successors", {})
    runtime = successor.get("production_runtime_manifest", {})
    worm = successor.get("java_build_context_and_worm_chain", {})
    if (
        document.get("contract_id")
        != "ti.phase4c.personal-bank-tag-migration-global-preflight-contract"
        or runtime.get("successor_file_count") != ACCEPTED_PRODUCTION_FILE_COUNT
        or runtime.get("successor_manifest_sha256")
        != ACCEPTED_PRODUCTION_MANIFEST_SHA256
        or runtime.get("learning_personalbank_main", {}).get(
            "successor_file_count"
        )
        != ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or runtime.get("learning_personalbank_main", {}).get(
            "successor_manifest_sha256"
        )
        != ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
        or worm.get("terminal_successor_chain_node_count") != 7
        or worm.get("terminal_successor_worm", {}).get("sha256")
        != WORM_PREDECESSOR_SHA256
        or worm.get("terminal_successor_build_context_sha256")
        != ACCEPTED_BUILD_CONTEXT_SHA256
    ):
        raise AssertionError("operator-core fixed Node A semantic authority drifted")
    return document


def accepted_production_runtime_files(root: Path = ROOT) -> dict[str, str]:
    global_preflight = _load_global_preflight(root)
    target_execution = _validated_json(
        root,
        HISTORICAL_RUNTIME_CONTRACT_RELATIVE,
        HISTORICAL_RUNTIME_CONTRACT_SHA256,
        HISTORICAL_RUNTIME_CONTRACT_BYTE_COUNT,
        HISTORICAL_RUNTIME_CONTRACT_PAYLOAD_SHA256,
    )
    historical = target_execution.get("production_surface", {})
    files = historical.get("files")
    if (
        historical.get("file_count") != 297
        or historical.get("manifest_sha256")
        != "d327a5ef85fa47abc6417527d7bfd99a01f29de6ea3c2f08205cbf30a6e38f79"
        or not isinstance(files, dict)
        or len(files) != 297
        or sha256_json(files) != historical["manifest_sha256"]
    ):
        raise AssertionError("operator-core historical production manifest drifted")
    node_a_additions = global_preflight["historical_semantic_successors"][
        "production_runtime_manifest"
    ]["added_files"]
    accepted = dict(files)
    accepted.update(node_a_additions)
    accepted = dict(sorted(accepted.items()))
    if (
        len(accepted) != ACCEPTED_PRODUCTION_FILE_COUNT
        or sha256_json(accepted) != ACCEPTED_PRODUCTION_MANIFEST_SHA256
    ):
        raise AssertionError("operator-core accepted production manifest drifted")
    return accepted


def production_runtime_manifests(
    root: Path = ROOT,
) -> tuple[dict[str, str], dict[str, str]]:
    accepted = accepted_production_runtime_files(root)
    for relative, expected_sha256 in {
        **PRODUCTION_RUNTIME_ADDITIONS,
        **PRODUCTION_RUNTIME_CHANGES,
    }.items():
        payload = fixed_regular_file(root, relative).read_bytes()
        if sha256_bytes(payload) != expected_sha256:
            raise AssertionError(
                f"operator-core production successor bytes drifted: {relative}"
            )
    if set(PRODUCTION_RUNTIME_ADDITIONS).intersection(accepted):
        raise AssertionError("operator-core production addition already existed")
    if not set(PRODUCTION_RUNTIME_CHANGES).issubset(accepted):
        raise AssertionError("operator-core production change did not exist")
    current = dict(accepted)
    current.update(PRODUCTION_RUNTIME_ADDITIONS)
    current.update(PRODUCTION_RUNTIME_CHANGES)
    current = dict(sorted(current.items()))
    if (
        len(current) != CURRENT_PRODUCTION_FILE_COUNT
        or sha256_json(current) != CURRENT_PRODUCTION_MANIFEST_SHA256
    ):
        raise AssertionError("operator-core current production manifest drifted")
    return accepted, current


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


def validated_source(root: Path, relative: str) -> bytes:
    if relative not in SOURCE_FILES or relative in CONTROL_SOURCES:
        raise AssertionError(f"operator-core unknown or self-authority source: {relative}")
    expected_sha256, expected_byte_count = SOURCE_FILES[relative]
    payload = fixed_regular_file(root, relative).read_bytes()
    if (
        len(payload) != expected_byte_count
        or sha256_bytes(payload) != expected_sha256
    ):
        raise AssertionError(f"operator-core fixed source bytes drifted: {relative}")
    return payload


def _validate_sources(root: Path) -> None:
    if (
        len(SOURCE_FILES) != FIXED_NON_CONTROL_SOURCE_COUNT
        or len(CONTROL_SOURCES) != CONTROL_SOURCE_COUNT
        or len(SOURCE_TRANSITIONS) != SOURCE_TRANSITION_COUNT
        or len(set(SOURCE_FILES)) != FIXED_NON_CONTROL_SOURCE_COUNT
        or len(set(CONTROL_SOURCES)) != CONTROL_SOURCE_COUNT
        or set(SOURCE_FILES).intersection(CONTROL_SOURCES)
        or not set(SOURCE_TRANSITIONS).issubset(SOURCE_FILES)
    ):
        raise AssertionError("operator-core source/control allowlist drifted")
    forbidden_tokens = ("PENDING_", "PLACEHOLDER", "SETTLED_LATER")
    encoded_constants = canonical_json(
        {"sources": SOURCE_FILES, "transitions": SOURCE_TRANSITIONS}
    )
    if any(token in encoded_constants for token in forbidden_tokens):
        raise AssertionError("operator-core unsettled source authority")
    for relative in SOURCE_FILES:
        validated_source(root, relative)
    for relative, transition in SOURCE_TRANSITIONS.items():
        successor_sha256, successor_byte_count = SOURCE_FILES[relative]
        if transition != {
            "source": relative,
            "accepted_sha256": transition["accepted_sha256"],
            "accepted_byte_count": transition["accepted_byte_count"],
            "successor_sha256": successor_sha256,
            "successor_byte_count": successor_byte_count,
        }:
            raise AssertionError(f"operator-core source transition drifted: {relative}")
        if (
            transition["accepted_sha256"] == successor_sha256
            and transition["accepted_byte_count"] == successor_byte_count
        ):
            raise AssertionError(f"operator-core source transition is a no-op: {relative}")


def _validate_worm(root: Path) -> dict[str, Any]:
    document = json.loads(validated_source(root, WORM_RELATIVE))
    if document != {
        "schemaVersion": 1,
        "capturedAt": "2026-07-19T17:10:23Z",
        "source": {
            "classification": "explicitly-approved-local-development-reference",
            "legacySourceCommit": "700006dfdfa063deb4387be572911e782bcea0d9",
            "alembicHead": "f5b6c7d8e9f0",
            "serverVersion": "18.4",
            "serverVersionNum": "180004",
            "publicBaseTables": 70,
            "publicColumns": 617,
        },
        "restore": {
            "image": (
                "postgres:18.4-alpine@sha256:"
                "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
            ),
            "serverVersion": "18.4",
            "serverVersionNum": "180004",
            "publicBaseTables": 70,
            "publicColumns": 617,
            "canonicalSchemaDumpSha256": (
                "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
            ),
            "schemaDumpPersisted": False,
        },
        "readRole": {
            "selectPassed": True,
            "defaultTransactionReadOnly": True,
            "temporaryPrivilege": False,
            "aclVerifiedWithReadOnlyDefaultDisabled": True,
            "insertRejected": True,
            "updateRejected": True,
            "deleteRejected": True,
            "ddlRejected": True,
            "temporaryDdlRejected": True,
        },
        "java": {
            "dockerfileSha256": DOCKERFILE_SHA256,
            "buildContextSha256": CURRENT_BUILD_CONTEXT_SHA256,
            "hibernateDdlAuto": "validate",
            "startupPassed": True,
            "readinessPassed": True,
        },
        "productionDatabaseVersion": "unknown",
        "flywayBaselineCreated": False,
    }:
        raise AssertionError("operator-core WORM payload drifted")
    return document


def _run_fixed_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "main", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("operator-core live/ref Git authority is forbidden")
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
        raise AssertionError("operator-core fixed bbeb08e Git replay failed") from error
    return completed.stdout


def _fixed_git_text(repository_root: Path, *arguments: str) -> str:
    return _run_fixed_git(repository_root, *arguments).decode("utf-8").strip()


def validate_node_b_anchor_git(repository_root: Path) -> None:
    """Explicitly replay only the fixed six-blob bbeb08e checkpoint."""
    root = repository_root.resolve(strict=True)
    checkpoint = NODE_B_ANCHOR_CHECKPOINT
    if Path(_fixed_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("operator-core explicit Git replay root drifted")
    if _fixed_git_text(root, "rev-parse", "--show-object-format") != "sha1":
        raise AssertionError("operator-core Git object format drifted")
    facts = _fixed_git_text(
        root,
        "show",
        "-s",
        "--format=%T%n%P%n%aI%n%cI%n%s",
        NODE_B_ANCHOR_COMMIT,
    ).splitlines()
    if facts != [
        checkpoint["root_tree_oid"],
        checkpoint["parent_oid"],
        checkpoint["authored_at"],
        checkpoint["committed_at"],
        checkpoint["subject"],
    ]:
        raise AssertionError("operator-core fixed Node B anchor commit drifted")
    for relative, key in {
        "Ti-Java": "ti_java_tree_oid",
        "Ti-Java/server": "server_tree_oid",
        "Ti-Java/server/src/main": "server_src_main_tree_oid",
        "Ti-Java/web": "web_tree_oid",
    }.items():
        if _fixed_git_text(root, "rev-parse", f"{NODE_B_ANCHOR_COMMIT}:{relative}") != checkpoint[key]:
            raise AssertionError(f"operator-core fixed Node B tree drifted: {relative}")
    for relative, key in {
        "Ti-Java": "parent_ti_java_tree_oid",
        "Ti-Java/server": "parent_server_tree_oid",
        "Ti-Java/server/src/main": "parent_server_src_main_tree_oid",
        "Ti-Java/web": "parent_web_tree_oid",
    }.items():
        if _fixed_git_text(root, "rev-parse", f"{NODE_B_IMPLEMENTATION_COMMIT}:{relative}") != checkpoint[key]:
            raise AssertionError(
                f"operator-core fixed Node B parent tree drifted: {relative}"
            )
    raw = _run_fixed_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--abbrev=40",
        "-r",
        NODE_B_ANCHOR_COMMIT,
    )
    expected_raw = [
        ":000000 100644 "
        "0000000000000000000000000000000000000000 "
        f"{artifact['git_blob_oid']} A\tTi-Java/{relative}"
        for relative, artifact in NODE_B_ANCHOR_ARTIFACTS.items()
    ]
    if (
        sha256_bytes(raw) != checkpoint["raw_delta_sha256"]
        or raw.decode("utf-8").splitlines() != expected_raw
    ):
        raise AssertionError("operator-core fixed Node B raw delta drifted")
    numstat = _run_fixed_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--numstat",
        "-r",
        NODE_B_ANCHOR_COMMIT,
    )
    parsed = [line.split("\t", 2) for line in numstat.decode("utf-8").splitlines()]
    if (
        sha256_bytes(numstat) != checkpoint["numstat_sha256"]
        or len(parsed) != checkpoint["changed_path_count"]
        or [row[2] for row in parsed]
        != [f"Ti-Java/{relative}" for relative in NODE_B_ANCHOR_ARTIFACTS]
        or sum(int(row[0]) for row in parsed) != checkpoint["inserted_line_count"]
        or sum(int(row[1]) for row in parsed) != checkpoint["deleted_line_count"]
    ):
        raise AssertionError("operator-core fixed Node B numstat drifted")
    total_bytes = 0
    for relative, artifact in NODE_B_ANCHOR_ARTIFACTS.items():
        payload = _run_fixed_git(root, "cat-file", "blob", artifact["git_blob_oid"])
        if (
            len(payload) != artifact["byte_count"]
            or sha256_bytes(payload) != artifact["sha256"]
        ):
            raise AssertionError(f"operator-core fixed Node B blob drifted: {relative}")
        total_bytes += len(payload)
    if total_bytes != checkpoint["added_total_bytes"]:
        raise AssertionError("operator-core fixed Node B byte total drifted")
    for relative, transition in SOURCE_TRANSITIONS.items():
        payload = _run_fixed_git(
            root,
            "cat-file",
            "blob",
            f"{NODE_B_ANCHOR_COMMIT}:Ti-Java/{relative}",
        )
        if (
            len(payload) != transition["accepted_byte_count"]
            or sha256_bytes(payload) != transition["accepted_sha256"]
        ):
            raise AssertionError(
                f"operator-core fixed predecessor source drifted: {relative}"
            )


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
        raise AssertionError("operator-core learning/personalbank view drifted")
    base = {
        "accepted_file_count": ACCEPTED_PRODUCTION_FILE_COUNT,
        "accepted_manifest_sha256": ACCEPTED_PRODUCTION_MANIFEST_SHA256,
        "current_file_count": CURRENT_PRODUCTION_FILE_COUNT,
        "current_manifest_sha256": CURRENT_PRODUCTION_MANIFEST_SHA256,
        "unchanged_file_count": ACCEPTED_PRODUCTION_FILE_COUNT - len(PRODUCTION_RUNTIME_CHANGES),
        "added_files": dict(sorted(PRODUCTION_RUNTIME_ADDITIONS.items())),
        "changed_files": dict(sorted(PRODUCTION_RUNTIME_CHANGES.items())),
        "deleted_files": [],
        "exact_additions_and_changes_only": True,
        "unknown_or_extra_files": "reject",
        "symlink_or_root_escape": "reject",
    }
    base["learning_personalbank_main"] = {
        "accepted_file_count": ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT,
        "accepted_manifest_sha256": ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256,
        "current_file_count": CURRENT_LEARNING_PERSONALBANK_MAIN_FILE_COUNT,
        "current_manifest_sha256": CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256,
        "unchanged_file_count": ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT - len(PRODUCTION_RUNTIME_CHANGES),
        "added_files": dict(sorted(PRODUCTION_RUNTIME_ADDITIONS.items())),
        "changed_files": dict(sorted(PRODUCTION_RUNTIME_CHANGES.items())),
        "deleted_files": [],
        "exact_additions_and_changes_only": True,
    }
    return base


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
        relative: deepcopy(transition)
        for relative, transition in sorted(SOURCE_TRANSITIONS.items())
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
            "immutable": True,
        },
        "node_b_git_authority": {
            "implementation_checkpoint_commit_oid": predecessor["git_checkpoint"][
                "commit_oid"
            ],
            "external_anchor_checkpoint": deepcopy(NODE_B_ANCHOR_CHECKPOINT),
            "external_anchor_artifacts": deepcopy(NODE_B_ANCHOR_ARTIFACTS),
            "external_anchor_artifact_count": len(NODE_B_ANCHOR_ARTIFACTS),
            "explicit_fixed_checkpoint_replay_available": True,
            "ordinary_build_and_load_require_git": False,
            "live_head_main_or_origin_authority": False,
        },
        "operator_core_implementation": {
            "owner": "learning",
            "entrypoint": (
                "io.saksk.ti.learning.infrastructure.migration."
                "LegacyPersonalBankTagMigrationOperatorCore"
            ),
            "explicit_callable_only": True,
            "spring_component_or_bean_registration": False,
            "command_line_runner_scheduler_or_http_registration": False,
            "environment_file_redis_or_local_marker_input": False,
            "production_data_source_wiring": False,
            "transaction_owner": "JdbcTagMigrationStore",
            "nonblocking_advisory_try_lock": True,
            "lock_busy_fails_without_business_dml": True,
            "statement_timeout_milliseconds": 30_000,
            "lock_timeout_milliseconds": 5_000,
            "idle_in_transaction_timeout_milliseconds": 60_000,
            "setup_schema_identity_and_recovery_queries_bounded": True,
            "setup_and_recovery_metadata_lock_wait_bounded_by_lock_timeout": True,
            "maximum_payload_bytes": 1_048_576,
            "maximum_source_rows": 100_001,
            "maximum_tag_utf8_bytes": 84,
            "maximum_target_facts": 200_001,
            "writer_stop_receipts": {
                "source_writer_stop_receipt_sha256": "required_separate_digest",
                "target_writer_stop_receipt_sha256": "required_separate_digest",
                "membership_writer_stop_receipt_sha256": "required_separate_digest",
                "single_collapsed_receipt_allowed": False,
                "pairwise_distinct_required": True,
                "all_three_bound_to_ledger_receipts_and_recovery": True,
            },
            "raw_sensitive_material_persisted_or_returned": False,
        },
        "schema_and_acl_verification": {
            "fixture_only_schema_scripts": [
                (
                    "server/src/test/resources/db/phase4c/"
                    "076-legacy-personal-bank-tag-operator-core-schema.sql"
                ),
                (
                    "server/src/test/resources/db/phase4c/"
                    "077-legacy-personal-bank-tag-operator-core-seed.sql"
                ),
            ],
            "production_flyway_or_schema_change": False,
            "postgresql_versions": ["16.14", "18.4"],
            "exact_relation_column_type_nullability_default_identity_checks": True,
            "primary_unique_foreign_check_and_trigger_closure": True,
            "owner_role_membership_and_effective_acl_closure": True,
            "function_identity_language_volatility_security_and_acl_closure": True,
            "hostile_search_path_safe": True,
            "schema_fingerprint_before_business_dml": True,
            "schema_or_acl_mismatch_business_dml": 0,
            "schema_verifier_uses_catalog_only": True,
            "expected_catalog_sha256": EXPECTED_CATALOG_SHA256,
        },
        "bounded_retry_and_ambiguity_recovery": {
            "retryable_root_sqlstates": ["40001", "40P01"],
            "maximum_attempts": 3,
            "maximum_retries": 2,
            "fresh_connection_pid_and_txid_per_retry": True,
            "root_sqlstate_only": True,
            "cause_or_next_exception_sqlstate_smuggling_rejected": True,
            "connection_acquisition_setup_rollback_close_and_commit_failures_terminal": True,
            "real_40001_success_and_exhaustion_on_both_postgresql_versions": True,
            "real_40P01_success_and_exhaustion_on_both_postgresql_versions": True,
            "deferred_commit_23503_nonretryable": True,
            "commit_outcome_unknown_never_reapplies_business_dml": True,
            "commit_ack_discard_evidence": "deterministic_test_fixture",
            "real_network_commit_ack_loss_evidenced": False,
            "recovery_uses_fresh_connection": True,
            "recovery_is_receipt_first": True,
        },
        "source_target_receipt_invariants": {
            "frozen_source_manifest_rechecked_before_apply": True,
            "source_target_membership_and_plan_digests_rechecked": True,
            "partial_receipts_must_be_strict_manifest_prefix": True,
            "sparse_or_out_of_order_partial_receipts_block": True,
            "exact_receipt_replay_business_dml": 0,
            "receipt_precedes_target_insert": True,
            "receipt_target_and_applied_state_commit_together": True,
            "target_digest_recomputed_from_canonical_facts": True,
            "all_empty_noop_requires_explicit_receipts": True,
            "ambiguous_recovery_mismatch_blocks": True,
            "schema_identity_or_digest_failure_fingerprint_unchanged": True,
            "users_last_active_dml": 0,
        },
        "historical_source_successors": {
            "predecessor_checkpoint": NODE_B_ANCHOR_COMMIT,
            "override_count": len(transitions),
            "overrides": transitions,
            "accepted_bytes_replayable_from_fixed_predecessor": True,
            "successor_external_git_anchor_complete": False,
            "unknown_path": "reject",
        },
        "production_runtime_successor": runtime,
        "worm_successor": {
            "accepted_report": {
                "source": (
                    "docs/refactor/phase4c/"
                    "personal-bank-tag-global-preflight-hardening-worm-evidence.json"
                ),
                "sha256": WORM_PREDECESSOR_SHA256,
            },
            "accepted_build_context_sha256": ACCEPTED_BUILD_CONTEXT_SHA256,
            "accepted_chain_node_count": 7,
            "current_report": {
                "source": WORM_RELATIVE,
                "sha256": WORM_SHA256,
                "byte_count": WORM_BYTE_COUNT,
                "captured_at": worm["capturedAt"],
            },
            "current_build_context_sha256": CURRENT_BUILD_CONTEXT_SHA256,
            "dockerfile_sha256": DOCKERFILE_SHA256,
            "current_chain_node_count": 8,
            "appended_node_count": 1,
            "historical_nodes_rewritten": False,
            "production_database_version": "unknown",
            "flyway_baseline_created": False,
        },
        "evidence": {
            "classification": (
                "test-only explicit operator core and PostgreSQL compatibility evidence; "
                "no production connection, schema, freeze or data migration"
            ),
            "targeted_unit_test_count": 83,
            "operator_postgresql_integration_test_count": 3,
            "bounded_retry_postgresql_integration_test_count": 2,
            "postgresql_versions": ["16.14", "18.4"],
            "canonical_cross_version_catalog_parity": True,
            "real_lock_wait_timeout_and_recovery_after_unlock": True,
            "sparse_partial_receipt_business_facts_and_existing_receipts_unchanged": True,
            "sparse_partial_receipt_durable_block_run_and_single_audit_only": True,
            "raw_sensitive_canary_excluded": True,
            "production_database_connected": False,
            "production_credentials_read": False,
            "production_data_read_or_mutated": False,
            "production_operator_executed": False,
            "user_compose_or_production_docker_mutated": False,
        },
        "authorization": {
            "newly_closed_gates": list(NEWLY_CLOSED_GATES),
            "migration_global_preflight_evidence_closed": True,
            "migration_durable_ledger_freeze_design_evidence_closed": True,
            "operator_core_evidence_closed": True,
            "bounded_40001_40P01_retry_implemented": True,
            "operator_migration_implementation": True,
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
            "historical_authority_source_count": 3,
            "historical_authority_sources": {
                PREDECESSOR_RELATIVE: {
                    "source": PREDECESSOR_RELATIVE,
                    "sha256": PREDECESSOR_SHA256,
                    "byte_count": PREDECESSOR_BYTE_COUNT,
                    "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
                },
                GLOBAL_PREFLIGHT_CONTRACT_RELATIVE: {
                    "source": GLOBAL_PREFLIGHT_CONTRACT_RELATIVE,
                    "sha256": GLOBAL_PREFLIGHT_CONTRACT_SHA256,
                    "byte_count": GLOBAL_PREFLIGHT_CONTRACT_BYTE_COUNT,
                    "document_payload_sha256": (
                        GLOBAL_PREFLIGHT_CONTRACT_PAYLOAD_SHA256
                    ),
                },
                HISTORICAL_RUNTIME_CONTRACT_RELATIVE: {
                    "source": HISTORICAL_RUNTIME_CONTRACT_RELATIVE,
                    "sha256": HISTORICAL_RUNTIME_CONTRACT_SHA256,
                    "byte_count": HISTORICAL_RUNTIME_CONTRACT_BYTE_COUNT,
                    "document_payload_sha256": (
                        HISTORICAL_RUNTIME_CONTRACT_PAYLOAD_SHA256
                    ),
                },
            },
            "fixed_non_control_source_count": len(source_descriptors),
            "fixed_non_control_sources": source_descriptors,
            "control_source_count": len(CONTROL_SOURCES),
            "control_sources": list(CONTROL_SOURCES),
            "control_sources_excluded_from_self_authority": True,
            "current_control_sources_external_git_anchor_complete": False,
            "fixed_source_allowlist_exact": True,
            "dynamic_source_discovery": False,
            "ordinary_build_and_load_are_gitless": True,
            "live_head_main_or_origin_authority": False,
            "unknown_source": "reject",
            "absolute_parent_escape_or_symlink": "reject",
            "historical_contract_or_worm_overwrite": False,
        },
        "next_gate": {
            "required_next": (
                "externally anchor this Node C control plane, then implement the "
                "separately authorized production schema/freeze/backup/apply gate"
            ),
            "node_c_operator_core_is_production_apply_authorization": False,
            "production_execution_requires_explicit_user_authorization": True,
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--validate-node-b-anchor-git",
        type=Path,
        help="explicit repository root for fixed bbeb08e replay",
    )
    arguments = parser.parse_args()
    if arguments.validate_node_b_anchor_git is not None:
        validate_node_b_anchor_git(arguments.validate_node_b_anchor_git)
    payload = serialized_contract(build_contract())
    if arguments.write:
        arguments.output.write_bytes(payload)
    else:
        print(payload.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
