# c239 — queue backpressure threshold audit: implementation roadmap

Task: `obi/code-c239-queue-backpressure-threshold-audit` (non-connector, offline, no `_app/` mirror)
Gates: oracle exactly 1.0, repeatable · GLM-5.2 1–3 of 4 fully passing (4/4 rejected)

## 0. What arrived (mined baseline)

6 queues, 5 config rows, a 4-section policy, 15 verifiers in `tests/verifier.json`,
binary reward (pytest exit code), gold installed by `solve.sh` from `solution/files/`.

Gold re-derived by hand from the policy: it is **correct**.

| queue | in-flight | drain | config | engaged | burst | finding |
|---|---|---|---|---|---|---|
| Q-01 | 800 | 10 | critical 1000/15 | F | F | none |
| Q-02 | 1500 | 10 | critical 1000/15 | F | F | BACKPRESSURE_THRESHOLD_EXCEEDED |
| Q-03 | 6000 | 50 | standard 5000/60 | F | **T** | none (burst exempt) |
| Q-04 | 2000 | 10 | — | F | F | NO_BACKPRESSURE_CONFIGURED |
| Q-05 | 4500 | 90 | standard 5000/60 | F | F | DRAIN_TIME_EXCEEDED |
| Q-06 | 1200 | 10 | critical 1000/15 | **T** | F | none (engaged) |

Figures 3 / 1 / 1 / 1 / 3 — correct. Expect the first GLM battery at **4/4**: six rows,
every rule is a column lookup, and the one trap is named in the instruction.

## 1. Reviewer findings on the mined package

### Missing pieces (report, then add — they are ours to add, not repairs of the core)
- `solution/golden_trajectory.json` — required Oracle asset, absent.
- `README.md`, `review.csv`, `qc_report.html`, `evaluations/` — absent (expected at intake).
- `tests/manifest.json` — absent; non-connector task, so `verifier.json` is rewritten to
  `manifest.json` as the **last** packaging step, oracle re-run after.
- Core five (`task.toml`, `instruction.md`, `tests/`, `environment/`, `solution/`) are present.

### Package consistency
- Dockerfile pulls `python:3.12-slim-bookworm` by mutable tag (QC D27 on siblings) — pin to
  the digest the three sibling bundles use.
- `verifier.json` `task_id` is `code-C239-…`, `task.toml` name is `…/code-c239-…` — align case.
- No verifier carries `metadata.tag`; none is `secondary`. Tag every shipped verifier `core`.

### Ambiguities (each is a guess a careful solver has to make)
| id | guess | where it bites after scaling |
|---|---|---|
| A1 | CSV columns other than `finding` unspecified; grader regex demands `queue_id` in the header **and** as the first column | a correct CSV with `finding` first, or `queue` as the id column, fails |
| A2 | queue breaching threshold **and** drain — which single finding? §4 lists names, no precedence | any queue with two breaches |
| A3 | does engaged backpressure suppress only §2 or every check? ("there is no finding") | engaged queue with a drain breach |
| A4 | "over its threshold" — `>` or `≥`? | a queue at exactly the threshold |
| A5 | config `in_flight_threshold` vs the §2 tier table — which wins if they differ? | any override |
| A6 | `flagged_count` counts queues or findings; `compliant_count` definition | figures |
| A7 | unconfigured queue in a burst window — §1 says "checked first", but say it outright | burst + no config |

### Leakage
- L1 instruction: "one queue's numbers are over threshold but the registry marks it inside a
  scheduled burst window, so check that field before flagging it" — names the only trap.
- L2 instruction: "including the burst-window queue" — asserts exactly one exists.
- Instruction is ~90 words of real voice otherwise; the finding-code list and the results.json
  key list are the deliverable contract, not leakage.

### Verifier coverage and fairness
- **Coverage gaps (forward):** Q-01 and Q-06 are never graded — the engaged-backpressure rule
  has no verifier at all. Memo is asked to explain **each** finding; only Q-03 is checked.
