# Task

After last week's backlog incident I need the broker snapshot taken at 01:50 UTC on the 17th audited against our backpressure policy, PLAT-31. The backpressure config and the BATCH-7 batch schedule are attached alongside it. Each queue in the snapshot gets exactly one finding under the policy: `NO_BACKPRESSURE_CONFIGURED`, `BACKPRESSURE_THRESHOLD_EXCEEDED`, `DRAIN_TIME_EXCEEDED` or `none`.

Save `backpressure_audit.csv` with one row per queue, including a `queue_id` column and a `finding` column. Then write `backpressure_memo.md` for the platform leads explaining each finding: for a threshold or drain finding, give the figure that tripped it and the limit it was measured against, and for any queue over its threshold that still comes out `none`, say what clears it. Finally, put the policy's audit figures in `results.json`.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `backpressure_audit.csv` — Per-queue backpressure audit
    - `backpressure_memo.md` — Markdown backpressure memo
    - `results.json` — a JSON object with the keys `flagged_count`, `threshold_exceeded_count`, `no_config_count`, `drain_exceeded_count`, `compliant_count`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
