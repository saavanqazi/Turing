# Queue Backpressure Threshold Audit

Audit every queue in a broker status export from an incident night against the
backpressure policy (PLAT-31), when each queue was sampled, and explain the result to the
platform leads.

## Task

The agent gets six attachments under `input/`: the policy, the broker's status export
(42 queues, each sampled at its own time), the backpressure config, a service catalogue
written by the owning teams, the batch schedule (BATCH-7) and the broker event log. It
writes:

- `backpressure_audit.csv`: one row per queue with a `queue_id` and a `finding`
  (`NO_BACKPRESSURE_CONFIGURED`, `BACKPRESSURE_THRESHOLD_EXCEEDED`,
  `DRAIN_TIME_EXCEEDED` or `none`)
- `backpressure_memo.md`: for each threshold or drain finding, the figure and the limit;
  for each queue over its threshold that still comes out `none`, what clears it
- `results.json`: the five figures PLAT-31 §8 defines

## Why it is hard

The export holds no tier, no drain time, no engagement flag and no exemption flag. Every
fact a rule needs has to be derived from a different source, and the one derivation that
cannot be scripted, the tier, feeds both limits a queue is measured against.

- **The tier is a judgement read from prose.** PLAT-31 §2 defines critical: a customer's
  call is held on the queue, or the queue instructs a movement of money. The service
  catalogue says what each queue does, in each team's own words and next to a priority
  label that is often wrong. A hold carries down a chain of services. For example,
  `devices.carrier-lookup` is critical because checkout waits on fraud-scoring, which
  waits on device-intel, which waits on the carrier check. Each link is stated in a
  different team's section, and device-intel describes itself as "internal lookups, P3".
  Other cases in the same catalogue:
  - a hold that only happens on a cache miss (critical, because §2 says some of the
    traffic is enough);
  - writes made mid-request that nobody waits on;
  - writes made after the answer has gone back;
  - queues only staff or a scheduled job wait on;
  - money-moving queues the team labels "low";
  - a refund-status lookup that moves no money.

  21 of the 38 configured queues have a name or label that points the wrong way, and
  following it changes the finding on 17 of them. 24 change finding if their tier is
  misread.
- **The limits are chained.** The threshold is the config override when one is set (one
  of the three overrides is below the tier default), and the tier default otherwise. The
  max drain time is always the tier's.
- **Drain time is derived** from in-flight count and the ack and publish rates. A queue
  whose acks do not outrun its publishes is not draining and exceeds any maximum. Two
  queues drain in exactly their maximum, and two more sit exactly on their threshold.
- **State is read at each queue's sample time.**
  - Engagement comes from the event log: one queue was released six minutes before its
    sample, and one engaged four minutes after.
  - Burst windows come from BATCH-7: one crosses midnight and closed seven minutes before
    its sample, two are weekday-only on the wrong day, and one entry is retired. The
    export's `dashboard_burst_hint` is not a source.
- **Precedence couples the rules.** Engagement clears only the threshold check, so an
  engaged queue can still fail on drain. A window never clears a queue that has no config.

## Grading

131 deterministic checks, all `core`, in `tests/manifest.json` (identical to
`tests/verifier.json`, which `test_outputs.py` reads). There is no LLM judge.

- **Per queue (84):** one check that the finding cell equals the right code, and one that
  no other finding code appears on that queue's row. Cells are matched whole, in any
  column order, quoted or not.
