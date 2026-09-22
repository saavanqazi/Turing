# Commission Report Reconciliation Audit

Consolidate a month of partner commission lines from five reports that do not
share a format, and reconcile them against the commission recognition policy, the
NetSuite revenue export and the VP exceptions register.

## Task Description

The agent is given `commission_policy.md`, five partner reports
(`partner_a_report.csv` .. `partner_e_report.csv`), `netsuite_revenue_export.csv`
and `commission_exceptions.csv` under `input/`. It must first consolidate the five
reports into one line list of 92 lines, normalising the rate to whole percent and
the end-user label to one of the three types, and then for each line:

1. Compare the reported rate against the rate R1 is read against for that
   end-user type — new 8%, renewal 4%, house 0% — unless an active exception
   displaces it (`RATE_MISMATCH`).
2. Decide whether the line is commissionable, which turns on the standard or
   approved rate being above 0% rather than on the rate the partner reported, and
   if so require a revenue record for the run month `2026-06`
   (`UNMATCHED_TO_LEDGER`).
3. Flag every occurrence of a `deal_id` that appears in more than one source
   report (`DUPLICATE_LINE`).

It writes `commission_findings.csv` (one row per finding), `commission_memo.md`
(the reasoning, including the lines that look wrong and are not) and
`results.json` (five figures).

## Why it is non-trivial

- **Nothing is read off a line directly.** The rate has to be normalised, the
  ledger match has to be joined from a separate export, and whether an exception
  applies has to be derived from its date window against the run month. Each of
  the three rules is a derivation over two sources rather than a column lookup.
- **The five reports disagree on format.** One files the rate as a decimal
  fraction, one as basis points, one with a percent sign; two label the end-user
  type in long form. A solver that compares the printed number against the
  standard rate is wrong on 25 checks.
- A line can be caught by more than one rule, and five of them are.
- Commissionability is defined on the standard or approved rate, not the reported
  one. A house line reported at 0% with no ledger match is out of scope for R2;
  a new line reported at 0% with no ledger match is in scope, because its
  standard rate is 8%, and it carries a rate mismatch as well.
- The ledger export is not a match flag. A deal can have a record in `2026-05`
  and none in the run month, which is not a match; the export also carries records
  for deals no partner reported, which match nothing.
- The exceptions register is not a simple override list, and `status` is not one
  of its columns: whether an exception applies is a date-window test against the
  run month. One window closed on 2026-05-31 and one opens on 2026-07-01, so
  neither displaces the standard rate; one opens mid-run-month and one closes on
  its last day, so both do; one approves the rate that is already standard and
  changes nothing; one makes a house line commissionable at 3%; and one names a
  deal that is in no report at all.
- One deal is reported by three partners rather than two, so a solver that
  flags only the later occurrence is wrong on every duplicate.

## Deliverables

- `commission_findings.csv` — `deal_id,source_report,finding_code`, one row per
  finding, a compliant line appearing not at all
- `commission_memo.md` — the reasoning for each finding, and the lines that look
  underpaid or overpaid against the standard rates but are compliant anyway
- `results.json` — `total_lines`, the three per-code counts, and `compliant_lines`

## Verification

The grader is the frozen verifier engine in `tests/` (`tests/verifier.json`, 294
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
- **Scaled from 8 lines to 92**, with the edge cases above built from the rules
  already in the policy.
- **15 checks to 294**, and the binary reward replaced with the graded one.
- **The inputs were re-cut across six files.** The single pre-consolidated
  `commission_lines.csv`, with the ledger match as a `yes`/`no` column and the
  exception state as a `status` column, was replaced by five partner reports in
  five formats plus a revenue export, after four of four GLM-5.2 rollouts passed
  every check on the pre-consolidated inputs. The four policy rules are unchanged.
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