- **Exploitable (backward):** row checks are `^Q-02,.*CODE` — a CSV writing all four codes on
  every row passes all five row checks. `trap_clean` matches the substring `none` anywhere
  in the row. `memo_names_trap` passes on a memo that is just "Q-03".
- **Over-strict:** `memo_explains_burst` needs "burst…window" on one line in that order;
  "window for the batch burst" fails. Column-order dependence (A1).
- No LLM judge anywhere — `JUDGE_MODEL` not needed for grading, but keep it set anyway.

## 2. Division of labour

| work | where |
|---|---|
| generator, fixtures, gold, verifiers, golden trajectory, README draft | this repo / this session |
| oracle via plain Docker (build image, run `solve.sh`, run `tests/test.sh`) | this session (Docker is available) |
| `harbor run -a oracle` and every GLM-5.2 battery | **you**, locally (harbor + personal key) |
| reading battery results (`tools/trial_summary.py`) and deciding the next version | together — commit the `jobs/<name>` folder or send it |
| `review.csv` via the review form, Delivery Gate, `qc_report.html`, Submit | **you** (human-only by rule) |

## 3. Phases

### Phase 0 — Intake (½ h)
1. Commit the mined bundle unmodified as `code-c239-queue-backpressure-threshold-audit/`
   (baseline commit, so every later diff is auditable). `.gitattributes` already keeps
   `rl_world_verifiers/**` byte-exact and scripts LF.
2. Oracle on the baseline: must be 1.0 (it will be; gold matches pins).
3. *Optional but cheap:* one baseline GLM battery → expected 4/4. That is the README's
   "mined baseline was 4/4" evidence line.

### Phase 1 — Fix defects, difficulty unchanged (1–2 h)
Goal: a clean, fair, 6-queue task before any hardening, so later batteries measure
difficulty and nothing else.
1. `build_task.py` (same pattern as g308/b39): declares the data, implements the policy once,
   emits fixtures, all three gold files, verifier pins and `solution/golden_trajectory.json`;
   asserts each write-step of the trajectory reproduces `solution/files/*` byte-for-byte.
2. Policy: add §5 "One finding per queue" (first applicable in order §1 → §2 → §3), state
   exactly what engagement suppresses (§2 only) and what a burst window suppresses (§2 and §3,
   never §1), "over" = strictly greater, which threshold governs, and a §6 defining every
   `results.json` key. → closes A2–A7.
3. Instruction: drop L1/L2; pin the CSV contract (`queue_id` and `finding` columns, one row
   per queue, extra columns allowed). → closes A1.
4. Verifiers: per queue, one positive check (finding cell equals the code, as a whole cell,
   any column position after `queue_id`) and one negative check (no other code on that row);
   header check; figures; memo checks on facts not phrasing (see Phase 2 §memo). All `core`.
5. Pin Dockerfile digest; align `task_id` case.
6. Oracle 1.0 (Docker here, then `harbor -a oracle` by you).

### Phase 2 — Hardening v1: coupled reasoning, not more rules (2–4 h build)
Lesson carried from g308 (seven batteries, all 4/4) and b39 (3/4): format irregularity,
scale and extra rules only make the task **longer**; GLM scripts precise rules perfectly.
The only lever that has moved GLM-5.2 in this task family is a **per-item judgement read
from prose under a precise definition**, sitting upstream of the arithmetic so a misread
cascades. v1 uses that lever plus chained derivations that feed it.

Inputs (≈48 queues):
- `queue_status.csv` — broker export: `queue_id, sampled_at (UTC), in_flight_count,
  publish_rate_per_min, ack_rate_per_min, dashboard_burst_flag`. **No drain column, no
  engaged column.**
- `backpressure_config.csv` — `queue_id, owning_service, in_flight_override` (mostly blank).
  **No tier column.** A handful of queues absent.
