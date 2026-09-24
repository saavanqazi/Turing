# c239: draft notes for the review form

Transcribe into the review form after you have checked each claim yourself. The form
writes `review.csv`. The platform requires it, and it has to be your review, so edit
anything you did not see for yourself. `<r4>` marks the replacement trial still to come.
Paths are relative to the task root.

---

### Layer 1 · Package consistency: FIXED_AND_VERIFIED

**review_notes.** instruction.md, the policy, the fixtures, the gold and both verifier
files name the same three deliverables and agree on every value. The mined bundle shipped
no `solution/golden_trajectory.json` and no `tests/manifest.json`. Its verifier `task_id`
was `code-C239-…`, against `…/code-c239-…` in task.toml.

**change_made.** Added `build_task.py` as the single source. It emits the fixtures, the
gold, `tests/verifier.json` and `tests/manifest.json` (identical to each other) and
`solution/golden_trajectory.json`. Aligned the `task_id` case.

**what_to_record.** The build asserts that the gold passes all 131 pins and that each
trajectory heredoc reproduces its gold file byte for byte. The two verifier files are
byte-identical (cmp). Oracle 1.0 in Harbor, and in fresh containers after the manifest
was added.

### Layer 1 · Clarity and scope: FIXED_AND_VERIFIED

**review_notes.** A cold read of the mined task needed seven guesses:
- CSV columns (the grader demanded `queue_id` as the first column, which was never
  stated);
- which finding wins when two rules apply;
- whether engagement also clears the drain check;
- `>` or `≥`;
- config value against tier table;
- what each results.json figure counts;
- whether a burst window clears a missing config.

For every hardened version, two independent cold readers without the gold listed every
guess they made. On v3 the tier reader agreed with the gold on 38/38 queues, and the full
solver scored 1.0 (131/131).

**change_made.**
- The instruction states the CSV contract (`queue_id` and `finding` columns, one row per
  queue).
- PLAT-31 gained §3 (limits), §7 (one finding, precedence) and §8 (figures), and states
  strict "more than" and exact drain comparison.
- Wording gaps raised by the cold readers were closed before each battery: who holds the
  call, requests sent on the customer's behalf, the carrier check reaching app checkouts.

**what_to_record.** Cold tier reading, v3: 38/38 with the gold. Cold full solve, v3: 1.0.
No GLM run failed the same check as another run (see Difficulty), so none of the misses
points to an ambiguity.

### Layer 1 · Realism and leakage: FIXED_AND_VERIFIED

**review_notes.** A backpressure audit after an incident, run against a platform policy,
a service catalogue, a batch schedule and a broker log, is ordinary SRE work.

The mined instruction leaked the only trap: "one queue's numbers are over threshold but
the registry marks it inside a scheduled burst window, so check that field before
flagging it". It also said "including the burst-window queue", which asserts there is
exactly one.

In v1 and v2 the policy leaked too. Each fairness clarification named the misreading to
avoid: "not the name, not the label", "published after answering does not count", "the
dashboard hint documents nothing", "a retired entry documents none", "equal is within".

**change_made.** Removed both instruction leaks. In v3, removed the signposts from the
policy and kept every rule, so each definition still decides every queue on its own. The
Dockerfile copies `environment/input/` only.

**what_to_record.** Swept the instruction and policy for trap-naming language. Cold v3
readers still resolved every queue uniquely from the definitions. `tests/` and
`solution/` are never copied into the image.

### Layer 2 Difficulty: FIXED_AND_VERIFIED

**review_notes.** The mined baseline (Phase 1 grader) passed 4/4, 28/28 each: every rule
was a column lookup on 6 queues.

- **v1:** 40 queues, with the tier read from the prose catalogue, drain derived from
  rates, engagement from the event log and windows from BATCH-7 at each sample time.
  4/4 at 122/122, 14–16 min.
- **v2:** holds carry down chains of services. 4/4 at 125/125.
- Diagnosis: the policy listed its own traps.
- **v3:** removed the signposts and added a three-hop chain, a cache-miss hold and a
  mid-request write.

v3 results:
- r1 1.0 and r2 1.0.
- r3 0.9466, MODEL. It hand-coded all 42 findings in a dict and entered `none` for
  `reports.priority-exports` (standard, override 3,000, 3,400 in flight). Its own memo
  states the override rule, it got the other two overrides right, and the other runs got
  this one right on identical data.
- r4 `<r4>`.
- Two further trials never reached the verifier and are excluded: one AgentTimeoutError
  after 5 turns in 30 min, and one LiteLLM InternalServerError. Both are proxy-side.

Evidence: `evaluations/difficulty/r1..r4/verifier/reward.txt`.

**change_made.** v1, v2 and v3 as above, in `environment/input/*` via `build_task.py`,
and in `instruction.md` (the inputs are named).

