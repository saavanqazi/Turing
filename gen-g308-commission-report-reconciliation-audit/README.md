# Commission Report Reconciliation Audit

Consolidate a month of partner commission lines from five reports that do not
share a format, and reconcile them against the commission recognition policy, the
NetSuite revenue export and the VP approvals thread.

## Task Description

The agent is given `commission_policy.md`, five partner reports
(`partner_a_report.csv` .. `partner_e_report.csv`), `netsuite_revenue_export.csv`
and `vp_approvals.md` under `input/`. It must first consolidate the five
reports into one line list of 97 lines, normalising the rate to whole percent and
reading each line's end-user type from its deal description under the policy's
definitions, and then for each line:

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

- **The end-user type is a judgement, not a column.** No report states it. Each
  line carries the partner's own description of the deal, and the policy defines
  house, new and renewal in three clauses with a precedence rule. About a quarter
  of the 97 descriptions are written so the obvious word points the wrong way:
  an "upsell" on a live contract is a renewal, a "win-back" after a lapse is new,
  "the partner handled the renewal admin" on an account our team sourced is
  house. Every one has exactly one answer under the definition and none by
  keyword, and the type sits upstream of the rate, of commissionability and so
  of the ledger test, so a misread cascades.
- **Nothing is read off a line directly.** The rate has to be normalised, the
  ledger match has to be joined from a separate export, and whether an exception
  applies has to be derived from its date window against the run month. Each of
  the three rules is a derivation over two sources rather than a column lookup.
- **The five reports disagree on format.** One files the rate as a decimal
  fraction, one as basis points, one with a percent sign; two label the end-user
  type in long form. A solver that compares the printed number against the
  standard rate is wrong on 26 checks.
- **The data is not clean.** Two reports close with a `TOTAL` line that names no
  deal. Eight lines are filed under a deal id that is lower case, space-padded or
  both, and two of the four duplicated deals are duplicated only across a
  spelling, so a solver that joins on the raw string never sees them and its
  ledger join misses as well.
- **The export nets.** Amounts are written `$50,000`, and a reversal is written
  `($50,000)`. One deal's run month recognises revenue and then takes all of it
  back, leaving a net of zero, which is not a match; another is reversed in part
  and is still matched. Counting records rather than netting them is wrong in
  both directions.
- A line can be caught by more than one rule, and five of them are.
- Commissionability is defined on the standard or approved rate, not the reported
  one. A house line reported at 0% with no ledger match is out of scope for R2;
  a new line reported at 0% with no ledger match is in scope, because its
  standard rate is 8%, and it carries a rate mismatch as well.
- The ledger export is not a match flag. A deal can have a record in `2026-05`
  and none in the run month, which is not a match; the export also carries records
  for deals no partner reported, which match nothing.
- **Approvals are a thread, not a register.** Seventeen messages in date order,
  and which rate is in force for June is the reading of the thread. One message
  corrects an earlier one's rate rather than replacing the approval; one lapses
  an approval at the end of May; one withdraws an approval in full four days
  after it issued; one approves from 1 July, after this run; two are conditional
  on what the run month recognises for the deal, and the condition holds for one
  and fails for the other; two grant nothing at all, and one of those names a
  deal without approving a rate on it. Each misreading costs three checks and so
  costs the full pass.
- One deal is reported by three partners rather than two, so a solver that
  flags only the later occurrence is wrong on every duplicate.

## Deliverables

- `commission_findings.csv` — `deal_id,source_report,finding_code`, one row per
  finding, a compliant line appearing not at all
- `commission_memo.md` — the reasoning for each finding, and the lines that look
  underpaid or overpaid against the standard rates but are compliant anyway
- `results.json` — `total_lines`, the three per-code counts, and `compliant_lines`

## Verification

The grader is the frozen verifier engine in `tests/` (`tests/verifier.json`, 365
checks). Every line carries one check per finding code, required where the code
applies and forbidden where it does not, so a missed finding and a false positive
are each caught on the line that caused them. The remaining checks are the CSV
header, the five figures, nine memo checks and three existence checks.

The memo checks pin facts, not vocabulary. Each is a single token matched with no
wildcard between anchors: the three finding codes the instruction names, and, for
each of the three lines that disagree with their standard rate and are compliant
anyway, that line and the register entry that makes it so. A memo of stock
reconciliation prose that names no deal and cites no register entry fails all nine.
For each rate-mismatch deal, the reported rate and the applicable rate must each
appear within 400 characters of the deal id, either order, with no other deal id in
between: an explanation of a rate mismatch states both rates, and a memo that names
every deal but explains nothing fails all thirty of those.

The reward is **graded**, not binary: `tests/test.sh` writes
`reward = passed / (passed + failed)`, with `1.0` only when every check passes.
A run that misclassifies one line scores 0.9966 rather than collapsing to 0.0,
which is what makes a near-miss legible as a near-miss.

`build_task.py` declares the line list, the ledger and the approvals thread, implements
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
- **Scaled from 8 lines to 97**, with the edge cases above built from the rules
  already in the policy.
- **15 checks to 365**, and the binary reward replaced with the graded one.
- **The inputs were re-cut across six files.** The single pre-consolidated
  `commission_lines.csv`, with the ledger match as a `yes`/`no` column and the
  exception state as a `status` column, was replaced by five partner reports in
  five formats plus a revenue export, after four of four GLM-5.2 rollouts passed
  every check on the pre-consolidated inputs. When four of four passed that too,
  the irregularities above were added: totals lines, deal ids filed in three
  spellings, and a revenue export that has to be netted. That was four of four
  as well, at 21 minutes a battery against 13 - the task had become longer, not
  harder, because every rule was one a solver could implement from a precise
  statement and run. The exceptions register was then replaced by the approvals
  thread, moving the facts out of columns and into prose that has to be read in
  order. That was four of four as well: the thread's reading rules were stated
  precisely in R4, so reading became mechanical too. The end-user type column
  was then removed from every report and replaced by a deal description, which
  is the one determination in the task that cannot be reduced to a stated
  algorithm; it is the same mechanism that lands the sibling b39 bundle in band.
  The four policy rules are unchanged throughout, and R0, R2 and R4 state every
  convention, so nothing rests on noticing something the policy does not say.
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