- `service_catalog.md` — one prose paragraph per owning service. **Tier is read from it**:
  policy defines critical as "a customer-facing request waits on it synchronously, or it
  carries payment-settlement messages"; everything else standard; the owner's own label does
  not decide. ~¼ of paragraphs written so the surface word points the wrong way
  ("priority-reports" is batch → standard; "low-volume refund callbacks" settle payments →
  critical). Each has exactly one answer under the definition.
- `batch_schedule.md` — the **documented** burst windows (queue, daily UTC window, some
  crossing midnight). Policy §2 already says the window must be *documented*; the broker's
  `dashboard_burst_flag` is the dashboard's opinion ("where a dashboard disagrees, this
  policy decides"). Traps: flag on with no documented window; flag off while a documented
  window holds at `sampled_at`; window documented for a sibling queue of the same service.
- `broker_events.log` — `BACKPRESSURE_ENGAGED` / `RELEASED` lines with timestamps; engaged
  = last event at or before `sampled_at` is ENGAGED (policy states this).

Derivations (all stated precisely in the policy):
- tier ← prose judgement → default threshold / max drain; override replaces threshold only.
- drain minutes = in_flight ÷ (ack − publish); net ≤ 0 = not draining = exceeds any max.
  Compared as exact rationals, so no rounding rule is needed.
- exemption state ← time comparison against schedule / event log at `sampled_at`.
- one finding by precedence; five figures.

Coupled edge density (each deliberately placed, each unique-answer): tier misread flips the
threshold *and* the drain limit; engaged queue that still breaches drain; burst window that
ends minutes before the sample; unconfigured queue inside a window; exactly-at-threshold;
negative net drain; override lower than the tier default.

