# Task

Consolidate this month's commission lines from the five partner reports in `input/`, which do not share a format and state no end-user type, and reconcile them against the commission recognition policy, the NetSuite revenue export and the VP approvals thread. Save `commission_findings.csv` with the columns `deal_id,source_report,finding_code`, one row per finding, where `finding_code` is one of `RATE_MISMATCH`, `UNMATCHED_TO_LEDGER` or `DUPLICATE_LINE`. Then write `commission_memo.md` explaining each finding, and any line that looks underpaid or overpaid against the standard rates but is compliant anyway, with the rule that makes it so.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `commission_findings.csv` — One row per commission line finding
    - `commission_memo.md` — Markdown reconciliation memo
    - `results.json` — a JSON object with the keys `total_lines`, `rate_mismatch_count`, `unmatched_to_ledger_count`, `duplicate_line_count`, `compliant_lines`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
