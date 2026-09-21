# law-b39-l5-tasting-programme-checklist-audit — change summary

A marketing agency's tasting-compliance checklist was drafted from a trade
association's guide instead of the regulation. The agent audits all sixteen
items against the regulation, the guide and this season's schedule, and delivers
`answer.md`, `checklist_audit.csv` and `results.json`.

## What changed from the mined baseline, and why

The bundle arrived working and too easy: GLM-5.2 passed **5/5**, with every
individual reward exactly 1.0. Three rounds of hardening followed.

**Round 1 — remove the shortcuts.** Every section header carried the
checklist's own `subject` key (`## BR-202 \`agency_staff_solicitor_permit\``),
so matching an item to its governing section was a string join, not a read.
Removed from all 22 headers and both preambles. Also removed the guide's
"a subject with no note here is one the guide does not address", AG-302's
"this has been the practice for years" (which pointed straight at the single
live conflict), and three protocol giveaways — TP-702's explicit
phantom-citation hint and TP-703's worked restatement.

Result: still 5/5, and *faster* — 15m54s to 9m39s. The model had never been
leaning on any of it.

**Round 2 — add conditionals.** Made BR-205, BR-206, BR-208 and AG-307 turn on
who staffs the table, and dropped the `subject` column from the checklist.
Gold moved 9/4/3/7 to 11/2/3/7.

Result: still 5/5, but runtime tripled to 28m48s. Difficulty had landed;
degradation had not. That is the useful finding of the whole exercise: the
four conditionals were *independent*, and independent obligations do not
compound — each one is a separate easy check.

**Round 3 — couple them.** This round makes correctness depend on
interactions rather than on more rules.

A new fixture, `environment/input/tasting_schedule.csv`, records what actually
ran: nine events, each with a store id, a store name, a date, who staffed the
table, and whether that store holds a tasting permit of its own. Two regulation
sections now resolve against it:

- **BR-205** requires the owner's written consent wherever *any* store lacks
  its own permit. Oakfield Bottle Shop does. The rule is in the regulation, the
  deciding fact is in the CSV, and neither is sufficient alone.
- **BR-209** covers up to five stores under one permit. The verdict cannot be
  reached until a count has been **derived from the data**.

That count is the trap. Three derivations are plausible and only one is right:

| derivation | count | verdict |
|---|---|---|
| schedule rows | 9 | more than five → REQUIRED — wrong |
| distinct store *names* | 6 | more than five → REQUIRED — wrong |
| distinct store *ids* | 5 | not more than five → NOT_REQUIRED — **right** |

Harbour Wine & Spirits appears twice with an ampersand and once spelled "and"
under one id; Kingsway Cellars and Kingsway Cellar are two different premises
with two ids. Deduplicating on the wrong column merges the second pair or
splits the first — and both mistakes land on the *same* wrong verdict as not
deduplicating at all, so a careless route is never rescued by luck.

`instruction.md` names the schedule and says some of the regulation turns on it.
It does not say which parts, or how.

Gold is now **12 required / 1 not required / 3 unaddressed / 6 draft-wrong**.

## Why the task is hard

Not because there are many rules — that was round 2, and it failed. Because
several verdicts cannot be reached from any single source. The governing
section comes from the regulation, the fact that decides it from a CSV, and one
of them needs a figure derived from that CSV **before** the rule can be applied,
against data shaped so that the obvious derivations are wrong.

The original trap survives underneath: the guide (AG-302) says agency staff need
no permit, the regulation (BR-202) requires one, and the regulation governs.
Three items cite sections that do not exist and are UNADDRESSED.

## QC findings

Both deterministic Delivery Gate findings are fixed:

- **QC1-1 / D27** — `environment/Dockerfile` pulled `python:3.12-slim-bookworm`
  by mutable tag. Repinned to the registry's multi-arch index digest.
- **QC1-2 / D1** — `answer_prose_floor` graded `answer.md` with a length-only
  quantifier, so a keyword-stuffed stub scored. Replaced with the same
  sixty-word floor plus key-fact set-membership. A 60-word filler stub that
  matched the old pattern now scores 0.0; gold still scores 1.0. Written as
  set-membership rather than an LLM rubric so grading stays judge-free.

`solution/golden_trajectory.json` was found embedding a superseded gold in its
write-steps; it is now rebuilt from `solution/files/` and asserted identical, so
the trajectory cannot drift from what `solve.sh` delivers.

The stale `consistency/` artifacts were removed: they carried a `revision_key`
describing the pre-hardening fixtures and no longer described this package.

## Left unfixed

**Layer 2 Difficulty is open.** As shipped, after round 1 and after round 2, the
battery read 5/5 every time — 4/4 after dropping a run, which is rejected. Round
3 is the first attempt built on coupling rather than accumulation, and its
battery has not been run yet. Until it reads 1, 2 or 3 of 4, this task is not
finished, and `review.csv` leaves that row open rather than claiming N/A.

`evaluations/` is empty pending that battery. No `stability/` is shipped —
Turing runs it — and no `platform/`, which the gate does not yet accept (R17).