Memo checks (fact-based, g308 v7 style, following the instruction's ask "explain each
finding with the figure and the limit"): for each flagged queue, the queue id and the
applicable limit within 400 chars, no other queue id between; for each exempted over-threshold
queue, the queue id and the exemption's source (window name / engagement). No wording regexes.

Reward: graded `passed/(passed+failed)` like g308 (1.0 only when every check passes), so a
near-miss reads 0.98 not 0.0 — "fully pass" is still exactly 1.0.

Pre-battery fairness gate (do not skip): a cold independent classification of the catalog
by a second reader; any paragraph where the two readings differ is rewritten, not kept.

### Phase 3 — Measure and iterate (per round: oracle ~5 min, battery ~20–30 min)
Order per round: `build_task.py` → Docker oracle 1.0 → you: `harbor -a oracle` 1.0 →
`docker ps` budget check → 1-run smoke → `-k 4` battery → `tools/trial_summary.py`.

| result | read it as | next |
|---|---|---|
| 1–3 of 4 at 1.0, failures classified MODEL | in band | **stop hardening** → Phase 4 |
| 4/4 | too easy | v2 lever below |
| 0/4, all four failing the **same** checks | ambiguity or verifier bug | fix definition/pin, re-grade same runs if verifier-only, else re-run |
| 0/4, failures spread | possibly too hard | soften one lever (fewer wrong-word paragraphs), re-run |
| exact 0.0 / missing trajectory / timeout / proxy 500 | infra | re-run that trial; never counted |
| bimodal 0.9/0.1 | coin-flip on an ambiguity | fix prompt |

Fallback ladder if v1 is 4/4 (one lever per round, highest leverage first):
- v2 — burst windows move from a schedule table into an ops thread (announcements,
  extensions, one cancellation, one "tentative" that never confirmed), read in order.
- v3 — raise the share of catalog paragraphs written against the surface word; add queues
  whose tier turns on a second clause (synchronous path via a downstream service).
- v4 — status export takes several samples per queue across the incident window; a breach is
  any non-exempt sample, so exemption must be evaluated per sample.
Budget: stop after ~5 batteries and write the g308-style evidence note if still 4/4.

Verifier-only change → re-grade existing runs. Instruction/data change → new battery.

### Phase 4 — Final packaging (1–2 h)
1. Rewrite `tests/verifier.json` → `tests/manifest.json` (keep `verifier.json` beside it if
   `test_outputs.py` still reads it, as g308 ships). Confirm zero `secondary`.
2. Oracle re-run **after** the rewrite, twice from fresh containers — 1.0 both.
3. `tools/assemble_evaluations.py --task code-c239-… --difficulty jobs/<battery> --solvability
   jobs/<passing run> --zip`:
   - `evaluations/difficulty/r1..r4` — four GLM trials, unflattened.
   - `evaluations/solvability/r1` — one non-oracle 1.0 run (copy of a passing difficulty run).
   - **no** `oracle/`, **no** `platform/` (R17), **no** `stability/` unless real repeats exist.
   - Nothing loose under `evaluations/`.
4. `README.md` — baseline → final, why it is hard, all four rewards, flags left unfixed.
5. `review.csv` — **you** write it in the review form (12 rows; Stability and Calibration may
   be blank). I can hand you notes per row to transcribe from. Expected statuses:
   Package consistency FIXED · Clarity FIXED · Realism/leakage FIXED · Difficulty FIXED ·
   Solvability PASS · Oracle Mode FIXED (golden trajectory added) · Environment/files FIXED
   (digest) · Connectors **N/A** (native task, `mcp_servers = []`) · Deliverables PASS/FIXED ·
   Verifier coverage FIXED · LLM judge consistency PASS (no judge used — say so, not N/A) ·
   Reward hacking FIXED (all-codes row exploit closed).
6. Zip the task folder alone.

### Phase 5 — Delivery Gate and submit
1. Upload → Delivery Gate. Expected advisory R3 (stability) — mark reviewed: "Turing runs
   stability".
2. Download `qc_report.html` → task root → re-zip → upload as a **new version** → gate again.
3. Submit that version once gate is PASS, score ≥ floor, `review.csv` present and resolved.
4. Rejection → fix, refresh `qc_report.html`, update affected rows to FIXED_AND_VERIFIED,
   new version.

## 4. Risks
- **Overshoot to 0/4** — prose judgement is a steep lever; mitigated by the cold second
  reading and by softening one lever at a time.
- **30-min agent timeout** under proxy latency — keep inputs to ~48 queues and five short
  files; a timeout is infra, re-run it.
- **Difficulty masquerading as ambiguity** — every 0/4 with identical failing checks is
  treated as a defect first.
- **Memo checks drifting into wording** — facts only (ids, limits), proximity not phrasing.

## 5. Progress log

### Phase 0 — done (commit a71d23a)
- Mined bundle committed unmodified. Vendored `rl_world_verifiers/` is byte-identical to g308's.
- Oracle (Docker pre-flight, `tools/oracle_docker.sh`): **1.0, 15/15**.
- Mined grader probed:
  - every code on every row, stub memo "Q-03 burst window" → **1.0** (exploit)
  - correct findings, `finding` column first, memo says "window for the scheduled batch
    burst" → **0.0**, 6 checks failed (over-strict)

### Phase 1 — done (commit 522304e)
- Same six queues and answers; input CSVs, gold CSV and results byte-identical to mined.
- Policy §1–§6 close A2–A7; instruction closes A1, L1, L2.
- 28 verifiers, all `core`; graded reward; digest-pinned base image; golden trajectory added.
- Oracle **1.0, 28/28**, two fresh containers.
- `tools/c239_probes.py`: gold and a differently-formatted correct answer (finding first,
  quoted, CRLF, BOM, no thousands commas, reordered memo) → 1.0. Three CSV exploits,
  stub memo, a missed engagement, a missed burst window, a memo without figures → 0.75–0.86.

### Waiting on you
1. `harbor run -p code-c239-queue-backpressure-threshold-audit -a oracle …` → expect 1.0.
2. Optional: a Phase-1 GLM battery (expect 4/4) as the README's "before hardening" line.