**what_to_record.** Oracle 1.0 before every battery. v3 battery: 1.0, 1.0, 0.9466,
`<r4>` → `<N>`/4 fully passing, in band. Every single misreading was priced with
`build_task.py --price`: each costs 4–38 of 131 checks, so none is free.

### Layer 2 Solvability: PASS

**review_notes.** Two GLM-5.2 v3 runs scored 1.0 (131/131), plus every run in the three
earlier batteries. The cold independent solve also scored 1.0. `evaluations/solvability/r1`
is a GLM-5.2 run at reward 1.0, and its trajectory hash differs from the golden, so it is
not an oracle replay.

**what_to_record.** `evaluations/solvability/r1/verifier/reward.txt` = 1.0. The assembler
printed trajectory sha256 ≠ golden sha256.

### Layer 3 Oracle Mode: FIXED_AND_VERIFIED

**review_notes.** The mined bundle had no `solution/golden_trajectory.json`. The oracle
installs the gold files with `solve.sh`.

**change_made.** Added `solution/golden_trajectory.json`, generated from the gold (read
the six inputs, write the three deliverables).

**what_to_record.** Harbor oracle 1.0 on every version (`oracle-c239-p1`, `-v1`, `-v2`,
`-v3`). Docker oracle 1.0 (131/131) in fresh containers, twice, after the manifest
change.

### Layer 4 · Environment and files: FIXED_AND_VERIFIED

**review_notes.** The Dockerfile pulled `python:3.12-slim-bookworm` by mutable tag. All
six inputs exist and every file, section and field the policy or instruction references
is present. The grader's dependencies are installed at build time.

**change_made.** Pinned the base image by digest (the same digest the sibling bundles use).

**what_to_record.** Harbor builds and runs it on every battery. Every queue the catalogue
names is asserted at build time.

### Layer 4 · Connectors, MCPs, and CLIs: N/A

**review_notes.** Native offline task: `mcp_servers = []` in task.toml, no connector
manifest, no `environment/_app` mirror. There is nothing to review here.

### Layer 4 · Deliverables and artifact quality: FIXED_AND_VERIFIED

**review_notes.** The three deliverables and their formats are stated in the instruction.
The memo is now asked for specific facts (figure and limit; what clears an over-threshold
queue) instead of "explain each finding" graded on one queue.

**change_made.** Rewrote the memo ask in `instruction.md` and regenerated the gold memo
from the data.

**what_to_record.** The gold memo and an independently written cold-solve memo both pass
all 38 memo checks.

### Layer 5 · Verifier coverage and fairness: FIXED_AND_VERIFIED

**review_notes.** Forward: every ask maps to checks (per-queue finding, five figures, memo
facts, three files). Backward: every check follows from an ask.

Problems found in the mined grader:
- two queues had no check at all;
- the memo was graded on one queue only;
- a correct answer with the columns reordered scored 0.0;
- a strict memo regex rejected "window for the scheduled batch burst".

In v3 the cold solve exposed one more over-strict check: burst windows explained by job
name failed a stem that required "burst" or "BATCH-7".

**change_made.**
- Whole-cell CSV matching in any column order.
- Per-queue checks for all 42 queues.
- Memo facts checked by proximity (within 400 characters of the queue id, no other queue
  id between), not by phrasing.
- The burst stem now also accepts "window" and the job's own name.

**what_to_record.** Probe set (`tools/c239_probes.py`): the gold and an alternate format
(finding first, quoted, CRLF, BOM, no thousands commas, facts before ids) score 1.0. The
cold-solve memo went from 0.985 to 1.0 after the stem fix.

### Layer 5 · LLM judge consistency: PASS

**review_notes.** No LLM judge is used: all 131 checks are deterministic, so a rerun
cannot vary on grading. `JUDGE_MODEL` is still set in our runs.

**what_to_record.** Checked `tests/manifest.json`: 0 rubric assertions, 131 deterministic.

### Layer 5 · Reward hacking and exploitability: FIXED_AND_VERIFIED

**review_notes.** On the mined grader, a CSV writing every code on every row, plus a stub
memo, scored 1.0.

**change_made.**
- Per queue, a finding cell must equal the right code and no other code may appear on
  that queue's row.
- Memo checks require facts near each queue id.
- `test.sh` runs pytest with `PYTHONSAFEPATH=1`, so a module the agent drops in `/app`
  cannot shadow the grader.

**what_to_record.** Probes:

| probe | score |
|---|---|
| all codes in one cell | 0.68 |
| all codes in four cells | 0.68 |
| duplicate rows | 0.68 |
| stub memo | 0.75 |
| memo without figures | 0.79 |

None reaches 1.0.

---

**Optional rows (Turing runs these; the form may ask for them):**

- **Layer 2 Stability:** Turing runs this.
- **Cross-trial · Calibration:** Turing runs this. For reference: the only completed-run
  miss is one hand-coded slip, and runs differ on no shared check.
