#!/usr/bin/env python3
"""Summarise every trial in a Harbor job directory: reward, agent wall time,
exception, per-check pass/fail, and what the agent actually did.

    python tools\trial_summary.py jobs\g308-glm-v6
    python tools\trial_summary.py jobs\g308-glm-v6 --commands 40   # more of the trajectory
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

def secs(t):
    if not t or not t.get("started_at") or not t.get("finished_at"):
        return None
    a = datetime.fromisoformat(t["started_at"]); b = datetime.fromisoformat(t["finished_at"])
    return (b - a).total_seconds()

def commands_from(traj):
    """Pull tool commands out of a trajectory json, whatever shape it takes."""
    out = []
    def walk(x):
        if isinstance(x, dict):
            for k in ("command", "cmd", "input"):
                v = x.get(k)
                if isinstance(v, str) and v.strip():
                    out.append(v); break
                if isinstance(v, dict) and isinstance(v.get("command"), str):
                    out.append(v["command"]); break
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(traj); return out

ap = argparse.ArgumentParser()
ap.add_argument("job_dir"); ap.add_argument("--commands", type=int, default=12)
args = ap.parse_args()
job = Path(args.job_dir)
trials = sorted(p.parent for p in job.rglob("result.json") if p.parent != job)
if not trials:
    sys.exit(f"no trial result.json under {job}")
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
    ctrf = next(iter(t.rglob("ctrf.json")), None)
    if ctrf:
        tests = json.loads(ctrf.read_text(encoding="utf-8"))["results"]["tests"]
        failed = [x["name"] for x in tests if x["status"] != "passed"]
        print(f"  checks {len(tests) - len(failed)} passed / {len(failed)} failed")
        for n in failed[:25]: print(f"     FAIL {n}")
        if len(failed) > 25: print(f"     ... and {len(failed) - 25} more")
    # what the agent did
    traj = next((p for p in t.rglob("*.json") if "traj" in p.name.lower()), None)
    if traj:
        try:
            cmds = commands_from(json.loads(traj.read_text(encoding="utf-8")))
        except Exception as e:
            cmds = []; print(f"  trajectory {traj.relative_to(t)} unreadable: {e}")
        print(f"  trajectory {traj.relative_to(t)}: {len(cmds)} commands")
        n = args.commands
        show = cmds if len(cmds) <= 2 * n else cmds[:n] + ["... "] + cmds[-n:]
        for c in show:
            c = c.strip().replace("\n", " | ")
            print(f"     $ {c[:150]}")
    else:
        logs = [p for p in t.rglob("*") if p.is_file() and p.suffix in (".log", ".txt", ".jsonl")]
        print(f"  no trajectory json; log files: {[str(p.relative_to(t)) for p in logs[:8]]}")
