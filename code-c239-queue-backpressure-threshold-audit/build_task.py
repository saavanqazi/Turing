#!/usr/bin/env python3
"""Generate the c239 fixtures AND derive the gold from the same data.

The broker snapshot, the backpressure config and the batch schedule are declared
here, PLAT-31 is implemented once, and every input fixture, all three gold
deliverables, the verifier pins and the golden trajectory are emitted from that
single source, so the gold cannot drift from the data it describes.

    python3 build_task.py            # build, then re-run the oracle
    python3 build_task.py --price    # also print what each single misreading costs
    python3 build_task.py --probes D # write known-answer submissions into D

The rules are stated in PLAT-31's own terms, and §6 defines each term once. The
broker's dashboard carries columns that look like those terms and are not them:
`in_flight` is unacknowledged messages only, `bp_armed` is backpressure armed
rather than publishers throttled, `eta_drain_min` is computed from the deliver
rate. The policy says the dashboard does not decide and never mentions the
columns by name; each definition decides every queue on its own.
"""
import csv, io, json, re, sys
from collections import OrderedDict
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INP = ROOT / "environment" / "input"
SOL = ROOT / "solution" / "files"
TASK_ID = "code-c239-queue-backpressure-threshold-audit"

TIERS = OrderedDict(critical=(1000, 15), standard=(5000, 60))   # default threshold, max drain minutes
NOCFG, THRESH, DRAIN, NONE = ("NO_BACKPRESSURE_CONFIGURED", "BACKPRESSURE_THRESHOLD_EXCEEDED",
                              "DRAIN_TIME_EXCEEDED", "none")
CODES = (NOCFG, THRESH, DRAIN)
SNAPSHOT = datetime.fromisoformat("2026-09-17T01:50:00+00:00")     # a Thursday
WD = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# ---- data -----------------------------------------------------------------
# queue, ready, unacked, publish/min, deliver/min, ack/min, bp_armed, publisher_flow
SNAP = [
    ("checkout.order-submit",          700,  450,  900, 1200, 1150, "no",  "running"),
    ("checkout.order-confirm",         300,  600,  800, 1100,  850, "no",  "running"),
    ("checkout.coupon-validate",       300,   50,  500,  560,  540, "no",  "running"),
    ("payments.charge-commands",      2600,  900,  500,  850,  800, "yes", "flow"),
    ("payments.refund-commands",       200, 1100,   30,  160,  120, "no",  "running"),
    ("payments.receipt-emails",          0,  900,   40,   40,   40, "no",  "running"),
    ("payments.settlement-report",       0,    0,    0,    0,    0, "no",  "running"),
    ("payouts.transfer-instructions", 7000, 1000, 1500, 1300, 1200, "yes", "running"),
    ("payouts.fx-quotes",              100,  750,  400,  480,  430, "no",  "running"),
    ("search.autocomplete-requests",   900,  700,  450,  650,  600, "yes", "running"),
    ("search.index-updates",          6800,  400,  800,  950,  900, "no",  "running"),
    ("search.synonym-reload",           20,    0,    0,    5,    5, "no",  "running"),
    ("identity.session-validate",      500,  600, 5000, 5200, 5100, "no",  "flow"),
    ("identity.login-otp",            3000, 2400,  800,  950,  900, "no",  "running"),
    ("identity.kyc-checks",           1200, 1000,  120,  200,  170, "no",  "running"),
    ("fraud.score-requests",             0,  400,  420,  420,  420, "no",  "running"),
    ("fraud.model-retrain",           5900,  300,  700,  800,  760, "no",  "running"),
    ("fraud.case-review",             2000, 1500,   60,  200,  100, "no",  "running"),
    ("inventory.stock-reserve",       1000, 1200,  620,  850,  800, "no",  "running"),
    ("inventory.restock-feed",         100,  200,   10,   40,   30, "no",  "running"),
    ("inventory.price-sync",            50,  600,  210,  260,  200, "no",  "running"),
    ("notify.email-digest",          11500,  500,  900,  750,  700, "yes", "blocked"),
    ("wallet.cashback-accrual",       1500,  300,  150,  320,  300, "yes", "running"),
    ("wallet.balance-query",           300,  700, 2000, 2150, 2100, "no",  "running"),
]
QUEUES = [s[0] for s in SNAP]
TIER = {
    "checkout.order-submit": "critical", "checkout.order-confirm": "critical",
    "payments.charge-commands": "critical", "payments.refund-commands": "critical",
    "payments.receipt-emails": "standard", "payments.settlement-report": "standard",
    "payouts.transfer-instructions": "critical", "payouts.fx-quotes": "critical",
    "search.autocomplete-requests": "critical", "search.index-updates": "standard",
    "identity.session-validate": "critical", "identity.login-otp": "standard",
    "identity.kyc-checks": "standard", "fraud.score-requests": "critical",
    "fraud.model-retrain": "standard", "fraud.case-review": "standard",
    "inventory.stock-reserve": "critical", "inventory.restock-feed": "standard",
    "inventory.price-sync": "standard", "wallet.cashback-accrual": "critical",
    "wallet.balance-query": "critical",
}
OVERRIDE = {"payments.refund-commands": 1500, "identity.kyc-checks": 2000, "inventory.stock-reserve": 2500}
DECOMMISSIONED = [("legacy.order-sync", "critical", "")]   # configured, no longer on the broker
UNCONFIGURED = set(QUEUES) - set(TIER)
assert UNCONFIGURED == {"checkout.coupon-validate", "search.synonym-reload", "notify.email-digest"}

