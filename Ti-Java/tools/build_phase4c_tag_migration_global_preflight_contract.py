#!/usr/bin/env python3
"""Build the append-only Phase 4C tag-migration global-preflight contract."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-global-preflight-contract.json"
)
EXPLANATION_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-tag-migration-global-preflight.md"
)
CONTRACT_ID = "ti.phase4c.personal-bank-tag-migration-global-preflight-contract"
CAPTURED_AT = "2026-07-19T05:52:21+08:00"
PHASE2_WORM_VALIDATOR_MODULE = "tools.phase2_wormhole_successor_acceptance"
PHASE2_WORM_VALIDATOR_DIRECT_MODULE = "phase2_wormhole_successor_acceptance"
PHASE2_DRIFT_MANIFEST_RELATIVE = "infra/phase2/reference-drift-manifest.json"
TAG_GLOBAL_PREFLIGHT_WORM_LABEL = "phase4c-personal-bank-tag-global-preflight"
TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256 = (
    "2b2f2b9956a9188a81606b50405ac82ded0253bbe2539d6fb841575b4c21dcf9"
)
TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
TAG_GLOBAL_PREFLIGHT_WORM_PREDECESSOR_SHA256 = (
    "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39"
)
TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_LABEL = (
    "phase4c-personal-bank-tag-global-preflight-hardening"
)
TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256 = (
    "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17"
)
TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_PREDECESSOR_SHA256 = (
    "283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72"
)
TYPED_ANCHOR_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-typed-normalization-anchor-contract.json"
)
PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE = (
    "docs/refactor/phase6/web-foundation-source-successor-anchor-contract.json"
)
HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-contract.json"
)
HISTORICAL_READ_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json"
)
MODULE_CONTRACT_PARITY_RELATIVE = (
    "server/src/test/java/io/saksk/ti/architecture/ModuleContractParityTest.java"
)
READ_SUCCESSOR_BRIDGE_RELATIVE = "tools/phase4c_read_successor_acceptance.py"
JAVA_READ_SUCCESSOR_BRIDGE_RELATIVE = (
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cReadSuccessorAcceptance.java"
)
ALL_SHARES_ENTRY_TEST_RELATIVE = (
    "tools/test_phase4b_personal_bank_all_shares_entry_contract.py"
)
ALL_SHARES_READ_TEST_RELATIVE = (
    "tools/test_phase4b_personal_bank_all_shares_read_contract.py"
)
SHARE_LIST_ENTRY_TEST_RELATIVE = (
    "tools/test_phase4b_personal_bank_share_list_entry_contract.py"
)
SHARE_LIST_READ_TEST_RELATIVE = (
    "tools/test_phase4b_personal_bank_share_list_read_contract.py"
)
USER_COUNTS_ENTRY_TEST_RELATIVE = (
    "tools/test_phase4b_personal_bank_user_counts_entry_contract.py"
)
USAGE_STATS_ENTRY_TEST_RELATIVE = (
    "tools/test_phase4b_personal_bank_usage_stats_entry_contract.py"
)
USAGE_STATS_READ_TEST_RELATIVE = (
    "tools/test_phase4b_personal_bank_usage_stats_read_contract.py"
)
HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-contract.json"
)
HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-contract.json"
)
HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-target-execution-post-push-anchor-contract.json"
)
HISTORICAL_PRODUCTION_FILE_COUNT = 297
HISTORICAL_PRODUCTION_MANIFEST_SHA256 = (
    "d327a5ef85fa47abc6417527d7bfd99a01f29de6ea3c2f08205cbf30a6e38f79"
)
SUCCESSOR_PRODUCTION_FILE_COUNT = 300
SUCCESSOR_PRODUCTION_MANIFEST_SHA256 = (
    "8d28a382447c8756b2ec4cfc4107bc55fd744587d81a8835b71eee1f1942fbb3"
)
HISTORICAL_LEARNING_PERSONALBANK_MAIN_FILE_COUNT = 40
HISTORICAL_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256 = (
    "d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1"
)
SUCCESSOR_LEARNING_PERSONALBANK_MAIN_FILE_COUNT = 43
SUCCESSOR_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256 = (
    "2cc855057a4b3b6b5693ad717404ea6b9828de3aa73ef9be8a9a1a62b177f751"
)
HISTORICAL_BUILD_CONTEXT_SHA256 = (
    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
)
PRODUCTION_MANIFEST_ADDITIONS = {
    (
        "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
        "LegacyPersonalBankTagGlobalPreflight.java"
    ): "cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76",
    (
        "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
        "LegacyPersonalBankTagPreflightParser.java"
    ): "c3311e28f33c8bc447fd72191af696ceca333162747e94eb91681dd75c0f5bf3",
    (
        "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
        "LegacyPersonalBankTagPreflightReport.java"
    ): "d7d988f5bfe7c86e30a5410e8eac0032a24ad5c85011b6c03de159c97d3ff750",
}
TYPED_ANCHOR_PYTHON_BRIDGE_RELATIVE = (
    "tools/phase4c_http_typed_normalization_anchor_successor_acceptance.py"
)
TYPED_ANCHOR_JAVA_BRIDGE_RELATIVE = (
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java"
)
TYPED_ANCHOR_PYTHON_TEST_RELATIVE = (
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "typed_normalization_anchor_contract.py"
)
TYPED_ANCHOR_JAVA_PARITY_RELATIVE = (
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java"
)
PHASE6_BOOTSTRAP_PYTHON_TEST_RELATIVE = (
    "tools/test_phase6_web_foundation_source_successor_contract.py"
)
PHASE6_BOOTSTRAP_JAVA_PARITY_RELATIVE = (
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorContractParityTest.java"
)
TYPED_PHASE2_SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    "infra/phase2/README.md": {
        "accepted_sha256": (
            "414901d53174c7875ea000c323652a1ddf046a2e97018bbbd1dc4c9a4b3bf988"
        ),
        "accepted_byte_count": 6_959,
        "successor_sha256": (
            "a0c467bfc8aa0f0b64b4d520f9cda60ff081a340f016647e1da934c73b7b99d5"
        ),
        "successor_byte_count": 7_474,
        "accepted_authority": TYPED_ANCHOR_CONTRACT_RELATIVE,
    },
    "infra/phase2/verify-static.sh": {
        "accepted_sha256": (
            "410108998f03e4d857d230c75687e854bd3bad99ba85d18c2fb090978ffa46d7"
        ),
        "accepted_byte_count": 14_719,
        "successor_sha256": (
            "893ca920d0ed1bd62e16509893fa30bbfc72b88368d66d96c2ebc5c2fbae38dc"
        ),
        "successor_byte_count": 16_417,
        "accepted_authority": TYPED_ANCHOR_CONTRACT_RELATIVE,
    },
    "tools/phase2_wormhole_successor_acceptance.py": {
        "accepted_sha256": (
            "1164b6c584f4905a8011c5320eac62591e039ad0526b5a0657908f7b82688480"
        ),
        "accepted_byte_count": 25_791,
        "successor_sha256": (
            "5c93b9aa00d3faec19ebc8d6472bd9e8ab1903a7116d487ff8a711fc60fd8d20"
        ),
        "successor_byte_count": 28_590,
        "accepted_authority": TYPED_ANCHOR_CONTRACT_RELATIVE,
    },
    "tools/test_phase2_wormhole_successor_acceptance.py": {
        "accepted_sha256": (
            "ff3250a88eb6e16102fc91930beec627f79ed57720140a32e7ad4410d7856e9f"
        ),
        "accepted_byte_count": 44_809,
        "successor_sha256": (
            "e61ed72335bba631cf34ebfe06fae8d391e7828622eba17d0240f59efed379a3"
        ),
        "successor_byte_count": 52_825,
        "accepted_authority": TYPED_ANCHOR_CONTRACT_RELATIVE,
    },
}
PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    TYPED_ANCHOR_PYTHON_BRIDGE_RELATIVE: {
        "accepted_sha256": (
            "cf434c2dc8e33c0b60d09646292fc358bc2df678bfe2f83d04edae79c7bd4aee"
        ),
        "accepted_byte_count": 41_725,
        "successor_sha256": (
            "c54843d2c759882e4d5e7553e9b76598a1ecd31038ace27ac265275887a414d2"
        ),
        "successor_byte_count": 45_142,
        "accepted_authority": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
    },
    TYPED_ANCHOR_JAVA_BRIDGE_RELATIVE: {
        "accepted_sha256": (
            "b762441b9d0537240e231effbe5477b89713e7abc861ff9d5a614fc80008848c"
        ),
        "accepted_byte_count": 43_848,
        "successor_sha256": (
            "57be8ccb44124d315c21e21e9041861cdcb4568a814af56dbe1725635a479374"
        ),
        "successor_byte_count": 45_695,
        "accepted_authority": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
    },
    TYPED_ANCHOR_PYTHON_TEST_RELATIVE: {
        "accepted_sha256": (
            "a96c4431b258b15d367250b668602fcb0ca04cab9555f13a4abfaa8914b0edec"
        ),
        "accepted_byte_count": 11_128,
        "successor_sha256": (
            "cdc78a5f771d09eb1822f3dbcd10030e812e4a5ab6b7792ce2b0a9d8366e90ba"
        ),
        "successor_byte_count": 13_443,
        "accepted_authority": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
    },
    TYPED_ANCHOR_JAVA_PARITY_RELATIVE: {
        "accepted_sha256": (
            "f0f57fbd1c24e8f26878209eba298645c63bd962381d26d2505fb76ee495cda8"
        ),
        "accepted_byte_count": 14_962,
        "successor_sha256": (
            "faff2f55f48cdaa8bab92530347cda47a0f3ba4dc4227c86242afb94d78aebc0"
        ),
        "successor_byte_count": 17_295,
        "accepted_authority": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
    },
}
PHASE6_DOCUMENT_SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    "docs/refactor/05-progress.md": {
        "accepted_sha256": (
            "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b"
        ),
        "accepted_byte_count": 105_423,
        "successor_sha256": (
            "8478e44622fc666fdb9a377b15ced624e34d104d1fcbb9b36a4913cfb3ddedf0"
        ),
        "successor_byte_count": 107_912,
        "accepted_authority": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
    },
    "docs/refactor/phase4c/README.md": {
        "accepted_sha256": (
            "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c"
        ),
        "accepted_byte_count": 23_309,
        "successor_sha256": (
            "4d75ba666d7d45d620a4fba4574e4c2640b754c5a6beadbdbfdee5498aa3cc48"
        ),
        "successor_byte_count": 26_858,
        "accepted_authority": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
    },
}
PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    PHASE6_BOOTSTRAP_PYTHON_TEST_RELATIVE: {
        "accepted_sha256": (
            "fb553e8d15c8b748dc62eb6517f775614132657a60b13716449ad1a72606685d"
        ),
        "accepted_byte_count": 9_139,
        "successor_sha256": (
            "3bc6342e7dad775f7c92acfc0f8cb23cd94aabd6d395f4f0fae420faea14ee6b"
        ),
        "successor_byte_count": 9_295,
        "accepted_authority": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
    },
    PHASE6_BOOTSTRAP_JAVA_PARITY_RELATIVE: {
        "accepted_sha256": (
            "34d6b638cf40667a2c0b1ce1214cc04b8e149321f3137ea8d5d09ee44290d694"
        ),
        "accepted_byte_count": 11_770,
        "successor_sha256": (
            "e61b445cbedddd5b71efe7dda22811128414b58089bf1525aaa4017485f6675d"
        ),
        "successor_byte_count": 11_762,
        "accepted_authority": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
    },
}
SEMANTIC_CONSUMER_SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    "tools/build_phase4c_personal_bank_user_counts_http_implementation_contract.py": {
        "accepted_sha256": (
            "d020cf859dcba608d9b67d122ebfaca0d1bfd3161a12fc7c386d090e65938ef0"
        ),
        "accepted_byte_count": 54_261,
        "successor_sha256": (
            "1f1c31977c356d93bfabe6714692efa27c5b3c34178e6df6b3517a3362f610e3"
        ),
        "successor_byte_count": 57_899,
        "accepted_authority": HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE,
    },
    "tools/phase4c_http_implementation_successor_acceptance.py": {
        "accepted_sha256": (
            "54438d9ee44d391b813a1c3503444dd65d627e3b5932971e49ef549650fbbff4"
        ),
        "accepted_byte_count": 59_107,
        "successor_sha256": (
            "f0eba1dbbe3f0cfdbd384c0aea8ba9b768d16edc414ed7c1b1cf5fa8fd31641d"
        ),
        "successor_byte_count": 61_439,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py": {
        "accepted_sha256": (
            "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209"
        ),
        "accepted_byte_count": 61_952,
        "successor_sha256": (
            "3064c164d300499d958947068d3acd50c8823c741d9a0144860b5f3b1b532f7d"
        ),
        "successor_byte_count": 65_798,
        "accepted_authority": (
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
        ),
    },
    "tools/phase4c_http_target_execution_successor_acceptance.py": {
        "accepted_sha256": (
            "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a"
        ),
        "accepted_byte_count": 81_902,
        "successor_sha256": (
            "daca285575123c6b3d690c52977bbf8797fa46d5db75862b774805acb586a230"
        ),
        "successor_byte_count": 84_585,
        "accepted_authority": (
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
        ),
    },
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py": {
        "accepted_sha256": (
            "b87133b5c187561970c322a92eb22f84cb7a768a9168870cc7517dd973616667"
        ),
        "accepted_byte_count": 34_518,
        "successor_sha256": (
            "624d741b383866ce1bb8ec49c24445164665096cdf5b9ab679b2561c61ab7e9a"
        ),
        "successor_byte_count": 36_240,
        "accepted_authority": (
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT_RELATIVE
        ),
    },
    "tools/phase4c_http_target_execution_anchor_successor_acceptance.py": {
        "accepted_sha256": (
            "03b411be87bd9f8d4dbb94ddcfb9495ec7523fb5c9482f3c1fb4098d1ab7e455"
        ),
        "accepted_byte_count": 34_568,
        "successor_sha256": (
            "e91c56e91cdeff3bf069407d8e43d7d1b76fb131c875cf536e561976fe395141"
        ),
        "successor_byte_count": 36_566,
        "accepted_authority": (
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT_RELATIVE
        ),
    },
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": {
        "accepted_sha256": (
            "b81c8fb13f2ce4dd0d917a0876b88a20804bd1d272a7c261563dad9513d42f17"
        ),
        "accepted_byte_count": 55_453,
        "successor_sha256": (
            "51ab42d0a220f3e91ac07a9b3ab1f6a2ca6c366b994de200effae31a074a766b"
        ),
        "successor_byte_count": 60_156,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": {
        "accepted_sha256": (
            "641c90d33de50daeb3a1a1c9a3ae5027562273f780f88e6a26cf00ad3bd462ac"
        ),
        "accepted_byte_count": 21_392,
        "successor_sha256": (
            "6c302395dca0d7d319233e6463ed65b26aa3ea103c90511752ae4cac710dbaad"
        ),
        "successor_byte_count": 24_536,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    MODULE_CONTRACT_PARITY_RELATIVE: {
        "accepted_sha256": (
            "02a4b9bfabe2f9e3789e94826b1f337e8a0986e5d36f42ac243cbe79060a82d2"
        ),
        "accepted_byte_count": 181_374,
        "successor_sha256": (
            "984863bff3762adc8e375f0073559bb1e0e1d0ed16c368147087fdc3ca4efcd1"
        ),
        "successor_byte_count": 182_577,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    READ_SUCCESSOR_BRIDGE_RELATIVE: {
        "accepted_sha256": (
            "1e494bce628e87bc2db3d01742fb929752fedaefd7563defccad7b972c951980"
        ),
        "accepted_byte_count": 13_218,
        "successor_sha256": (
            "25792f3a1371b8a492d674d70228ce81872e0ce48c2aab8051805c8c0b41de8a"
        ),
        "successor_byte_count": 15_161,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    JAVA_READ_SUCCESSOR_BRIDGE_RELATIVE: {
        "accepted_sha256": (
            "5047c8b0a36450a72ba74a460db115ab33a58861b64216fa2cc67a7ddb0a026d"
        ),
        "accepted_byte_count": 18_364,
        "successor_sha256": (
            "4699c29cb6e5f790b448752896cc42c413e9f0b3c4844551c4a0b2931517d1a0"
        ),
        "successor_byte_count": 19_159,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    ALL_SHARES_ENTRY_TEST_RELATIVE: {
        "accepted_sha256": (
            "e37b0418e8018d58135c5b1c55149d9679dfedb21f8b67fca3425b874ea23efc"
        ),
        "accepted_byte_count": 23_701,
        "successor_sha256": (
            "31dec8b10fad1f044ecbca4a76da0d4f1f97ffbbe32e075895e050372ff8ba4a"
        ),
        "successor_byte_count": 24_249,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    ALL_SHARES_READ_TEST_RELATIVE: {
        "accepted_sha256": (
            "f236ed8080a4e73d294d0eb96f1b19f8b3116ef0a51ba1be6d5d8e695dc558e0"
        ),
        "accepted_byte_count": 18_911,
        "successor_sha256": (
            "7afd91f0e0048cba029d38965c900da670d5f327b8b9541b0962533b1b1f09eb"
        ),
        "successor_byte_count": 19_451,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    SHARE_LIST_ENTRY_TEST_RELATIVE: {
        "accepted_sha256": (
            "c60e4d9abb01c70001e703cf8c4c5eed77bd65445c506e99a9e3dd38dadab2ee"
        ),
        "accepted_byte_count": 32_717,
        "successor_sha256": (
            "32b4d8e625f452ba20852fe64805086a6d878f3f8518298e7340122ff6120943"
        ),
        "successor_byte_count": 33_265,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    SHARE_LIST_READ_TEST_RELATIVE: {
        "accepted_sha256": (
            "ffde7c337edf81ba8cf1a457800e89e3150df10b44ea7da50e99436534caa671"
        ),
        "accepted_byte_count": 45_007,
        "successor_sha256": (
            "047563af77f5786b0af24eeb20f8d287163df44778aad1ee56d1805a05207ec4"
        ),
        "successor_byte_count": 45_547,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    USER_COUNTS_ENTRY_TEST_RELATIVE: {
        "accepted_sha256": (
            "84f7ee524b57e9417267380b73ebc68439382b578f2b7674c50cdbf2a6021e0e"
        ),
        "accepted_byte_count": 36_086,
        "successor_sha256": (
            "162e057e07d6d0d0f73b6ee8bf9210fd98c492369222ce649a4f5bd5418b16b4"
        ),
        "successor_byte_count": 37_033,
        "accepted_authority": HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE,
    },
    USAGE_STATS_ENTRY_TEST_RELATIVE: {
        "accepted_sha256": (
            "de1415897a0cef4e98266aaca699b162dd469caf17628dd2fde19bed691ef32c"
        ),
        "accepted_byte_count": 25_059,
        "successor_sha256": (
            "4f3c9ab19370eabd6dbe6dbea047d1e176c3a4e8ed947035a54dc210b75e2057"
        ),
        "successor_byte_count": 25_598,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    USAGE_STATS_READ_TEST_RELATIVE: {
        "accepted_sha256": (
            "90c77b28c1c08822d900f150e5c4c69fe4a7463b5dfc7a4ce021fc599c71a15a"
        ),
        "accepted_byte_count": 33_924,
        "successor_sha256": (
            "0a980e05a5fd4204e5db630447c7b018d54e2e89b64e7f069eb1329f85a5d372"
        ),
        "successor_byte_count": 34_463,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ): {
        "accepted_sha256": (
            "1d2c193fb7a63173850bfee7ce382e7b4bc417c5b3879f3ef4bb43187f980275"
        ),
        "accepted_byte_count": 79_412,
        "successor_sha256": (
            "fff0820405e76a4b7c58b094e21619ea050664a3b3ebfbc59abc29a83755465d"
        ),
        "successor_byte_count": 80_984,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): {
        "accepted_sha256": (
            "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578"
        ),
        "accepted_byte_count": 89_014,
        "successor_sha256": (
            "10d19deb68495db02f9113dd58bdf7bbf7dfa67a8885c49f7dd88685f574ff78"
        ),
        "successor_byte_count": 91_381,
        "accepted_authority": (
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
        ),
    },
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py": {
        "accepted_sha256": (
            "a8ce7fc93fe022d16a10e4bdd0fa9bff55788b076eb78601efba373c29c54a4b"
        ),
        "accepted_byte_count": 32_651,
        "successor_sha256": (
            "469c46bde8e339ef28a461f3fd2a34ee7e02bfa12cb75eec4f881454049e7957"
        ),
        "successor_byte_count": 34_398,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
    "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py": {
        "accepted_sha256": (
            "c87d528ad6ee912863da16a49e0a398cffe3c9479d1f58461e32035b76fafd26"
        ),
        "accepted_byte_count": 31_074,
        "successor_sha256": (
            "fcc4eee103b33604addfd17e453793dd41c498de62fe0538e873520dbd285b26"
        ),
        "successor_byte_count": 32_398,
        "accepted_authority": HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE,
    },
    (
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py"
    ): {
        "accepted_sha256": (
            "a215e6b65624630de990dcae7e8d718e8a38a1fadae3e00ee0f3ccb81788959f"
        ),
        "accepted_byte_count": 31_546,
        "successor_sha256": (
            "bbafe62ee77ab0e5c25ed0daf96dc8207cc033d4f39f6cdb3d9cfa8f18365285"
        ),
        "successor_byte_count": 33_559,
        "accepted_authority": (
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
        ),
    },
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py"
    ): {
        "accepted_sha256": (
            "87078f6d01957dcbbb37b488048a6702bc2212850ee9b2b75aa9b68aba352057"
        ),
        "accepted_byte_count": 12_208,
        "successor_sha256": (
            "420a727733f4c3a72f1c78c933491ab89fff7bbba0ddb1f1c9f7a8867a73c3bf"
        ),
        "successor_byte_count": 12_482,
        "accepted_authority": TYPED_ANCHOR_CONTRACT_RELATIVE,
    },
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py"
    ): {
        "accepted_sha256": (
            "3ded87895b33befb0f80905a1490d5f9207ae4e9ee26e939e5c00ebbd30a7874"
        ),
        "accepted_byte_count": 19_311,
        "successor_sha256": (
            "49621a580785ddd0c1210bf564e563b41e04bebbc87c33752e95bc6cb9cb89fd"
        ),
        "successor_byte_count": 19_769,
        "accepted_authority": TYPED_ANCHOR_CONTRACT_RELATIVE,
    },
    "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py": {
        "accepted_sha256": (
            "9c61d6cefdd980457197fb850f690c6adc1a84fdb3d21905a2a5cfdb1bc258c2"
        ),
        "accepted_byte_count": 10_281,
        "successor_sha256": (
            "a6b70a441470d079b5bc2dc392887d49af72d6dc75a4feba3226a772b5b4c9d5"
        ),
        "successor_byte_count": 10_308,
        "accepted_authority": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
    },
}
SEMANTIC_TARGET_EXECUTION_SOURCE_KEYS = {
    READ_SUCCESSOR_BRIDGE_RELATIVE: "historical_python_read_successor_bridge",
    JAVA_READ_SUCCESSOR_BRIDGE_RELATIVE: "historical_java_read_successor_bridge",
    ALL_SHARES_ENTRY_TEST_RELATIVE: (
        "historical_all_shares_entry_contract_test"
    ),
    SHARE_LIST_READ_TEST_RELATIVE: (
        "historical_share_list_read_contract_test"
    ),
    "tools/phase4c_http_implementation_successor_acceptance.py": (
        "historical_python_implementation_successor_bridge"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ): "historical_java_implementation_successor_bridge",
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "historical_composition_contract_test"
    ),
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": (
        "historical_read_contract_test"
    ),
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py": (
        "contract_test"
    ),
    "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py": (
        "historical_implementation_contract_test"
    ),
}
SEMANTIC_TARGET_EXECUTION_OVERRIDE_PATHS = frozenset(
    {
        READ_SUCCESSOR_BRIDGE_RELATIVE,
        JAVA_READ_SUCCESSOR_BRIDGE_RELATIVE,
        ALL_SHARES_ENTRY_TEST_RELATIVE,
        SHARE_LIST_READ_TEST_RELATIVE,
        "tools/phase4c_http_implementation_successor_acceptance.py",
        (
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpImplementationSuccessorAcceptance.java"
        ),
        "tools/test_phase4c_personal_bank_user_counts_composition_contract.py",
        "tools/test_phase4c_personal_bank_user_counts_read_contract.py",
        "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py",
    }
)
SEMANTIC_HTTP_IMPLEMENTATION_OVERRIDE_PATH = (
    "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py"
)
SEMANTIC_POST_PUSH_ANCHOR_PATHS = (
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py",
    "tools/phase4c_http_target_execution_successor_acceptance.py",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ),
)
SEMANTIC_POST_PUSH_CONTRACT_ARTIFACT_KEYS = {
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py": (
        "anchor_builder"
    ),
    "tools/phase4c_http_target_execution_anchor_successor_acceptance.py": (
        "python_anchor_acceptance"
    ),
}
SEMANTIC_POST_PUSH_ANCHOR_OVERRIDE_PATH = (
    "tools/build_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py"
)
SEMANTIC_TYPED_ANCHOR_OVERRIDE_PATHS = (
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_contract.py",
    "tools/test_phase4c_personal_bank_user_counts_http_"
    "target_execution_post_push_anchor_contract.py",
)
CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY = (
    "code_fixed_pending_bootstrap_external_git_anchor"
)
SEMANTIC_READ_CONSUMER_PATHS = frozenset(
    {
        MODULE_CONTRACT_PARITY_RELATIVE,
        ALL_SHARES_READ_TEST_RELATIVE,
        SHARE_LIST_ENTRY_TEST_RELATIVE,
        USAGE_STATS_ENTRY_TEST_RELATIVE,
        USAGE_STATS_READ_TEST_RELATIVE,
    }
)
SEMANTIC_HTTP_IMPLEMENTATION_SOURCE_KEYS = {
    USER_COUNTS_ENTRY_TEST_RELATIVE: "historical_phase4b_entry_contract_test",
}
SEMANTIC_ACCEPTED_AUTHORITY_FIELDS: dict[str, dict[str, str]] = {
    (
        "tools/build_phase4c_personal_bank_user_counts_"
        "http_implementation_contract.py"
    ): {
        "accepted_sha256_authority": (
            f"{HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE}"
            "#/source_contracts/contract_builder/sha256"
        ),
        "accepted_byte_count_authority": (
            CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
        ),
    },
    SEMANTIC_HTTP_IMPLEMENTATION_OVERRIDE_PATH: {
        "accepted_sha256_authority": (
            f"{HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE}"
            "#/historical_successor_acceptance/http_entry_source_overrides/"
            "tools~1test_phase4c_personal_bank_user_counts_http_entry_contract.py/"
            "successor_sha256"
        ),
        "accepted_byte_count_authority": (
            CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
        ),
    },
    **{
        relative: {
            "accepted_sha256_authority": (
                f"{HISTORICAL_READ_CONTRACT_RELATIVE}"
                "#/historical_successor_acceptance/"
                f"{'java_sources' if relative == MODULE_CONTRACT_PARITY_RELATIVE else 'python_sources'}/"
                f"{relative.replace('/', '~1')}/successor_sha256"
            ),
            "accepted_byte_count_authority": (
                CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
            ),
        }
        for relative in SEMANTIC_READ_CONSUMER_PATHS
    },
    USER_COUNTS_ENTRY_TEST_RELATIVE: {
        "accepted_sha256_authority": (
            f"{HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE}"
            "#/source_contracts/historical_phase4b_entry_contract_test/sha256"
        ),
        "accepted_byte_count_authority": (
            CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
        ),
    },
    **{
        relative: {
            "accepted_sha256_authority": (
                f"{HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE}"
                f"#/source_contracts/{source_key}/sha256"
            ),
            "accepted_byte_count_authority": (
                CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
            ),
        }
        for relative, source_key in SEMANTIC_TARGET_EXECUTION_SOURCE_KEYS.items()
    },
    **{
        relative: {
            "accepted_sha256_authority": (
                f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE}"
                f"#/git_checkpoint/artifacts/{relative.replace('/', '~1')}/sha256"
            ),
            "accepted_byte_count_authority": (
                f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE}"
                f"#/git_checkpoint/artifacts/{relative.replace('/', '~1')}/byte_count"
            ),
        }
        for relative in SEMANTIC_POST_PUSH_ANCHOR_PATHS
    },
    **{
        relative: {
            "accepted_sha256_authority": (
                f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT_RELATIVE}"
                f"#/git_checkpoint/artifacts/{artifact_key}/sha256"
            ),
            "accepted_byte_count_authority": (
                f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT_RELATIVE}"
                f"#/git_checkpoint/artifacts/{artifact_key}/byte_count"
            ),
        }
        for relative, artifact_key in (
            SEMANTIC_POST_PUSH_CONTRACT_ARTIFACT_KEYS.items()
        )
    },
    SEMANTIC_POST_PUSH_ANCHOR_OVERRIDE_PATH: {
        "accepted_sha256_authority": (
            f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE}"
            "#/historical_source_successors/overrides/"
            "tools~1build_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_contract.py/successor_sha256"
        ),
        "accepted_byte_count_authority": (
            f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE}"
            "#/historical_source_successors/overrides/"
            "tools~1build_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_contract.py/successor_byte_count"
        ),
    },
    **{
        relative: {
            "accepted_sha256_authority": (
                f"{TYPED_ANCHOR_CONTRACT_RELATIVE}"
                "#/historical_source_successors/overrides/"
                f"{relative.replace('/', '~1')}/successor_sha256"
            ),
            "accepted_byte_count_authority": (
                f"{TYPED_ANCHOR_CONTRACT_RELATIVE}"
                "#/historical_source_successors/overrides/"
                f"{relative.replace('/', '~1')}/successor_byte_count"
            ),
        }
        for relative in SEMANTIC_TYPED_ANCHOR_OVERRIDE_PATHS
    },
}
if set(SEMANTIC_ACCEPTED_AUTHORITY_FIELDS) != set(
    SEMANTIC_CONSUMER_SOURCE_SUCCESSORS
):
    raise AssertionError("tag preflight semantic authority-field allowlist drifted")
for _relative, _authority_fields in SEMANTIC_ACCEPTED_AUTHORITY_FIELDS.items():
    SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[_relative].update(_authority_fields)
POST_PUSH_BRIDGE_SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    "tools/phase4c_http_target_execution_post_push_successor_acceptance.py": {
        "accepted_sha256": (
            "944c925704e1b237a7d8e16c76591a0e8b7965d388bedd9e2a52492e0511c90c"
        ),
        "accepted_byte_count": 30_640,
        "successor_sha256": (
            "b19db64d6ddb71b0cac1d4ae296c02e65e82d476b37b9db5ec5fbfcfd7f4a8df"
        ),
        "successor_byte_count": 32_538,
        "accepted_authority": (
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
        ),
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java"
    ): {
        "accepted_sha256": (
            "46f68412ea0cf42687133ba87a2184b86fe1b0c29625b1ee3f6e8f7301399efa"
        ),
        "accepted_byte_count": 45_004,
        "successor_sha256": (
            "a39a7b768979208e5bdcbdcbcbfa7d327521fb69e65d271b5d2f2da47f7ad348"
        ),
        "successor_byte_count": 46_017,
        "accepted_authority": (
            HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
        ),
    },
}
for _relative, _transition in POST_PUSH_BRIDGE_SOURCE_SUCCESSORS.items():
    _pointer = _relative.replace("/", "~1")
    _transition.update(
        {
            "accepted_sha256_authority": (
                f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE}"
                f"#/historical_source_successors/overrides/{_pointer}/"
                "successor_sha256"
            ),
            "accepted_byte_count_authority": (
                f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE}"
                f"#/historical_source_successors/overrides/{_pointer}/"
                "successor_byte_count"
            ),
        }
    )
TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS: dict[str, dict[str, Any]] = {
    "tools/phase4c_http_typed_normalization_successor_acceptance.py": {
        "accepted_sha256": (
            "e71a5eec0e71ff824750f6eb20c4b310fdb0d8273fe89d83a23aee422ba282c5"
        ),
        "accepted_byte_count": 54_168,
        "successor_sha256": (
            "a852f20ffccd8d2f1597a1bd2adb525ca66e83fed707ef6d44ff9a8d35c240c8"
        ),
        "successor_byte_count": 57_882,
        "accepted_authority": TYPED_ANCHOR_CONTRACT_RELATIVE,
    },
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTypedNormalizationSuccessorAcceptance.java"
    ): {
        "accepted_sha256": (
            "f78882b20e38857c420b750677e4e8dd52922a1f0c04c249db9ed0d4f3db4fd5"
        ),
        "accepted_byte_count": 76_703,
        "successor_sha256": (
            "ec7c98b04a26f25940fd5b9ec4120ebd478aa41798d4040f1cce97336898d6d2"
        ),
        "successor_byte_count": 79_735,
        "accepted_authority": TYPED_ANCHOR_CONTRACT_RELATIVE,
    },
}
for _relative, _transition in (
    TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS.items()
):
    _pointer = _relative.replace("/", "~1")
    _transition.update(
        {
            "accepted_sha256_authority": (
                f"{TYPED_ANCHOR_CONTRACT_RELATIVE}"
                f"#/historical_source_successors/overrides/{_pointer}/"
                "successor_sha256"
            ),
            "accepted_byte_count_authority": (
                f"{TYPED_ANCHOR_CONTRACT_RELATIVE}"
                f"#/historical_source_successors/overrides/{_pointer}/"
                "successor_byte_count"
            ),
        }
    )
SOURCE_SUCCESSORS = {
    **TYPED_PHASE2_SOURCE_SUCCESSORS,
    **PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS,
    **PHASE6_DOCUMENT_SOURCE_SUCCESSORS,
    **PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS,
    **SEMANTIC_CONSUMER_SOURCE_SUCCESSORS,
    **POST_PUSH_BRIDGE_SOURCE_SUCCESSORS,
    **TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS,
}
PHASE2_FIXED_CHAIN_FIXTURE_PATHS = (
    PHASE2_DRIFT_MANIFEST_RELATIVE,
    "infra/phase2/local-reference-verification.json",
    "docs/refactor/phase4c/personal-bank-user-counts-entry-worm-evidence.json",
    "docs/refactor/phase4c/personal-bank-user-counts-read-worm-evidence.json",
    "docs/refactor/phase4c/personal-bank-user-counts-read-access-worm-evidence.json",
    (
        "docs/refactor/phase4c/"
        "personal-bank-user-counts-http-implementation-worm-evidence.json"
    ),
    "docs/refactor/phase4c/personal-bank-tag-global-preflight-worm-evidence.json",
    (
        "docs/refactor/phase4c/"
        "personal-bank-tag-global-preflight-hardening-worm-evidence.json"
    ),
    "docs/refactor/phase4b/personal-bank-share-list-worm-evidence.json",
)


def _successor_source_descriptor(relative: str) -> dict[str, Any]:
    transition = SOURCE_SUCCESSORS[relative]
    return {
        "source": relative,
        "sha256": transition["successor_sha256"],
        "byte_count": transition["successor_byte_count"],
    }

# Every authority-bearing input is a code-fixed path -> physical-bytes descriptor.
# The Phase 4C control files below are deliberately absent: a contract must not
# authorize itself, its builder, its acceptance bridge, its tests, or its prose.
SOURCES: dict[str, dict[str, Any]] = {
    "semantic_composition": {
        "source": "docs/refactor/phase4c/personal-bank-user-counts-composition-contract.json",
        "sha256": "ba900795d92046693617d92f4de7599d604e389e7b60e1cc145d08a737518f6b",
        "document_payload_sha256": (
            "b7cdfcfe3ec0ca29a397c608439c18810c3d55c42b64ad94368d1a0337771409"
        ),
        "byte_count": 105_146,
    },
    "current_route_promotion": {
        "source": "docs/refactor/phase4c/personal-bank-user-counts-route-promotion-contract.json",
        "sha256": "e5bc53bb8c011c5cf2f08447543aa3e5dd2a045b6226f064c6594a3639d7b5c9",
        "document_payload_sha256": (
            "1503c4dd5905abb70a77835e6602d8e51a7f042f5eed6b0a25a9a0de4b5f6e0f"
        ),
        "byte_count": 4_365,
    },
    "approved_differences": {
        "source": "docs/refactor/phase4c/approved-differences.md",
        "sha256": "921d6626ab11d59a9667e1942953807b0aa1a81c06c01094cc109312f9d6b300",
        "byte_count": 27_510,
    },
    "effective_data_ownership": {
        "source": "docs/refactor/phase4c/effective-data-ownership-status.json",
        "sha256": "025a9f24edfb502b49e672c7c0a2e52b6bba022d6337dfe56159ebd498b69eb7",
        "document_payload_sha256": (
            "e3c7e2cde4853c241fccc5626da4ed9690d09c74f4bd8c3075d1b2fe5f2b75d9"
        ),
        "byte_count": 1_081,
    },
    "data_ownership_delta": {
        "source": "docs/refactor/phase4c/data-ownership-delta.csv",
        "sha256": "b7ce8ba5a8ed221bd89c8b2287cb7fdc77caa424614097e62f141d923cc66b40",
        "byte_count": 388,
    },
    "historical_row_primitive": {
        "source": (
            "server/src/test/java/io/saksk/ti/learning/infrastructure/persistence/"
            "LegacyPersonalBankTagMigrationEvidence.java"
        ),
        "sha256": "978437b09667155250d7ef14f59ad841eeb7637bf9324953b41256ce8512cc96",
        "byte_count": 34_650,
    },
    "historical_row_primitive_unit": {
        "source": (
            "server/src/test/java/io/saksk/ti/learning/infrastructure/persistence/"
            "LegacyPersonalBankTagMigrationEvidenceTest.java"
        ),
        "sha256": "ccfacca97b2c249f830f28046b4f465d26d47dc6bb00d6f804d18565f70e5ce4",
        "byte_count": 26_764,
    },
    "historical_row_primitive_pg_it": {
        "source": (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4cLegacyPersonalBankTagMigrationEvidenceIT.java"
        ),
        "sha256": "0f76421bcb6d609897359c03d8e2abd650076fe4db3bead6f402914175e2e70f",
        "byte_count": 16_705,
    },
    "historical_row_primitive_schema": {
        "source": (
            "server/src/test/resources/db/phase4c/"
            "069-legacy-personal-bank-tag-migration-schema.sql"
        ),
        "sha256": "c873c1660963fff337346d0252f9a6bc5dd40d78f8cf41d3478dbaedfaecb0cb",
        "byte_count": 370,
    },
    "historical_row_primitive_seed": {
        "source": (
            "server/src/test/resources/db/phase4c/"
            "070-legacy-personal-bank-tag-migration-seed.sql"
        ),
        "sha256": "c079c66fe31d5a9594341e8d296fbc1fc3bde8790eb7d09952e68f17ae424323",
        "byte_count": 4_668,
    },
    "membership_api": {
        "source": (
            "server/src/main/java/io/saksk/ti/personalbank/api/"
            "PersonalBankQuestionFactsApi.java"
        ),
        "sha256": "afd5b38759ae2d38cc4ef59ef0bcd25ac68df43b265f13ebb35b4b9a3482d99d",
        "byte_count": 641,
    },
    "membership_view": {
        "source": (
            "server/src/main/java/io/saksk/ti/personalbank/api/"
            "PersonalBankQuestionMembershipView.java"
        ),
        "sha256": "4a7a7086bde507d6f3390ec718bca9f17c838984be056ffa4323f743e8429423",
        "byte_count": 3_202,
    },
    "typed_anchor_contract": {
        "source": TYPED_ANCHOR_CONTRACT_RELATIVE,
        "sha256": "c713aa04a82f340ea04fdd5ae870bd5cfae82f099101431c664f047c2d5218ca",
        "document_payload_sha256": (
            "430ef24103006265001ecd1f2f6aa5e4b24a886e82fcc1391cc516eba5dbde7c"
        ),
        "byte_count": 43_737,
    },
    "phase6_source_successor_anchor_contract": {
        "source": PHASE6_SOURCE_SUCCESSOR_ANCHOR_CONTRACT_RELATIVE,
        "sha256": "c91b924c027af0099dfec9d8ff36945635b128ba5822c8faca1f6fcfb2167da2",
        "document_payload_sha256": (
            "87d952b1ba4ca4336c067d8d68ffbe86101ea0263c854541674ac3dbd7feb4af"
        ),
        "byte_count": 29_658,
    },
    "historical_target_execution_contract": {
        "source": HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE,
        "sha256": "9f6c37c4217da83199403da8207ed4f89a3999fafd149f069afb520dee4d2460",
        "document_payload_sha256": (
            "331c82ad941f4eeb3e07d1701271310f2b1dea91132794e4e5d1eb1b466fc458"
        ),
        "byte_count": 74_597,
    },
    "historical_read_contract": {
        "source": HISTORICAL_READ_CONTRACT_RELATIVE,
        "sha256": "458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73",
        "document_payload_sha256": (
            "216cf664c4d74e67169f4f5c8091f80296964938d31911e3a32aeb3630a3d7a5"
        ),
        "byte_count": 82_766,
    },
    "historical_http_implementation_contract": {
        "source": HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE,
        "sha256": "c6a977f260bdd0ab4af6dace1b4c7d48803b5e8f9bc5299723b662226e45cfbd",
        "document_payload_sha256": (
            "f6eff86bea6a1d04bc43bfe8a532ff952f295c6aa2d1d89f6b40f6fe02dc91f9"
        ),
        "byte_count": 94_142,
    },
    "historical_target_execution_post_push_contract": {
        "source": HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT_RELATIVE,
        "sha256": "3d7208eb2f70b9eb2b559e15acb4cc7882dacecf8cad941f2978678f93b12628",
        "document_payload_sha256": (
            "c2382550719d97e74f93db97bf74e70e246cca1e35ac6cc9c6c9e8d13b964dba"
        ),
        "byte_count": 17_974,
    },
    "historical_target_execution_post_push_anchor_contract": {
        "source": HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE,
        "sha256": "1aa86e7cd8fe4f6c6c808eee166ff0ed30f7e228e707941efde87323b9ae057a",
        "document_payload_sha256": (
            "b38abd80403536c7e6db2ec9b8a8920dc06e9f740ed9c065941e483a0b5a30e2"
        ),
        "byte_count": 32_763,
    },
    "phase2_readme_successor": {
        "source": "infra/phase2/README.md",
        "sha256": TYPED_PHASE2_SOURCE_SUCCESSORS[
            "infra/phase2/README.md"
        ]["successor_sha256"],
        "byte_count": TYPED_PHASE2_SOURCE_SUCCESSORS[
            "infra/phase2/README.md"
        ]["successor_byte_count"],
    },
    "phase2_verify_static_successor": {
        "source": "infra/phase2/verify-static.sh",
        "sha256": TYPED_PHASE2_SOURCE_SUCCESSORS[
            "infra/phase2/verify-static.sh"
        ]["successor_sha256"],
        "byte_count": TYPED_PHASE2_SOURCE_SUCCESSORS[
            "infra/phase2/verify-static.sh"
        ]["successor_byte_count"],
    },
    "phase2_acceptance_successor": {
        "source": "tools/phase2_wormhole_successor_acceptance.py",
        "sha256": TYPED_PHASE2_SOURCE_SUCCESSORS[
            "tools/phase2_wormhole_successor_acceptance.py"
        ]["successor_sha256"],
        "byte_count": TYPED_PHASE2_SOURCE_SUCCESSORS[
            "tools/phase2_wormhole_successor_acceptance.py"
        ]["successor_byte_count"],
    },
    "phase2_acceptance_test_successor": {
        "source": "tools/test_phase2_wormhole_successor_acceptance.py",
        "sha256": TYPED_PHASE2_SOURCE_SUCCESSORS[
            "tools/test_phase2_wormhole_successor_acceptance.py"
        ]["successor_sha256"],
        "byte_count": TYPED_PHASE2_SOURCE_SUCCESSORS[
            "tools/test_phase2_wormhole_successor_acceptance.py"
        ]["successor_byte_count"],
    },
    "typed_anchor_python_bridge_successor": {
        "source": TYPED_ANCHOR_PYTHON_BRIDGE_RELATIVE,
        "sha256": PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS[
            TYPED_ANCHOR_PYTHON_BRIDGE_RELATIVE
        ]["successor_sha256"],
        "byte_count": PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS[
            TYPED_ANCHOR_PYTHON_BRIDGE_RELATIVE
        ]["successor_byte_count"],
    },
    "typed_anchor_java_bridge_successor": {
        "source": TYPED_ANCHOR_JAVA_BRIDGE_RELATIVE,
        "sha256": PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS[
            TYPED_ANCHOR_JAVA_BRIDGE_RELATIVE
        ]["successor_sha256"],
        "byte_count": PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS[
            TYPED_ANCHOR_JAVA_BRIDGE_RELATIVE
        ]["successor_byte_count"],
    },
    "typed_anchor_python_test_successor": {
        "source": TYPED_ANCHOR_PYTHON_TEST_RELATIVE,
        "sha256": PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS[
            TYPED_ANCHOR_PYTHON_TEST_RELATIVE
        ]["successor_sha256"],
        "byte_count": PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS[
            TYPED_ANCHOR_PYTHON_TEST_RELATIVE
        ]["successor_byte_count"],
    },
    "typed_anchor_java_parity_successor": {
        "source": TYPED_ANCHOR_JAVA_PARITY_RELATIVE,
        "sha256": PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS[
            TYPED_ANCHOR_JAVA_PARITY_RELATIVE
        ]["successor_sha256"],
        "byte_count": PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS[
            TYPED_ANCHOR_JAVA_PARITY_RELATIVE
        ]["successor_byte_count"],
    },
    "phase4c_progress_successor": {
        "source": "docs/refactor/05-progress.md",
        "sha256": PHASE6_DOCUMENT_SOURCE_SUCCESSORS[
            "docs/refactor/05-progress.md"
        ]["successor_sha256"],
        "byte_count": PHASE6_DOCUMENT_SOURCE_SUCCESSORS[
            "docs/refactor/05-progress.md"
        ]["successor_byte_count"],
    },
    "phase4c_readme_successor": {
        "source": "docs/refactor/phase4c/README.md",
        "sha256": PHASE6_DOCUMENT_SOURCE_SUCCESSORS[
            "docs/refactor/phase4c/README.md"
        ]["successor_sha256"],
        "byte_count": PHASE6_DOCUMENT_SOURCE_SUCCESSORS[
            "docs/refactor/phase4c/README.md"
        ]["successor_byte_count"],
    },
    "phase6_bootstrap_python_test_successor": {
        "source": PHASE6_BOOTSTRAP_PYTHON_TEST_RELATIVE,
        "sha256": PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS[
            PHASE6_BOOTSTRAP_PYTHON_TEST_RELATIVE
        ]["successor_sha256"],
        "byte_count": PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS[
            PHASE6_BOOTSTRAP_PYTHON_TEST_RELATIVE
        ]["successor_byte_count"],
    },
    "phase6_bootstrap_java_parity_successor": {
        "source": PHASE6_BOOTSTRAP_JAVA_PARITY_RELATIVE,
        "sha256": PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS[
            PHASE6_BOOTSTRAP_JAVA_PARITY_RELATIVE
        ]["successor_sha256"],
        "byte_count": PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS[
            PHASE6_BOOTSTRAP_JAVA_PARITY_RELATIVE
        ]["successor_byte_count"],
    },
    "semantic_http_implementation_builder_successor": {
        **_successor_source_descriptor(
            "tools/build_phase4c_personal_bank_user_counts_"
            "http_implementation_contract.py"
        ),
    },
    "semantic_http_implementation_python_successor": {
        **_successor_source_descriptor(
            "tools/phase4c_http_implementation_successor_acceptance.py"
        ),
    },
    "semantic_target_execution_builder_successor": {
        **_successor_source_descriptor(
            "tools/build_phase4c_personal_bank_user_counts_"
            "http_target_execution_contract.py"
        ),
    },
    "semantic_target_execution_python_successor": {
        **_successor_source_descriptor(
            "tools/phase4c_http_target_execution_successor_acceptance.py"
        ),
    },
    "semantic_target_execution_anchor_builder_successor": {
        **_successor_source_descriptor(
            "tools/build_phase4c_personal_bank_user_counts_"
            "http_target_execution_anchor_contract.py"
        ),
    },
    "semantic_target_execution_anchor_python_successor": {
        **_successor_source_descriptor(
            "tools/phase4c_http_target_execution_anchor_"
            "successor_acceptance.py"
        ),
    },
    "semantic_composition_python_test_successor": {
        **_successor_source_descriptor(
            "tools/test_phase4c_personal_bank_user_counts_"
            "composition_contract.py"
        ),
    },
    "semantic_read_python_test_successor": {
        **_successor_source_descriptor(
            "tools/test_phase4c_personal_bank_user_counts_read_contract.py"
        ),
    },
    "semantic_module_contract_java_successor": {
        **_successor_source_descriptor(MODULE_CONTRACT_PARITY_RELATIVE),
    },
    "semantic_read_successor_bridge_successor": {
        **_successor_source_descriptor(READ_SUCCESSOR_BRIDGE_RELATIVE),
    },
    "semantic_java_read_successor_bridge_successor": {
        **_successor_source_descriptor(JAVA_READ_SUCCESSOR_BRIDGE_RELATIVE),
    },
    "semantic_all_shares_entry_python_test_successor": {
        **_successor_source_descriptor(ALL_SHARES_ENTRY_TEST_RELATIVE),
    },
    "semantic_all_shares_read_python_test_successor": {
        **_successor_source_descriptor(ALL_SHARES_READ_TEST_RELATIVE),
    },
    "semantic_share_list_entry_python_test_successor": {
        **_successor_source_descriptor(SHARE_LIST_ENTRY_TEST_RELATIVE),
    },
    "semantic_share_list_read_python_test_successor": {
        **_successor_source_descriptor(SHARE_LIST_READ_TEST_RELATIVE),
    },
    "semantic_user_counts_entry_python_test_successor": {
        **_successor_source_descriptor(USER_COUNTS_ENTRY_TEST_RELATIVE),
    },
    "semantic_usage_stats_entry_python_test_successor": {
        **_successor_source_descriptor(USAGE_STATS_ENTRY_TEST_RELATIVE),
    },
    "semantic_usage_stats_read_python_test_successor": {
        **_successor_source_descriptor(USAGE_STATS_READ_TEST_RELATIVE),
    },
    "semantic_http_implementation_java_successor": {
        **_successor_source_descriptor(
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpImplementationSuccessorAcceptance.java"
        ),
    },
    "semantic_target_execution_java_successor": {
        **_successor_source_descriptor(
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
        ),
    },
    "semantic_target_execution_python_test_successor": {
        **_successor_source_descriptor(
            "tools/test_phase4c_personal_bank_user_counts_"
            "http_target_execution_contract.py"
        ),
    },
    "semantic_http_entry_python_test_successor": {
        **_successor_source_descriptor(
            "tools/test_phase4c_personal_bank_user_counts_"
            "http_entry_contract.py"
        ),
    },
    "semantic_post_push_builder_successor": {
        **_successor_source_descriptor(
            "tools/build_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_contract.py"
        ),
    },
    "semantic_post_push_python_test_successor": {
        **_successor_source_descriptor(
            "tools/test_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_contract.py"
        ),
    },
    "semantic_post_push_anchor_python_test_successor": {
        **_successor_source_descriptor(
            "tools/test_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_anchor_contract.py"
        ),
    },
    "semantic_http_implementation_python_test_successor": {
        **_successor_source_descriptor(
            "tools/test_phase4c_personal_bank_user_counts_http_"
            "implementation_contract.py"
        ),
    },
    "post_push_python_bridge_successor": {
        **_successor_source_descriptor(
            "tools/phase4c_http_target_execution_post_push_"
            "successor_acceptance.py"
        ),
    },
    "post_push_java_bridge_successor": {
        **_successor_source_descriptor(
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java"
        ),
    },
    "typed_normalization_python_bridge_successor": {
        **_successor_source_descriptor(
            "tools/phase4c_http_typed_normalization_"
            "successor_acceptance.py"
        ),
    },
    "typed_normalization_java_bridge_successor": {
        **_successor_source_descriptor(
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpTypedNormalizationSuccessorAcceptance.java"
        ),
    },
    "old_worm_predecessor": {
        "source": (
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-http-implementation-worm-evidence.json"
        ),
        "sha256": "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39",
        "byte_count": 1_442,
    },
    "tag_global_preflight_worm_successor": {
        "source": (
            "docs/refactor/phase4c/"
            "personal-bank-tag-global-preflight-worm-evidence.json"
        ),
        "sha256": "283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72",
        "byte_count": 1_442,
    },
    "tag_global_preflight_hardening_worm_successor": {
        "source": (
            "docs/refactor/phase4c/"
            "personal-bank-tag-global-preflight-hardening-worm-evidence.json"
        ),
        "sha256": "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344",
        "byte_count": 1_442,
    },
    # The eight Java/SQL descriptors below bind the settled evidence bytes.
    "preflight_parser": {
        "source": (
            "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
            "LegacyPersonalBankTagPreflightParser.java"
        ),
        "sha256": "c3311e28f33c8bc447fd72191af696ceca333162747e94eb91681dd75c0f5bf3",
        "byte_count": 18_525,
    },
    "preflight_report": {
        "source": (
            "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
            "LegacyPersonalBankTagPreflightReport.java"
        ),
        "sha256": "d7d988f5bfe7c86e30a5410e8eac0032a24ad5c85011b6c03de159c97d3ff750",
        "byte_count": 12_567,
    },
    "global_preflight": {
        "source": (
            "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
            "LegacyPersonalBankTagGlobalPreflight.java"
        ),
        "sha256": "cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76",
        "byte_count": 35_830,
    },
    "preflight_parser_unit": {
        "source": (
            "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
            "LegacyPersonalBankTagPreflightParserTest.java"
        ),
        "sha256": "d811cf59f1a778760fc54ebc3a01f5e93be496e8bb9439e92020af576c9e0f8f",
        "byte_count": 10_279,
    },
    "global_preflight_unit": {
        "source": (
            "server/src/test/java/io/saksk/ti/learning/infrastructure/migration/"
            "LegacyPersonalBankTagGlobalPreflightTest.java"
        ),
        "sha256": "8fc30419dee8be99b8081f873d38921fdedb2beea42a7c1b4c8e2241e844ce3f",
        "byte_count": 34_570,
    },
    "global_preflight_pg_it": {
        "source": (
            "server/src/test/java/io/saksk/ti/integration/"
            "Phase4cLegacyPersonalBankTagGlobalPreflightIT.java"
        ),
        "sha256": "6cd525dd7153efb1641a8e629e21ba874b0582a11666a4b89877baa359f4717d",
        "byte_count": 28_063,
    },
    "global_preflight_schema": {
        "source": (
            "server/src/test/resources/db/phase4c/"
            "071-legacy-personal-bank-tag-global-preflight-schema.sql"
        ),
        "sha256": "aee1ec236cf119f5f5801f9cdb4856a5011373a81c8ac703b029365758bc9af6",
        "byte_count": 1_254,
    },
    "global_preflight_seed": {
        "source": (
            "server/src/test/resources/db/phase4c/"
            "072-legacy-personal-bank-tag-global-preflight-seed.sql"
        ),
        "sha256": "a70f125c4359b99568f8aa0db19879af0a2d5a0c7dfc064c077e48c3a8ea27a9",
        "byte_count": 8_940,
    },
}

SOURCE_SUCCESSOR_SOURCE_NAMES = {
    "infra/phase2/README.md": "phase2_readme_successor",
    "infra/phase2/verify-static.sh": "phase2_verify_static_successor",
    "tools/phase2_wormhole_successor_acceptance.py": (
        "phase2_acceptance_successor"
    ),
    "tools/test_phase2_wormhole_successor_acceptance.py": (
        "phase2_acceptance_test_successor"
    ),
    TYPED_ANCHOR_PYTHON_BRIDGE_RELATIVE: (
        "typed_anchor_python_bridge_successor"
    ),
    TYPED_ANCHOR_JAVA_BRIDGE_RELATIVE: "typed_anchor_java_bridge_successor",
    TYPED_ANCHOR_PYTHON_TEST_RELATIVE: "typed_anchor_python_test_successor",
    TYPED_ANCHOR_JAVA_PARITY_RELATIVE: "typed_anchor_java_parity_successor",
    "docs/refactor/05-progress.md": "phase4c_progress_successor",
    "docs/refactor/phase4c/README.md": "phase4c_readme_successor",
    PHASE6_BOOTSTRAP_PYTHON_TEST_RELATIVE: (
        "phase6_bootstrap_python_test_successor"
    ),
    PHASE6_BOOTSTRAP_JAVA_PARITY_RELATIVE: (
        "phase6_bootstrap_java_parity_successor"
    ),
    "tools/build_phase4c_personal_bank_user_counts_http_implementation_contract.py": (
        "semantic_http_implementation_builder_successor"
    ),
    "tools/phase4c_http_implementation_successor_acceptance.py": (
        "semantic_http_implementation_python_successor"
    ),
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py": (
        "semantic_target_execution_builder_successor"
    ),
    "tools/phase4c_http_target_execution_successor_acceptance.py": (
        "semantic_target_execution_python_successor"
    ),
    "tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py": (
        "semantic_target_execution_anchor_builder_successor"
    ),
    "tools/phase4c_http_target_execution_anchor_successor_acceptance.py": (
        "semantic_target_execution_anchor_python_successor"
    ),
    "tools/test_phase4c_personal_bank_user_counts_composition_contract.py": (
        "semantic_composition_python_test_successor"
    ),
    "tools/test_phase4c_personal_bank_user_counts_read_contract.py": (
        "semantic_read_python_test_successor"
    ),
    MODULE_CONTRACT_PARITY_RELATIVE: (
        "semantic_module_contract_java_successor"
    ),
    READ_SUCCESSOR_BRIDGE_RELATIVE: (
        "semantic_read_successor_bridge_successor"
    ),
    JAVA_READ_SUCCESSOR_BRIDGE_RELATIVE: (
        "semantic_java_read_successor_bridge_successor"
    ),
    ALL_SHARES_ENTRY_TEST_RELATIVE: (
        "semantic_all_shares_entry_python_test_successor"
    ),
    ALL_SHARES_READ_TEST_RELATIVE: (
        "semantic_all_shares_read_python_test_successor"
    ),
    SHARE_LIST_ENTRY_TEST_RELATIVE: (
        "semantic_share_list_entry_python_test_successor"
    ),
    SHARE_LIST_READ_TEST_RELATIVE: (
        "semantic_share_list_read_python_test_successor"
    ),
    USER_COUNTS_ENTRY_TEST_RELATIVE: (
        "semantic_user_counts_entry_python_test_successor"
    ),
    USAGE_STATS_ENTRY_TEST_RELATIVE: (
        "semantic_usage_stats_entry_python_test_successor"
    ),
    USAGE_STATS_READ_TEST_RELATIVE: (
        "semantic_usage_stats_read_python_test_successor"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpImplementationSuccessorAcceptance.java"
    ): "semantic_http_implementation_java_successor",
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionSuccessorAcceptance.java"
    ): "semantic_target_execution_java_successor",
    "tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py": (
        "semantic_target_execution_python_test_successor"
    ),
    "tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py": (
        "semantic_http_entry_python_test_successor"
    ),
    (
        "tools/build_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py"
    ): "semantic_post_push_builder_successor",
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_contract.py"
    ): "semantic_post_push_python_test_successor",
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "target_execution_post_push_anchor_contract.py"
    ): "semantic_post_push_anchor_python_test_successor",
    (
        "tools/test_phase4c_personal_bank_user_counts_http_"
        "implementation_contract.py"
    ): "semantic_http_implementation_python_test_successor",
    "tools/phase4c_http_target_execution_post_push_successor_acceptance.py": (
        "post_push_python_bridge_successor"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java"
    ): "post_push_java_bridge_successor",
    "tools/phase4c_http_typed_normalization_successor_acceptance.py": (
        "typed_normalization_python_bridge_successor"
    ),
    (
        "server/src/test/java/io/saksk/ti/architecture/"
        "Phase4cHttpTypedNormalizationSuccessorAcceptance.java"
    ): "typed_normalization_java_bridge_successor",
}

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    EXPLANATION_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightContractParityTest.java",
    "tools/build_phase4c_tag_migration_global_preflight_contract.py",
    "tools/phase4c_tag_migration_global_preflight_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_global_preflight_contract.py",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase6WebFoundationSourceSuccessorAnchorContractParityTest.java",
    "tools/phase6_web_foundation_source_successor_anchor_acceptance.py",
    "tools/test_phase6_web_foundation_source_successor_anchor_contract.py",
)

HISTORICAL_ROW_OUTCOMES = (
    "MIGRATED",
    "EMPTY_NOOP",
    "TARGET_ALREADY_PRESENT",
    "TARGET_CONFLICT",
    "INVALID_KEY",
    "INVALID_DATA",
    "BANK_MISSING",
    "ORPHAN_QUESTION",
    "SOURCE_DISAPPEARED",
    "FAILED_ROLLED_BACK",
    "ROLLBACK_FAILED",
    "COMMIT_OUTCOME_UNKNOWN",
)

HISTORICAL_REPORTING_GROUPS = {
    "eligible": ["MIGRATED", "EMPTY_NOOP", "TARGET_ALREADY_PRESENT"],
    "conflict": ["TARGET_CONFLICT"],
    "invalid": ["INVALID_KEY", "INVALID_DATA"],
    "unresolved": ["BANK_MISSING", "ORPHAN_QUESTION", "SOURCE_DISAPPEARED"],
    "transaction_failed": [
        "FAILED_ROLLED_BACK",
        "ROLLBACK_FAILED",
        "COMMIT_OUTCOME_UNKNOWN",
    ],
}

PREFLIGHT_DISPOSITIONS = (
    "MIGRATABLE",
    "EMPTY_NOOP",
    "TARGET_ALREADY_PRESENT",
    "TARGET_CONFLICT",
    "NORMALIZED_BANK_COLLISION",
    "TARGET_INVALID",
    "INVALID_KEY",
    "INVALID_DATA",
    "BANK_MISSING",
    "ORPHAN_QUESTION",
    "MEMBERSHIP_UNAVAILABLE",
)

PREFLIGHT_REPORTING_GROUPS = {
    "ELIGIBLE": ["MIGRATABLE", "EMPTY_NOOP", "TARGET_ALREADY_PRESENT"],
    "CONFLICT": ["TARGET_CONFLICT", "NORMALIZED_BANK_COLLISION", "TARGET_INVALID"],
    "INVALID": ["INVALID_KEY", "INVALID_DATA"],
    "UNRESOLVED": ["BANK_MISSING", "ORPHAN_QUESTION", "MEMBERSHIP_UNAVAILABLE"],
    "GLOBAL_FAILURE": [],
}

MIXED_FIXTURE_REPORTING_GROUP_COUNTS = {
    "ELIGIBLE": 4,
    "CONFLICT": 5,
    "INVALID": 4,
    "UNRESOLVED": 3,
    "GLOBAL_FAILURE": 0,
}

PREFLIGHT_STATUSES = ("COMPLETED", "LOCK_BUSY", "FAILED")

GLOBAL_FAILURE_CODES = (
    "CONNECTION_ACQUISITION_FAILED",
    "CONNECTION_SETUP_FAILED",
    "ADVISORY_LOCK_ACQUISITION_FAILED",
    "CONNECTION_METADATA_READ_FAILED",
    "TRANSACTION_SETUP_FAILED",
    "SOURCE_SCAN_FAILED",
    "CLASSIFICATION_READ_FAILED",
    "READ_ONLY_COMMIT_FAILED",
    "READ_ONLY_ROLLBACK_FAILED",
    "ADVISORY_UNLOCK_REJECTED",
    "ADVISORY_UNLOCK_FAILED",
    "CONNECTION_CLOSE_FAILED",
)

APPLY_PREREQUISITE_BLOCKERS = (
    "PREFLIGHT_ONLY_NO_APPLY_OPERATOR",
    "WRITE_FREEZE_OR_VERSION_RECHECK_NOT_PROVEN",
    "DURABLE_MIGRATION_MARKER_NOT_IMPLEMENTED",
)

MIGRATION_APPROVED_DIFFERENCE_IDS = tuple(
    f"P4C-LEARNING-{number:03d}" for number in range(1, 7)
)
CURRENT_APPROVED_DIFFERENCE_IDS = tuple(
    f"P4C-LEARNING-{number:03d}" for number in range(1, 13)
)

ROUTE_STATE = {
    "total_operation_count": 611,
    "migrated_operation_count": 13,
    "pending_operation_count": 598,
    "production_cutover_operation_count": 0,
}

NEWLY_CLOSED_GATES = ("migration_global_preflight_evidence_closed",)
NEW_MAIN_SOURCE_NAMES = ("preflight_parser", "preflight_report", "global_preflight")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def payload_sha256(document: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "document_payload_sha256"
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def serialized(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"tag preflight path escapes root: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"tag preflight path contains symlink: {relative}")
    resolved = (resolved_root / candidate).resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise AssertionError(f"tag preflight path escapes root: {relative}") from error
    if not resolved.is_file():
        raise AssertionError(f"tag preflight path is not a regular file: {relative}")
    return resolved


def validated_source(root: Path, source_name: str) -> bytes:
    if source_name not in SOURCES:
        raise AssertionError(f"tag preflight unknown or self-authority source: {source_name}")
    descriptor = SOURCES[source_name]
    relative = descriptor["source"]
    if relative in CONTROL_SOURCES:
        raise AssertionError(f"tag preflight self-authority source: {relative}")
    payload = fixed_regular_file(root, relative).read_bytes()
    if (
        descriptor["sha256"] == "PENDING_SETTLED_SOURCE_SHA256"
        or descriptor["byte_count"] < 0
    ):
        raise AssertionError(f"tag preflight source descriptor is not settled: {relative}")
    if (
        sha256_bytes(payload) != descriptor["sha256"]
        or len(payload) != descriptor["byte_count"]
    ):
        raise AssertionError(f"tag preflight fixed bytes drifted: {relative}")
    return payload


def _validated_json(root: Path, source_name: str) -> dict[str, Any]:
    try:
        document = json.loads(validated_source(root, source_name))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"tag preflight JSON source is unreadable: {source_name}") from error
    if not isinstance(document, dict):
        raise AssertionError(f"tag preflight JSON source is not an object: {source_name}")
    descriptor = SOURCES[source_name]
    expected_payload = descriptor.get("document_payload_sha256")
    if expected_payload is not None and (
        document.get("document_payload_sha256") != expected_payload
        or payload_sha256(document) != expected_payload
    ):
        raise AssertionError(f"tag preflight JSON payload drifted: {source_name}")
    return document


def _load_phase2_worm_validator() -> Any:
    """Load only the physical-chain validator; never the acceptance aggregator."""
    try:
        return importlib.import_module(PHASE2_WORM_VALIDATOR_MODULE)
    except ModuleNotFoundError as error:
        if error.name not in {"tools", PHASE2_WORM_VALIDATOR_MODULE}:
            raise
    return importlib.import_module(PHASE2_WORM_VALIDATOR_DIRECT_MODULE)


def _validate_fixed_worm_chain(root: Path) -> None:
    phase2_worm = _load_phase2_worm_validator()
    validate_fixed_chain = getattr(phase2_worm, "validate_fixed_chain", None)
    fixed_chain = getattr(phase2_worm, "FIXED_EVIDENCE_CHAIN", ())
    if not callable(validate_fixed_chain) or len(fixed_chain) != 7:
        raise AssertionError("tag preflight fixed WORM chain validator drifted")

    initial = fixed_chain[-2]
    expected_initial = (
        TAG_GLOBAL_PREFLIGHT_WORM_LABEL,
        SOURCES["tag_global_preflight_worm_successor"]["source"],
        SOURCES["tag_global_preflight_worm_successor"]["sha256"],
        TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256,
        TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
        TAG_GLOBAL_PREFLIGHT_WORM_PREDECESSOR_SHA256,
    )
    actual_initial = (
        getattr(initial, "label", None),
        getattr(initial, "relative_path", None),
        getattr(initial, "sha256", None),
        getattr(initial, "build_context_sha256", None),
        getattr(initial, "dockerfile_sha256", None),
        getattr(initial, "predecessor_sha256", None),
    )
    if actual_initial != expected_initial:
        raise AssertionError("tag preflight initial WORM chain node drifted")

    tip = validate_fixed_chain(
        root,
        fixed_regular_file(root, PHASE2_DRIFT_MANIFEST_RELATIVE),
        TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
        TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256,
    )
    expected_tip = (
        TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_LABEL,
        SOURCES["tag_global_preflight_hardening_worm_successor"]["source"],
        SOURCES["tag_global_preflight_hardening_worm_successor"]["sha256"],
        TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256,
        TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
        TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_PREDECESSOR_SHA256,
    )
    actual_tip = (
        getattr(tip, "label", None),
        getattr(tip, "relative_path", None),
        getattr(tip, "sha256", None),
        getattr(tip, "build_context_sha256", None),
        getattr(tip, "dockerfile_sha256", None),
        getattr(tip, "predecessor_sha256", None),
    )
    if actual_tip != expected_tip:
        raise AssertionError("tag preflight fixed WORM chain tip drifted")


def _validate_semantic_authority(root: Path) -> None:
    composition = _validated_json(root, "semantic_composition")
    migration = composition.get("explicit_bank_tag_migration")
    authorization = composition.get("authorization")
    approved = composition.get("approved_differences")
    if (
        composition.get("contract_id")
        != "ti.phase4c.personal-bank-user-counts-composition-contract"
        or not isinstance(migration, dict)
        or migration.get("owner") != "learning"
        or migration.get("execution")
        != "operator-only one-shot job; startup and HTTP invocation forbidden"
        or migration.get("default_mode") != "dry-run"
        or migration.get("row_outcomes") != list(HISTORICAL_ROW_OUTCOMES)
        or migration.get("reporting_groups") != HISTORICAL_REPORTING_GROUPS
        or not isinstance(authorization, dict)
        or authorization.get("migration_global_preflight_evidence_closed") is not False
        or authorization.get("operator_migration_implementation") is not False
        or authorization.get("production_schema_or_index") is not False
        or authorization.get("real_data_migration_execution") is not False
        or authorization.get("production_cutover") is not False
        or not isinstance(approved, dict)
        or approved.get("ids") != list(MIGRATION_APPROVED_DIFFERENCE_IDS)
    ):
        raise AssertionError("tag preflight semantic composition authority drifted")

    route = _validated_json(root, "current_route_promotion")
    if (
        route.get("contract_id")
        != "ti.phase4c.personal-bank-user-counts-route-promotion-contract"
        or route.get("route_state") != ROUTE_STATE
        or route.get("authorization", {}).get("operator_migration_implementation") is not False
        or route.get("authorization", {}).get("production_schema_or_index") is not False
        or route.get("authorization", {}).get("real_data_migration_execution") is not False
        or route.get("authorization", {}).get("production_cutover") is not False
    ):
        raise AssertionError("tag preflight current route authority drifted")

    approved_bytes = validated_source(root, "approved_differences")
    try:
        approved_text = approved_bytes.decode("utf-8")
    except UnicodeError as error:
        raise AssertionError("tag preflight approved differences are unreadable") from error
    for difference_id in CURRENT_APPROVED_DIFFERENCE_IDS:
        if approved_text.count(difference_id) < 1:
            raise AssertionError(
                f"tag preflight approved difference is absent: {difference_id}"
            )

    ownership = _validated_json(root, "effective_data_ownership")
    overrides = ownership.get("effective", {}).get("owner_overrides")
    if overrides != [{
        "resource_kind": "db_kv_namespace",
        "resource_name": "bank_<bank_id>_tags",
        "base_owner": "personalbank",
        "owner": "learning",
        "production_cutover": False,
    }]:
        raise AssertionError("tag preflight effective ownership authority drifted")
    validated_source(root, "data_ownership_delta")

    old_worm = _validated_json(root, "old_worm_predecessor")
    if (
        old_worm.get("java", {}).get("buildContextSha256")
        != "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
        or old_worm.get("java", {}).get("dockerfileSha256")
        != "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
    ):
        raise AssertionError("tag preflight old WORM predecessor drifted")

    initial_worm = _validated_json(root, "tag_global_preflight_worm_successor")
    if (
        initial_worm.get("java", {}).get("buildContextSha256")
        != TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256
        or initial_worm.get("java", {}).get("dockerfileSha256")
        != TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256
        or initial_worm.get("java", {}).get("hibernateDdlAuto") != "validate"
        or initial_worm.get("java", {}).get("startupPassed") is not True
        or initial_worm.get("java", {}).get("readinessPassed") is not True
        or initial_worm.get("productionDatabaseVersion") != "unknown"
        or initial_worm.get("flywayBaselineCreated") is not False
    ):
        raise AssertionError("tag preflight initial WORM successor drifted")

    hardening_worm = _validated_json(
        root, "tag_global_preflight_hardening_worm_successor"
    )
    if (
        hardening_worm.get("java", {}).get("buildContextSha256")
        != TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256
        or hardening_worm.get("java", {}).get("dockerfileSha256")
        != TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256
        or hardening_worm.get("java", {}).get("hibernateDdlAuto") != "validate"
        or hardening_worm.get("java", {}).get("startupPassed") is not True
        or hardening_worm.get("java", {}).get("readinessPassed") is not True
        or hardening_worm.get("productionDatabaseVersion") != "unknown"
        or hardening_worm.get("flywayBaselineCreated") is not False
    ):
        raise AssertionError("tag preflight hardening WORM successor drifted")
    _validate_fixed_worm_chain(root)


def _validate_evidence_sources(root: Path) -> None:
    for source_name in (
        "historical_row_primitive",
        "historical_row_primitive_unit",
        "historical_row_primitive_pg_it",
        "historical_row_primitive_schema",
        "historical_row_primitive_seed",
        "membership_api",
        "membership_view",
        "preflight_parser",
        "preflight_report",
        "global_preflight",
        "preflight_parser_unit",
        "global_preflight_unit",
        "global_preflight_pg_it",
        "global_preflight_schema",
        "global_preflight_seed",
        "typed_anchor_contract",
        "phase6_source_successor_anchor_contract",
        "historical_target_execution_contract",
        "historical_read_contract",
        "historical_http_implementation_contract",
        "historical_target_execution_post_push_contract",
        "historical_target_execution_post_push_anchor_contract",
        *SOURCE_SUCCESSOR_SOURCE_NAMES.values(),
    ):
        validated_source(root, source_name)

    global_source = validated_source(root, "global_preflight").decode("utf-8")
    parser_source = validated_source(root, "preflight_parser").decode("utf-8")
    global_unit_source = validated_source(root, "global_preflight_unit").decode("utf-8")
    parser_unit_source = validated_source(root, "preflight_parser_unit").decode("utf-8")
    report_source = validated_source(root, "preflight_report").decode("utf-8")
    pg_it_source = validated_source(root, "global_preflight_pg_it").decode("utf-8")
    required_tokens = {
        "global_preflight": (
            "LegacyPersonalBankTagGlobalPreflight",
            "pg_try_advisory_lock",
            "pg_advisory_unlock",
            "TRANSACTION_SERIALIZABLE",
            "setReadOnly(true)",
            "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE",
            "CONNECTION_ACQUISITION_FAILED",
            "CONNECTION_CLOSE_FAILED",
            "statementSurface",
            "MAX_RESERVED_SOURCE_ROWS = 100_000",
            "MAX_RESERVED_SOURCE_UTF8_BYTES = 256L * 1024L * 1024L",
            "AS bounded_data",
            "AS data_utf8_bytes",
            "reserved source row limit exceeded",
            "reserved source byte limit exceeded",
        ),
        "preflight_parser": (
            "LegacyPersonalBankTagPreflightParser",
            "bank_",
            "question_tags",
            "MAX_PAYLOAD_UTF8_BYTES = 1_048_576",
            "PAYLOAD_LIMIT_EXCEEDED",
            "TAG_NOT_LOSSLESS",
            "isLosslessPostgresText",
        ),
        "global_preflight_unit": (
            "rejectsOversizedPayloadWithoutMaterializingRawDataOrReadingTarget",
            'never()).getString("data")',
            "MAX_RESERVED_SOURCE_UTF8_BYTES",
        ),
        "preflight_parser_unit": (
            "preservesCaseAndUnicodeNormalizationFormsAsDistinctLegacyTags",
            "rejectsTextPostgresCannotRepresentWithoutUtf8Replacement",
            "rejectsPayloadsLargerThanOneMebibyteBeforeJsonParsing",
        ),
        "preflight_report": (
            "LegacyPersonalBankTagPreflightReport",
            '"DRY_RUN"',
            "MIGRATABLE",
            "MEMBERSHIP_UNAVAILABLE",
            "PREFLIGHT_ONLY_NO_APPLY_OPERATOR",
            "DURABLE_MIGRATION_MARKER_NOT_IMPLEMENTED",
            "mutationStatementCount",
            "ddlStatementCount",
            "isDataEligible",
            "isApplyEligible",
        ),
        "global_preflight_pg_it": (
            "globalReadOnlyPreflightEvidenceHoldsOnPostgres18",
            "globalReadOnlyPreflightEvidenceHoldsOnPostgres16",
        ),
    }
    for token in required_tokens["global_preflight"]:
        if token not in global_source:
            raise AssertionError(f"tag preflight global evidence token absent: {token}")
    for token in required_tokens["preflight_parser"]:
        if token not in parser_source:
            raise AssertionError(f"tag preflight parser evidence token absent: {token}")
    for token in required_tokens["global_preflight_unit"]:
        if token not in global_unit_source:
            raise AssertionError(f"tag preflight global unit token absent: {token}")
    for token in required_tokens["preflight_parser_unit"]:
        if token not in parser_unit_source:
            raise AssertionError(f"tag preflight parser unit token absent: {token}")
    for token in required_tokens["preflight_report"]:
        if token not in report_source:
            raise AssertionError(f"tag preflight report evidence token absent: {token}")
    for token in required_tokens["global_preflight_pg_it"]:
        if token not in pg_it_source:
            raise AssertionError(f"tag preflight PostgreSQL evidence token absent: {token}")


def _validate_source_successor_authority(root: Path) -> None:
    successor_groups = (
        TYPED_PHASE2_SOURCE_SUCCESSORS,
        PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS,
        PHASE6_DOCUMENT_SOURCE_SUCCESSORS,
        PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS,
        SEMANTIC_CONSUMER_SOURCE_SUCCESSORS,
        POST_PUSH_BRIDGE_SOURCE_SUCCESSORS,
        TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS,
    )
    if (
        set(SOURCE_SUCCESSORS) != set(SOURCE_SUCCESSOR_SOURCE_NAMES)
        or any(
            set(left).intersection(right)
            for index, left in enumerate(successor_groups)
            for right in successor_groups[index + 1:]
        )
    ):
        raise AssertionError("tag preflight source-successor allowlist drifted")

    typed_anchor = _validated_json(root, "typed_anchor_contract")
    typed_overrides = typed_anchor.get(
        "historical_source_successors", {}
    ).get("overrides")
    if not isinstance(typed_overrides, dict):
        raise AssertionError("tag preflight typed-anchor successor authority is absent")
    for relative, expected in TYPED_PHASE2_SOURCE_SUCCESSORS.items():
        historical = typed_overrides.get(relative)
        if (
            not isinstance(historical, dict)
            or historical.get("source") != relative
            or historical.get("successor_sha256") != expected["accepted_sha256"]
            or historical.get("successor_byte_count")
            != expected["accepted_byte_count"]
        ):
            raise AssertionError(
                f"tag preflight typed-anchor accepted source drifted: {relative}"
            )
    for relative, expected in (
        TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS.items()
    ):
        authority = typed_overrides.get(relative)
        pointer = relative.replace("/", "~1")
        if (
            not isinstance(authority, dict)
            or authority.get("source") != relative
            or authority.get("successor_sha256")
            != expected["accepted_sha256"]
            or authority.get("successor_byte_count")
            != expected["accepted_byte_count"]
            or expected["accepted_authority"] != TYPED_ANCHOR_CONTRACT_RELATIVE
            or expected["accepted_sha256_authority"]
            != (
                f"{TYPED_ANCHOR_CONTRACT_RELATIVE}"
                f"#/historical_source_successors/overrides/{pointer}/"
                "successor_sha256"
            )
            or expected["accepted_byte_count_authority"]
            != (
                f"{TYPED_ANCHOR_CONTRACT_RELATIVE}"
                f"#/historical_source_successors/overrides/{pointer}/"
                "successor_byte_count"
            )
        ):
            raise AssertionError(
                "tag preflight typed-normalization bridge authority drifted: "
                f"{relative}"
            )

    phase6_anchor = _validated_json(
        root, "phase6_source_successor_anchor_contract"
    )
    phase6_artifacts = phase6_anchor.get(
        "typed_anchor_bridge_source_anchor", {}
    ).get("artifacts")
    if not isinstance(phase6_artifacts, dict):
        raise AssertionError("tag preflight Phase6 bridge authority is absent")
    for relative, expected in PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS.items():
        historical = phase6_artifacts.get(relative)
        if (
            not isinstance(historical, dict)
            or historical.get("ti_java_relative_path") != relative
            or historical.get("sha256") != expected["accepted_sha256"]
            or historical.get("byte_count") != expected["accepted_byte_count"]
        ):
            raise AssertionError(
                f"tag preflight Phase6 accepted bridge drifted: {relative}"
            )

    phase6_successors = phase6_anchor.get("source_successors", {}).get(
        "overrides"
    )
    if not isinstance(phase6_successors, dict):
        raise AssertionError("tag preflight Phase6 successor authority is absent")
    for relative, expected in {
        **PHASE6_DOCUMENT_SOURCE_SUCCESSORS,
        **PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS,
    }.items():
        historical = phase6_successors.get(relative)
        if (
            not isinstance(historical, dict)
            or historical.get("source") != relative
            or historical.get("successor_sha256")
            != expected["accepted_sha256"]
            or historical.get("successor_byte_count")
            != expected["accepted_byte_count"]
        ):
            raise AssertionError(
                f"tag preflight Phase6 accepted successor drifted: {relative}"
            )

    implementation_builder_relative = (
        "tools/build_phase4c_personal_bank_user_counts_"
        "http_implementation_contract.py"
    )
    semantic_expected_paths = {
        implementation_builder_relative,
        SEMANTIC_HTTP_IMPLEMENTATION_OVERRIDE_PATH,
        *SEMANTIC_HTTP_IMPLEMENTATION_SOURCE_KEYS,
        *SEMANTIC_READ_CONSUMER_PATHS,
        *SEMANTIC_TARGET_EXECUTION_SOURCE_KEYS,
        *SEMANTIC_POST_PUSH_ANCHOR_PATHS,
        *SEMANTIC_POST_PUSH_CONTRACT_ARTIFACT_KEYS,
        SEMANTIC_POST_PUSH_ANCHOR_OVERRIDE_PATH,
        *SEMANTIC_TYPED_ANCHOR_OVERRIDE_PATHS,
    }
    if set(SEMANTIC_CONSUMER_SOURCE_SUCCESSORS) != semantic_expected_paths:
        raise AssertionError("tag preflight semantic-consumer allowlist drifted")

    implementation_contract = _validated_json(
        root, "historical_http_implementation_contract"
    )
    implementation_reference = implementation_contract.get(
        "source_contracts", {}
    ).get("contract_builder")
    implementation_transition = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[
        implementation_builder_relative
    ]
    if (
        not isinstance(implementation_reference, dict)
        or implementation_reference.get("source")
        != implementation_builder_relative
        or implementation_reference.get("sha256")
        != implementation_transition["accepted_sha256"]
        or implementation_transition["accepted_authority"]
        != HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE
        or implementation_transition["accepted_sha256_authority"]
        != (
            f"{HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE}"
            "#/source_contracts/contract_builder/sha256"
        )
        or implementation_transition["accepted_byte_count_authority"]
        != CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
    ):
        raise AssertionError(
            "tag preflight implementation-builder accepted authority drifted"
        )

    entry_transition = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[
        SEMANTIC_HTTP_IMPLEMENTATION_OVERRIDE_PATH
    ]
    entry_override = implementation_contract.get(
        "historical_successor_acceptance", {}
    ).get("http_entry_source_overrides", {}).get(
        SEMANTIC_HTTP_IMPLEMENTATION_OVERRIDE_PATH
    )
    if (
        not isinstance(entry_override, dict)
        or entry_override.get("source")
        != SEMANTIC_HTTP_IMPLEMENTATION_OVERRIDE_PATH
        or entry_override.get("successor_sha256")
        != entry_transition["accepted_sha256"]
        or entry_transition["accepted_authority"]
        != HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE
        or entry_transition["accepted_sha256_authority"]
        != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[
            SEMANTIC_HTTP_IMPLEMENTATION_OVERRIDE_PATH
        ]["accepted_sha256_authority"]
        or entry_transition["accepted_byte_count_authority"]
        != CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
    ):
        raise AssertionError(
            "tag preflight HTTP-entry test accepted authority drifted"
        )

    implementation_sources = implementation_contract.get("source_contracts")
    implementation_read_overrides = implementation_contract.get(
        "historical_successor_acceptance", {}
    ).get("read_terminal_source_overrides")
    if not isinstance(implementation_sources, dict) or not isinstance(
        implementation_read_overrides, dict
    ):
        raise AssertionError(
            "tag preflight HTTP-implementation source authority is absent"
        )
    for relative, source_key in SEMANTIC_HTTP_IMPLEMENTATION_SOURCE_KEYS.items():
        expected = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[relative]
        reference = implementation_sources.get(source_key)
        override = implementation_read_overrides.get(relative)
        if (
            not isinstance(reference, dict)
            or reference.get("source") != relative
            or reference.get("sha256") != expected["accepted_sha256"]
            or not isinstance(override, dict)
            or override.get("source") != relative
            or override.get("successor_sha256")
            != expected["accepted_sha256"]
            or expected["accepted_authority"]
            != HISTORICAL_HTTP_IMPLEMENTATION_CONTRACT_RELATIVE
            or expected["accepted_sha256_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_sha256_authority"
            ]
            or expected["accepted_byte_count_authority"]
            != CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
        ):
            raise AssertionError(
                "tag preflight HTTP-implementation accepted consumer "
                f"drifted: {relative}"
            )

    target_contract = _validated_json(
        root, "historical_target_execution_contract"
    )
    target_sources = target_contract.get("source_contracts")
    target_overrides = target_contract.get(
        "historical_successor_acceptance", {}
    ).get("anchored_source_overrides")
    if not isinstance(target_sources, dict) or not isinstance(
        target_overrides, dict
    ):
        raise AssertionError(
            "tag preflight target-execution semantic authority is absent"
        )
    for relative, source_key in SEMANTIC_TARGET_EXECUTION_SOURCE_KEYS.items():
        expected = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[relative]
        reference = target_sources.get(source_key)
        override = target_overrides.get(relative)
        if (
            not isinstance(reference, dict)
            or reference.get("source") != relative
            or reference.get("sha256") != expected["accepted_sha256"]
            or (
                relative in SEMANTIC_TARGET_EXECUTION_OVERRIDE_PATHS
                and (
                    not isinstance(override, dict)
                    or override.get("source") != relative
                    or override.get("successor_sha256")
                    != expected["accepted_sha256"]
                )
            )
            or (
                relative not in SEMANTIC_TARGET_EXECUTION_OVERRIDE_PATHS
                and override is not None
            )
            or expected["accepted_authority"]
            != HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE
            or expected["accepted_sha256_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_sha256_authority"
            ]
            or expected["accepted_byte_count_authority"]
            != CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
        ):
            raise AssertionError(
                f"tag preflight target accepted consumer drifted: {relative}"
            )

    read_reference = target_sources.get("phase4c_read_predecessor")
    read_payload = fixed_regular_file(
        root, HISTORICAL_READ_CONTRACT_RELATIVE
    ).read_bytes()
    read_contract = json.loads(read_payload)
    if (
        not isinstance(read_reference, dict)
        or read_reference.get("source") != HISTORICAL_READ_CONTRACT_RELATIVE
        or read_reference.get("sha256") != sha256_bytes(read_payload)
    ):
        raise AssertionError("tag preflight read-contract authority drifted")
    read_history = read_contract.get("historical_successor_acceptance", {})
    for relative in SEMANTIC_READ_CONSUMER_PATHS:
        expected = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[relative]
        source_group = (
            "java_sources"
            if relative == MODULE_CONTRACT_PARITY_RELATIVE
            else "python_sources"
        )
        authority = read_history.get(source_group, {}).get(relative)
        if (
            not isinstance(authority, dict)
            or authority.get("source") != relative
            or authority.get("successor_sha256")
            != expected["accepted_sha256"]
            or expected["accepted_authority"]
            != HISTORICAL_TARGET_EXECUTION_CONTRACT_RELATIVE
            or expected["accepted_sha256_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_sha256_authority"
            ]
            or expected["accepted_byte_count_authority"]
            != CODE_FIXED_ACCEPTED_BYTE_COUNT_AUTHORITY
        ):
            raise AssertionError(
                f"tag preflight read consumer authority drifted: {relative}"
            )

    post_push_anchor = _validated_json(
        root, "historical_target_execution_post_push_anchor_contract"
    )
    post_push_anchor_artifacts = post_push_anchor.get(
        "git_checkpoint", {}
    ).get("artifacts")
    if not isinstance(post_push_anchor_artifacts, dict):
        raise AssertionError("tag preflight post-push anchor artifacts are absent")
    for relative in SEMANTIC_POST_PUSH_ANCHOR_PATHS:
        expected = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[relative]
        artifact = post_push_anchor_artifacts.get(relative)
        if (
            not isinstance(artifact, dict)
            or artifact.get("ti_java_relative_path") != relative
            or artifact.get("repository_path") != f"Ti-Java/{relative}"
            or artifact.get("sha256") != expected["accepted_sha256"]
            or artifact.get("byte_count") != expected["accepted_byte_count"]
            or expected["accepted_authority"]
            != HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
            or expected["accepted_sha256_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_sha256_authority"
            ]
            or expected["accepted_byte_count_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_byte_count_authority"
            ]
        ):
            raise AssertionError(
                f"tag preflight post-push accepted consumer drifted: {relative}"
            )

    post_push_anchor_overrides = post_push_anchor.get(
        "historical_source_successors", {}
    ).get("overrides")
    post_push_builder_transition = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[
        SEMANTIC_POST_PUSH_ANCHOR_OVERRIDE_PATH
    ]
    post_push_builder_override = (
        post_push_anchor_overrides.get(SEMANTIC_POST_PUSH_ANCHOR_OVERRIDE_PATH)
        if isinstance(post_push_anchor_overrides, dict)
        else None
    )
    if (
        not isinstance(post_push_builder_override, dict)
        or post_push_builder_override.get("source")
        != SEMANTIC_POST_PUSH_ANCHOR_OVERRIDE_PATH
        or post_push_builder_override.get("successor_sha256")
        != post_push_builder_transition["accepted_sha256"]
        or post_push_builder_override.get("successor_byte_count")
        != post_push_builder_transition["accepted_byte_count"]
        or post_push_builder_transition["accepted_authority"]
        != HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
        or post_push_builder_transition["accepted_sha256_authority"]
        != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[
            SEMANTIC_POST_PUSH_ANCHOR_OVERRIDE_PATH
        ]["accepted_sha256_authority"]
        or post_push_builder_transition["accepted_byte_count_authority"]
        != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[
            SEMANTIC_POST_PUSH_ANCHOR_OVERRIDE_PATH
        ]["accepted_byte_count_authority"]
    ):
        raise AssertionError(
            "tag preflight post-push builder successor authority drifted"
        )

    typed_anchor_contract = _validated_json(root, "typed_anchor_contract")
    typed_anchor_overrides = typed_anchor_contract.get(
        "historical_source_successors", {}
    ).get("overrides")
    if not isinstance(typed_anchor_overrides, dict):
        raise AssertionError("tag preflight typed-anchor overrides are absent")
    for relative in SEMANTIC_TYPED_ANCHOR_OVERRIDE_PATHS:
        expected = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[relative]
        authority = typed_anchor_overrides.get(relative)
        if (
            not isinstance(authority, dict)
            or authority.get("source") != relative
            or authority.get("successor_sha256") != expected["accepted_sha256"]
            or authority.get("successor_byte_count")
            != expected["accepted_byte_count"]
            or expected["accepted_authority"] != TYPED_ANCHOR_CONTRACT_RELATIVE
            or expected["accepted_sha256_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_sha256_authority"
            ]
            or expected["accepted_byte_count_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_byte_count_authority"
            ]
        ):
            raise AssertionError(
                f"tag preflight typed-anchor test authority drifted: {relative}"
            )

    post_push_contract = _validated_json(
        root, "historical_target_execution_post_push_contract"
    )
    post_push_artifacts = post_push_contract.get(
        "git_checkpoint", {}
    ).get("artifacts")
    if not isinstance(post_push_artifacts, dict):
        raise AssertionError("tag preflight post-push artifacts are absent")
    for relative, artifact_key in (
        SEMANTIC_POST_PUSH_CONTRACT_ARTIFACT_KEYS.items()
    ):
        expected = SEMANTIC_CONSUMER_SOURCE_SUCCESSORS[relative]
        artifact = post_push_artifacts.get(artifact_key)
        if (
            not isinstance(artifact, dict)
            or artifact.get("ti_java_relative_path") != relative
            or artifact.get("repository_path") != f"Ti-Java/{relative}"
            or artifact.get("sha256") != expected["accepted_sha256"]
            or artifact.get("byte_count") != expected["accepted_byte_count"]
            or expected["accepted_authority"]
            != HISTORICAL_TARGET_EXECUTION_POST_PUSH_CONTRACT_RELATIVE
            or expected["accepted_sha256_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_sha256_authority"
            ]
            or expected["accepted_byte_count_authority"]
            != SEMANTIC_ACCEPTED_AUTHORITY_FIELDS[relative][
                "accepted_byte_count_authority"
            ]
        ):
            raise AssertionError(
                f"tag preflight anchor accepted consumer drifted: {relative}"
            )

    post_push_historical_successors = post_push_anchor.get(
        "historical_source_successors", {}
    ).get("overrides")
    if not isinstance(post_push_historical_successors, dict):
        raise AssertionError(
            "tag preflight post-push bridge successor authority is absent"
        )
    for relative, expected in POST_PUSH_BRIDGE_SOURCE_SUCCESSORS.items():
        authority = post_push_historical_successors.get(relative)
        pointer = relative.replace("/", "~1")
        if (
            not isinstance(authority, dict)
            or authority.get("source") != relative
            or authority.get("successor_sha256")
            != expected["accepted_sha256"]
            or authority.get("successor_byte_count")
            != expected["accepted_byte_count"]
            or expected["accepted_authority"]
            != HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE
            or expected["accepted_sha256_authority"]
            != (
                f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE}"
                f"#/historical_source_successors/overrides/{pointer}/"
                "successor_sha256"
            )
            or expected["accepted_byte_count_authority"]
            != (
                f"{HISTORICAL_TARGET_EXECUTION_POST_PUSH_ANCHOR_CONTRACT_RELATIVE}"
                f"#/historical_source_successors/overrides/{pointer}/"
                "successor_byte_count"
            )
        ):
            raise AssertionError(
                f"tag preflight post-push bridge authority drifted: {relative}"
            )

    for relative, transition in SOURCE_SUCCESSORS.items():
        source_name = SOURCE_SUCCESSOR_SOURCE_NAMES[relative]
        descriptor = SOURCES[source_name]
        if (
            descriptor["source"] != relative
            or descriptor["sha256"] != transition["successor_sha256"]
            or descriptor["byte_count"] != transition["successor_byte_count"]
            or transition["accepted_sha256"] == transition["successor_sha256"]
            or transition["accepted_byte_count"] <= 0
            or transition["successor_byte_count"] <= 0
        ):
            raise AssertionError(
                f"tag preflight source-successor descriptor drifted: {relative}"
            )
        validated_source(root, source_name)


def _historical_semantic_successor_authority(root: Path) -> dict[str, Any]:
    historical = _validated_json(root, "historical_target_execution_contract")
    production = historical.get("production_surface")
    if not isinstance(production, dict):
        raise AssertionError("tag preflight historical production surface is absent")
    accepted_files = production.get("files")
    if (
        production.get("file_count") != HISTORICAL_PRODUCTION_FILE_COUNT
        or production.get("manifest_sha256")
        != HISTORICAL_PRODUCTION_MANIFEST_SHA256
        or production.get("unchanged_from_predecessor") is not True
        or not isinstance(accepted_files, dict)
        or len(accepted_files) != HISTORICAL_PRODUCTION_FILE_COUNT
        or sha256_bytes(canonical_json(accepted_files).encode("utf-8"))
        != HISTORICAL_PRODUCTION_MANIFEST_SHA256
    ):
        raise AssertionError("tag preflight historical production surface drifted")

    for relative, expected_sha256 in PRODUCTION_MANIFEST_ADDITIONS.items():
        if relative in accepted_files:
            raise AssertionError(
                f"tag preflight production addition already existed: {relative}"
            )
        payload = fixed_regular_file(root, relative).read_bytes()
        if sha256_bytes(payload) != expected_sha256:
            raise AssertionError(
                f"tag preflight production addition bytes drifted: {relative}"
            )
    successor_files = {
        **accepted_files,
        **PRODUCTION_MANIFEST_ADDITIONS,
    }
    successor_files = dict(sorted(successor_files.items()))
    if (
        len(successor_files) != SUCCESSOR_PRODUCTION_FILE_COUNT
        or sha256_bytes(canonical_json(successor_files).encode("utf-8"))
        != SUCCESSOR_PRODUCTION_MANIFEST_SHA256
    ):
        raise AssertionError("tag preflight successor production manifest drifted")

    main_prefixes = (
        "server/src/main/java/io/saksk/ti/learning/",
        "server/src/main/java/io/saksk/ti/personalbank/",
    )
    accepted_main = {
        relative: digest
        for relative, digest in accepted_files.items()
        if relative.startswith(main_prefixes)
    }
    successor_main = {
        relative: digest
        for relative, digest in successor_files.items()
        if relative.startswith(main_prefixes)
    }
    if (
        len(accepted_main) != HISTORICAL_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or sha256_bytes(canonical_json(accepted_main).encode("utf-8"))
        != HISTORICAL_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
        or len(successor_main) != SUCCESSOR_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or sha256_bytes(canonical_json(successor_main).encode("utf-8"))
        != SUCCESSOR_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
    ):
        raise AssertionError("tag preflight learning/personalbank main view drifted")

    return {
        "production_runtime_manifest": {
            "accepted_authority": SOURCES[
                "historical_target_execution_contract"
            ],
            "accepted_file_count": HISTORICAL_PRODUCTION_FILE_COUNT,
            "accepted_manifest_sha256": HISTORICAL_PRODUCTION_MANIFEST_SHA256,
            "successor_file_count": SUCCESSOR_PRODUCTION_FILE_COUNT,
            "successor_manifest_sha256": SUCCESSOR_PRODUCTION_MANIFEST_SHA256,
            "unchanged_file_count": HISTORICAL_PRODUCTION_FILE_COUNT,
            "added_files": dict(sorted(PRODUCTION_MANIFEST_ADDITIONS.items())),
            "changed_files": {},
            "deleted_files": [],
            "exact_additions_only": True,
            "unknown_or_extra_files": "reject",
            "symlink_or_root_escape": "reject",
            "learning_personalbank_main": {
                "accepted_file_count": (
                    HISTORICAL_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
                ),
                "accepted_manifest_sha256": (
                    HISTORICAL_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
                ),
                "successor_file_count": (
                    SUCCESSOR_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
                ),
                "successor_manifest_sha256": (
                    SUCCESSOR_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
                ),
                "unchanged_file_count": (
                    HISTORICAL_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
                ),
                "added_files": dict(sorted(PRODUCTION_MANIFEST_ADDITIONS.items())),
                "changed_files": {},
                "deleted_files": [],
                "exact_additions_only": True,
            },
        },
        "java_build_context_and_worm_chain": {
            "accepted_worm": SOURCES["old_worm_predecessor"],
            "accepted_chain_node_count": 5,
            "accepted_build_context_sha256": HISTORICAL_BUILD_CONTEXT_SHA256,
            "first_successor_worm": SOURCES[
                "tag_global_preflight_worm_successor"
            ],
            "first_successor_chain_node_count": 6,
            "first_successor_build_context_sha256": (
                TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256
            ),
            "terminal_successor_worm": SOURCES[
                "tag_global_preflight_hardening_worm_successor"
            ],
            "terminal_successor_chain_node_count": 7,
            "terminal_successor_build_context_sha256": (
                TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256
            ),
            "appended_node_count": 2,
            "historical_nodes_rewritten": False,
            "current_tip_is_terminal_successor": True,
            "unknown_build_context": "reject",
        },
        "historical_contracts_unchanged": True,
        "historical_contract_fields_rewritten": False,
        "semantic_successor_external_git_anchor_complete": False,
    }


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    _validate_semantic_authority(root)
    _validate_evidence_sources(root)
    _validate_source_successor_authority(root)
    historical_semantic_successors = _historical_semantic_successor_authority(root)
    source_paths = [descriptor["source"] for descriptor in SOURCES.values()]
    if len(source_paths) != len(set(source_paths)):
        raise AssertionError("tag preflight source allowlist contains duplicate paths")
    if set(source_paths).intersection(CONTROL_SOURCES):
        raise AssertionError("tag preflight control source entered evidence authority")
    if len(GLOBAL_FAILURE_CODES) != len(set(GLOBAL_FAILURE_CODES)):
        raise AssertionError("tag preflight global failure codes are not unique")

    document: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "captured_at": CAPTURED_AT,
        "scope": "phase4c-learning-owned-personal-bank-tag-global-preflight",
        "status": (
            "global_preflight_bounded_payload_and_unicode_lossless_evidence_closed_"
            "migration_design_operator_apply_and_cutover_unauthorized"
        ),
        "append_only_predecessors": {
            "semantic_composition": {**SOURCES["semantic_composition"], "immutable": True},
            "current_route_promotion": {
                **SOURCES["current_route_promotion"],
                "immutable": True,
            },
            "approved_differences": {
                **SOURCES["approved_differences"],
                "accepted_migration_ids": list(MIGRATION_APPROVED_DIFFERENCE_IDS),
                "current_physical_file_ids": list(CURRENT_APPROVED_DIFFERENCE_IDS),
                "immutable": True,
            },
            "effective_data_ownership": {
                **SOURCES["effective_data_ownership"],
                "immutable": True,
            },
        },
        "source_successor_bridges": {
            "path_count": len(SOURCE_SUCCESSORS),
            "paths": sorted(SOURCE_SUCCESSORS),
            "path_allowlist_exact": True,
            "typed_phase2_paths": sorted(TYPED_PHASE2_SOURCE_SUCCESSORS),
            "phase6_typed_bridge_paths": sorted(
                PHASE6_TYPED_BRIDGE_SOURCE_SUCCESSORS
            ),
            "phase6_document_paths": sorted(PHASE6_DOCUMENT_SOURCE_SUCCESSORS),
            "phase6_bootstrap_paths": sorted(PHASE6_BOOTSTRAP_SOURCE_SUCCESSORS),
            "semantic_consumer_paths": sorted(
                SEMANTIC_CONSUMER_SOURCE_SUCCESSORS
            ),
            "post_push_bridge_paths": sorted(
                POST_PUSH_BRIDGE_SOURCE_SUCCESSORS
            ),
            "typed_normalization_bridge_paths": sorted(
                TYPED_NORMALIZATION_BRIDGE_SOURCE_SUCCESSORS
            ),
            "overrides": {
                relative: {
                    "source": relative,
                    **transition,
                    "successor_authority": SOURCES[
                        SOURCE_SUCCESSOR_SOURCE_NAMES[relative]
                    ],
                    "transition_fixed_by_this_contract": True,
                    "successor_external_git_anchor_complete": False,
                }
                for relative, transition in sorted(SOURCE_SUCCESSORS.items())
            },
            "historical_typed_anchor_contract": SOURCES[
                "typed_anchor_contract"
            ],
            "historical_phase6_source_successor_anchor_contract": SOURCES[
                "phase6_source_successor_anchor_contract"
            ],
            "unknown_paths": "reject",
            "symlink_or_root_escape": "reject",
            "dynamic_source_discovery": False,
            "live_git_head_authority": False,
            "source_successor_external_git_anchor_complete": False,
        },
        "historical_semantic_successors": historical_semantic_successors,
        "semantic_authority": {
            "owner": "learning",
            "execution": "operator-only one-shot; startup and HTTP invocation forbidden",
            "default_mode": "DRY_RUN",
            "source_namespace_regex": "^bank_[1-9][0-9]*_tags$",
            "source_key_round_trip_required": True,
            "source_mutation_or_deletion": False,
            "target_table": "user_question_tag_items",
            "target_delete_or_update": False,
            "automatic_target_merge": False,
            "runtime_get_ddl": False,
            "runtime_get_dml": False,
        },
        "global_preflight_protocol": {
            "connection": {
                "dedicated_connection": True,
                "session_level_postgresql_advisory_lock_across_complete_sweep": True,
                "read_only": True,
                "isolation": "SERIALIZABLE",
                "deferrable": True,
                "acquire_setup_and_close_failures_are_global_blockers": True,
                "global_failure_codes": list(GLOBAL_FAILURE_CODES),
            },
            "selection_and_parsing": {
                "strict_namespace_and_round_trip": True,
                "strict_json_duplicate_keys_and_trailing_tokens_rejected": True,
                "per_payload_utf8_byte_limit": 1_048_576,
                "oversized_payload_rejected_before_json_parsing": True,
                "python_compatible_unicode_whitespace_normalization": True,
                "legacy_list_json_array_string_and_csv_forms_supported": True,
                "twenty_unicode_code_point_cleaning_and_collision_detection": True,
                "postgresql_text_lossless_required": True,
                "nul_and_unpaired_surrogates_rejected": True,
                "valid_surrogate_pairs_preserved": True,
                "unicode_case_and_normalization_forms_preserved": True,
                "positive_canonical_question_ids_required": True,
                "invalid_key_or_data_is_reported_not_dropped": True,
            },
            "source_sweep_bounds": {
                "maximum_reserved_source_rows": 100_000,
                "maximum_reserved_source_utf8_bytes": 268_435_456,
                "source_fetch_size": 16,
                "sql_octet_length_checked_before_payload_materialization": True,
                "oversized_payload_materialized": False,
                "oversized_payload_classification": "INVALID_DATA/PAYLOAD_LIMIT_EXCEEDED",
                "oversized_payload_target_or_membership_read": False,
                "bounds_are_production_scale_evidence": False,
            },
            "membership": {
                "provider": "personalbank::api#inspectQuestionMembership",
                "bank_must_exist": True,
                "positive_question_must_belong_to_bank": True,
                "unresolved_or_orphan_blocks_apply": True,
                "membership_digest_is_canonical_and_reported": True,
            },
            "target_precedence": {
                "valid_source_plan_required": True,
                "source_plan_must_be_subset_of_target": True,
                "target_tags_must_be_canonical": True,
                "positive_target_questions_must_belong_to_bank": True,
                "conflict_blocks_apply": True,
                "automatic_merge": False,
            },
            "aggregation": {
                "all_rows_are_classified_without_first_blocker_short_circuit": True,
                "historical_row_outcomes": list(HISTORICAL_ROW_OUTCOMES),
                "historical_reporting_groups": HISTORICAL_REPORTING_GROUPS,
                "historical_vocabulary_is_apply_predecessor_only": True,
                "dry_run_emits_migrated_or_transaction_failure_outcomes": False,
                "preflight_dispositions": list(PREFLIGHT_DISPOSITIONS),
                "preflight_reporting_groups": PREFLIGHT_REPORTING_GROUPS,
                "preflight_statuses": list(PREFLIGHT_STATUSES),
                "global_all_or_block": True,
                "per_item_disposition_approval_audit_required": True,
                "aggregate_digest": True,
                "raw_tag_or_credential_material_in_report": False,
            },
            "mutation_safety": {
                "mode": "DRY_RUN",
                "source_dml": 0,
                "target_dml": 0,
                "schema_or_index_ddl": 0,
                "mutation_statement_count": 0,
                "source_target_schema_and_index_fingerprints_unchanged": True,
            },
        },
        "evidence": {
            "classification": "test-only local fixture evidence; no production execution",
            "postgresql_versions": ["16.14", "18.4"],
            "integration_test_methods": [
                "globalReadOnlyPreflightEvidenceHoldsOnPostgres16",
                "globalReadOnlyPreflightEvidenceHoldsOnPostgres18",
            ],
            "mixed_fixture_global_blocker_aggregation": True,
            "mixed_fixture_candidate_count": 16,
            "mixed_fixture_reporting_group_counts": MIXED_FIXTURE_REPORTING_GROUP_COUNTS,
            "session_lock_contention_and_release_after_connection_close": True,
            "dry_run_zero_mutation_fingerprints": True,
            "bounded_source_payload_and_sweep_limits_evidenced": True,
            "unicode_postgresql_text_losslessness_evidenced": True,
            "bounded_payload_or_unicode_hardening_authorizes_apply": False,
            "historical_row_primitive_is_only_a_predecessor": True,
            "historical_row_primitive_reclassified_as_global_preflight": False,
            "production_database_connected": False,
            "production_credentials_read": False,
            "production_data_read_or_mutated": False,
            "production_operator_executed": False,
        },
        "apply_fail_closed": {
            "production_apply_authorized": False,
            "planner_cleanliness_eligibility_is_production_authorization": False,
            "planner_apply_prerequisite_blockers": list(APPLY_PREREQUISITE_BLOCKERS),
            "durable_migration_ledger_or_tombstone_exists": False,
            "durable_marker_absence_blocks_apply": True,
            "source_write_freeze_evidenced": False,
            "target_write_freeze_or_common_version_protocol_evidenced": False,
            "membership_write_freeze_or_digest_recheck_evidenced": False,
            "bounded_40001_40P01_retry_implemented": False,
            "backup_and_rollback_evidence_exists": False,
            "production_data_cleanliness_or_scale_proven": False,
            "all_dispositions_approved": False,
            "real_apply_path_present": False,
        },
        "authorization": {
            "newly_closed_gates": list(NEWLY_CLOSED_GATES),
            "migration_global_preflight_evidence_closed": True,
            "migration_design_closed": False,
            "operator_migration_implementation": False,
            "production_schema_or_index": False,
            "real_data_migration_execution": False,
            "production_cutover": False,
            "route_or_openapi_delta": False,
            "http_security_or_rate_limit_delta": False,
            "client_gateway_or_proxy_change": False,
            "source_successor_external_git_anchor_complete": False,
            "semantic_successor_external_git_anchor_complete": False,
            "bootstrap_control_sources_external_git_anchor_complete": False,
        },
        "route_state": ROUTE_STATE,
        "build_context_authority": {
            "old_worm_predecessor": {
                **SOURCES["old_worm_predecessor"],
                "java_build_context_sha256": (
                    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
                ),
                "immutable": True,
            },
            "initial_worm_successor": {
                **SOURCES["tag_global_preflight_worm_successor"],
                "java_build_context_sha256": TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256,
                "dockerfile_sha256": TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
                "predecessor_sha256": TAG_GLOBAL_PREFLIGHT_WORM_PREDECESSOR_SHA256,
                "fixed_chain_node_count": 6,
                "immutable": True,
            },
            "new_worm_successor": {
                **SOURCES["tag_global_preflight_hardening_worm_successor"],
                "java_build_context_sha256": (
                    TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256
                ),
                "dockerfile_sha256": TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
                "predecessor_sha256": (
                    TAG_GLOBAL_PREFLIGHT_HARDENING_WORM_PREDECESSOR_SHA256
                ),
                "fixed_chain_node_count": 7,
                "immutable": True,
            },
            "current_build_context_changed": True,
            "new_main_source_count": len(NEW_MAIN_SOURCE_NAMES),
            "new_main_sources": [SOURCES[name] for name in NEW_MAIN_SOURCE_NAMES],
            "spring_component_runner_scheduler_or_http_registration": False,
            "apply_statement_or_operator_entrypoint_added": False,
            "old_tip_reused_as_current": False,
            "initial_worm_tip_reused_as_current": False,
            "initial_worm_successor_appended": True,
            "new_worm_successor_was_required": True,
            "new_worm_successor_required": False,
            "new_worm_successor_appended": True,
            "new_build_context_worm_closed": True,
            "historical_worm_chain_overwritten": False,
        },
        "source_authority": {
            "fixed_source_count": len(SOURCES),
            "fixed_sources": SOURCES,
            "unknown_sources": "reject",
            "symlink_or_root_escape": "reject",
            "control_source_count": len(CONTROL_SOURCES),
            "control_sources": list(CONTROL_SOURCES),
            "control_sources_excluded_from_self_authority": True,
            "control_sources_external_git_anchor_complete": False,
            "dynamic_source_discovery": False,
            "historical_contracts_or_evidence_overwritten": False,
            "source_successor_path_count": len(SOURCE_SUCCESSORS),
            "source_successor_paths": sorted(SOURCE_SUCCESSORS),
        },
        "next_gate": {
            "worm_successor_gate": "closed by the fixed seventh hardening WORM node",
            "required_next": (
                "design and separately authorize the durable ledger, freeze/recheck, "
                "bounded retry, backup/rollback and operator apply protocol"
            ),
            "production_execution_requires_explicit_user_authorization": True,
        },
    }
    document["document_payload_sha256"] = payload_sha256(document)
    return document


def main() -> None:
    print(serialized(build_contract()).decode("utf-8"), end="")


if __name__ == "__main__":
    main()