- **Figures (5):** the five PLAT-31 §8 figures.
- **Memo (38):** facts, not phrasing. For a threshold finding, the in-flight figure and
  the threshold. For a drain finding, the max drain time. For an unconfigured queue, the
  queue id. For an over-threshold queue that comes out `none`, what clears it (the stem
  `engag`, or `burst`, `window`, `BATCH-7` or the window's own job name). Each fact must
  sit within 400 characters of the queue id, with no other queue id in between.
- **Existence and header (4).**

The reward is graded: `passed / (passed + failed)`, and 1.0 only when every check passes.

`build_task.py` declares the data, implements PLAT-31 once, and emits every fixture, the
gold deliverables, both verifier files and `solution/golden_trajectory.json`. It asserts
that the gold passes every pin and that each trajectory heredoc reproduces its gold file.
`python3 build_task.py --price` scores each single misreading against the pins; each
costs 4 to 38 checks.

## Changes from the mined baseline

The mined task was 6 queues and 15 checks with a binary reward. GLM-5.2 passed it 4/4
(28/28 on the Phase-1 grader, 1.5 to 2.5 minutes a run).

**Defects fixed first, difficulty unchanged:**

- **Reward hacking.** A CSV writing all four codes on every row scored 1.0 on the mined
  grader. Now each row must carry exactly one finding. The same submission scores 0.68.
- **Over-strict matching.** A correct answer with the columns reordered, and a memo
  saying "window for the scheduled batch burst", scored 0.0 (6 of 15 checks failed). The
  same answer now scores 1.0.
- **Coverage.** Two queues, including the only engaged-backpressure case, had no check at
  all. The memo was asked to explain each finding, but was graded on one queue only.
- **Leakage.** The instruction named the burst-window trap and said there was exactly
  one.
- **Ambiguity.** Seven guesses were closed in the policy: which threshold governs, strict
  "more than", engagement clearing the threshold check only, precedence, a window never
  clearing a missing config, one finding per queue, and the definition of each figure.
- **Packaging.**
  - Base image pinned by digest.
  - `solution/golden_trajectory.json` added.
  - `tests/manifest.json` added.
  - Graded reward.

**Hardening:**

| version | change | GLM-5.2 (4 runs) |
|---|---|---|
| Phase 1 | the six queues, defects fixed | 4/4, 28/28 each |
| v1 | 40 queues. Tier from the catalogue, drain from rates, engagement from the log, windows from BATCH-7, overrides | 4/4, 122/122, 14 to 16 min |
| v2 | holds carry down a chain of services; catalogue rewritten in the teams' voice | 4/4, 125/125, 16 to 21 min |
| v3 | the policy stops naming its own traps; §2(a) causal; three-hop chain, cache-miss hold, mid-request write | in band (below) |

v1 and v2 left the reward unchanged because the policy listed its own traps: every
clarification added for fairness named a misreading to avoid ("not the label", "published
after answering does not count", "the dashboard hint documents nothing"). v3 keeps every
rule and removes those warnings. Each definition still decides every queue on its own.

**Fairness checks, every version:**

- two independent cold readings, one of the tiers alone and one full solve, with no
  access to the gold;
- every wording gap they raised was closed before a battery;
- on v3 the tier reading agreed with the gold on 38 of 38 queues, and the full cold solve
  scored 1.0.

That cold solve also exposed a verifier bug. It explained two burst windows by their job
names, and the memo check at the time required "burst" or "BATCH-7". The check now also
accepts "window" and the job's name, and the same memo scores 1.0.

## Measured

Oracle: exactly 1.0, repeated (Harbor, and fresh Docker containers after every change).

GLM-5.2, terminus-2, battery of record in `evaluations/difficulty/r1` to `r4`:

| run | reward | class |
|---|---|---|
| r1 | 1.0 | pass (131/131) |
| r2 | 1.0 | pass (131/131) |
| r3 | 0.9466 | **MODEL** |
| r4 | _pending replacement run_ | |

**r3.** The run never computed its findings: it typed all 42 into a Python dict by hand
after reading the inputs. It entered `none` for `reports.priority-exports`, a standard
queue whose config override lowers its threshold to 3,000, with 3,400 in flight. Its own
memo states the rule ("Threshold is the override when set, otherwise the tier default").
It got the other two overrides right, and the other runs got this one right on identical
data. This is an attention slip under a rule it stated, not an ambiguity. It costs
7 checks: the queue's two row checks, three figures and two memo checks.

**Two further v3 trials did not count.** Neither reached the verifier, both failures were
on the model-proxy side, and neither is in the bundle:

- one `AgentTimeoutError` after only 5 model turns in 30 minutes, against 8 to 10 turns
  in 8 to 16 minutes for completed runs;
- one `InternalServerError` from the LiteLLM proxy.

## Evaluation structure

- `evaluations/difficulty/r1` to `r4`: the four scored GLM-5.2 trials, as Harbor wrote
  them.
- `evaluations/solvability/r1`: a non-oracle GLM-5.2 run at reward 1.0.
- No `oracle/` (the oracle is replayed from `solution/golden_trajectory.json`), no
  `stability/` (Turing runs it; the Delivery Gate's R3 advisory is expected), and no
  `platform/` (the gate does not accept it yet, R17).
