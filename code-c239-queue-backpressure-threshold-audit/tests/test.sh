#!/bin/bash
# Harbor verifier entrypoint. Harbor copies this to /tests/test.sh and runs it
# from the task working directory; reward is read back from
# /logs/verifier/reward.txt.
#
# Graded reward: passed/(passed+failed); 1.0 when every check passes.
# This replaces the previous binary 1/0 gate, which collapsed any
# partial-credit run to 0.0. Per-check outcomes are unchanged.
mkdir -p /logs/verifier

cd /app || exit 1

# PYTHONSAFEPATH=1 prevents /app from entering sys.path, blocking a shadowing
# pytest.py (or other module) placed in the agent's writable directory.
PYTHONSAFEPATH=1 python3 -m pytest \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_outputs.py \
    -rA 2>&1 | tee /tmp/pytest_summary.txt
status=${PIPESTATUS[0]}

python3 - "$status" <<'PYEOF'
import re, sys
status = int(sys.argv[1])
text = open("/tmp/pytest_summary.txt", encoding="utf-8", errors="replace").read()
passed = 0
failed = 0
m = re.search(r"(\d+)\s+passed", text)
if m:
    passed = int(m.group(1))
m = re.search(r"(\d+)\s+failed", text)
if m:
    failed = int(m.group(1))
total = passed + failed
reward = 0.0 if total == 0 else passed / total
if failed == 0 and status == 0:
    reward = 1.0
with open("/logs/verifier/reward.txt", "w") as f:
    f.write(repr(reward))
PYEOF

exit 0
