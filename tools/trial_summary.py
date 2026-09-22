#!/usr/bin/env python3
r"""Summarise every trial in a Harbor job directory: reward, agent wall time,
exception, per-check outcomes from the verifier's stdout, and what the agent
did, read from the ATIF trajectory that Terminus writes.

    uv run --no-project tools\trial_summary.py jobs\g308-glm-v6
    uv run --no-project tools\trial_summary.py jobs\g308-glm-v6 --trial LXumUbD --full
"""
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

def secs(t):
    if not t or not t.get("started_at") or not t.get("finished_at"):
        return None
    a = datetime.fromisoformat(t["started_at"]); b = datetime.fromisoformat(t["finished_at"])
    return (b - a).total_seconds()

def check_outcomes(trial):
    """pytest -rA prints one PASSED/FAILED line per parametrised check."""
    f = trial / "verifier" / "test-stdout.txt"
    if not f.exists():
        return None, []
    text = f.read_text(encoding="utf-8", errors="replace")
    passed = len(re.findall(r"^PASSED .*test_deliverable\[", text, re.M))
    failed = re.findall(r"^FAILED .*test_deliverable\[([^\]]+)\]", text, re.M)
    return passed, failed

def text_of(msg):
    if isinstance(msg, str):
        return msg
    return " ".join(p.get("text", "") for p in msg if isinstance(p, dict))

def trajectory(trial):
    f = trial / "agent" / "trajectory.json"
    if not f.exists():
        return []
    steps = json.loads(f.read_text(encoding="utf-8")).get("steps", [])
    out = []
    for s in steps:
        keys = [tc.get("arguments", {}).get("keystrokes", "")
                for tc in (s.get("tool_calls") or []) if isinstance(tc, dict)]
        out.append((s.get("source"), text_of(s.get("message", "")), keys))
    return out

def short(s, n):
    s = s.strip().replace("\n", " | ")
    return s if len(s) <= n else s[:n] + " ..."

ap = argparse.ArgumentParser()
ap.add_argument("job_dir")
ap.add_argument("--trial", help="only trials whose name contains this")
ap.add_argument("--full", action="store_true", help="print every agent step, not a head and tail")
ap.add_argument("--n", type=int, default=8, help="steps to show at each end when not --full")
args = ap.parse_args()
job = Path(args.job_dir)
trials = sorted(p.parent for p in job.rglob("result.json") if p.parent != job)
if args.trial:
    trials = [t for t in trials if args.trial in t.name]
if not trials:
    sys.exit(f"no trials under {job}")
for t in trials:
    r = json.loads((t / "result.json").read_text(encoding="utf-8"))
    v = r.get("verifier_result") or {}
    reward = v.get("reward")
    if reward is None and isinstance(v.get("rewards"), dict):
        reward = v["rewards"].get("reward")
    exc = (r.get("exception_info") or {}).get("exception_type")
    agent_s = secs(r.get("agent_execution"))
    print("=" * 78)
    print(f"{t.name}")
    print(f"  reward {reward}   agent {agent_s and round(agent_s/60,1)} min   exception {exc}")
    passed, failed = check_outcomes(t)
    if passed is None:
        print("  no verifier/test-stdout.txt")
    else:
        print(f"  checks {passed} passed / {len(failed)} failed")
        for n in failed[:40]: print(f"     FAIL {n}")
        if len(failed) > 40: print(f"     ... and {len(failed) - 40} more")
    steps = trajectory(t)
    agent_steps = [(i, m, k) for i, (src, m, k) in enumerate(steps) if src == "agent"]
    ncmd = sum(len(k) for _, _, k in agent_steps)
    print(f"  trajectory: {len(steps)} steps, {len(agent_steps)} agent turns, {ncmd} commands")
    if args.full or len(agent_steps) <= 2 * args.n:
        show = agent_steps
    else:
        show = agent_steps[:args.n] + [None] + agent_steps[-args.n:]
    for item in show:
        if item is None:
            print("     ..."); continue
        i, m, keys = item
        if m.strip():
            print(f"  [{i}] {short(m, 400 if args.full else 220)}")
        for k in keys:
            print(f"        $ {short(k, 300 if args.full else 160)}")
