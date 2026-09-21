#!/usr/bin/env python3
"""Assemble evaluations/ by mirroring the reference bundle that passed QC.

    uv run --python 3.12 tools/assemble_evaluations.py \
        --task gen-g308-commission-report-reconciliation-audit \
        --difficulty jobs/g308-glm

The reference ships each Harbor job essentially as Harbor wrote it: the four
job-level files sit directly under evaluations/difficulty/, and each trial
folder is copied whole — agent/, artifacts/, verifier/, config.json, lock.json,
result.json, trial.log — renamed r1..r4. One reward-1.0 non-oracle trial is
copied the same way into evaluations/solvability/r1.

That differs from the written guide, which says to drop the job-level files and
to add model/overall_pass/final_answer to each result.json. The reference does
neither and cleared the gate, so it is followed here.

Never point --solvability at an oracle run: an oracle replays the gold, so it
shows the verifier can grade the gold, not that a model can solve the task.
"""
import argparse, hashlib, json, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
JOB_FILES = ("config.json", "lock.json", "job.log", "result.json")

def trials(job: Path):
    return sorted(p for p in job.iterdir() if p.is_dir() and (p / "verifier").is_dir())

def reward(trial: Path) -> float:
    for name, read in (("reward.json", lambda f: json.loads(f.read_text())["reward"]),
                       ("reward.txt",  lambda f: float(f.read_text().strip()))):
        f = trial / "verifier" / name
        if f.exists():
            return float(read(f))
    raise SystemExit(f"no reward file in {trial}")

ap = argparse.ArgumentParser()
ap.add_argument("--task", required=True, help="task folder name, e.g. gen-g308-commission-report-reconciliation-audit")
ap.add_argument("--difficulty", required=True, type=Path, help="job folder holding the 4 GLM rollouts")
ap.add_argument("--solvability", type=Path, help="job folder holding a reward-1.0 non-oracle run")
a = ap.parse_args()

TASK = REPO / a.task
if not (TASK / "task.toml").exists():
    sys.exit(f"no task.toml under {TASK} — is --task right?")

root = TASK / "evaluations"
for sub in ("difficulty", "solvability"):
    shutil.rmtree(root / sub, ignore_errors=True)
root.mkdir(parents=True, exist_ok=True)
(root / ".gitkeep").unlink(missing_ok=True)      # nothing may sit loose under evaluations/

ts = trials(a.difficulty)
if len(ts) < 4:
    sys.exit(f"need 4 trial folders in {a.difficulty}, found {len(ts)}")
if len(ts) > 4:
    print(f"note: {len(ts)} trials present; taking the first four — four runs, not five")

diff = root / "difficulty"; diff.mkdir(parents=True)
for name in JOB_FILES:                            # as the reference ships them
    src = a.difficulty / name
    if src.exists():
        shutil.copy2(src, diff / name)

rewards = []
for i, t in enumerate(ts[:4], 1):
    shutil.copytree(t, diff / f"r{i}")
    rewards.append(reward(t))

src = a.solvability or a.difficulty
win = next((t for t in trials(src) if reward(t) == 1.0), None)
if win:
    (root / "solvability").mkdir(parents=True)
    shutil.copytree(win, root / "solvability" / "r1")
    print(f"solvability/r1  <- {win.name} (reward 1.0)")
    # The gate raises a minor advisory when solvability/ is byte-identical to a
    # difficulty run. It is not an oracle replay either way; show that here.
    traj = root / "solvability" / "r1" / "agent" / "trajectory.json"
    golden = TASK / "solution" / "golden_trajectory.json"
    if traj.exists() and golden.exists():
        h = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
        a_, b_ = h(traj), h(golden)
        print(f"  trajectory sha256 {a_[:16]} vs golden {b_[:16]} — "
              f"{'IDENTICAL, this IS an oracle replay' if a_ == b_ else 'differs, so not an oracle replay'}")
else:
    print("NO reward-1.0 run found — solvability/ needs one from any non-oracle model")

for i, r in enumerate(rewards, 1):
    print(f"  difficulty/r{i}  reward {r}")
passed = sum(1 for r in rewards if r == 1.0)
print(f"{passed} of 4 fully passed —", 
      "REJECTED: 4/4 is too easy" if passed == 4 else
      "IN BAND" if passed in (1, 2, 3) else
      "0/4: submittable, but Turing must re-run on another frontier model")