# BATCH-7: job, queue, days, opens, closes (UTC), status
SCHEDULE = [
    ("Nightly payout run",      "payouts.transfer-instructions", "daily",    "01:00", "02:00", "active"),
    ("Search full reindex",     "search.index-updates",          "daily",    "23:30", "01:45", "active"),
    ("Fraud model retrain",     "fraud.model-retrain",           "Wed, Sun", "01:30", "03:00", "active"),
    ("Weekly digest send",      "notify.email-digest",           "Thu",      "01:00", "03:00", "active"),
    ("Cashback accrual batch",  "wallet.cashback-accrual",       "daily",    "01:00", "03:00", "retired 2026-08-31"),
]

# ---- PLAT-31, implemented once ---------------------------------------------
# `m` switches in one misreading at a time; the gold passes none.
def load(r, m=frozenset()):
    """§6 in-flight load: ready plus unacknowledged (the dashboard's in_flight is unacked only)."""
    return r[2] if "in_flight_column" in m else r[1] + r[2]

def threshold(q, m=frozenset()):
    if q in OVERRIDE and "ignore_override" not in m:
        return OVERRIDE[q]
    return TIERS[TIER[q]][0]

def engaged(r, m=frozenset()):
    """§6 engaged: publishers are being throttled (flow or blocked), not merely armed."""
    return r[6] == "yes" if "armed_column" in m else r[7] in ("flow", "blocked")

def holds_work(r, m=frozenset()):
    if "drain_check_all" in m:
        return True
    return (r[1] > 0) if "ready_only_work" in m else load(r, m) > 0

def drain_minutes(r, m=frozenset()):
    """§6 drain time: load over (ack - publish); None when not draining."""
    net = (r[4] if "deliver_rate" in m else r[5]) - r[3]
    if "eta_column" in m:
        eta = eta_col(r)
        return None if eta == "" else Fraction(eta)
    return Fraction(load(r, m), net) if net > 0 else None

def eta_col(r):
    """The dashboard's own estimate: ready over (deliver - publish), blank when it cannot say."""
    net = r[4] - r[3]
    return f"{r[1] / net:.1f}" if net > 0 and r[1] > 0 else ""

def open_window(q, m=frozenset()):
    for job, wq, days, opens, closes, status in SCHEDULE:
        if wq != q or (status != "active" and "ignore_retired" not in m):
            continue
        for back in (0, 1):                                # a window that opened yesterday may still hold
            d0 = SNAPSHOT.date() - timedelta(days=back)
            if days != "daily" and WD[d0.weekday()] not in days and "ignore_weekday" not in m:
                continue
            s = datetime.fromisoformat(f"{d0}T{opens}:00+00:00")
            e = datetime.fromisoformat(f"{d0}T{closes}:00+00:00")
            if e <= s:
                e += timedelta(days=1)
            if s <= SNAPSHOT < e:
                return job
    return None

