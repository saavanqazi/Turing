# Change summary — same-day replacement cord sourcing

> Fill the bracketed figures after the GLM batteries. Everything else is final.

## What the task asks

A buyer in Phenix City, AL needs a 10-ft figure-8 (IEC C7, non-polarized) AC cord the
same Friday afternoon. Twenty Kestrel same-day offers across six stores must each be ruled
eligible or not under the chain's terms, with the first refusing clause and the landed
cost, then the eligible count, the offer to take and its total.

## From the mined baseline to this version

**Baseline (as mined).** 11 offers, 5 stores, 8 SKUs, an `on_hand` count in the offers
file, tax always at the fulfilling store. One real trap (two stores across the Eastern
state line are past the 15:00 cutoff). The `STOCK_RESERVE` clause and every tie-break rule
were dead: no row ever exercised them. Oracle was 1.0 (shipped mined evidence, 2026-09-20,
and a local engine replay). GLM-5.2 baseline battery: 4/4 passing, rewards 1.0, 1.0, 1.0,
1.0 (harbor job glm-b7a4-baseline, terminus-2, on the untouched package at commit b41f537).

**Round 1 (measured 4/4, rewards 1.0, 1.0, 1.0, 1.0; oracle 1.0; harbor jobs
oracle-b7a4-r1, glm-b7a4-r1; terminus-2 harness).**
Stock ledger in store-local time with `NO_STOCK`, destination-based tax on delivery,
a same-cent tie resolved by distance, precedence edge rows. GLM-5.2 scripted every
explicit rule correctly, so round 1 was not enough.

**Round 2 (current).** The rules stay explicit, but the data and the sources now punish
the shortcuts a one-pass script takes. Each is governed by a clause in
`same_day_terms.md` so a careful analyst lands on exactly one answer:

1. **Stock is a ledger, not a snapshot.** `stock_ledger.csv` holds opening counts and
   timestamped movements in each store's local time. Effective stock is the sum of lines
   at or before the order instant *on that store's clock*, so the stock figure depends on
   the same timezone reasoning as the cutoff: a 15:20 sale at an Eastern store has
   already happened (OF-01 is `NO_STOCK`, not `CUTOFF_PASSED`), a 15:05 hold at a Central
   store has not (OF-09 keeps its two units). A pickup and a delivery on the same
   store/SKU share one figure. New reason `NO_STOCK`; `STOCK_RESERVE` now fires (OF-13,
   OF-19, the latter ahead of `OUT_OF_RADIUS` by precedence).
2. **Destination-based tax on delivery.** Collection is taxed at the store's rate;
   delivery at the delivery address's rate from `tax_jurisdictions.csv`. OF-17 lands at
   25.89, not the 25.86 a store-rate reading gives.
3. **A real tie.** OF-04 (Opelika) and OF-12 (Smiths Station) both land at 18.62. Both
   are collections ready at the same time, so the nearer store decides: OF-12. Picking
   the first or lowest-id minimum gives OF-04.
4. **Precedence edge rows.** 8-ft 20 AWG (`FIT_GAUGE` before `FIT_LENGTH`), 6-ft 20 AWG
   (gauge rule does not apply at 6 ft, so `FIT_LENGTH`), 20-ft 18 AWG (`FIT_LENGTH`), a
   14:40 sale that counts under "at or before".
5. **Warehouse-shaped ledger.** `qty` is unsigned and the event type gives the
   direction; a `VOID` puts a sold unit back (OF-20 is eligible, not `NO_STOCK`); some
   lines carry the supplier part number instead of the SKU (OF-12's opening count is
   under `VLX-F8-12`, so a missed alias turns the chosen offer into `NO_STOCK`); lines
   posted the day before are already inside Friday's `OPENING` (counting them makes
   OF-13 deliverable).
6. **Store notices override the tables.** Columbus accepts collection until 16:00
   today (OF-18 eligible although 15:40 is past the default cutoff); Smiths Station's
   delivery is paused (OF-17 `SAME_DAY_SUSPENDED` though the directory flag is N).
7. **A stale duplicate store row.** Opelika appears twice with `effective_from`; the
   newer 9.50% row is listed first, so a last-row-wins dictionary keeps the old 9.00%
   and prices OF-04 at 18.53 instead of 18.62.
8. **Money rounding.** PC-1012 at 17.00 with 9.5% tax is exactly 18.615. The terms say
   half-cent rounds up (18.62); `round()` on a float gives 18.61 on the chosen offer.

Result: 7 eligible of 20, chosen OF-12 at USD 18.62.

**Also changed.** `solution/compute_gold.py` derives the gold files, the golden
trajectory and the manifest's expected values from the inputs in one run, so the three
copies of the answer can no longer drift. `tests/verifier.json` was renamed to
`tests/manifest.json` and the two loaders updated. The mined `evaluations/oracle` and
`evaluations/nop` folders were removed. The mining pipeline's `consistency/` metadata was
dropped from the bundle because it describes the pre-hardening gold.

## Why it is hard now

Correctness is no longer eight independent rule checks. The stock figure depends on the
clock conversion, the tax rate depends on the method, the choice depends on a tie-break
chain that only decides once the other rules are right, and several rows fail two clauses
so the precedence order is load-bearing. A per-rule script that treats each clause on its
own misclassifies OF-09, OF-13, OF-14, OF-15, OF-17, OF-18, OF-19, OF-20 or the chosen offer. Six
such shortcuts (float rounding, notices ignored, stale store row, missed alias, VOID ignored,
prior-day lines counted) were replayed against the verifier and each scores 0.0.

## Scoring shape

Every verifier is core and the reward is core-gated (`tests/score.py`), so a run scores
exactly 1.0 or 0.0. A spread like 0.2–0.35 cannot occur on this task by design; the
difficulty signal is the pass count.

**Final battery (harbor job glm-b7a4-r2, terminus-2, GLM-5.2): 3 of 4 passing.**

| rollout | harbor trial | reward | outcome |
|---|---|---|---|
| difficulty/r1 | task__EGsQHvh | 0.0 | MODEL failure: reasoned by hand (no script), 19 of 20 rows right, reported OF-13 as `SAME_DAY_SUSPENDED` where `STOCK_RESERVE` precedes it under S5. Same run applied that precedence correctly on OF-19. |
| difficulty/r2 | task__LZ5ZyDc | 1.0 | Decimal-based script, alias map, notices parsed |
| difficulty/r3 | task__QMJpLL8 | 1.0 | as above |
| difficulty/r4 | task__vR6K4Kt | 1.0 | as above |

Oracle on the final package: 1.0 (harbor job oracle-b7a4-r2; graded files unchanged since).
`evaluations/solvability/r1` is a copy of difficulty/r2 (a GLM-5.2 run, not the oracle).

**Evidence format note.** This harbor build writes `verifier/reward.txt` and
`verifier/score.json`; the bundle's `verifier/reward.json` and
`verifier/verifier_summary.json` were derived from those two files by
`tools/annotate_rollout.py` (a format conversion, no new facts), which also added
`model`, `overall_pass`, `final_answer`, `reward` and `judge` to each `result.json`.

## QC flags left as-is

- R3 stability evidence: Turing runs stability; no `stability/` folder is shipped.
