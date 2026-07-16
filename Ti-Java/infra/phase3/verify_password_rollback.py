#!/usr/bin/env python3
"""Verify the public Java-generated transition hash with the retained Flask stack."""

import json

from werkzeug.security import check_password_hash


PASSWORD = "PUBLIC-TEST-ONLY-Java-Rollback-密码"
JAVA_GENERATED_HASH = (
    "scrypt:32768:8:1$JavaRollback0001$"
    "852cfabaed211c8db8f333be1d3e83869dc1791e39853b1f00c4a5aa1c267abc"
    "c1c5d81267cc4859e215e6dd9935731ec91472b603b35f94b510f61da3d41e7a"
)


def main() -> None:
    accepted = check_password_hash(JAVA_GENERATED_HASH, PASSWORD)
    rejected_wrong = not check_password_hash(JAVA_GENERATED_HASH, PASSWORD + "-wrong")
    if not accepted or not rejected_wrong:
        raise SystemExit("public Java-to-Flask rollback password vector failed")
    print(json.dumps({
        "classification": "PUBLIC TEST-ONLY",
        "java_generated_target_accepted_by_flask": True,
        "wrong_password_rejected": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
