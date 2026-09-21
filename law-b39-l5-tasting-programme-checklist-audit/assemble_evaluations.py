#!/usr/bin/env python3
"""Assemble evaluations/ from Harbor job folders, to the delivery spec.

    python assemble_evaluations.py --difficulty jobs/glm-h3 [--solvability jobs/glm-h3]

Copies four GLM trial folders into evaluations/difficulty/r1..r4 and one
reward-1.0 non-oracle run into evaluations/solvability/r1, keeping each trial
folder nested. Drops job-level files the gate rejects, and fills the fields
Harbor does not write (model, overall_pass, final_answer).

Never point --solvability at an oracle run: an oracle replays the gold, so it
proves the verifier can grade the gold, not that a model can solve the task.
"""
import argparse, json, shutil, sys
from pathlib import Path

JOB_LEVEL = {"config.json", "lock.json", "job.log", "result.json"}     # job root only
KEEP_DIFF  = ["agent/trajectory.json", "result.json", "verifier/reward.json",
              "verifier/verifier_summary.json", "config.json"]
KEEP_SOLV  = ["agent/trajectory.json", "result.json", "verifier/reward.json"]

def trials(job: Path):
    """Trial folders are the job's subdirectories that carry a verifier/."""
    return sorted(p for p in job.iterdir() if p.is_dir() and (p / "verifier").is_dir())

def reward(trial: Path) -> float:
    f = trial / "verifier" / "reward.json"
    if f.exists():
        return float(json.loads(f.read_text())["reward"])
    return float((trial / "verifier" / "reward.txt").read_text().strip())

def final_answer(trial: Path):
    ws = trial / "artifacts"
    out = {}
    for name in ("results.json", "checklist_audit.csv", "answer.md"):
        for hit in ws.rglob(name):
            out[name] = hit.read_text(encoding="utf-8", errors="replace")[:20000]
            break
    return out or None

def place(trial: Path, dest: Path, keep, model: str):
    dest.mkdir(parents=True, exist_ok=True)
    for rel in keep:
        src = trial / rel
        if src.exists():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / rel)
    r = reward(trial)
    res = json.loads((trial / "result.json").read_text()) if (trial / "result.json").exists() else {}
    res.update({"model": model, "overall_pass": r == 1.0, "reward": r,
                "final_answer": final_answer(trial)})
    res.setdefault("judge", {"judge_model": None, "note": "deterministic verifier; no LLM judge"})
    (dest / "result.json").write_text(json.dumps(res, indent=2) + "\n")
    return r

ap = argparse.ArgumentParser()
ap.add_argument("--difficulty", required=True, type=Path, help="job folder with the 4 GLM rollouts")
ap.add_argument("--solvability", type=Path, help="job folder holding a reward-1.0 non-oracle run")
ap.add_argument("--model", default="GLM-5.2")
a = ap.parse_args()

root = Path(__file__).resolve().parent / "evaluations"
for sub in ("difficulty", "solvability"):
    shutil.rmtree(root / sub, ignore_errors=True)

ts = trials(a.difficulty)
if len(ts) < 4:
    sys.exit(f"need 4 trial folders in {a.difficulty}, found {len(ts)}")
if len(ts) > 4:
    print(f"note: {len(ts)} trials found; using the first four (four runs, not five)")
rewards = [place(t, root / "difficulty" / f"r{i}", KEEP_DIFF, a.model)
           for i, t in enumerate(ts[:4], 1)]

src = a.solvability or a.difficulty
win = next((t for t in trials(src) if reward(t) == 1.0), None)
if win:
    place(win, root / "solvability" / "r1", KEEP_SOLV, a.model)
    print(f"solvability/r1  <- {win.name} (reward 1.0)")
else:
    print("NO reward-1.0 run found for solvability/ — supply one from another model")

passed = sum(1 for r in rewards if r == 1.0)
print("difficulty rewards:", ", ".join(f"r{i}={r}" for i, r in enumerate(rewards, 1)))
print(f"{passed} of 4 fully passed", end="  ")
print("REJECTED: 4/4 is too easy" if passed == 4 else
      "IN BAND" if passed in (1, 2, 3) else
      "0/4 — submittable, but Turing must re-run on another frontier model")
