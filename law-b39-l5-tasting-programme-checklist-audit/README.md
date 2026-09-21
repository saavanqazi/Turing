# Tasting-programme checklist audit

This task audits 51 checklist mentions representing 35 distinct checklist items.
Solvers must reconcile the mention export, the structured tasting contexts, the
citation manifest, the district control totals, a dated source register and the
audit policy, then deliver a distinct-item register and eight summary figures.

## Rebuilt from the mined baseline

The mined bundle was a sixteen-item lookup with a prose deliverable, and GLM-5.2
passed it 5 of 5. Three rounds of hardening in place — removing the subject tags
that made the document lookup a string join, adding conditional sections, then
coupling two verdicts to a schedule file — moved the rate not at all for the
first two rounds, and the third was never measured cleanly because a verifier
defect of ours zeroed two correct runs.

The diagnosis those rounds produced is why the task was rebuilt rather than
patched again: difficulty from independent per-item obligations does not
compound. A solver writes one rule per obligation and handles N of them as N
easy checks. What compounds is a dependency chain, where a later step cannot be
taken until an earlier one has been derived correctly.

## Why the task is hard

Nothing here is decided by a single lookup. Each item's status is the end of a
chain, and every link can be got wrong on its own:

    51 mention rows  ->  deduplicate to 35 items (mention_count is graded)
      ->  the item's district, subject and event date
      ->  the most recent register record in force ON OR BEFORE that date
      ->  that record's holding
      ->  applied to the facts recorded in the item's context row
      ->  REQUIRED / NOT_REQUIRED / UNADDRESSED

`corrected_citation_count` cannot be computed until the governing section is
resolved, and `distinct_item_count` cannot be computed before deduplication.

The register is dated and supersedes itself, so the same district and subject
gives different answers on different dates. Records exist that never govern any
item because they took effect after every event. A regulation record and a guide
record take effect on the same day on the same point, and the regulation governs.
Some items sit in a district where the record on their subject exists only for a
different district, so nothing governs them at all.

The register states its holdings as the records state them. A holding says
"unless every person serving is an employee of the permit holder", not the name of
a column; which recorded fact it turns on is the solver's to work out. No context
column name appears anywhere in the register.

Measured against the gold: treating the register as undated and taking the newest
record changes 10 of the 35 rows; applying holdings without reading the context
changes 5.

## Provenance

`build_task.py` declares the register, the contexts and the mention export,
implements the audit policy once, and emits every input fixture, both gold
deliverables and the verifier pins from that single source. The gold is computed
from the fixtures rather than written beside them, so the two cannot drift. Re-run
it after any change to the data, then re-run the oracle.

## Deliverables and grading

`checklist_audit.csv` and `results.json`. There is no prose deliverable: the
previous version graded one with a regex, which is how both a reward-hacking
finding and a later over-strict fix arrived, and neither belongs in a
deterministic task.

Fourteen verifiers, all core, no LLM judge. Each of the eight figures carries its
own check, plus the table, a trap row on the superseded-record item, the header,
the key set and the two existence checks.

## QC findings carried forward

- **QC1-1 / D27** — the Dockerfile pulled `python:3.12-slim-bookworm` by mutable
  tag; repinned to the registry's multi-arch index digest.
- **QC1-2 / D1** — the prose deliverable was graded by a length-only regex. The
  deliverable is gone, so the finding cannot recur.

## Measured

The first battery on this structure returned 0 of 4, and the per-verifier detail
showed why: every run passed the table — all 105 graded cells, four times over —
and every figure but one. `distinct_governing_section_count` failed in all four,
because the protocol defined the table but never defined the figures, so whether
`NONE` counted was a guess. That is an ambiguity, not difficulty, and it was
fixed rather than kept: section 7 now defines all eight figures.

The same result showed the chain alone does not trouble GLM-5.2, so the holdings
were rewritten to name facts in the records' own language rather than naming the
context columns, which is where the sibling bundle's difficulty actually lives.

## Open

`evaluations/` is empty pending the oracle run and the four-run GLM battery on
this rebuild. No `stability/` is shipped — Turing runs it — and no `platform/`,
which the gate does not yet accept.
