# g308 — difficulty band not reachable against GLM-5.2: evidence and recommendation

Task: `obi/gen-g308-commission-report-reconciliation-audit`
Gate: oracle exactly 1.0 (met on every version); difficulty 1–3 of 4 GLM-5.2
rollouts fully passing, advisory target at most 2 (not met on any version).

## What was run

Seven batteries of four `terminus-2` + `openai/glm-5.2` rollouts, each after
an oracle at 1.0. Twenty-five rollouts completed; three scored below 1.0, all
in the first battery, all on the same check.

| battery | task version | checks | completed rollouts | fully passing | below 1.0 | not completed |
|---|---|---|---|---|---|---|
| v1 | mined inputs, slack memo regexes | 286 | 4 | 1 | 3 × 0.9965, all `memo_ledger` | — |
| v2 | memo regexes replaced by token checks (QC1-3..6) | 291 | 4 | 4 | — | — |
| v3 | five partner reports in five formats, ledger export, exception date windows | 294 | 4 | 4 | — | — |
| v4 | totals rows, deal ids in three spellings, accounting-format ledger with reversals to net | 300 | 4 | 4 | — | — |
| v5 | exceptions register replaced by a 17-message VP approvals thread, read in order | 311 | 4 | 4 | — | — |
| v6 | end-user type removed from every report; classified from a prose deal description under a three-clause definition, 22 of 97 written against the surface word | 335 | 2 | 2 | — | 2 × AgentTimeoutError |
| v7 | memo graded on explaining each rate mismatch: both rates within 400 chars of the deal id | 365 | 3 | 3 | — | 1 × InternalServerError |

The two v6 timeouts made five and six model turns in thirty minutes on the
same file-reading loop that passing runs complete in ten turns and seven
minutes; the v7 error is a proxy 500. All three are infrastructure and are
not counted either way. The v7 rollout that timed out had already written
all three deliverables and scored 365/365.

## Why every version came back the same

The reward never moved because the difficulty was never of a kind that could
move it. A solver with a shell reads a precisely stated rule, writes a script,
and runs it; a script is exactly right or exactly wrong, and GLM-5.2 does not
misread precise statements. Every hardening that stayed within the reviewer
guide — no ambiguity, every convention stated — handed the solver a precise
statement, and the solver executed it. This held for prose as well: the
approvals thread came with R4 saying how to read it; the deal descriptions
came with R0 defining the three types; in both cases the model read every
item and encoded its reading in a lookup table, correctly.

The one time rollouts differed was the first battery, where three memos did
not use the word "ledger" before a word beginning "match". That was a
vocabulary accident on a check the Delivery Gate then required removed, and
it is the same mechanism by which the c240 reference sits at three of four
(`memo_sample_first`, a proximity regex on its memo, later relaxed). In this
task family the rules produce no variance between rollouts; only the wording
of the write-up does, and once the memo is graded on facts rather than words
that variance disappears too (v7: a hand-written memo passed all thirty
explanation checks).

## What has not been tried

Every version kept the line data in CSV. A version in which the partner
reports are narrative — each deal described in a paragraph, with the rate,
the revenue and the deal's history in prose — would make the extraction of
all 97 lines a reading task before any script can start. That is the shape of
the b39 sibling, which sits at three of four, and it is the only mechanism
the guide permits that has not been tested here. It carries two risks: an
overshoot to zero of four, and more reading turns against a thirty-minute
agent timeout that the proxy's latency already reaches.

## Recommendation

Decide one of:

1. Accept the task as verified solvable and stable at its current form and
   record the band as not reachable against GLM-5.2 by permitted means, with
   this file and the seven batteries in `jobs/` as evidence.
2. Authorise one further round on the narrative-report shape above, with the
   understanding that it is the last mechanism available and may overshoot.
3. Re-scope the task's core, which is a decision for the task's owner.

All seven task versions are in the git history of
`claude/law-b39-checklist-audit-i7fx2q`; `tools/trial_summary.py` reads any
battery's per-check outcomes and trajectories.
