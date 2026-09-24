#!/usr/bin/env python3
"""Write probe submissions for c239 and grade each one in the task image.

    python3 tools/c239_probes.py <out-dir>

Each probe is a submission the grader must answer a known way: correct answers
written differently must score 1.0, and exploits and single mistakes must not.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "code-c239-queue-backpressure-threshold-audit"
GOLD = TASK / "solution" / "files"
OUT = Path(sys.argv[1]).resolve()

gold_csv = (GOLD / "backpressure_audit.csv").read_text()
gold_memo = (GOLD / "backpressure_memo.md").read_text()
gold_res = json.loads((GOLD / "results.json").read_text())
rows = [l.split(",") for l in gold_csv.splitlines()[1:]]
finding = {r[0]: r[-1] for r in rows}
CODES = ["NO_BACKPRESSURE_CONFIGURED", "BACKPRESSURE_THRESHOLD_EXCEEDED", "DRAIN_TIME_EXCEEDED", "none"]

def csv_of(header, body):
    return ",".join(header) + "\n" + "".join(",".join(map(str, r)) + "\n" for r in body)

probes = {}   # name -> (csv, memo, results, expect_full_pass)
probes["gold"] = (gold_csv, gold_memo, gold_res, True)
# Correct, written differently: finding first, extra notes column, quoted cells,
# CRLF, BOM, no thousands commas, and a memo that orders every fact the other way.
alt_csv = "﻿" + csv_of(['"finding"', '"queue_id"', '"notes"'],
                            [(f'"{f}"', f'"{q}"', '"see memo"') for q, f in finding.items()]).replace("\n", "\r\n")
alt_memo = """Audit notes

Queue Q-02: the critical limit is 1000 messages and it held 1500 with backpressure off, so BACKPRESSURE_THRESHOLD_EXCEEDED.

Queue Q-04 is missing from the config entirely: NO_BACKPRESSURE_CONFIGURED.

Queue Q-05: allowed 60 min to drain, measured 90 min. DRAIN_TIME_EXCEEDED.

Q-03 is above its in-flight limit, but it sits in a scheduled Burst Window, so it is exempt.

Q-06 is above its in-flight limit too; backpressure had engaged already, so nothing to flag.
"""
probes["correct_alt_format"] = (alt_csv, alt_memo, gold_res, True)
# Exploits the mined grader passed.
hack_row = " ".join(CODES)
probes["hack_all_codes_one_cell"] = (csv_of(["queue_id", "finding"], [(q, hack_row) for q in finding]),
                                     gold_memo, gold_res, False)
probes["hack_all_codes_four_cells"] = (csv_of(["queue_id", "finding", "f2", "f3", "f4"], [(q, *CODES) for q in finding]),
                                       gold_memo, gold_res, False)
probes["hack_duplicate_rows"] = (csv_of(["queue_id", "finding"], [(q, c) for q in finding for c in CODES]),
                                 gold_memo, gold_res, False)
probes["hack_stub_memo"] = (gold_csv, "Q-03 burst window\n", gold_res, False)
# Single mistakes each rule can produce.
def with_finding(q, f):
    return csv_of(["queue_id", "finding"], [(k, f if k == q else v) for k, v in finding.items()])
probes["miss_engaged_q06"] = (with_finding("Q-06", "BACKPRESSURE_THRESHOLD_EXCEEDED"), gold_memo,
                              {**gold_res, "flagged_count": 4, "threshold_exceeded_count": 2, "compliant_count": 2}, False)
probes["miss_burst_q03"] = (with_finding("Q-03", "BACKPRESSURE_THRESHOLD_EXCEEDED"), gold_memo,
                            {**gold_res, "flagged_count": 4, "threshold_exceeded_count": 2, "compliant_count": 2}, False)
probes["memo_without_figures"] = (gold_csv, re.sub(r"(?<!Q-)\b\d[\d,]*", "N", gold_memo), gold_res, False)

shutil.rmtree(OUT, ignore_errors=True)
bad = 0
for name, (c, m, r, full) in probes.items():
    d = OUT / name
    d.mkdir(parents=True)
    (d / "backpressure_audit.csv").write_bytes(c.encode("utf-8"))
    (d / "backpressure_memo.md").write_text(m, encoding="utf-8")
    (d / "results.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    out = subprocess.run([str(REPO / "tools" / "oracle_docker.sh"), str(TASK), str(d)],
                         capture_output=True, text=True).stdout
    reward = float(re.search(r"reward: (\S+)", out).group(1))
    failed = re.findall(r"FAILED \S+\[([^\]]+)\]", out)
    ok = (reward == 1.0) == full
    bad += not ok
    print(f"{'ok ' if ok else 'BAD'} {name:28s} reward={reward:.4f}  failed={failed}")
sys.exit(1 if bad else 0)