def audit(r, m=frozenset()):
    q = r[0]
    if q in UNCONFIGURED:                                  # §1, first
        return NOCFG, "no_config", None
    job = open_window(q, m)
    t, dmax = threshold(q, m), TIERS[TIER[q]][1]
    over = load(r, m) >= t if "ge_threshold" in m else load(r, m) > t
    if job:                                                # §4 exempts §2 and §3
        return NONE, ("window" if over else "clean"), job
    if over and not engaged(r, m):                         # §2
        return THRESH, "threshold", None
    if holds_work(r, m):                                   # §3
        dm = drain_minutes(r, m)
        if dm is None or dm > dmax:
            return DRAIN, "drain", dm
    return NONE, ("engaged" if over else "clean"), None

def run(m=frozenset()):
    rows = [(r, *audit(r, m)) for r in SNAP]
    res = OrderedDict(
        flagged_count=sum(f != NONE for _r, f, *_ in rows),
        threshold_exceeded_count=sum(f == THRESH for _r, f, *_ in rows),
        no_config_count=sum(f == NOCFG for _r, f, *_ in rows),
        drain_exceeded_count=sum(f == DRAIN for _r, f, *_ in rows),
        compliant_count=sum(f == NONE for _r, f, *_ in rows),
    )
    return rows, res

rows, RESULTS = run()
assert RESULTS["flagged_count"] + RESULTS["compliant_count"] == len(SNAP)

# ---- fixtures ---------------------------------------------------------------
def w_csv(path, header, body):
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(header)
    wr.writerows(body)
    path.write_text(buf.getvalue(), encoding="utf-8")

INP.mkdir(parents=True, exist_ok=True)
for stale in INP.iterdir():
    stale.unlink()
stamp = SNAPSHOT.strftime("%Y-%m-%dT%H:%MZ")
w_csv(INP / "broker_snapshot.csv",
      ["queue_id", "sampled_at", "messages_ready", "messages_unacked", "in_flight", "publish_rate_per_min",
       "deliver_rate_per_min", "ack_rate_per_min", "eta_drain_min", "bp_armed", "publisher_flow"],
      [(q, stamp, rd, un, un, p, d, a, eta_col(r), arm, flow)
       for r in SNAP for (q, rd, un, p, d, a, arm, flow) in [r]])
w_csv(INP / "backpressure_config.csv", ["queue_id", "tier", "in_flight_threshold_override"],
      sorted([(q, TIER[q], OVERRIDE.get(q, "")) for q in TIER] + DECOMMISSIONED))
sched = "\n".join(f"| {j} | `{q}` | {d} | {o} | {c} | {st} |" for j, q, d, o, c, st in SCHEDULE)
(INP / "batch_schedule.md").write_text(f"""# Scheduled batch windows (BATCH-7)

Burst windows agreed with the platform team for scheduled batch work. Times are UTC. `daily`
runs every day; otherwise the window opens on the days listed. A window whose closing time is
earlier than its opening time runs past midnight and closes the next day.

| job | queue | days | opens | closes | status |
|---|---|---|---|---|---|
{sched}
""", encoding="utf-8")

tier_rows = "\n".join(f"| {t} | {n:,} messages | {d} minutes |" for t, (n, d) in TIERS.items())
POLICY = f"""# Queue backpressure policy (PLAT-31)

This decides whether a queue was compliant at the moment its broker snapshot was taken. Where
a broker dashboard disagrees, this policy decides. Terms in *italics* are defined in section 6.

## 1. Configuration required

A queue with no entry in the backpressure config is `NO_BACKPRESSURE_CONFIGURED`. This is
checked first: there is nothing to measure an unconfigured queue against.

## 2. In-flight threshold

A configured queue whose *in-flight load* is more than its *threshold* is
`BACKPRESSURE_THRESHOLD_EXCEEDED`, unless backpressure is *engaged* on it, in which case there
is no threshold finding.

## 3. Drain time

A configured queue that *holds work* and whose *drain time* is more than its tier's max drain
time is `DRAIN_TIME_EXCEEDED`.

## 4. Scheduled batch windows

A configured queue inside an *open batch window* is exempt from sections 2 and 3.

## 5. Findings and figures

Each queue in the snapshot carries exactly one finding: the first of sections 1, 2 and 3 that
applies to it, or `none`. `flagged_count` counts queues whose finding is not `none`;
`threshold_exceeded_count`, `no_config_count` and `drain_exceeded_count` count queues carrying
`BACKPRESSURE_THRESHOLD_EXCEEDED`, `NO_BACKPRESSURE_CONFIGURED` and `DRAIN_TIME_EXCEEDED`;
`compliant_count` counts queues whose finding is `none`.

## 6. Terms

| tier | default threshold | max drain time |
|---|---|---|
{tier_rows}

- *In-flight load*: the messages a queue holds that have not been acknowledged, those ready
  for delivery and those delivered and awaiting acknowledgement together.
- *Threshold*: the queue's `in_flight_threshold_override` in the backpressure config when one
  is set, otherwise its tier's default threshold.
- *Engaged*: the broker is throttling the queue's publishers, which it reports as a publisher
  flow state of `flow` or `blocked`.
- *Holds work*: the queue's in-flight load is above zero.
- *Drain time*: in-flight load ÷ (ack rate − publish rate), with both rates per minute,
  compared exactly without rounding. A queue whose ack rate is not above its publish rate is
  not draining, and its drain time exceeds any maximum.
- *Open batch window*: an active BATCH-7 entry for the queue whose window contains the
  snapshot time, from its opening time up to but not including its closing time.
"""
(INP / "backpressure_policy.md").write_text(POLICY, encoding="utf-8")

