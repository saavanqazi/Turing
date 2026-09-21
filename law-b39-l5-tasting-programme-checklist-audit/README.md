# Tasting-programme checklist audit

This task audits 55 checklist mentions representing 39 distinct checklist items.
Solvers must reconcile the mention export, the structured tasting contexts, the
citation manifest, the district control totals, a dated source register and the
audit policy, then deliver a distinct-item register and seven summary figures.

## What was measured, and what each measurement changed

The mined bundle was a sixteen-item lookup with a prose deliverable. GLM-5.2
passed it 5 of 5. Every round since has been driven by a battery result rather
than a guess, and three of the four told us something we had wrong.

**Removing the shortcuts** — the subject tags that made the document lookup a
string join, the signposted conflict, three protocol giveaways. Still 5 of 5,
and *faster*: 15m54s to 9m39s. The model had never leaned on any of it.

**Adding conditionals** — four sections turning on who staffed the table. Still
5 of 5, though runtime tripled. Difficulty had landed; degradation had not.
Independent obligations do not compound: a solver writes one rule per
obligation and handles N of them as N easy checks.

**Rebuilding as a dependency chain** — 51 mentions deduplicating to 35 items,
each resolved against a dated register that supersedes itself, the holding then
applied to recorded facts. That battery read 0 of 4, but the per-verifier detail
showed every run passing the table — all 105 graded cells, four times — and
failing one figure. `distinct_governing_section_count` was undefined: the
protocol described the table and never the figures, so whether `NONE` counted
was a guess. An ambiguity, not difficulty. It was defined rather than kept.

**Defining the figures** — 4 of 4. Which settled what the chain is worth on its
own against GLM-5.2: nothing. The audit was right every time.

**Making the audit a comparison** — each item asserts one of thirty opposed
positions in its own words, and the status is whether the governing holding, on
the item's facts, gives that position or its opposite. First battery read 0 of 4,
and again the detail showed a defect rather than difficulty: the superseded-record
trap, the unsupported count, the dedup and every join passed, and only the
supported/contradicted split failed, identically in all four runs. Half the items
had been written as statements of conduct rather than positions on what the
register requires, and comparing conduct with a holding is undefined.

**Rewriting the items as legal positions** — 3 of 4, oracle 1.0. In band.

## Why the task is hard

The difficulty is not the chain. It is that each item asserts a position in its
own words, and the audit is a comparison between that assertion and the position
the governing holding gives on the item's recorded facts.

    55 mention rows  ->  deduplicate to 39 items (mention_count is graded)
      ->  district, subject and event date
      ->  the most recent record in force ON OR BEFORE that date
      ->  the position that record's holding gives on this item's facts
      ->  compared with the position the item asserts
      ->  SUPPORTED / CONTRADICTED / UNSUPPORTED

An item reading "Our people at the table work under the brand's permit and need
nothing of their own" asserts `covered_by_holder`. Whether that is supported
depends on which record was in force on its date, and on whether the servers
were the permit holder's employees. Items that assert the register is silent
invert: they are `SUPPORTED` where nothing governs and `CONTRADICTED` where
something does.

No context column name appears anywhere in the register — asserted at build time.
A holding says "unless every person serving is an employee of the permit holder";
which recorded fact that turns on is the solver's to work out.

## Provenance

`build_task.py` declares the register, the contexts and the mention export,
implements the policy once, and emits every input fixture, both gold deliverables,
the verifier pins and the golden trajectory from that single source. Gold is
computed from the fixtures rather than written beside them. Re-run it after any
change, then re-run the oracle.

## Deliverables and grading

`checklist_audit.csv` and `results.json`. There is no prose deliverable: the
earlier version graded one with a regex, which is how a reward-hacking finding
arrived and how a later over-strict fix zeroed two correct runs. Thirteen
verifiers, all core, no LLM judge.

## QC findings

- **QC1-1 / D27** — the Dockerfile pulled `python:3.12-slim-bookworm` by mutable
  tag; repinned to the registry's multi-arch index digest.
- **QC1-2 / D1** — the prose deliverable was graded by a length-only regex. The
  deliverable is gone, so the finding cannot recur.

## Measured

Oracle: reward exactly 1.0, repeated, all thirteen verifiers.

GLM-5.2, four runs under terminus-2: **1.0, 1.0, 1.0, 0.0 — 3 of 4 fully
passing**, inside the accepted band.

The failing run is a MODEL failure. It passed the header, the superseded-record
trap row, both existence checks, `mention_count`, both distinct counts and the
citation figure, and failed only `register_table` with `supported_count` and
`contradicted_count` — the comparison step — while the other three runs got that
same comparison right. An ambiguity fails all four runs the same way, which is
what the preceding battery did; one run in four erring is the model.

No `stability/` is shipped — Turing runs it — and no `platform/`, which the gate
does not yet accept (R17).
