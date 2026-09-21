# Commission Report Reconciliation Audit

Consolidate a month of partner commission lines and reconcile them against the
commission recognition policy, the NetSuite match flag recorded on each line, and
the VP exceptions register.

## Task Description

The agent is given `commission_policy.md`, `commission_lines.csv` and
`commission_exceptions.csv` under `input/`. For each of 91 commission lines it must:

1. Compare the reported rate against the rate R1 is read against for that
   end-user type — new 8%, renewal 4%, house 0% — unless an active exception
   displaces it (`RATE_MISMATCH`).
2. Decide whether the line is commissionable, which turns on the standard or
   approved rate being above 0% rather than on the rate the partner reported, and
   if so require a June NetSuite match (`UNMATCHED_TO_LEDGER`).
3. Flag every occurrence of a `deal_id` that appears in more than one source
   report (`DUPLICATE_LINE`).

It writes `commission_findings.csv` (one row per finding), `commission_memo.md`
(the reasoning, including the lines that look wrong and are not) and
`results.json` (five figures).

## Why it is non-trivial

- A line can be caught by more than one rule, and four of them are.
- Commissionability is defined on the standard or approved rate, not the reported
  one. A house line reported at 0% with no ledger match is out of scope for R2;
  a new line reported at 0% with no ledger match is in scope, because its
  standard rate is 8%, and it carries a rate mismatch as well.
- The exceptions register is not a simple override list. One exception is
  expired and does not displace the standard rate; one approves the rate that is
  already standard and changes nothing; one approves a rate the line does not
  report, so the mismatch is against the approved rate rather than the standard
  one; one makes a house line commissionable at 3%; and one names a deal that is
  not in the line list at all.
- One deal is reported by three partners rather than two, so a solver that
  flags only the later occurrence is wrong on every duplicate.

## Deliverables

- `commission_findings.csv` — `deal_id,source_report,finding_code`, one row per
  finding, a compliant line appearing not at all
- `commission_memo.md` — the reasoning for each finding, and the lines that look
  underpaid or overpaid against the standard rates but are compliant anyway
- `results.json` — `total_lines`, the three per-code counts, and `compliant_lines`

## Verification

The grader is the frozen verifier engine in `tests/` (`tests/verifier.json`, 291
checks). Every line carries one check per finding code, required where the code
applies and forbidden where it does not, so a missed finding and a false positive
are each caught on the line that caused them. The remaining checks are the CSV
header, the five figures, nine memo checks and three existence checks.

The memo checks pin facts, not vocabulary. Each is a single token matched with no
wildcard between anchors: the three finding codes the instruction names, and, for
each of the three lines that disagree with their standard rate and are compliant
anyway, that line and the register entry that makes it so. A memo of stock
reconciliation prose that names no deal and cites no register entry fails all nine.

The reward is **graded**, not binary: `tests/test.sh` writes
`reward = passed / (passed + failed)`, with `1.0` only when every check passes.
A run that misclassifies one line scores 0.9966 rather than collapsing to 0.0,
which is what makes a near-miss legible as a near-miss.

`build_task.py` declares the line list and the exceptions register, implements
the four rules once, and emits every input fixture, all three gold deliverables,
the verifier pins and `solution/golden_trajectory.json` from that single source,
so the gold cannot drift from the data it describes.

## Changes from the mined baseline

- **`compliant_lines` was wrong.** The policy says a line with none of the
  findings is compliant; eight lines carried four findings, so four were
  compliant, and the shipped gold and verifier both said five. A solver reading
  the policy correctly failed. Corrected to follow the policy.
- **Two answer leaks removed.** R4 ended by naming the trap — "flagging it as a
  rate mismatch is the commonest false positive in this audit" — and the
  instruction asked the memo to explain "the line that looks underpaid or
  overpaid and is not", asserting both that such a line exists and that there is
  exactly one. The rules stay; the tip-offs are gone.
- **Two policy sections added.** How a line caught by two rules is reported, and
  what all five figures mean, neither of which the policy said.
- **Scaled from 8 lines to 91**, with the edge cases above built from the rules
  already in the policy.
- **15 checks to 291**, and the binary reward replaced with the graded one.
- **The base image is pinned by digest**, not by the mutable `python:3.12-slim-bookworm`
  tag, so the image the grader runs on cannot drift under the tag.

## Evaluation structure

`evaluations/` holds the standardized evidence in three subfolders and no
`oracle/` folder:

- `solvability/r1/` — a non-oracle GLM-5.2 run at reward 1.0
- `difficulty/r1`..`r4/` — the four scored GLM-5.2 trials
- `stability/` — not shipped; Turing runs it

Measured result: the oracle scores exactly 1.0, and the four-run GLM-5.2 battery
returned 1.0, 0.9965034965034965, 0.9965034965034965 and 0.9965034965034965 —
**1 of 4 fully passing**, inside the accepted band and under the stated target of
at most 2. Zero exceptions.

The three failing runs share one reward, and it is the value a solver scores when
it reads commissionability off the reported rate instead of the standard or
approved one, missing DEAL-075. Classified MODEL: one run made that inference
correctly and three did not, on identical data.
