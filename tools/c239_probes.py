#!/usr/bin/env python3
"""Grade c239's probe submissions in the task image.

    python3 tools/c239_probes.py <out-dir>

build_task.py --probes writes the submissions from the task's own data, so they
always match the current version. A probe named *_ok must score exactly 1.0 and
every other probe must score below it.
"""
import re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "code-c239-queue-backpressure-threshold-audit"
OUT = Path(sys.argv[1]).resolve()

subprocess.run([sys.executable, str(TASK / "build_task.py"), "--probes", str(OUT)], check=True,
               stdout=subprocess.DEVNULL)
bad = 0
for d in sorted(p for p in OUT.iterdir() if p.is_dir()):
    out = subprocess.run([str(REPO / "tools" / "oracle_docker.sh"), str(TASK), str(d)],
                         capture_output=True, text=True).stdout
    reward = float(re.search(r"reward: (\S+)", out).group(1))
    failed = re.findall(r"FAILED \S+\[([^\]]+)\]", out)
    ok = (reward == 1.0) == d.name.endswith("_ok")
    bad += not ok
    shown = ", ".join(failed[:4]) + (f" … +{len(failed) - 4}" if len(failed) > 4 else "")
    print(f"{'ok ' if ok else 'BAD'} {d.name:36s} reward={reward:.4f}  failed {len(failed):>3}: {shown}")
sys.exit(1 if bad else 0)
