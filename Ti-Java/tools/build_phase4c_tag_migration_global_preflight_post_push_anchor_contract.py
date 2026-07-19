#!/usr/bin/env python3
"""Build the fixed post-push Git anchor for Phase 4C tag preflight Node A."""

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
OUTPUT_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-global-preflight-post-push-anchor-contract.json"
)
DEFAULT_OUTPUT = ROOT / OUTPUT_RELATIVE

CONTRACT_ID = (
    "ti.phase4c.personal-bank-tag-migration-global-preflight-"
    "post-push-anchor-contract"
)
CAPTURED_AT = "2026-07-19T11:15:25+08:00"
STATUS = (
    "global_preflight_checkpoint_externally_anchored_"
    "migration_design_operator_apply_and_cutover_unauthorized"
)
SCOPE = (
    "phase4c-personal-bank-tag-migration-global-preflight-"
    "post-push-external-anchor"
)

PREDECESSOR_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-global-preflight-contract.json"
)
PREDECESSOR_ID = (
    "ti.phase4c.personal-bank-tag-migration-global-preflight-contract"
)
PREDECESSOR_CAPTURED_AT = "2026-07-19T05:52:21+08:00"
PREDECESSOR_STATUS = (
    "global_preflight_bounded_payload_and_unicode_lossless_evidence_closed_"
    "migration_design_operator_apply_and_cutover_unauthorized"
)
PREDECESSOR_SCOPE = "phase4c-learning-owned-personal-bank-tag-global-preflight"
PREDECESSOR_SHA256 = (
    "65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e"
)
PREDECESSOR_PAYLOAD_SHA256 = (
    "c7a94e88772a2453743f9821b165ae10f52650a41bf6dab78006d7058951159e"
)
PREDECESSOR_BYTE_COUNT = 102_931

GIT_OBJECT_FORMAT = "sha1"
GIT_COMMIT_OID = "256d5b347e2e5266eef084221807337427ceb16f"
GIT_PARENT_OID = "08328c3fe18e074f581bb9e782ee4ae86cf46c53"
GIT_ROOT_TREE_OID = "efcd304e85f597ac22840110630d9fc0ae9a8fb0"
GIT_PARENT_ROOT_TREE_OID = "ffd636fbedd6f39dc1975a8752b3a250a4bd184c"
GIT_TI_JAVA_TREE_OID = "e47d851f451fdf045d2c456065ae6913c69229d2"
GIT_PARENT_TI_JAVA_TREE_OID = "0e2fbc42f39f00753c4588e1ddc690725413b88c"
GIT_SERVER_TREE_OID = "0adfaa0bf6e0edeba2aceebce6c267421e3b8144"
GIT_PARENT_SERVER_TREE_OID = "0471b8408a1149f38b3c98d57b1a11cab8288d3a"
GIT_SERVER_SRC_MAIN_TREE_OID = "21fe4902d57a11998502e63041b5a56fb039a090"
GIT_PARENT_SERVER_SRC_MAIN_TREE_OID = (
    "7130e1d1fde766030689658cdd508794ab9a12d6"
)
GIT_WEB_TREE_OID = "a75f69a8205a56843feb055656ddb015ec5b5215"
GIT_PARENT_WEB_TREE_OID = GIT_WEB_TREE_OID
GIT_AUTHORED_AT = "2026-07-19T11:15:25+08:00"
GIT_COMMITTED_AT = GIT_AUTHORED_AT
GIT_SUBJECT = "refactor(java): close tag migration global preflight"
GIT_RAW_DELTA_SHA256 = (
    "035e51e17ce5b2596b604e479c244a1b2af711f14940730095a268257209ebcf"
)
GIT_NUMSTAT_SHA256 = (
    "8f06547f62f829b0b3c20f7596f0e5879377a76d08b5ee03ff5860f74792c7dd"
)
GIT_INSERTED_LINE_COUNT = 14_390
GIT_DELETED_LINE_COUNT = 329
CHECKPOINT_CURRENT_TOTAL_BYTES = 2_485_297
CHECKPOINT_ADDED_TOTAL_BYTES = 586_594
CHECKPOINT_MODIFIED_CURRENT_BYTES = 1_898_703
CHECKPOINT_MODIFIED_PARENT_BYTES = 1_806_829
CHECKPOINT_NET_BYTE_INCREASE = 678_468
CONTROL_CURRENT_TOTAL_BYTES = 554_504
CONTROL_PARENT_TOTAL_BYTES = 109_721
CONTROL_NET_BYTE_INCREASE = 444_783
CHANGED_FIXED_CURRENT_TOTAL_BYTES = 1_930_793
CHANGED_FIXED_PARENT_TOTAL_BYTES = 1_697_108
CHANGED_FIXED_NET_BYTE_INCREASE = 233_685
TRANSITION_CURRENT_TOTAL_BYTES = 1_777_881
TRANSITION_ACCEPTED_TOTAL_BYTES = 1_697_108
TRANSITION_NET_BYTE_INCREASE = 80_773
SEMANTIC_CURRENT_TOTAL_BYTES = 1_179_001
SEMANTIC_ACCEPTED_TOTAL_BYTES = 1_137_011
ADDED_FIXED_TOTAL_BYTES = 152_912
ALL_FIXED_TOTAL_BYTES = 2_533_362
UNCHANGED_FIXED_TOTAL_BYTES = 602_569