# ---- gold -------------------------------------------------------------------
def fmt(x):
    return f"{float(x):.1f}".rstrip("0").rstrip(".")

def explain(r, f, why, extra):
    q = r[0]
    if why == "no_config":
        return f"- `{q}` — `{f}`: it has no entry in the backpressure config."
    t, dmax, tier = threshold(q), TIERS[TIER[q]][1], TIER[q]
    src = "its config override" if q in OVERRIDE else f"the {tier} default"
    L = load(r)
    if why == "threshold":
        return (f"- `{q}` — `{f}`: in-flight load {L:,} ({r[1]:,} ready + {r[2]:,} unacked) against a threshold "
                f"of {t:,} ({src}); publishers were not being throttled (publisher flow `{r[7]}`).")
    if why == "drain":
        how = (f"it is not draining (acks {r[5]}/min against publishes {r[3]}/min)" if extra is None else
               f"its drain time is {fmt(extra)} minutes ({L:,} in flight over a net {r[5] - r[3]}/min of acks)")
        return f"- `{q}` — `{f}`: {how}; the {tier} max drain time is {dmax} minutes."
    if why == "window":
        return (f"- `{q}` — `none`: in-flight load {L:,} is over its threshold of {t:,}, but the BATCH-7 "
                f"\"{extra}\" window was open at the snapshot, which exempts it.")
    if why == "engaged":
        return (f"- `{q}` — `none`: in-flight load {L:,} is over its threshold of {t:,}, but backpressure was "
                f"engaged (publisher flow `{r[7]}`), and its drain time of {fmt(drain_minutes(r))} minutes is "
                f"within the {dmax}-minute maximum.")
    return None

flagged = [explain(r, f, w, x) for r, f, w, x in rows if f != NONE]
cleared = [explain(r, f, w, x) for r, f, w, x in rows if w in ("window", "engaged")]
table = "\n".join(f"| `{r[0]}` | {TIER.get(r[0], '—')} | {load(r):,} | {f} |" for r, f, _w, _x in rows)

SOL.mkdir(parents=True, exist_ok=True)
w_csv(SOL / "backpressure_audit.csv", ["queue_id", "tier", "in_flight_load", "finding"],
      [(r[0], TIER.get(r[0], ""), load(r), f) for r, f, _w, _x in rows])
(SOL / "results.json").write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")
MEMO = f"""# Queue backpressure audit — snapshot {stamp}

{len(rows)} queues in the broker snapshot, audited against PLAT-31. {RESULTS['compliant_count']} are compliant \
and {RESULTS['flagged_count']} carry a finding: {RESULTS['threshold_exceeded_count']} over threshold, \
{RESULTS['drain_exceeded_count']} over their drain time, {RESULTS['no_config_count']} with no backpressure config.

| Queue | Tier | In-flight load | Finding |
|---|---|---|---|
{table}

## Findings

{chr(10).join(flagged)}

## Over threshold but no finding

{chr(10).join(cleared)}
"""
(SOL / "backpressure_memo.md").write_text(MEMO, encoding="utf-8")

# ---- verifiers --------------------------------------------------------------
def V(name, how, why, src, assertion):
    return OrderedDict(name=name, metadata=OrderedDict(how_justification=how, why_justification=why, tag="core"),
                       source=OrderedDict(type="file", file=OrderedDict(type=src[0], command=src[1], arguments=src[2])),
                       assertion=assertion)

