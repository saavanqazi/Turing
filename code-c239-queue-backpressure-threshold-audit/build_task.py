#!/usr/bin/env python3
"""Generate the c239 fixtures AND derive the gold from the same data.

The queues, their config and the policy are declared here, the policy is
implemented once, and every input fixture, all three gold deliverables, the
verifier pins and the golden trajectory are emitted from that single source, so
the gold cannot drift from the data it describes.

    python3 build_task.py        # then re-run the oracle
"""
import csv, io, json, re
from collections import OrderedDict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INP = ROOT / "environment" / "input"
SOL = ROOT / "solution" / "files"
TASK_ID = "code-c239-queue-backpressure-threshold-audit"

TIERS = OrderedDict(critical=(1000, 15), standard=(5000, 60))   # threshold, max drain minutes
CODES = ("NO_BACKPRESSURE_CONFIGURED", "BACKPRESSURE_THRESHOLD_EXCEEDED", "DRAIN_TIME_EXCEEDED")
NONE = "none"

# ---- data -----------------------------------------------------------------
# queue_id -> tier, or absent when the queue has no backpressure config
CONFIG = OrderedDict([("Q-01", "critical"), ("Q-02", "critical"), ("Q-03", "standard"),
                      ("Q-05", "standard"), ("Q-06", "critical")])
# queue_id, in_flight_count, drain_minutes, backpressure_engaged, burst_window_active
STATUS = [
    ("Q-01",  800, 10, False, False),
    ("Q-02", 1500, 10, False, False),
    ("Q-03", 6000, 50, False, True),
    ("Q-04", 2000, 10, False, False),
    ("Q-05", 4500, 90, False, False),
    ("Q-06", 1200, 10, True,  False),
]

# ---- the policy, implemented once ----------------------------------------
def limits(q):
    """The threshold and max drain recorded for q in the config (PLAT-31 §2)."""
    t, d = TIERS[CONFIG[q]]
    return t, d

def audit(q, in_flight, drain, engaged, burst):
    """(finding, reason). Reason is what the memo has to explain."""
    if q not in CONFIG:                                      # §1, checked first, burst or not
        return CODES[0], "no_config"
    if burst:                                                # §4 exempts §2 and §3
        return NONE, "burst" if in_flight > limits(q)[0] or drain > limits(q)[1] else "clean"
    threshold, max_drain = limits(q)
    if in_flight > threshold:                                # §2, strictly more than
        if not engaged:
            return CODES[1], "threshold"
        cleared = "engaged"                                  # engagement answers §2 only
    else:
        cleared = "clean"
    if Fraction(drain) > max_drain:                          # §3
        return CODES[2], "drain"
    return NONE, cleared

rows = [(q, n, d, e, b, *audit(q, n, d, e, b)) for q, n, d, e, b in STATUS]
RESULTS = OrderedDict(
    flagged_count=sum(r[5] != NONE for r in rows),
    threshold_exceeded_count=sum(r[5] == CODES[1] for r in rows),
    no_config_count=sum(r[5] == CODES[0] for r in rows),
    drain_exceeded_count=sum(r[5] == CODES[2] for r in rows),
    compliant_count=sum(r[5] == NONE for r in rows),
)
assert RESULTS["flagged_count"] + RESULTS["compliant_count"] == len(rows)

# ---- fixtures ---------------------------------------------------------------
def w_csv(path, header, body):
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(header)
    wr.writerows(body)
    path.write_text(buf.getvalue(), encoding="utf-8")

INP.mkdir(parents=True, exist_ok=True)
w_csv(INP / "backpressure_config.csv", ["queue_id", "tier", "in_flight_threshold", "max_drain_minutes"],
      [(q, t, *TIERS[t]) for q, t in CONFIG.items()])
w_csv(INP / "queue_status.csv",
      ["queue_id", "in_flight_count", "drain_minutes", "backpressure_engaged", "burst_window_active"],
      STATUS)