# path|change|old-mode|mode|old-oid|oid|sha256|bytes.  This is deliberately
# code-fixed: neither ordinary construction nor Git replay discovers paths.
_CHECKPOINT_ROWS = r"""
docs/refactor/05-progress.md|M|100644|100644|74974ed6ca408e90846ab90b90e965d8fc9faa5b|8024a5d49022f1aa135cd7e4a984f760f666cf2f|8478e44622fc666fdb9a377b15ced624e34d104d1fcbb9b36a4913cfb3ddedf0|107912
docs/refactor/phase4c/README.md|M|100644|100644|8659b84a26ea0b7182c4e375bcb1a1ee185e58b6|15ea8a348a9d6cf54a46b9cad953908da3296c71|4d75ba666d7d45d620a4fba4574e4c2640b754c5a6beadbdbfdee5498aa3cc48|26858
docs/refactor/phase4c/personal-bank-tag-global-preflight-hardening-worm-evidence.json|A|000000|100644|0000000000000000000000000000000000000000|f1cd575801c8212e3a004817b8fe50c030d15a05|93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344|1442
docs/refactor/phase4c/personal-bank-tag-global-preflight-worm-evidence.json|A|000000|100644|0000000000000000000000000000000000000000|bc200af42dcb9e82f11cb3c35782ba52a78f4636|283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72|1442
docs/refactor/phase4c/personal-bank-tag-migration-global-preflight-contract.json|A|000000|100644|0000000000000000000000000000000000000000|d63d6eadbae78fa402bfa34ea8ecf44938ed7801|65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e|102931
docs/refactor/phase4c/personal-bank-tag-migration-global-preflight.md|A|000000|100644|0000000000000000000000000000000000000000|9f4d6db882559363c7fb68c968a17b93c2f86684|2f3ede787e3925771ac0974094c44efeb7b9b02967fb14439ea78c3394cab0e0|10400
infra/phase2/README.md|M|100644|100644|074a75015a4722835b4dfb1a3a0295bbc1822b5a|83919691c5e8b1e16aaa7a1522d4ba5ac74ce70f|a0c467bfc8aa0f0b64b4d520f9cda60ff081a340f016647e1da934c73b7b99d5|7474
infra/phase2/verify-static.sh|M|100755|100755|73124b57758ef4b8eb3acec969dd189361bcfc63|adf88dd68d10de4d55165a43384fec0589a94f2e|893ca920d0ed1bd62e16509893fa30bbfc72b88368d66d96c2ebc5c2fbae38dc|16417
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagGlobalPreflight.java|A|000000|100644|0000000000000000000000000000000000000000|9b4b6c87bbdae94d52e56b821654a5e044f74e71|cdb8fbe7e7a38307642c026b97cafbed040b732d687e30b52f950881f4ab5a76|35830
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagPreflightParser.java|A|000000|100644|0000000000000000000000000000000000000000|be5d89eea24c282f1116d62840bb1e1003270539|c3311e28f33c8bc447fd72191af696ceca333162747e94eb91681dd75c0f5bf3|18525
server/src/main/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagPreflightReport.java|A|000000|100644|0000000000000000000000000000000000000000|55b2844d8f8bf486fca0c3a77ec8a478b43c3ff1|d7d988f5bfe7c86e30a5410e8eac0032a24ad5c85011b6c03de159c97d3ff750|12567
server/src/test/java/io/saksk/ti/architecture/ModuleContractParityTest.java|M|100644|100644|111e73040b0b259e1e24cccbb3798e73356e3ee8|cf799016429c12a5d1f4f06bfb5358605d776205|984863bff3762adc8e375f0073559bb1e0e1d0ed16c368147087fdc3ca4efcd1|182577
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpImplementationSuccessorAcceptance.java|M|100644|100644|c22c17f627642cf65e14e87a2fd0348ae804c189|3a6809865b62958a9e2df81258d42ddd23a1258f|fff0820405e76a4b7c58b094e21619ea050664a3b3ebfbc59abc29a83755465d|80984
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java|M|100644|100644|4d5bb01b4b367da7cd7c270c62c3b5f82083a4fe|545d3405d02b6716ec92a0f7390de0cc69467b9d|a39a7b768979208e5bdcbdcbcbfa7d327521fb69e65d271b5d2f2da47f7ad348|46017
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTargetExecutionSuccessorAcceptance.java|M|100644|100644|6a98738b1db5de7d3d32cfbafe72e16efe7dbd72|ad349777c43cbe0f07c15d9bf3e1621139557c9d|10d19deb68495db02f9113dd58bdf7bbf7dfa67a8885c49f7dd88685f574ff78|91381
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java|M|100644|100644|41fedbae3238f0fb2d839e705ad673b65be56ec0|10edf0dc7e66fa28dbf455fa7d5f949641700ffc|57be8ccb44124d315c21e21e9041861cdcb4568a814af56dbe1725635a479374|45695
server/src/test/java/io/saksk/ti/architecture/Phase4cHttpTypedNormalizationSuccessorAcceptance.java|M|100644|100644|2ece5c8d78b41042817159da04dbf63d4feff0c0|5e99fef2ea9d2b0807f8b1d003c7851893fefe26|ec7c98b04a26f25940fd5b9ec4120ebd478aa41798d4040f1cce97336898d6d2|79735
server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest.java|M|100644|100644|078eb34c6bc7bee1989697ca08f1c4ada0117a26|ede9ab2803ef8b8b98c8e9fbc9b2c96de426856f|faff2f55f48cdaa8bab92530347cda47a0f3ba4dc4227c86242afb94d78aebc0|17295
server/src/test/java/io/saksk/ti/architecture/Phase4cReadSuccessorAcceptance.java|M|100644|100644|3e17d11d936b10d183e2db4acf806ab95a0d018b|328538a39c710afb83533f84e7a244d18dd92078|4699c29cb6e5f790b448752896cc42c413e9f0b3c4844551c4a0b2931517d1a0|19159
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightContractParityTest.java|A|000000|100644|0000000000000000000000000000000000000000|33e9a10a4450201ef1df9975854004084832001b|15dd2e02d5230970358d1761a8298cf44b837c7beda7459d4c4a69173c42f472|38080
server/src/test/java/io/saksk/ti/architecture/Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.java|A|000000|100644|0000000000000000000000000000000000000000|3890b307df0391755d2cb597e85c5d87f86cec99|4a7a9ee5338b8a2dc3b57fd660b3ca9dc30b81e0fcb68d06437bd0f53d3a58b0|94373
server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAnchorAcceptance.java|M|100644|100644|f0338c42fa68f47679fd010bbf782a2eab36e54a|824ef36d39fe097f7f238ddfb1e9261316939536|e5ccdf547d1c11edaf58298a2759241c64731c048bc1bef67f5be046237c01aa|51024
server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorAnchorContractParityTest.java|M|100644|100644|5979e972b460cea532e64a1a5a9f731903baa3e4|c189c6324f7f6cf4db67ac5d8df470bfdbcaa370|47bd6cb662bdc188929afb83c85ff84deccccab97a594bd7f995d7d2cc58faa8|18836
server/src/test/java/io/saksk/ti/architecture/Phase6WebFoundationSourceSuccessorContractParityTest.java|M|100644|100644|8d567fdf4ec2d2dff67a68a9360fcba12d9ce9bc|56241815979f836bba81bfc30482a5b835819895|e61b445cbedddd5b71efe7dda22811128414b58089bf1525aaa4017485f6675d|11762
server/src/test/java/io/saksk/ti/integration/Phase4cLegacyPersonalBankTagGlobalPreflightIT.java|A|000000|100644|0000000000000000000000000000000000000000|20b7d0c6a638238aef3cf0f23728dcb7b8a3a818|6cd525dd7153efb1641a8e629e21ba874b0582a11666a4b89877baa359f4717d|28063
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagGlobalPreflightTest.java|A|000000|100644|0000000000000000000000000000000000000000|b562a4133cc055d57d7333a1988075031d7b81f9|8fc30419dee8be99b8081f873d38921fdedb2beea42a7c1b4c8e2241e844ce3f|34570
server/src/test/java/io/saksk/ti/learning/infrastructure/migration/LegacyPersonalBankTagPreflightParserTest.java|A|000000|100644|0000000000000000000000000000000000000000|5d389bd47277d2fcdce2c50b71432ca9e0a52275|d811cf59f1a778760fc54ebc3a01f5e93be496e8bb9439e92020af576c9e0f8f|10279
server/src/test/resources/db/phase4c/071-legacy-personal-bank-tag-global-preflight-schema.sql|A|000000|100644|0000000000000000000000000000000000000000|48b0b3118f50a597f42ae49795444213ce084ebb|aee1ec236cf119f5f5801f9cdb4856a5011373a81c8ac703b029365758bc9af6|1254
server/src/test/resources/db/phase4c/072-legacy-personal-bank-tag-global-preflight-seed.sql|A|000000|100644|0000000000000000000000000000000000000000|07da62cfa1b25693f49fdbb4a8ad170e93e89244|a70f125c4359b99568f8aa0db19879af0a2d5a0c7dfc064c077e48c3a8ea27a9|8940
tools/build_phase4c_personal_bank_user_counts_http_implementation_contract.py|M|100644|100644|74e55db8f59b7af333c969f680c8bb9d34400ab8|c4a86bc6d206c6a022fd5dbb78b86103323dfa08|1f1c31977c356d93bfabe6714692efa27c5b3c34178e6df6b3517a3362f610e3|57899
tools/build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract.py|M|100644|100644|b3af05cc0a086122e4dd9b0a61f0389bcbe880c3|2ee18b389990d3b17336884c6b88f3bcb4f17861|624d741b383866ce1bb8ec49c24445164665096cdf5b9ab679b2561c61ab7e9a|36240
tools/build_phase4c_personal_bank_user_counts_http_target_execution_contract.py|M|100644|100644|c1910a9ccd2cc8e0773bfb0c7cfdd89c31806db1|0ad1af01a78e60d0fee126d44d5f455eaf978cbc|3064c164d300499d958947068d3acd50c8823c741d9a0144860b5f3b1b532f7d|65798
tools/build_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py|M|100644|100644|74931224e3e620ee5a40a6d9aeb478956ed9528f|b308e53b90f77320935bb8d9ab6e2e65f6bc2786|bbafe62ee77ab0e5c25ed0daf96dc8207cc033d4f39f6cdb3d9cfa8f18365285|33559
tools/build_phase4c_tag_migration_global_preflight_contract.py|A|000000|100644|0000000000000000000000000000000000000000|2564bdc7f0decf91c273256421c0b90108b59cb9|fa5fb43b5caa24006c5d08b94a12eeafaa25be927165f14ae4cf170ff59c03d5|124466
tools/phase2_wormhole_successor_acceptance.py|M|100644|100644|65dd89fd0470becda4476507900b9347c5f0e3af|097866ed80a1534e4adab5015fb40b2c57cc1468|5c93b9aa00d3faec19ebc8d6472bd9e8ab1903a7116d487ff8a711fc60fd8d20|28590
tools/phase4c_http_implementation_successor_acceptance.py|M|100644|100644|5aff7d252b84af1af6188b65294fc19dd266a939|0000cb49aa2a44078837bffe9ad048244f439eb5|f0eba1dbbe3f0cfdbd384c0aea8ba9b768d16edc414ed7c1b1cf5fa8fd31641d|61439
tools/phase4c_http_target_execution_anchor_successor_acceptance.py|M|100644|100644|14cfc16aad7fbae8df09a46c846d890a43663587|6cace9389eb64752ec85637915b6bd1891706446|e91c56e91cdeff3bf069407d8e43d7d1b76fb131c875cf536e561976fe395141|36566
tools/phase4c_http_target_execution_post_push_successor_acceptance.py|M|100644|100644|4db7542d4172bb0b717e439688c5d3d008a9f7d4|f5e2f64be51c621a5f26e01dbb8f555489793a81|b19db64d6ddb71b0cac1d4ae296c02e65e82d476b37b9db5ec5fbfcfd7f4a8df|32538
tools/phase4c_http_target_execution_successor_acceptance.py|M|100644|100644|70248a346d5153062625bd124ab3d9a7c2fc019d|b1e21ca7471b6faaf2842bb3766736f39334b102|daca285575123c6b3d690c52977bbf8797fa46d5db75862b774805acb586a230|84585
tools/phase4c_http_typed_normalization_anchor_successor_acceptance.py|M|100644|100644|3ea8170b0a9392b332f2794269c8f30a390b72ee|f051e43c33b4d4a1134207c4ead3ce24c52ee172|c54843d2c759882e4d5e7553e9b76598a1ecd31038ace27ac265275887a414d2|45142
tools/phase4c_http_typed_normalization_successor_acceptance.py|M|100644|100644|67518ff1ae88eafd386ab0bc64c01c3a1e11aec4|b70d9707ee226f581afda72ff210e4b29c24bae8|a852f20ffccd8d2f1597a1bd2adb525ca66e83fed707ef6d44ff9a8d35c240c8|57882
tools/phase4c_read_successor_acceptance.py|M|100644|100644|4aa5f55aef386d3461b7109af122dbeaf3d0ca49|65da03bfdcc2c221b4cf5fd1ed61b7cecd13a8eb|25792f3a1371b8a492d674d70228ce81872e0ce48c2aab8051805c8c0b41de8a|15161
tools/phase4c_tag_migration_global_preflight_successor_acceptance.py|A|000000|100644|0000000000000000000000000000000000000000|7de3f4025d780814a0a1ffe1ac95f9bf15d7c894|258ba0903f318aae40ebeba1b693bd97fe13ea534e1afcb423f1a373b9e05a44|27736
tools/phase6_web_foundation_source_successor_anchor_acceptance.py|M|100644|100644|4959ac71172e151f813c6e17421bdf36c493962a|d3625fa5606b5ce48f4323c37fca38a299ad0b4a|d2454682218947e92fa3a616e7eecf592e0d7ee23c208b0068421a94def919c9|35750
tools/test_phase2_wormhole_successor_acceptance.py|M|100644|100644|8c103010f09cadc4f4afe49b9ca1b62d50dc1bd4|ce500babe903983b5dc61bdf2206108172628b9e|e61ed72335bba631cf34ebfe06fae8d391e7828622eba17d0240f59efed379a3|52825
tools/test_phase4b_personal_bank_all_shares_entry_contract.py|M|100644|100644|1685936b2fb4439e964243751924bc7405c44bca|ee92a7c2ebdb8ae874324405daa350dedfe749a2|31dec8b10fad1f044ecbca4a76da0d4f1f97ffbbe32e075895e050372ff8ba4a|24249
tools/test_phase4b_personal_bank_all_shares_read_contract.py|M|100644|100644|829a63396f04e86b26147a1a0984b457a78c253b|23889fd141dc034f9f72e2b01a4fb8317432c3e9|7afd91f0e0048cba029d38965c900da670d5f327b8b9541b0962533b1b1f09eb|19451
tools/test_phase4b_personal_bank_share_list_entry_contract.py|M|100644|100644|15bc6df39f3a7a1a41f8b60566d09e1a6e3b9c51|7df80701b89014f1f6709e304db3ce1d5e0da3fc|32b4d8e625f452ba20852fe64805086a6d878f3f8518298e7340122ff6120943|33265
tools/test_phase4b_personal_bank_share_list_read_contract.py|M|100644|100644|8d8dde32475341b9a077b0b0edf4f9d80856ba68|1d1720238d0a1a82d30dcad10e068405fabb4b7d|047563af77f5786b0af24eeb20f8d287163df44778aad1ee56d1805a05207ec4|45547
tools/test_phase4b_personal_bank_usage_stats_entry_contract.py|M|100644|100644|917e8a08ae150b90a9225e0ecb11cdf8e331d422|550883d86e3bdf8a0fcae82fc568a8fff0204b78|4f3c9ab19370eabd6dbe6dbea047d1e176c3a4e8ed947035a54dc210b75e2057|25598
tools/test_phase4b_personal_bank_usage_stats_read_contract.py|M|100644|100644|6f331239d9d9b6d04766ba68cc27ff0718842f42|98e4aebd874eefde518d9bec6b979f33fd3452bc|0a980e05a5fd4204e5db630447c7b018d54e2e89b64e7f069eb1329f85a5d372|34463
tools/test_phase4b_personal_bank_user_counts_entry_contract.py|M|100644|100644|bd267dd81233de5f4118793f20f967c76a180a7d|c725a2afbe664ae8325dc18463d2690de87c66d7|162e057e07d6d0d0f73b6ee8bf9210fd98c492369222ce649a4f5bd5418b16b4|37033
tools/test_phase4c_personal_bank_user_counts_composition_contract.py|M|100644|100644|f9460c80973033e30a4392515ea4bbc52cd8b644|5ec3ce4c4b6f5c8524a47b5ae595e635249245e5|51ab42d0a220f3e91ac07a9b3ab1f6a2ca6c366b994de200effae31a074a766b|60156
tools/test_phase4c_personal_bank_user_counts_http_entry_contract.py|M|100644|100644|b40ef597db466504c3c4c81e571eafe8fa307265|6cdf4e9578f3e2929588417853561461d9bd79dd|fcc4eee103b33604addfd17e453793dd41c498de62fe0538e873520dbd285b26|32398
tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py|M|100644|100644|7a57b4cc860a9b531383931e7259fc610a3cffa8|f87fd6fbf7568fb9fc618eb558428f6a6918767e|a6b70a441470d079b5bc2dc392887d49af72d6dc75a4feba3226a772b5b4c9d5|10308
tools/test_phase4c_personal_bank_user_counts_http_target_execution_contract.py|M|100644|100644|c810a5ecdfb3c1991c3ef9d644417a962da0ac47|8d6844edc1f356d3201b0e59550177e3c5add968|469c46bde8e339ef28a461f3fd2a34ee7e02bfa12cb75eec4f881454049e7957|34398
tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract.py|M|100644|100644|644110dbefc21cd1264433b8917fe1ddccc11181|36e4537e591dccedd4b2d46f765586340a99788f|49621a580785ddd0c1210bf564e563b41e04bebbc87c33752e95bc6cb9cb89fd|19769
tools/test_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py|M|100644|100644|70c732bf1236be10a66bf8d2f5678193bd15d661|810058dfd0f2db123dd3f787953188f9130ef16a|420a727733f4c3a72f1c78c933491ab89fff7bbba0ddb1f1c9f7a8867a73c3bf|12482
tools/test_phase4c_personal_bank_user_counts_http_typed_normalization_anchor_contract.py|M|100644|100644|3c7af81193452fc00a2d98458025431f4ca7ad73|0c0343d6fe641d081127c0307a340cb1a2736331|cdc78a5f771d09eb1822f3dbcd10030e812e4a5ab6b7792ce2b0a9d8366e90ba|13443
tools/test_phase4c_personal_bank_user_counts_read_contract.py|M|100644|100644|89142b57f5f615c74a7b5ff3f95927875daca217|57f5d9ec83f23b06ef358bbed5dc9f7defbeea71|6c302395dca0d7d319233e6463ed65b26aa3ea103c90511752ae4cac710dbaad|24536
tools/test_phase4c_tag_migration_global_preflight_contract.py|A|000000|100644|0000000000000000000000000000000000000000|099afdeb2891ddf1237a633766960b7947487841|3644acb20bb3ddf220d1c088c2e52778742892d8bae843c697314372fa858b87|35696
tools/test_phase6_web_foundation_source_successor_anchor_contract.py|M|100644|100644|37ed5fb31d5a3ed7de57eb28507fb94c0b6e0d8b|c6734f46e657a088ced7ed168ad096a93efbde1b|05b81017196ea0cb4581d5ad6be8a027f4d83060e98de7abb1ff209c9d51ae02|15212
tools/test_phase6_web_foundation_source_successor_contract.py|M|100644|100644|4b8f6d059444ecab311759821cf6f31f938c220d|a635cc54aff77b4acafd66e6eba5f811a3d9c8b1|3bc6342e7dad775f7c92acfc0f8cb23cd94aabd6d395f4f0fae420faea14ee6b|9295
""".strip()