def det(path, cmp, expected):
    return OrderedDict(type="deterministic", expected=expected, deterministic=OrderedDict(path=path, comparison=cmp))

def cell(value):
    """A whole CSV cell equal to value, in any column: bounded by a comma or the line's ends."""
    return r"(?:^|,)[ \t]*\x22?" + re.escape(value) + r"\x22?[ \t]*(?:,|\r?$)"

def row_with(q):
    return r"(?mi)^(?=[^\n]*" + cell(q) + r")"

def key(q):
    return q.replace(".", "_").replace("-", "_")

AUDIT = ("csv", "extract_text", {"path": "backpressure_audit.csv"})
MEMO_SRC = ("md", "extract_text", {"path": "backpressure_memo.md"})
RES = ("json", "read_file", {"path": "results.json"})
EXIST = lambda p: ("filesystem", "check_path_exists", {"path": p})

vs = [
    V("audit_exists", "Checks backpressure_audit.csv is present as a file.",
      "The audit is a named deliverable.", EXIST("backpressure_audit.csv"), det("$.is_file", "equals", True)),
    V("memo_exists", "Checks backpressure_memo.md is present as a file.",
      "The memo is a named deliverable.", EXIST("backpressure_memo.md"), det("$.is_file", "equals", True)),
    V("results_exists", "Checks results.json is present as a file.",
      "The figures file is a named deliverable.", EXIST("results.json"), det("$.is_file", "equals", True)),
    V("audit_header",
      "Opens backpressure_audit.csv and requires a header row with a queue_id cell and a finding cell, in either order.",
      "The instruction asks for a queue_id and a finding column; any other columns are the solver's choice.",
      AUDIT, det("$.text", "regex_match",
                 r"(?mi)\A(?=[^\n]*" + cell("queue_id") + r")(?=[^\n]*" + cell("finding") + r")")),
]
for r, f, _w, _x in rows:
    q = r[0]
    others = [c for c in (*CODES, NONE) if c != f]
    vs.append(V(f"row_{key(q)}_finding",
                f"Opens backpressure_audit.csv and requires a row with a {q} cell and a finding cell equal to {f}.",
                f"{q}'s finding under PLAT-31 is {f}.",
                AUDIT, det("$.text", "regex_match", row_with(q) + r"(?=[^\n]*" + cell(f) + r")")))
    vs.append(V(f"row_{key(q)}_no_other_finding",
                f"Opens backpressure_audit.csv and forbids any row with a {q} cell from also carrying a cell equal to "
                f"{', '.join(others)}.",
                f"Each queue carries exactly one finding (PLAT-31 §5); a {q} row naming another contradicts it.",
                AUDIT, det("$.text", "not_regex_match",
                           row_with(q) + r"(?=[^\n]*(?:" + "|".join(cell(o) for o in others) + r"))")))
for k, v in RESULTS.items():
    vs.append(V(f"result_{k}", f"Reads results.json and compares $.{k}.",
                f"`{k}` as PLAT-31 §5 defines it.", RES, det(f"$.{k}", "equals", v)))

# The memo is graded on the facts the instruction asks it to carry, never on
# phrasing: for a threshold finding, the in-flight load and the threshold; for a
# drain finding, the max drain time (the drain figure is a quotient a writer may
# round any way, so it is not pinned); for a queue with no config, the queue; for
# a queue over its threshold that comes out none, what clears it. Each fact must
# sit within 400 characters of the queue id, either order, with no other queue id
# in between.
def qid(q):
    return r"(?<![\w.-])" + re.escape(q) + r"(?![\w-]|\.\w)"

ANY_Q = "(?:" + "|".join(qid(q) for q in QUEUES) + ")"
GAP = r"(?:(?!" + ANY_Q + r").){0,400}?"

def near(q, fact):
    return r"(?is)(?:" + qid(q) + GAP + fact + r"|" + fact + GAP + qid(q) + r")"

def num(n):
    """n with or without a thousands comma, optionally .0, not part of a longer number."""
    return r"(?<![\d.,])" + f"{n:,}".replace(",", ",?") + r"(?:\.0+)?(?![\d]|[.,]\d)"

