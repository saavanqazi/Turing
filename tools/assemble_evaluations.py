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
import argparse, hashlib, json, shutil, sys, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
JOB_FILES = ("config.json", "lock.json", "job.log", "result.json")

def trials(job: Path):
    """Every trial Harbor wrote, including one that errored before verification."""
    return sorted(p for p in job.iterdir() if p.is_dir() and (p / "result.json").exists())

def reward(trial: Path):
    """The verifier's reward, or None when the trial never reached the verifier."""
    for name, read in (("reward.json", lambda f: json.loads(f.read_text())["reward"]),
                       ("reward.txt",  lambda f: float(f.read_text().strip()))):
        f = trial / "verifier" / name
        if f.exists():
            return float(read(f))
    return None

def exception_of(trial: Path):
    info = json.loads((trial / "result.json").read_text(encoding="utf-8")).get("exception_info")
    return info and info.get("exception_type")

ap = argparse.ArgumentParser()
ap.add_argument("--task", required=True, help="task folder name, e.g. gen-g308-commission-report-reconciliation-audit")
ap.add_argument("--difficulty", required=True, type=Path, nargs="+",
                help="job folder(s) holding the GLM rollouts; trials are taken in the order given")
ap.add_argument("--exclude", nargs="*", default=[],
                help="trial names (or unique parts of them) to leave out, e.g. a run that never "
                     "reached the verifier because of infrastructure; each exclusion is reported")
ap.add_argument("--solvability", type=Path, help="job folder holding a reward-1.0 non-oracle run")
ap.add_argument("--zip", action="store_true", help="also write <task>.zip beside the task folder")
ap.add_argument("--allow-unscored", action="store_true",
                help="assemble even if one of the four trials never reached the verifier "
                     "(normally refused: such a run is infrastructure, not a result)")
a = ap.parse_args()

TASK = REPO / a.task
if not (TASK / "task.toml").exists():
    sys.exit(f"no task.toml under {TASK} — is --task right?")


ts, left_out = [], []
for job in a.difficulty:
    for t in trials(job):
        (left_out if any(x in t.name for x in a.exclude) else ts).append(t)
for x in a.exclude:
    if not any(x in t.name for t in left_out):
        sys.exit(f"--exclude {x!r} matched no trial")
for t in left_out:
    print(f"excluded {t.parent.name}/{t.name}  reward {reward(t)}  ({exception_of(t) or 'no exception'})")
if len(ts) < 4:
    sys.exit(f"need 4 trial folders across {[str(j) for j in a.difficulty]}, found {len(ts)}")
unscored = [t for t in ts[:4] if reward(t) is None]
if unscored and not a.allow_unscored:
    for t in unscored:
        print(f"REFUSED: {t.parent.name}/{t.name} never reached the verifier "
              f"({exception_of(t) or 'no reward file'}).")
    sys.exit("Nothing written. Re-run a replacement trial and pass its job folder instead, "
             "or --exclude this one; --allow-unscored overrides.")
if len(ts) > 4:
    print(f"note: {len(ts)} trials present; taking the first four — four runs, not five")

root = TASK / "evaluations"
for sub in ("difficulty", "solvability"):
    shutil.rmtree(root / sub, ignore_errors=True)
root.mkdir(parents=True, exist_ok=True)
(root / ".gitkeep").unlink(missing_ok=True)      # nothing may sit loose under evaluations/
diff = root / "difficulty"; diff.mkdir(parents=True)
for name in JOB_FILES:                            # as the reference ships them
    src = a.difficulty[0] / name
    if src.exists():
        shutil.copy2(src, diff / name)

rewards = []
for i, t in enumerate(ts[:4], 1):
    shutil.copytree(t, diff / f"r{i}")
    rewards.append(reward(t))

src = a.solvability or a.difficulty[0]
# A clean 1.0 first; a 1.0 that Harbor also marked with an exception (a run that
# wrote its files and then hit the agent timeout) only if nothing cleaner exists.
cands = [t for t in trials(src) if reward(t) == 1.0]
win = next((t for t in cands if not exception_of(t)), cands[0] if cands else None)
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

for i, (t, r) in enumerate(zip(ts[:4], rewards), 1):
    exc = exception_of(t)
    print(f"  difficulty/r{i}  reward {r}" + (f"   ({exc})" if exc else "") + f"   <- {t.name}")
passed = sum(1 for r in rewards if r == 1.0)
completed = sum(1 for r in rewards if r is not None)
print(f"{passed} of 4 fully passed ({completed} reached the verifier) —",
      "REJECTED: 4/4 is too easy" if passed == 4 else
      "IN BAND" if passed in (1, 2, 3) else
      "0/4: submittable, but Turing must re-run on another frontier model")
if completed < 4:
    print(f"  {4 - completed} trial(s) never reached the verifier; say so in review.csv rather than counting them as fails")

if a.zip:
    out = REPO / f"{a.task}.zip"
    skip = {"__pycache__", ".pytest_cache", ".gitkeep"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(TASK.rglob("*")):
            if f.is_file() and not (set(f.relative_to(TASK).parts) & skip):
                z.write(f, Path(a.task) / f.relative_to(TASK))
    print(f"zip: {out}  ({out.stat().st_size // 1024} KB, top-level folder {a.task}/)")