def _checkpoint_changes() -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for row in _CHECKPOINT_ROWS.splitlines():
        (relative, change_type, previous_mode, mode, previous_oid, oid,
         sha256, byte_count) = row.split("|")
        changes[relative] = {
            "repository_path": f"Ti-Java/{relative}",
            "ti_java_relative_path": relative,
            "change_type": change_type,
            "previous_mode": previous_mode,
            "mode": mode,
            "previous_git_blob_oid": previous_oid,
            "git_blob_oid": oid,
            "object_type": "blob",
            "sha256": sha256,
            "byte_count": int(byte_count),
        }
    return changes


CHECKPOINT_CHANGES = _checkpoint_changes()
CHECKPOINT_PATHS = tuple(CHECKPOINT_CHANGES)

NODE_A_SOURCE_SUCCESSOR_COUNT = 42
NODE_A_SEMANTIC_CONSUMER_COUNT = 26
NODE_A_FIXED_SOURCE_COUNT = 72
NODE_A_CONTROL_SOURCE_COUNT = 11
NODE_A_SOURCE_SUCCESSOR_MANIFEST_SHA256 = (
    "d1ab1bf37de977c934968a6d07cd711b6bec06e1b3bc22bbaa9978d8a3764b4a"
)
NODE_A_SEMANTIC_CONSUMER_MANIFEST_SHA256 = (
    "1fba3c51e73af84e21b54e6930272dc6cc1c058dbf7ceadaff8d73d1af1698db"
)
NODE_A_FIXED_SOURCE_MANIFEST_SHA256 = (
    "ec95c0105bf8f6d5e2c4b1cf3a32178a379b4efa17e1020cf4e320d49f0facbf"
)
NODE_A_CONTROL_SOURCE_MANIFEST_SHA256 = (
    "e78f71fc2a9b7d4e23ddc93ded7229c11f3d39c604d06f2c11f585bd4b0f813c"
)
NODE_A_SOURCE_PATHS_SHA256 = (
    "a353fb2043030dec804a6fd04426e946d5ffd4f0031e2394875e22ea453b20a9"
)
NODE_A_SEMANTIC_PATHS_SHA256 = (
    "b253d7834590211524367196f92efa3927d6d4c02048eed011b42d2d6559d6c1"
)
NODE_A_FIXED_PATHS_SHA256 = (
    "ec38260effc79d85db6214776b3bb9569f7e330d0ece2b0f72a40d580b12e8e9"
)