# What clears it, as a stem, not a phrase.
REASON = {"window": r"(?:window|batch|BATCH-7|{job})", "engaged": r"(?:engag|throttl|\bflow\b)"}
for r, f, why, extra in rows:
    q = r[0]
    if why == "no_config":
        vs.append(V(f"memo_{key(q)}_named", f"Opens backpressure_memo.md and requires the queue id {q}.",
                    f"{q} is flagged {f}, and the memo explains each finding.",
                    MEMO_SRC, det("$.text", "regex_match", qid(q))))
    elif why == "threshold":
        t = threshold(q)
        for tag, v in (("figure", load(r)), ("limit", t)):
            vs.append(V(f"memo_{key(q)}_{tag}",
                        f"Opens backpressure_memo.md and requires {v:,} within 400 characters of {q}, either order, "
                        f"with no other queue id in between.",
                        f"{q} is flagged {f} at an in-flight load of {load(r):,} against a threshold of {t:,}; the "
                        f"instruction asks the memo for the figure and the limit.",
                        MEMO_SRC, det("$.text", "regex_match", near(q, num(v)))))
    elif why == "drain":
        dmax = TIERS[TIER[q]][1]
        vs.append(V(f"memo_{key(q)}_limit",
                    f"Opens backpressure_memo.md and requires {dmax} within 400 characters of {q}, either order, "
                    f"with no other queue id in between.",
                    f"{q} is flagged {f} against a max drain time of {dmax} minutes; the instruction asks the memo "
                    f"for the limit.",
                    MEMO_SRC, det("$.text", "regex_match", near(q, num(dmax)))))
    elif why in REASON:
        pat = REASON[why].replace("{job}", re.escape(extra) if why == "window" else "")
        vs.append(V(f"memo_{key(q)}_cleared",
                    f"Opens backpressure_memo.md and requires {pat!r} within 400 characters of {q}, either order, "
                    f"with no other queue id in between.",
                    f"{q} is over its threshold and comes out none because "
                    f"{'a BATCH-7 window was open' if why == 'window' else 'backpressure was engaged'}; the "
                    f"instruction asks the memo to say what clears it.",
                    MEMO_SRC, det("$.text", "regex_match", near(q, pat))))

spec = OrderedDict(task_id=TASK_ID, verifiers=vs)
# tests/manifest.json is the delivery format; test_outputs.py reads verifier.json,
# as the reference bundle ships. The two are written identical.
for _name in ("verifier.json", "manifest.json"):
    (ROOT / "tests" / _name).write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

def failed_checks(files):
    """Pin names a submission fails, evaluated exactly as the engine does (re.search / equals)."""
    bad = []
    for v in vs:
        a, src = v["assertion"], v["source"]["file"]
        path, cmp = src["arguments"]["path"], a["deterministic"]["comparison"]
        if src["type"] == "filesystem":
            ok = path in files
        elif src["type"] == "json":
            ok = json.loads(files[path]).get(a["deterministic"]["path"][2:]) == a["expected"]
        else:
            ok = bool(re.search(a["expected"], files[path])) == (cmp == "regex_match")
        if not ok:
            bad.append(v["name"])
    return bad

GOLD = {p.name: p.read_text(encoding="utf-8") for p in SOL.iterdir()}
assert failed_checks(GOLD) == [], failed_checks(GOLD)

# ---- golden trajectory ------------------------------------------------------
steps = [{"name": "bash", "arguments": {"command": f"cat input/{f.name}"}} for f in sorted(INP.iterdir())]
for name, marker in (("backpressure_audit.csv", "AUDITEOF"), ("backpressure_memo.md", "MEMOEOF"),
                     ("results.json", "RESULTSEOF")):
    steps.append({"name": "bash", "arguments": {"command": f"cat > {name} << '{marker}'\n{GOLD[name]}{marker}"}})
steps.append({"name": "bash", "arguments": {"command": "ls -la backpressure_audit.csv backpressure_memo.md results.json"}})
for s in steps:
    mt = re.match(r"cat > (\S+) << '(\w+)'\n(.*)\2\Z", s["arguments"]["command"], re.S)
    if mt:
        assert mt.group(3) == GOLD[mt.group(1)], mt.group(1)
(ROOT / "solution" / "golden_trajectory.json").write_text(json.dumps(steps, indent=2) + "\n", encoding="utf-8")

print(f"{len(rows)} queues; figures {dict(RESULTS)}")
print(f"verifiers: {len(vs)} (all core); golden_trajectory: {len(steps)} steps")
for p in sorted(INP.iterdir()):
    print(f"  input/{p.name}: {len(p.read_text().splitlines())} lines, {p.stat().st_size} bytes")