tier_rows = "\n".join(f"| {t} | {n:,} messages | {d} minutes |" for t, (n, d) in TIERS.items())
POLICY = f"""# Queue backpressure policy (PLAT-31)

This decides whether a queue's in-flight load is compliant. Where a broker dashboard's own
health colour disagrees, this policy decides.

## 1. Configuration required

A queue with no entry in the backpressure config at all is `NO_BACKPRESSURE_CONFIGURED`.
This is checked first, and it applies whatever else is true of the queue, a burst window
included: there is no threshold to measure an unconfigured queue against.

## 2. In-flight threshold

A configured queue is measured against the in-flight threshold and maximum drain time
recorded for it in the backpressure config. The config is set from these tier defaults:

| tier | in-flight threshold | max drain time |
|---|---|---|
{tier_rows}

A configured queue whose in-flight count is more than its threshold is
`BACKPRESSURE_THRESHOLD_EXCEEDED` (a count equal to the threshold is within it) — **unless**
backpressure has already engaged for that queue, in which case the system responded
correctly and there is no threshold finding. Engagement answers this section only; it does
not clear section 3.

## 3. Drain time

A configured queue whose drain time is more than its maximum drain time is
`DRAIN_TIME_EXCEEDED`.

## 4. Scheduled burst windows

A queue marked inside a documented scheduled-batch burst window is exempt from sections 2
and 3 for as long as the window holds. It is not exempt from section 1.

## 5. One finding per queue

Each queue carries exactly one finding: the first of sections 1, 2 and 3 that applies to
it, or `none` when none does. The finding names are `NO_BACKPRESSURE_CONFIGURED`,
`BACKPRESSURE_THRESHOLD_EXCEEDED`, `DRAIN_TIME_EXCEEDED` and `none`.

## 6. Audit figures

- `flagged_count` — queues whose finding is not `none`.
- `threshold_exceeded_count`, `no_config_count`, `drain_exceeded_count` — queues carrying
  `BACKPRESSURE_THRESHOLD_EXCEEDED`, `NO_BACKPRESSURE_CONFIGURED` and `DRAIN_TIME_EXCEEDED`
  respectively.
- `compliant_count` — queues whose finding is `none`.

`flagged_count` and `compliant_count` together make up every queue audited.
"""
(INP / "backpressure_policy.md").write_text(POLICY, encoding="utf-8")

# ---- gold -------------------------------------------------------------------
SOL.mkdir(parents=True, exist_ok=True)
w_csv(SOL / "backpressure_audit.csv", ["queue_id", "in_flight_count", "drain_minutes", "finding"],
      [(q, n, d, f) for q, n, d, _e, _b, f, _r in rows])
(SOL / "results.json").write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")

def explain(q, n, d, f, why):
    if why == "no_config":
        return f"- **{q}** — `{f}`. {q} has no entry in the backpressure config, so there is no threshold to measure its {n:,} in-flight messages against."
    t, m = limits(q)
    tier = CONFIG[q]
    if why == "threshold":
        return f"- **{q}** — `{f}`. {n:,} in flight against the {tier} threshold of {t:,}, and backpressure has not engaged."
    if why == "drain":
        return f"- **{q}** — `{f}`. Drain time of {d} minutes against the {tier} maximum of {m} minutes."
    if why == "burst":
        return (f"- **{q}** — `none`. {n:,} in flight is over the {tier} threshold of {t:,}, but the queue is marked "
                f"inside a documented scheduled-batch burst window, which exempts it from the threshold and "
                f"drain checks while the window holds.")
    if why == "engaged":
        return (f"- **{q}** — `none`. {n:,} in flight is over the {tier} threshold of {t:,}, but backpressure has "
                f"already engaged, so the system responded correctly. Its drain time of {d} minutes is within "
                f"the {m}-minute maximum.")
    return None