CURRENT_CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/"
    "Phase4cTagMigrationGlobalPreflightPostPushAnchorContractParityTest.java",
    "tools/build_phase4c_tag_migration_global_preflight_"
    "post_push_anchor_contract.py",
    "tools/phase4c_tag_migration_global_preflight_"
    "post_push_anchor_successor_acceptance.py",
    "tools/test_phase4c_tag_migration_global_preflight_"
    "post_push_anchor_contract.py",
)

TERMINAL_WORM_RELATIVE = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-global-preflight-hardening-worm-evidence.json"
)
TERMINAL_WORM_SHA256 = (
    "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344"
)
TERMINAL_WORM_BYTE_COUNT = 1_442
JAVA_BUILD_CONTEXT_SHA256 = (
    "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17"
)
DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
MAIN_ADDITIONS = (
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
    "LegacyPersonalBankTagGlobalPreflight.java",
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
    "LegacyPersonalBankTagPreflightParser.java",
    "server/src/main/java/io/saksk/ti/learning/infrastructure/migration/"
    "LegacyPersonalBankTagPreflightReport.java",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def document_payload_sha256(document: dict[str, Any]) -> str:
    return sha256_json({key: value for key, value in document.items()
                        if key != "document_payload_sha256"})


def serialized_contract(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n").encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    value = Path(relative)
    if (value.is_absolute() or not value.parts
            or any(part in ("", ".", "..") for part in value.parts)):
        raise AssertionError(f"Node A anchor path escapes root: {relative}")
    candidate = root.joinpath(*value.parts)
    cursor = root
    for part in value.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"Node A anchor path is a symlink: {relative}")
    if not candidate.is_file():
        raise AssertionError(f"Node A anchor path is not regular: {relative}")
    return candidate


def _read_fixed_predecessor(root: Path) -> dict[str, Any]:
    payload = fixed_regular_file(root, PREDECESSOR_RELATIVE).read_bytes()
    if (len(payload) != PREDECESSOR_BYTE_COUNT
            or sha256_bytes(payload) != PREDECESSOR_SHA256):
        raise AssertionError("Node A anchor predecessor fixed bytes drifted")
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("Node A anchor predecessor is not an object")
    if (document.get("contract_id") != PREDECESSOR_ID
            or document.get("captured_at") != PREDECESSOR_CAPTURED_AT
            or document.get("status") != PREDECESSOR_STATUS
            or document.get("scope") != PREDECESSOR_SCOPE
            or document.get("document_payload_sha256")
            != PREDECESSOR_PAYLOAD_SHA256
            or document_payload_sha256(document)
            != PREDECESSOR_PAYLOAD_SHA256):
        raise AssertionError("Node A anchor predecessor identity drifted")
    _validate_node_a_authority(document)
    return document


def _validate_node_a_authority(document: dict[str, Any]) -> None:
    bridges = document.get("source_successor_bridges", {})
    source_paths = bridges.get("paths")
    semantic_paths = bridges.get("semantic_consumer_paths")
    overrides = bridges.get("overrides")
    authority = document.get("source_authority", {})
    fixed_sources = authority.get("fixed_sources")
    controls = authority.get("control_sources")
    if (not isinstance(source_paths, list)
            or len(source_paths) != NODE_A_SOURCE_SUCCESSOR_COUNT
            or len(set(source_paths)) != NODE_A_SOURCE_SUCCESSOR_COUNT
            or sha256_json(source_paths) != NODE_A_SOURCE_PATHS_SHA256
            or not isinstance(overrides, dict)
            or set(overrides) != set(source_paths)
            or sha256_json(overrides)
            != NODE_A_SOURCE_SUCCESSOR_MANIFEST_SHA256
            or not isinstance(semantic_paths, list)
            or len(semantic_paths) != NODE_A_SEMANTIC_CONSUMER_COUNT
            or len(set(semantic_paths)) != NODE_A_SEMANTIC_CONSUMER_COUNT
            or not set(semantic_paths) < set(source_paths)
            or sha256_json(semantic_paths) != NODE_A_SEMANTIC_PATHS_SHA256
            or sha256_json({path: overrides[path] for path in semantic_paths})
            != NODE_A_SEMANTIC_CONSUMER_MANIFEST_SHA256):
        raise AssertionError("Node A anchor successor authority drifted")
    if (not isinstance(fixed_sources, dict)
            or len(fixed_sources) != NODE_A_FIXED_SOURCE_COUNT
            or sha256_json(fixed_sources) != NODE_A_FIXED_SOURCE_MANIFEST_SHA256
            or not isinstance(controls, list)
            or len(controls) != NODE_A_CONTROL_SOURCE_COUNT
            or len(set(controls)) != NODE_A_CONTROL_SOURCE_COUNT
            or sha256_json(controls) != NODE_A_CONTROL_SOURCE_MANIFEST_SHA256):
        raise AssertionError("Node A anchor fixed/control authority drifted")
    fixed_paths = sorted(item.get("source") for item in fixed_sources.values())
    if (any(not isinstance(path, str) for path in fixed_paths)
            or len(set(fixed_paths)) != NODE_A_FIXED_SOURCE_COUNT
            or sha256_json(fixed_paths) != NODE_A_FIXED_PATHS_SHA256):
        raise AssertionError("Node A anchor fixed-source paths drifted")
    authorization = document.get("authorization", {})
    route = document.get("route_state", {})
    if (authorization.get("migration_global_preflight_evidence_closed") is not True
            or authorization.get("migration_design_closed") is not False
            or authorization.get("operator_migration_implementation") is not False
            or authorization.get("production_schema_or_index") is not False
            or authorization.get("real_data_migration_execution") is not False
            or authorization.get("production_cutover") is not False
            or route != {
                "migrated_operation_count": 13,
                "pending_operation_count": 598,
                "production_cutover_operation_count": 0,
                "total_operation_count": 611,
            }):
        raise AssertionError("Node A anchor authorization/route boundary drifted")


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    forbidden = {"HEAD", "origin/main", "@", "--all"}
    if any(argument in forbidden for argument in arguments):
        raise AssertionError("Node A anchor live/ref Git authority is forbidden")
    environment = os.environ.copy()
    environment.update({
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
    })
    try:
        completed = subprocess.run(
            ("git", "--no-optional-locks", *arguments), cwd=repository_root,
            env=environment, check=True, timeout=30,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise AssertionError("Node A anchor read-only Git replay failed") from error
    return completed.stdout


def _git_text(repository_root: Path, *arguments: str) -> str:
    return _run_git(repository_root, *arguments).decode("utf-8").strip()


def _expected_raw_delta() -> list[str]:
    return [
        f":{item['previous_mode']} {item['mode']} "
        f"{item['previous_git_blob_oid']} {item['git_blob_oid']} "
        f"{item['change_type']}\t{item['repository_path']}"
        for item in CHECKPOINT_CHANGES.values()
    ]


def validate_git_checkpoint(repository_root: Path) -> None:
    root = repository_root.resolve(strict=True)
    if Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise AssertionError("Node A anchor repository root was not explicit")
    if _git_text(root, "rev-parse", "--show-object-format") != GIT_OBJECT_FORMAT:
        raise AssertionError("Node A anchor Git object format drifted")
    if (_git_text(root, "cat-file", "-t", GIT_COMMIT_OID) != "commit"
            or _git_text(root, "rev-parse", "--verify",
                         f"{GIT_COMMIT_OID}^{{commit}}") != GIT_COMMIT_OID):
        raise AssertionError("Node A anchor commit object drifted")
    facts = _git_text(
        root, "show", "-s", "--format=%T%n%P%n%aI%n%cI%n%s", GIT_COMMIT_OID
    ).splitlines()
    if facts != [GIT_ROOT_TREE_OID, GIT_PARENT_OID, GIT_AUTHORED_AT,
                 GIT_COMMITTED_AT, GIT_SUBJECT]:
        raise AssertionError("Node A anchor commit identity/unique parent drifted")
    trees = {
        "Ti-Java": GIT_TI_JAVA_TREE_OID,
        "Ti-Java/server": GIT_SERVER_TREE_OID,
        "Ti-Java/server/src/main": GIT_SERVER_SRC_MAIN_TREE_OID,
        "Ti-Java/web": GIT_WEB_TREE_OID,
    }
    for relative, expected in trees.items():
        if _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:{relative}") != expected:
            raise AssertionError(f"Node A anchor tree drifted: {relative}")
    parent_facts = _git_text(root, "show", "-s", "--format=%T", GIT_PARENT_OID)
    if (parent_facts != GIT_PARENT_ROOT_TREE_OID
            or _git_text(root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java")
            != GIT_PARENT_TI_JAVA_TREE_OID
            or _git_text(root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java/server")
            != GIT_PARENT_SERVER_TREE_OID
            or _git_text(root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java/web")
            != GIT_PARENT_WEB_TREE_OID
            or _git_text(root, "rev-parse",
                         f"{GIT_PARENT_OID}:Ti-Java/server/src/main")
            != GIT_PARENT_SERVER_SRC_MAIN_TREE_OID
            or GIT_SERVER_SRC_MAIN_TREE_OID
            == GIT_PARENT_SERVER_SRC_MAIN_TREE_OID):
        raise AssertionError("Node A anchor production tree boundary drifted")
    raw = _run_git(root, "diff-tree", "--no-commit-id", "--raw",
                   "--abbrev=40", "-r", GIT_COMMIT_OID)
    if (sha256_bytes(raw) != GIT_RAW_DELTA_SHA256
            or raw.decode("utf-8").splitlines() != _expected_raw_delta()):
        raise AssertionError("Node A anchor exact 63-path raw delta drifted")
    numstat_raw = _run_git(root, "diff-tree", "--no-commit-id", "--numstat",
                           "-r", GIT_COMMIT_OID)
    if sha256_bytes(numstat_raw) != GIT_NUMSTAT_SHA256:
        raise AssertionError("Node A anchor raw numstat drifted")
    numstat = numstat_raw.decode("utf-8").splitlines()
    parsed = [line.split("\t", 2) for line in numstat]
    if (len(parsed) != 63
            or any(len(parts) != 3 or not parts[0].isdigit()
                   or not parts[1].isdigit() for parts in parsed)
            or sum(int(parts[0]) for parts in parsed)
            != GIT_INSERTED_LINE_COUNT
            or sum(int(parts[1]) for parts in parsed)
            != GIT_DELETED_LINE_COUNT
            or [parts[2] for parts in parsed]
            != [item["repository_path"]
                for item in CHECKPOINT_CHANGES.values()]):
        raise AssertionError("Node A anchor exact numstat drifted")
    current_total = added_total = modified_current = modified_parent = 0
    for item in CHECKPOINT_CHANGES.values():
        payload = _run_git(root, "cat-file", "blob", item["git_blob_oid"])
        if (len(payload) != item["byte_count"]
                or sha256_bytes(payload) != item["sha256"]):
            raise AssertionError(
                f"Node A anchor Git blob drifted: {item['repository_path']}"
            )
        current_total += len(payload)
        if item["change_type"] == "A":
            added_total += len(payload)
        elif item["change_type"] == "M":
            modified_current += len(payload)
            modified_parent += len(_run_git(
                root, "cat-file", "blob", item["previous_git_blob_oid"]
            ))
        else:
            raise AssertionError("Node A anchor unexpected change type")
    if (current_total != CHECKPOINT_CURRENT_TOTAL_BYTES
            or added_total != CHECKPOINT_ADDED_TOTAL_BYTES
            or modified_current != CHECKPOINT_MODIFIED_CURRENT_BYTES
            or modified_parent != CHECKPOINT_MODIFIED_PARENT_BYTES
            or current_total - modified_parent
            != CHECKPOINT_NET_BYTE_INCREASE):
        raise AssertionError("Node A anchor byte aggregates drifted")


def validate_node_a_fixed_sources_at_checkpoint(
        repository_root: Path, predecessor: dict[str, Any]) -> None:
    root = repository_root.resolve(strict=True)
    fixed_sources = predecessor["source_authority"]["fixed_sources"]
    fixed_by_path = {
        descriptor["source"]: descriptor for descriptor in fixed_sources.values()
    }
    controls = set(predecessor["source_authority"]["control_sources"])
    transitions = set(predecessor["source_successor_bridges"]["paths"])
    semantic = set(
        predecessor["source_successor_bridges"]["semantic_consumer_paths"]
    )
    delta = set(CHECKPOINT_CHANGES)
    changed_fixed = delta & set(fixed_by_path)
    unchanged_fixed = set(fixed_by_path) - delta
    if (controls & set(fixed_by_path)
            or controls & transitions
            or transitions - changed_fixed
            or semantic - transitions
            or delta != controls | changed_fixed
            or len(changed_fixed) != 52
            or len(unchanged_fixed) != 20
            or sum(CHECKPOINT_CHANGES[path]["change_type"] == "A"
                   for path in controls) != 7
            or sum(CHECKPOINT_CHANGES[path]["change_type"] == "M"
                   for path in controls) != 4
            or sum(CHECKPOINT_CHANGES[path]["change_type"] == "A"
                   for path in changed_fixed) != 10
            or sum(CHECKPOINT_CHANGES[path]["change_type"] == "M"
                   for path in changed_fixed) != 42):
        raise AssertionError("Node A anchor 63-path authority partition drifted")
    fixed_current_total = 0
    unchanged_total = 0
    for descriptor in fixed_sources.values():
        relative = descriptor["source"]
        oid = _git_text(root, "rev-parse", f"{GIT_COMMIT_OID}:Ti-Java/{relative}")
        payload = _run_git(root, "cat-file", "blob", oid)
        if (len(payload) != descriptor["byte_count"]
                or sha256_bytes(payload) != descriptor["sha256"]):
            raise AssertionError(
                f"Node A anchor fixed tree source drifted: {relative}"
            )
        fixed_current_total += len(payload)
        if relative in unchanged_fixed:
            parent_oid = _git_text(
                root, "rev-parse", f"{GIT_PARENT_OID}:Ti-Java/{relative}"
            )
            if parent_oid != oid:
                raise AssertionError(
                    f"Node A anchor unchanged fixed source drifted: {relative}"
                )
            unchanged_total += len(payload)
    overrides = predecessor["source_successor_bridges"]["overrides"]
    transition_current = transition_accepted = 0
    semantic_current = semantic_accepted = 0
    for relative in transitions:
        item = CHECKPOINT_CHANGES[relative]
        override = overrides[relative]
        previous = _run_git(root, "cat-file", "blob",
                            item["previous_git_blob_oid"])
        if (item["change_type"] != "M"
                or item["sha256"] != override["successor_sha256"]
                or item["byte_count"] != override["successor_byte_count"]
                or sha256_bytes(previous) != override["accepted_sha256"]
                or len(previous) != override["accepted_byte_count"]
                or _git_text(root, "rev-parse",
                             f"{GIT_PARENT_OID}:Ti-Java/{relative}")
                != item["previous_git_blob_oid"]):
            raise AssertionError(
                f"Node A anchor accepted/successor transition drifted: {relative}"
            )
        transition_current += item["byte_count"]
        transition_accepted += len(previous)
        if relative in semantic:
            semantic_current += item["byte_count"]
            semantic_accepted += len(previous)
    control_current = sum(CHECKPOINT_CHANGES[path]["byte_count"]
                          for path in controls)
    control_parent = sum(
        len(_run_git(root, "cat-file", "blob",
                     CHECKPOINT_CHANGES[path]["previous_git_blob_oid"]))
        for path in controls if CHECKPOINT_CHANGES[path]["change_type"] == "M"
    )
    changed_fixed_current = sum(CHECKPOINT_CHANGES[path]["byte_count"]
                                for path in changed_fixed)
    changed_fixed_parent = sum(
        len(_run_git(root, "cat-file", "blob",
                     CHECKPOINT_CHANGES[path]["previous_git_blob_oid"]))
        for path in changed_fixed
        if CHECKPOINT_CHANGES[path]["change_type"] == "M"
    )
    added_fixed = sum(CHECKPOINT_CHANGES[path]["byte_count"]
                      for path in changed_fixed
                      if CHECKPOINT_CHANGES[path]["change_type"] == "A")
    if (control_current != CONTROL_CURRENT_TOTAL_BYTES
            or control_parent != CONTROL_PARENT_TOTAL_BYTES
            or control_current - control_parent != CONTROL_NET_BYTE_INCREASE
            or changed_fixed_current != CHANGED_FIXED_CURRENT_TOTAL_BYTES
            or changed_fixed_parent != CHANGED_FIXED_PARENT_TOTAL_BYTES
            or changed_fixed_current - changed_fixed_parent
            != CHANGED_FIXED_NET_BYTE_INCREASE
            or transition_current != TRANSITION_CURRENT_TOTAL_BYTES
            or transition_accepted != TRANSITION_ACCEPTED_TOTAL_BYTES
            or transition_current - transition_accepted
            != TRANSITION_NET_BYTE_INCREASE
            or semantic_current != SEMANTIC_CURRENT_TOTAL_BYTES
            or semantic_accepted != SEMANTIC_ACCEPTED_TOTAL_BYTES
            or added_fixed != ADDED_FIXED_TOTAL_BYTES
            or fixed_current_total != ALL_FIXED_TOTAL_BYTES
            or unchanged_total != UNCHANGED_FIXED_TOTAL_BYTES):
        raise AssertionError("Node A anchor authority byte partition drifted")


def build_contract(
        ti_java_root: Path = ROOT, *,
        repository_root: Path | None = None) -> dict[str, Any]:
    root = ti_java_root.resolve(strict=True)
    predecessor = _read_fixed_predecessor(root)
    if repository_root is not None:
        validate_git_checkpoint(repository_root)
        validate_node_a_fixed_sources_at_checkpoint(repository_root, predecessor)
    bridges = predecessor["source_successor_bridges"]
    authority = predecessor["source_authority"]
    fixed_paths = sorted(
        descriptor["source"] for descriptor in authority["fixed_sources"].values()
    )
    document: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "captured_at": CAPTURED_AT,
        "status": STATUS,
        "scope": SCOPE,
        "predecessor": {
            "source": PREDECESSOR_RELATIVE,
            "contract_id": PREDECESSOR_ID,
            "captured_at": PREDECESSOR_CAPTURED_AT,
            "status": PREDECESSOR_STATUS,
            "scope": PREDECESSOR_SCOPE,
            "sha256": PREDECESSOR_SHA256,
            "byte_count": PREDECESSOR_BYTE_COUNT,
            "document_payload_sha256": PREDECESSOR_PAYLOAD_SHA256,
            "immutable": True,
        },
        "git_checkpoint": {
            "object_format": GIT_OBJECT_FORMAT,
            "commit_oid": GIT_COMMIT_OID,
            "parent_oid": GIT_PARENT_OID,
            "unique_parent_fixed": True,
            "root_tree_oid": GIT_ROOT_TREE_OID,
            "parent_root_tree_oid": GIT_PARENT_ROOT_TREE_OID,
            "ti_java_tree_oid": GIT_TI_JAVA_TREE_OID,
            "parent_ti_java_tree_oid": GIT_PARENT_TI_JAVA_TREE_OID,
            "server_tree_oid": GIT_SERVER_TREE_OID,
            "parent_server_tree_oid": GIT_PARENT_SERVER_TREE_OID,
            "server_src_main_tree_oid": GIT_SERVER_SRC_MAIN_TREE_OID,
            "parent_server_src_main_tree_oid":
                GIT_PARENT_SERVER_SRC_MAIN_TREE_OID,
            "web_tree_oid": GIT_WEB_TREE_OID,
            "parent_web_tree_oid": GIT_PARENT_WEB_TREE_OID,
            "web_tree_unchanged_from_parent": True,
            "server_src_main_tree_changed_from_parent": True,
            "authored_at": GIT_AUTHORED_AT,
            "committed_at": GIT_COMMITTED_AT,
            "subject": GIT_SUBJECT,
            "raw_delta_sha256": GIT_RAW_DELTA_SHA256,
            "numstat_sha256": GIT_NUMSTAT_SHA256,
            "changed_path_count": 63,
            "added_count": 17,
            "modified_count": 46,
            "deleted_count": 0,
            "non_ti_java_count": 0,
            "inserted_line_count": GIT_INSERTED_LINE_COUNT,
            "deleted_line_count": GIT_DELETED_LINE_COUNT,
            "current_total_bytes": CHECKPOINT_CURRENT_TOTAL_BYTES,
            "added_total_bytes": CHECKPOINT_ADDED_TOTAL_BYTES,
            "modified_current_bytes": CHECKPOINT_MODIFIED_CURRENT_BYTES,
            "modified_parent_bytes": CHECKPOINT_MODIFIED_PARENT_BYTES,
            "net_byte_increase": CHECKPOINT_NET_BYTE_INCREASE,
            "exact_sixty_three_path_delta": True,
            "artifacts": deepcopy(CHECKPOINT_CHANGES),
        },
        "node_a_authority_anchor": {
            "source_successor_paths": list(bridges["paths"]),
            "source_successor_path_count": NODE_A_SOURCE_SUCCESSOR_COUNT,
            "source_successor_path_allowlist_exact": True,
            "source_successor_manifest_sha256":
                NODE_A_SOURCE_SUCCESSOR_MANIFEST_SHA256,
            "semantic_consumer_paths": list(bridges["semantic_consumer_paths"]),
            "semantic_consumer_path_count": NODE_A_SEMANTIC_CONSUMER_COUNT,
            "semantic_consumer_path_allowlist_exact": True,
            "semantic_consumer_manifest_sha256":
                NODE_A_SEMANTIC_CONSUMER_MANIFEST_SHA256,
            "fixed_source_paths": fixed_paths,
            "fixed_source_count": NODE_A_FIXED_SOURCE_COUNT,
            "fixed_source_path_allowlist_exact": True,
            "fixed_source_manifest_sha256": NODE_A_FIXED_SOURCE_MANIFEST_SHA256,
            "control_sources": list(authority["control_sources"]),
            "control_source_count": NODE_A_CONTROL_SOURCE_COUNT,
            "control_source_allowlist_exact": True,
            "control_source_manifest_sha256":
                NODE_A_CONTROL_SOURCE_MANIFEST_SHA256,
            "all_42_source_successors_are_exact_commit_delta_blobs": True,
            "all_26_semantic_consumers_are_exact_commit_delta_blobs": True,
            "all_11_predecessor_controls_are_exact_commit_delta_blobs": True,
            "all_72_fixed_sources_are_fixed_by_ti_java_tree_and_manifests": True,
            "delta_partition": {
                "control_path_count": 11,
                "control_added_count": 7,
                "control_modified_count": 4,
                "control_current_total_bytes": CONTROL_CURRENT_TOTAL_BYTES,
                "control_parent_total_bytes": CONTROL_PARENT_TOTAL_BYTES,
                "changed_fixed_path_count": 52,
                "changed_fixed_added_count": 10,
                "changed_fixed_modified_count": 42,
                "changed_fixed_current_total_bytes":
                    CHANGED_FIXED_CURRENT_TOTAL_BYTES,
                "changed_fixed_parent_total_bytes":
                    CHANGED_FIXED_PARENT_TOTAL_BYTES,
                "transition_current_total_bytes": TRANSITION_CURRENT_TOTAL_BYTES,
                "transition_accepted_total_bytes":
                    TRANSITION_ACCEPTED_TOTAL_BYTES,
                "semantic_current_total_bytes": SEMANTIC_CURRENT_TOTAL_BYTES,
                "semantic_accepted_total_bytes": SEMANTIC_ACCEPTED_TOTAL_BYTES,
                "added_fixed_total_bytes": ADDED_FIXED_TOTAL_BYTES,
                "all_fixed_total_bytes": ALL_FIXED_TOTAL_BYTES,
                "unchanged_fixed_path_count": 20,
                "unchanged_fixed_total_bytes": UNCHANGED_FIXED_TOTAL_BYTES,
                "exact_disjoint_partition": True,
                "accepted_parent_and_successor_current_bytes_fixed": True,
            },
            "dynamic_source_discovery_forbidden": True,
            "live_head_or_ref_authority_forbidden": True,
            "source_successor_external_git_anchor_complete": True,
            "semantic_successor_external_git_anchor_complete": True,
            "bootstrap_control_sources_external_git_anchor_complete": True,
        },
        "route_state": {
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "total_operation_count": 611,
            "legacy_flask_remains_production_owner": True,
        },
        "production_and_worm_boundary": {
            "terminal_worm_source": TERMINAL_WORM_RELATIVE,
            "terminal_worm_sha256": TERMINAL_WORM_SHA256,
            "terminal_worm_byte_count": TERMINAL_WORM_BYTE_COUNT,
            "terminal_worm_chain_node_count": 7,
            "java_build_context_sha256": JAVA_BUILD_CONTEXT_SHA256,
            "dockerfile_sha256": DOCKERFILE_SHA256,
            "main_additions": list(MAIN_ADDITIONS),
            "main_addition_count": 3,
            "existing_main_modified_count": 0,
            "existing_main_deleted_count": 0,
            "web_tree_unchanged_from_parent": True,
            "operator_or_apply_entrypoint_added": False,
        },
        "authorization": {
            "migration_global_preflight_evidence_closed": True,
            "source_successor_external_git_anchor_complete": True,
            "semantic_successor_external_git_anchor_complete": True,
            "bootstrap_control_sources_external_git_anchor_complete": True,
            "migration_durable_ledger_freeze_design_evidence_closed": False,
            "migration_design_closed": False,
            "operator_migration_implementation": False,
            "production_schema_or_index": False,
            "real_data_migration_execution": False,
            "route_or_openapi_delta": False,
            "client_gateway_or_proxy_change": False,
            "production_cutover": False,
        },
        "current_node_trust_boundary": {
            "control_sources": list(CURRENT_CONTROL_SOURCES),
            "control_source_count": 6,
            "control_source_allowlist_exact": True,
            "control_sources_excluded_from_self_authority": True,
            "control_sources_external_git_anchor_complete": False,
            "independently_signed_provenance": False,
            "tamper_evident_scope": (
                "fixed_predecessor_commit_tree_delta_blobs_and_node_a_manifests"
            ),
        },
        "acceptance": {
            "checkpoint_changed_path_count": 63,
            "checkpoint_added_count": 17,
            "checkpoint_modified_count": 46,
            "checkpoint_deleted_count": 0,
            "source_successor_path_count": NODE_A_SOURCE_SUCCESSOR_COUNT,
            "semantic_consumer_path_count": NODE_A_SEMANTIC_CONSUMER_COUNT,
            "fixed_source_count": NODE_A_FIXED_SOURCE_COUNT,
            "predecessor_control_source_count": NODE_A_CONTROL_SOURCE_COUNT,
            "current_control_source_count": 6,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
            "migration_design_closed": False,
            "production_cutover": False,
            "next_gate": (
                "durable ledger and freeze/recheck design evidence remains required"
            ),
        },
    }
    document["document_payload_sha256"] = document_payload_sha256(document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ti-java-root", type=Path, default=ROOT)
    parser.add_argument("--repository-root", type=Path, default=ROOT.parent)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-git-replay", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    document = build_contract(
        arguments.ti_java_root,
        repository_root=(None if arguments.skip_git_replay
                         else arguments.repository_root),
    )
    payload = serialized_contract(document)
    if arguments.check:
        if arguments.output.read_bytes() != payload:
            raise AssertionError("Node A post-push anchor contract drifted")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_bytes(payload)
    print(f"Node A post-push anchor passed: {sha256_bytes(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