def audit_csv(pairs, header=("queue_id", "finding")):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([header, *pairs])
    return buf.getvalue()

MISTAKES = ["in_flight_column", "armed_column", "drain_check_all", "ready_only_work", "deliver_rate",
            "eta_column", "ignore_override", "ignore_retired", "ignore_weekday", "ge_threshold"]

# ---- what each single misreading costs --------------------------------------
if "--price" in sys.argv:
    print(f"\n{'misreading':22s} queues changed  checks failed / {len(vs)}")
    for mk in MISTAKES:
        mrows, mres = run(frozenset([mk]))
        changed = [r[0] for (r, f, *_), (_r2, g, *_) in zip(mrows, rows) if f != g]
        if not changed:
            print(f"{mk:22s} (no effect)")
            continue
        sub = {**GOLD, "backpressure_audit.csv": audit_csv([(r[0], f) for r, f, *_ in mrows]),
               "results.json": json.dumps(mres)}
        print(f"{mk:22s} {len(changed):>3}            {len(failed_checks(sub)):>3}   {', '.join(changed)}")

# ---- probe submissions: known answers for the grader ------------------------
# `--probes DIR` writes one folder per probe; tools/c239_probes.py grades each in
# the task image. A name ending in `_ok` must score 1.0; every other must not.
if "--probes" in sys.argv:
    import shutil
    out = Path(sys.argv[sys.argv.index("--probes") + 1])
    shutil.rmtree(out, ignore_errors=True)

    def write(name, files):
        d = out / name
        d.mkdir(parents=True)
        for fn, text in files.items():
            (d / fn).write_bytes(text.encode("utf-8"))

    gold_pairs = [(r[0], f) for r, f, *_ in rows]
    write("gold_ok", GOLD)
    # Correct, written differently: finding first, quoted, notes column, CRLF, BOM; a
    # memo with no thousands commas, each fact stated before the queue id.
    alt_csv = "﻿" + '"finding","queue_id","notes"\r\n' + "".join(
        f'"{f}","{q}","see memo"\r\n' for q, f in gold_pairs)
    lines = ["Backpressure audit notes", ""]
    for r, f, why, extra in rows:
        q = r[0]
        if why == "no_config":
            lines.append(f"Nothing in the config for {q}: {f}.")
        elif why == "threshold":
            lines.append(f"Limit {threshold(q)}, load {load(r)}: {q} is {f}.")
        elif why == "drain":
            lines.append(f"Allowed {TIERS[TIER[q]][1]} min to drain; it does not: {q} is {f}.")
        elif why == "window":
            lines.append(f"Snapshot fell inside the {extra} slot, so {q} is exempt: none.")
        elif why == "engaged":
            lines.append(f"Publishers were throttled, so {q} is none.")
        lines.append("")
    write("correct_alt_format_ok", {**GOLD, "backpressure_audit.csv": alt_csv, "backpressure_memo.md": "\n".join(lines)})
    every = " ".join((*CODES, NONE))
    write("hack_all_codes_one_cell", {**GOLD, "backpressure_audit.csv": audit_csv([(q, every) for q in QUEUES])})
    write("hack_all_codes_four_cells", {**GOLD, "backpressure_audit.csv": audit_csv(
        [(q, *CODES, NONE) for q in QUEUES], header=("queue_id", "finding", "f2", "f3", "f4"))})
    write("hack_duplicate_rows", {**GOLD, "backpressure_audit.csv": audit_csv(
        [(q, c) for q in QUEUES for c in (*CODES, NONE)])})
    write("hack_stub_memo", {**GOLD, "backpressure_memo.md": " ".join(QUEUES) + " window engaged\n"})
    write("memo_without_figures", {**GOLD, "backpressure_memo.md": re.sub(r"(?<![\w.-])\d[\d,.]*", "N", GOLD["backpressure_memo.md"])})
    for mk in MISTAKES:
        mrows, mres = run(frozenset([mk]))
        if any(f != g for (_r, f, *_), (_r2, g, *_) in zip(mrows, rows)):
            write("mistake_" + mk, {**GOLD, "results.json": json.dumps(mres),
                                    "backpressure_audit.csv": audit_csv([(r[0], f) for r, f, *_ in mrows])})
    print(f"probes written to {out}")