flagged = [explain(q, n, d, f, why) for q, n, d, _e, _b, f, why in rows if f != NONE]
cleared = [explain(q, n, d, f, why) for q, n, d, _e, _b, f, why in rows if why in ("burst", "engaged")]
table = "\n".join(f"| {q} | {n:,} | {d} | {f} |" for q, n, d, _e, _b, f, _r in rows)
MEMO = f"""# Queue backpressure audit — {len(rows)} queues

{len(rows)} queues checked against PLAT-31. {RESULTS['compliant_count']} are compliant and \
{RESULTS['flagged_count']} carry a finding.

| Queue | In-flight | Drain (min) | Finding |
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
    """Anchors at the start of a row that has a cell equal to queue id q."""
    return r"(?mi)^(?=[^\n]*" + cell(q) + r")"

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
for q, n, d, _e, _b, f, _why in rows:
    others = [c for c in (*CODES, NONE) if c != f]
    key = q.lower().replace("-", "_")
    vs.append(V(
        f"row_{key}_finding",
        f"Opens backpressure_audit.csv and requires a row with a {q} cell and a finding cell equal to {f}.",
        f"{q}'s finding under PLAT-31 is {f}.",
        AUDIT, det("$.text", "regex_match", row_with(q) + r"(?=[^\n]*" + cell(f) + r")")))
    vs.append(V(
        f"row_{key}_no_other_finding",
        f"Opens backpressure_audit.csv and forbids any row with a {q} cell from also carrying a cell equal to "
        f"{', '.join(others)}.",
        f"Each queue carries exactly one finding (PLAT-31 §5); a {q} row naming another finding contradicts it.",
        AUDIT, det("$.text", "not_regex_match",
                   row_with(q) + r"(?=[^\n]*(?:" + "|".join(cell(o) for o in others) + r"))")))
for k, v in RESULTS.items():
    vs.append(V(f"result_{k}", f"Reads results.json and compares $.{k}.",
                f"`{k}` as PLAT-31 §6 defines it.", RES, det(f"$.{k}", "equals", v)))

# The memo is graded on the facts the instruction asks it to carry, never on
# phrasing: for a threshold or drain finding, the figure that tripped it and the
# limit it was measured against; for a queue with no config, the queue; for a
# queue over its threshold that carries no finding, what clears it. Each fact
# must sit within 400 characters of the queue id, either order, with no other
# queue id in between, so it cannot be borrowed from a neighbouring queue.
GAP = r"(?:(?!\bQ-\d{2}\b).){0,400}?"

def near(q, fact):
    d = r"\b" + re.escape(q) + r"\b"
    return r"(?is)(?:" + d + GAP + fact + r"|" + fact + GAP + d + r")"

def num(n):
    """n as written with or without a thousands comma, not part of a longer number."""
    s = f"{n:,}".replace(",", ",?")
    return r"(?<![\d.,])" + s + r"(?![\d]|[.,]\d)"

REASON = {"burst": r"burst", "engaged": r"engag"}
for q, n, d, _e, _b, f, why in rows:
    key = q.lower().replace("-", "_")
    if why == "no_config":
        vs.append(V(f"memo_{key}_named", f"Opens backpressure_memo.md and requires the token {q}.",
                    f"{q} is flagged {f}, and the memo explains each finding.",
                    MEMO_SRC, det("$.text", "regex_match", r"\b" + re.escape(q) + r"\b")))
    elif why in ("threshold", "drain"):
        t, m = limits(q)
        figure, limit, unit = (n, t, "in-flight messages") if why == "threshold" else (d, m, "drain minutes")
        for tag, v in (("figure", figure), ("limit", limit)):
            vs.append(V(f"memo_{key}_{tag}",
                        f"Opens backpressure_memo.md and requires {v:,} within 400 characters of {q}, either order, "
                        f"with no other queue id in between.",
                        f"{q} is flagged {f} at {figure:,} {unit} against a limit of {limit:,}; the instruction asks "
                        f"the memo to state the figure and the limit.",
                        MEMO_SRC, det("$.text", "regex_match", near(q, num(v)))))
    elif why in REASON:
        vs.append(V(f"memo_{key}_cleared",
                    f"Opens backpressure_memo.md and requires the stem '{REASON[why]}' within 400 characters of {q}, "
                    f"either order, with no other queue id in between.",
                    f"{q} is over its threshold and carries no finding because "
                    f"{'it is inside a burst window' if why == 'burst' else 'backpressure has engaged'}; "
                    f"the instruction asks the memo to say what clears it.",
                    MEMO_SRC, det("$.text", "regex_match", near(q, REASON[why]))))

spec = OrderedDict(task_id=TASK_ID, verifiers=vs)
(ROOT / "tests" / "verifier.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

# The gold must satisfy every pin it was generated beside.
_text = {"backpressure_audit.csv": (SOL / "backpressure_audit.csv").read_text(encoding="utf-8"),
         "backpressure_memo.md": (SOL / "backpressure_memo.md").read_text(encoding="utf-8")}
for v in vs:
    a, src = v["assertion"], v["source"]["file"]
    if a["deterministic"]["comparison"] in ("regex_match", "not_regex_match"):
        hit = bool(re.search(a["expected"], _text[src["arguments"]["path"]]))
        assert hit == (a["deterministic"]["comparison"] == "regex_match"), v["name"]

# ---- golden trajectory ------------------------------------------------------
steps = [{"name": "bash", "arguments": {"command": f"cat input/{f.name}"}} for f in sorted(INP.iterdir())]
for name, marker in (("backpressure_audit.csv", "AUDITEOF"), ("backpressure_memo.md", "MEMOEOF"),
                     ("results.json", "RESULTSEOF")):
    steps.append({"name": "bash", "arguments": {"command": f"cat > {name} << '{marker}'\n{(SOL / name).read_text()}{marker}"}})
steps.append({"name": "bash", "arguments": {"command": "ls -la backpressure_audit.csv backpressure_memo.md results.json"}})
# Each write step, replayed as a heredoc, must reproduce the gold file byte for byte.
for s in steps:
    m = re.match(r"cat > (\S+) << '(\w+)'\n(.*)\2\Z", s["arguments"]["command"], re.S)
    if m:
        assert m.group(3) == (SOL / m.group(1)).read_text(), m.group(1)
(ROOT / "solution" / "golden_trajectory.json").write_text(json.dumps(steps, indent=2) + "\n", encoding="utf-8")

print(f"{len(rows)} queues, figures {dict(RESULTS)}")
print(f"verifiers: {len(vs)} (all core); golden_trajectory: {len(steps)} steps")
