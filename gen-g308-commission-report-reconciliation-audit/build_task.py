#!/usr/bin/env python3
"""Generate the g308 fixtures AND derive the gold from the same data.

The line list, the ledger export and the exceptions register are declared here,
the policy rules are implemented once, and every input fixture, all three gold
deliverables and the verifier pins are emitted from that single source, so the
gold cannot drift from the data it describes.

The five partner reports do not share a format. That is deliberate: consolidating
them is part of the task, so the rate unit and the end-user label are normalised
here exactly as the policy says a solver must normalise them.
"""
import csv, io, json, re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INP  = ROOT / "environment" / "input"
STANDARD = {"new": 8, "renewal": 4, "house": 0}
RUN_MONTH_FIRST, RUN_MONTH_LAST, RUN_PERIOD = "2026-06-01", "2026-06-30", "2026-06"

# (deal_id, partner, end_user_type, rate_pct, revenue_usd); the ledger lives apart
L = []
LEDGER = {}          # deal_id -> [(period, amount), ...]; amount may be negative
def add(deal, partner, ctype, rate, rev, ledger):
    """`ledger` is "june", "may", "none", or an explicit list of records."""
    L.append((deal, partner, ctype, rate, rev))
    if isinstance(ledger, list):
        LEDGER[deal] = ledger
    else:
        LEDGER[deal] = {"june": [(RUN_PERIOD, rev)], "may": [("2026-05", rev)], "none": []}[ledger]

def net_recognised(deal):
    """What the run month recognised for this deal, reversals netted off."""
    return sum(a for period, a in LEDGER.get(deal, []) if period == RUN_PERIOD)

PARTNERS = ["PartnerA","PartnerB","PartnerC","PartnerD","PartnerE"]
TYPES    = ["new","renewal","house"]

# --- 60 ordinary lines: correct rate, in the ledger, unique --------------
for i in range(1, 61):
    t = TYPES[i % 3]
    add(f"DEAL-{i:03d}", PARTNERS[i % 5], t, STANDARD[t], 10000 + (i * 1370) % 90000, "june")

# --- rate mismatches: reported disagrees with the standard for its type --
for i, (t, wrong) in enumerate([("new",6),("renewal",8),("house",4),("new",4),
                                ("renewal",6),("house",8),("new",10),("renewal",2)], start=61):
    add(f"DEAL-{i:03d}", PARTNERS[i % 5], t, wrong, 20000 + i * 900, "june")

# --- commissionable with no run-month record. 69 and 70 have no record at
#     all; 71 and 72 have one in the wrong period, which is not a match ---
for i, (t, led) in enumerate([("new","none"),("renewal","none"),
                              ("new","may"),("renewal","may")], start=69):
    add(f"DEAL-{i:03d}", PARTNERS[i % 5], t, STANDARD[t], 25000 + i * 800, led)

# --- house lines at 0% with no record: the standard rate is 0 so R2 does
#     not reach them. Matching on the flag rather than on commissionability
#     is the mistake these punish.
for i in (73, 74):
    add(f"DEAL-{i:03d}", PARTNERS[i % 5], "house", 0, 12000 + i * 500, "none")

# --- a new line reported at 0% with a May record only: commissionable on
#     the STANDARD rate, so a rate mismatch AND a ledger finding ----------
add("DEAL-075", "PartnerB", "new", 0, 41000, "may")

# --- duplicates: the same deal filed by more than one partner -----------
add("DEAL-076", "PartnerA", "new",     8, 60000, "june")
add("DEAL-076", "PartnerC", "new",     8, 60000, "june")
add("DEAL-077", "PartnerB", "renewal", 4, 32000, "june")
add("DEAL-077", "PartnerD", "renewal", 4, 32000, "june")
add("DEAL-077", "PartnerE", "renewal", 4, 32000, "june")     # three reports
add("DEAL-078", "PartnerA", "new",     6, 45000, "june")     # duplicate AND mismatch
add("DEAL-078", "PartnerE", "new",     6, 45000, "june")
add("DEAL-079", "PartnerC", "renewal", 4, 28000, "none")     # duplicate AND unmatched
add("DEAL-079", "PartnerD", "renewal", 4, 28000, "none")

# --- exception-register interactions ------------------------------------
add("DEAL-080", "PartnerB", "renewal", 6, 35000, "june")  # window open -> paid at 6
add("DEAL-081", "PartnerA", "new",    12, 70000, "june")  # window covers June -> 12
add("DEAL-082", "PartnerC", "renewal", 6, 26000, "june")  # window closed in May -> mismatch
add("DEAL-083", "PartnerD", "new",     6, 38000, "june")  # window opens mid-June at 8 -> mismatch
add("DEAL-084", "PartnerE", "new",     8, 52000, "june")  # approved == standard -> compliant
add("DEAL-085", "PartnerA", "house",   3, 16000, "june")  # house at 3 -> commissionable, matched
add("DEAL-086", "PartnerB", "house",   3, 18000, "none")  # house at 3 -> commissionable, no record
add("DEAL-087", "PartnerD", "new",    10, 47000, "june")  # window opens in July -> mismatch

# --- reversals: the run month recognised revenue and then took it back.
#     088 nets to zero and is unmatched; 089 is reversed in part and is
#     still matched, so netting the wrong way is wrong in both directions.
add("DEAL-088", "PartnerC", "new",     8, 50000,
    [(RUN_PERIOD, 50000), (RUN_PERIOD, -50000)])
add("DEAL-089", "PartnerE", "renewal", 4, 30000,
    [(RUN_PERIOD, 30000), (RUN_PERIOD, -12000)])

# --- lines whose approval turns on reading the thread, not a cell -------
#     090 is approved on a condition the run month does not meet; 091 on one
#     it does; 092 was approved and then withdrawn in full four days later.
add("DEAL-090", "PartnerD", "renewal", 6, 38500, "june")
add("DEAL-091", "PartnerA", "renewal", 6, 31000, "june")
add("DEAL-092", "PartnerE", "new",    12, 55000, "june")

# ---- the VP approvals thread -------------------------------------------
# Approvals do not arrive as a register with a status column. They arrive as a
# mailbox: grants, a correction, a lapse, a withdrawal, two approvals conditional
# on what the run month recognises, and two messages that name a deal or a rate
# without approving anything. Which rate is in force for June is the reading of
# the thread, not the reading of a cell.
#
# (msg_id, date, deal, kind, rate, covers_from, covers_to, condition, text)
# kind: grant | amend | end | revoke | note
THREAD = [
 ("APR-0088","2025-07-03","DEAL-081","grant",10,"2025-07-01","2026-12-31",None,
  "Approving a commission rate of 10% on DEAL-081 for the term of the reseller agreement, "
  "1 July 2025 through 31 December 2026."),
 ("APR-0091","2025-09-19","DEAL-082","grant",6,"2025-09-01","",None,
  "DEAL-082 is approved at 6% with effect from 1 September 2025, until further notice."),
 ("APR-0104","2026-01-12","DEAL-080","grant",6,"2026-01-01","",None,
  "Approving 6% on DEAL-080 with effect from 1 January 2026, until further notice."),
 ("APR-0112","2026-02-01","DEAL-085","grant",3,"2026-02-01","2026-06-30",None,
  "The house account on DEAL-085 is approved at 3% from 1 February 2026 through 30 June 2026."),
 ("APR-0118","2026-02-14","DEAL-081","amend",12,None,None,None,
  "Correction to APR-0088. The rate approved on DEAL-081 should read 12%, not 10%. The term "
  "of that approval is unchanged."),
 ("APR-0125","2026-03-01","DEAL-084","grant",8,"2026-03-01","",None,
  "DEAL-084 is approved at 8% from 1 March 2026, until further notice."),
 ("APR-0130","2026-04-02","DEAL-086","grant",3,"2026-04-01","",None,
  "DEAL-086 is approved at 3% with effect from 1 April 2026, until further notice."),
 ("APR-0136","2026-04-20",None,"note",None,None,None,None,
  "Reminder to the desk: an approval binds the commission run only once it carries an APR "
  "number in this thread. Nothing agreed verbally is binding on a run."),
 ("APR-0138","2026-04-25",None,"note",None,None,None,None,
  "DEAL-045 came up in the quarterly review. No change to its commission treatment; it stays "
  "on the standard rate for its end-user type."),
 ("APR-0141","2026-05-06","DEAL-090","grant",6,"2026-05-01","",("min_recognised",40000),
  "Approving 6% on DEAL-090 from 1 May 2026, until further notice, provided the run month "
  "recognises at least $40,000 of revenue on that deal. If it recognises less than that, the "
  "deal is paid at the standard rate for its end-user type."),
 ("APR-0142","2026-05-06","DEAL-091","grant",6,"2026-05-01","",("min_recognised",25000),
  "Approving 6% on DEAL-091 from 1 May 2026, until further notice, provided the run month "
  "recognises at least $25,000 of revenue on that deal. If it recognises less than that, the "
  "deal is paid at the standard rate for its end-user type."),
 ("APR-0147","2026-05-28","DEAL-082","end",None,None,"2026-05-31",None,
  "The approval on DEAL-082 lapses at the end of May 2026 and is not being renewed."),
 ("APR-0150","2026-06-04","DEAL-092","grant",12,"2026-06-01","",None,
  "DEAL-092 is approved at 12% with effect from 1 June 2026, until further notice."),
 ("APR-0154","2026-06-15","DEAL-083","grant",8,"2026-06-15","",None,
  "Approving 8% on DEAL-083 with immediate effect."),
 ("APR-0158","2026-06-18","DEAL-092","revoke",None,None,None,None,
  "The approval on DEAL-092 at APR-0150 is withdrawn in full. It should not have issued, and "
  "no part of this run is to be paid on it."),
 ("APR-0161","2026-06-20","DEAL-087","grant",10,"2026-07-01","",None,
  "Approving 10% on DEAL-087 with effect from 1 July 2026."),
 ("APR-0163","2026-06-22","DEAL-099","grant",5,"2026-06-01","",None,
  "DEAL-099 is approved at 5% with effect from 1 June 2026, until further notice."),
]

def applies(frm, to):
    """The period covers part of the run month."""
    return frm <= RUN_MONTH_LAST and (to == "" or to >= RUN_MONTH_FIRST)

def condition_holds(cond, deal):
    kind, threshold = cond
    assert kind == "min_recognised"
    return net_recognised(deal) >= threshold

def resolve_approvals():
    """Read the thread in date order; a later message about a deal governs."""
    standing = {}
    for mid, date, deal, kind, rate, frm, to, cond, _text in sorted(THREAD, key=lambda m: m[1]):
        if kind == "note" or deal is None:
            continue
        if kind == "grant":
            standing[deal] = dict(msg=mid, rate=rate, frm=frm, to=to, cond=cond)
        elif kind == "amend":
            s = standing[deal]
            if rate is not None: s["rate"] = rate
            if frm is not None:  s["frm"]  = frm
            if to is not None:   s["to"]   = to
            s["msg"] = mid
        elif kind == "end":
            standing[deal].update(to=to, msg=mid)
        elif kind == "revoke":
            standing.pop(deal, None)
    return {d: s for d, s in standing.items()
            if applies(s["frm"], s["to"]) and (s["cond"] is None or condition_holds(s["cond"], d))}

IN_FORCE = resolve_approvals()
APPROVED = {d: s["rate"] for d, s in IN_FORCE.items()}

# The prose is what the solver reads, so it must say what the fields say.
for mid, date, deal, kind, rate, frm, to, cond, text in THREAD:
    if deal is not None:
        assert deal in text, f"{mid} does not name {deal}"
    if rate is not None:
        assert f"{rate}%" in text, f"{mid} does not state {rate}%"
    if kind == "note":
        assert "approv" not in text.lower().split("approvals")[0] or "%" not in text, mid

# ---- the rules, implemented once ----------------------------------------
dup_deals = {d for d in {x[0] for x in L} if sum(1 for y in L if y[0] == d) > 1}

def findings_for(line):
    deal, partner, ctype, rate, rev = line
    out = []
    effective = APPROVED.get(deal, STANDARD[ctype])      # R4 displaces R1's rate
    if rate != effective:                                # R1
        out.append("RATE_MISMATCH")
    if effective > 0 and net_recognised(deal) <= 0:      # R2, on the effective rate
        out.append("UNMATCHED_TO_LEDGER")
    if deal in dup_deals:                                # R3, on every occurrence
        out.append("DUPLICATE_LINE")
    return out

ORDER = ["RATE_MISMATCH", "UNMATCHED_TO_LEDGER", "DUPLICATE_LINE"]
rows, per_line = [], []
for line in L:
    f = sorted(findings_for(line), key=ORDER.index)
    per_line.append((line, f))
    for code in f:
        rows.append({"deal_id": line[0], "source_report": line[1], "finding_code": code})

RESULTS = OrderedDict([
 ("total_lines",              len(L)),
 ("rate_mismatch_count",      sum(1 for r in rows if r["finding_code"] == "RATE_MISMATCH")),
 ("unmatched_to_ledger_count",sum(1 for r in rows if r["finding_code"] == "UNMATCHED_TO_LEDGER")),
 ("duplicate_line_count",     sum(1 for r in rows if r["finding_code"] == "DUPLICATE_LINE")),
 ("compliant_lines",          sum(1 for _, f in per_line if not f)),
])
multi = [(l[0], l[1], f) for l, f in per_line if len(f) > 1]
print(f"lines={len(L)} findings={len(rows)} deals={len({x[0] for x in L})} duplicated={len(dup_deals)}")
print("results:", json.dumps(RESULTS))
print(f"lines carrying more than one finding: {len(multi)}")
for m in multi: print("   ", m)

def w_csv(path, rows, cols):
    o = io.StringIO(); w = csv.DictWriter(o, fieldnames=cols, lineterminator="\n")
    w.writeheader(); w.writerows([{k: r[k] for k in cols} for r in rows])
    Path(path).write_text(o.getvalue(), encoding="utf-8")

# ---- the five partner reports, each in its own format -------------------
# No report states the end-user type. Each line carries the partner's own
# description of the deal, and the type is read from it under the definitions
# in policy R0. Most descriptions say what they are. About a quarter are written
# so the obvious word points the wrong way -- "upsell" on a live contract is a
# renewal, "win-back" after a lapse is new, "partner handled the renewal admin"
# on an account our team sourced is house -- and every one of those has exactly
# one answer under the definition and none by keyword. The type sits upstream
# of the rate, of commissionability and so of the ledger test, so a misread
# cascades.
PLAIN = {
 "new": [
  "First subscription for this customer; 12-month term.",
  "Net-new customer, no prior relationship with us.",
  "New logo signed this month, 24-month agreement.",
  "Customer's first paid agreement with us.",
  "New account; the partner sourced and closed it.",
 ],
 "renewal": [
  "Annual renewal of the existing subscription, same seat count.",
  "Term renewal, 24 months, no change to plan.",
  "Renewal with seat increase from 20 to 25 on the live agreement.",
  "Renewal of the current subscription, signed two weeks before expiry.",
  "Straight renewal, existing customer, existing plan.",
 ],
 "house": [
  "House account sourced by our own sales team; the partner processed the order.",
  "Direct account of ours; partner fulfilled the order only.",
  "Sourced by our enterprise team; partner is reseller of record for billing.",
  "Our own account. Partner submitted the order paperwork at the customer's request.",
 ],
}
# Deal -> description, where the surface word points the wrong way.
TRICKY = {
 # reads as renewal, is new: no active subscription on the day of signature
 "DEAL-003": "Win-back. The customer let their 2023 subscription lapse in January and signed a fresh two-year agreement on 12 June.",
 "DEAL-009": "Returning customer. Their previous contract expired last November; they signed again this month.",
 "DEAL-015": "Customer ran an unpaid trial last year that ended in October. This is their first paid agreement.",
 "DEAL-051": "Former customer, churned in 2022, re-signed on 4 June on a new 12-month plan.",
 # reads as house, is new: the partner sourced the customer
 "DEAL-021": "Partner sourced the customer at a trade show; our AE joined the final call to help close. Customer's first subscription.",
 "DEAL-033": "Co-sell: the partner brought the opportunity and our team helped with pricing. First subscription for this customer.",
 # reads as new, is renewal: an active subscription on the day of signature
 "DEAL-004": "Upsell: added the analytics module to the customer's live contract mid-term.",
 "DEAL-010": "Expansion order, 30 additional seats on the existing agreement, which runs to 2027.",
 "DEAL-016": "Customer signed a brand-new three-year agreement replacing their current contract six months early.",
 "DEAL-022": "Plan migration from Standard to Enterprise; the existing agreement still had eight months to run.",
 "DEAL-028": "First order under the new MSA. The customer's 2025 subscription is live until December.",
 "DEAL-034": "Cross-sell of a second product to a customer whose main subscription is active through 2027.",
 "DEAL-052": "Net-new order for the data add-on; the customer's core subscription is mid-term.",
 # reads as renewal or new, is house: our own team sourced the customer
 "DEAL-002": "Sourced and negotiated by our enterprise AE; the partner processed the paperwork at the customer's request.",
 "DEAL-008": "Inbound lead from our website, worked by our SDR team; the partner was added to the order for billing only.",
 "DEAL-014": "Existing house account; the partner handled the renewal admin on this cycle.",
 "DEAL-020": "Our SDR booked the meeting and our AE closed. The partner is listed as reseller of record.",
 "DEAL-026": "Subsidiary of a house account, sourced by our team through the parent relationship; partner papered the order.",
 # special rows whose type the trap depends on
 "DEAL-063": "Our own team sourced this account; the partner asked to be paid the standard renewal rate on it.",
 "DEAL-066": "Direct house account; the partner processed a term extension for the customer.",
 "DEAL-073": "House account sourced by our field team; partner submitted the order.",
 "DEAL-074": "Sourced by our own sales team; partner fulfilled.",
 "DEAL-075": "Customer's first paid agreement with us, signed 9 June.",
 "DEAL-085": "House account sourced by our sales team; the partner fulfils the order each cycle.",
 "DEAL-086": "Our own account; the partner is reseller of record for billing.",
 "DEAL-088": "New customer; first subscription, 12 months.",
 "DEAL-092": "New logo, first agreement, sourced and closed by the partner.",
}
def description(deal, ctype):
    if deal in TRICKY:
        return TRICKY[deal]
    n = int(deal.split("-")[1])
    return PLAIN[ctype][n % len(PLAIN[ctype])]
# A tricky description filed against the wrong declared type would grade the
# solver on my slip, so the declared type is checked against each one by eye
# above and by key below: every TRICKY key must be a real deal.
for _d in TRICKY:
    assert any(x[0] == _d for x in L), f"TRICKY names {_d}, which is no deal"

REPORT_FILE = {p: f"partner_{p[-1].lower()}_report.csv" for p in PARTNERS}

# Deal ids as filed. Partners key their own systems differently and some export
# with padding, so the same deal reaches the run in more than one spelling. Two
# of the duplicated deals are duplicated only across a spelling, so a solver that
# joins on the raw string never sees them -- and its ledger join misses too.
ID_FORM = {
 ("DEAL-076","PartnerC"): "lower",   ("DEAL-077","PartnerE"): "pad",
 ("DEAL-078","PartnerE"): "lowerpad",("DEAL-012","PartnerC"): "lower",
 ("DEAL-027","PartnerC"): "lower",   ("DEAL-034","PartnerE"): "pad",
 ("DEAL-042","PartnerC"): "lower",   ("DEAL-054","PartnerE"): "pad",
}
# An entry naming a partner that does not file that deal would quietly do nothing.
for _key in ID_FORM:
    assert _key in {(d, p) for d, p, *_ in L}, f"ID_FORM entry {_key} matches no line"
def filed_id(deal, partner):
    form = ID_FORM.get((deal, partner))
    if form == "lower":    return deal.lower()
    if form == "pad":      return f" {deal} "
    if form == "lowerpad": return f" {deal.lower()} "
    return deal

# Two partners close their report with a totals line. It names no deal, so it is
# not a commission line; counting it inflates total_lines and invents a line.
TOTALS_ROW = {"PartnerA", "PartnerD"}

def report_rows(partner):
    out = []
    for deal, p, ctype, rate, rev in L:
        if p != partner:
            continue
        desc = description(deal, ctype)
        deal = filed_id(deal, partner)
        if partner == "PartnerA":
            out.append(dict(deal_id=deal, deal_description=desc, commission_rate_pct=rate, revenue_usd=rev))
        elif partner == "PartnerB":
            out.append({"Deal": deal, "Description": desc, "Rate": f"{rate/100:.2f}", "Amount": rev})
        elif partner == "PartnerC":
            out.append(dict(deal_id=deal, notes=desc, rate_bps=rate * 100, revenue_usd=rev))
        elif partner == "PartnerD":
            out.append(dict(deal_id=deal, deal_summary=desc, rate=f"{rate}%", revenue=rev))
        else:
            out.append(dict(deal_id=deal, context=desc, commission_rate_pct=rate, revenue_usd=rev))
    if partner in TOTALS_ROW:
        total = sum(x[4] for x in L if x[1] == partner)
        if partner == "PartnerA":
            out.append(dict(deal_id="TOTAL", deal_description="", commission_rate_pct="", revenue_usd=total))
        else:
            out.append(dict(deal_id="TOTAL", deal_summary="", rate="", revenue=total))
    return out

COLS = {
 "PartnerA": ["deal_id","deal_description","commission_rate_pct","revenue_usd"],
 "PartnerB": ["Deal","Description","Rate","Amount"],
 "PartnerC": ["deal_id","notes","rate_bps","revenue_usd"],
 "PartnerD": ["deal_id","deal_summary","rate","revenue"],
 "PartnerE": ["deal_id","context","commission_rate_pct","revenue_usd"],
}
for p in PARTNERS:
    w_csv(INP/REPORT_FILE[p], report_rows(p), COLS[p])
(INP/"commission_lines.csv").unlink(missing_ok=True)      # superseded by the reports

# ---- the NetSuite revenue export ----------------------------------------
# One record per deal that has one, in the period that deal's record sits in,
# plus records for deals no partner reported. Absence and wrong-period are
# both "no run-month record"; only one of them looks like a match.
def money(a):
    """The export's own convention: a reversal is written in parentheses."""
    return f"${a:,}" if a >= 0 else f"(${-a:,})"

ledger_rows, rid = [], 0
for deal in sorted({x[0] for x in L}):
    for period, amount in LEDGER[deal]:
        rid += 1
        ledger_rows.append(dict(revenue_record_id=f"REV-{rid:04d}", deal_id=deal,
                                recognized_usd=money(amount), period=period))
for deal, amount, period in (("DEAL-099", 31000, RUN_PERIOD),
                             ("DEAL-120", 18500, RUN_PERIOD),
                             ("DEAL-121", 22400, "2026-05")):
    rid += 1
    ledger_rows.append(dict(revenue_record_id=f"REV-{rid:04d}", deal_id=deal,
                            recognized_usd=money(amount), period=period))
w_csv(INP/"netsuite_revenue_export.csv", ledger_rows,
      ["revenue_record_id","deal_id","recognized_usd","period"])

(INP/"commission_exceptions.csv").unlink(missing_ok=True)    # superseded by the thread
thread_md = ["# VP commission approvals — thread extract", "",
 "Every approval that binds a commission run appears here, in the order it was sent.", ""]
for mid, date, deal, kind, rate, frm, to, cond, text in sorted(THREAD, key=lambda m: m[1]):
    thread_md += [f"## {mid} — {date}", "", text, ""]
(INP/"vp_approvals.md").write_text("\n".join(thread_md), encoding="utf-8")

# ---- the policy ---------------------------------------------------------
(INP/"commission_policy.md").write_text("""# Commission recognition policy (COMM-POL-6)

Binding for the June 2026 commission run. The run month is `2026-06`, which runs from
2026-06-01 to 2026-06-30 inclusive. Where a partner report and this policy disagree,
this policy wins.

## R0 — Consolidating the partner reports

Each partner files its own report and the reports do not share a format. Read all five,
and normalise every line to one consolidated line carrying a deal id, an end-user type,
a commission rate in whole percent, and the partner whose report it came from. The
consolidated line list is every line of every report.

`source_report` is the partner the report belongs to: `PartnerA` for
`partner_a_report.csv`, `PartnerB` for `partner_b_report.csv`, and so on.

A report may close with a totals line, which names no deal and is not a commission line.
The consolidated line list is every line of every report that names a deal.

Partners key their own systems, so the same deal reaches this run in more than one
spelling. Deal ids are compared with surrounding spaces trimmed and case ignored:
` deal-076 ` and `DEAL-076` are the same deal, in this policy and in every file it names.
Write a deal id into `commission_findings.csv` in the form the approvals thread and the
revenue export use, upper case with no surrounding spaces.

A report states its rate in the unit its own column name declares:

| rate column | unit |
|---|---|
| `commission_rate_pct` | whole percent; `8` is 8% |
| `rate_bps` | basis points, one hundredth of one percent; `800` is 8% |
| `Rate` | decimal fraction of revenue; `0.08` is 8% |
| `rate` | whole percent written with a percent sign; `8%` is 8% |

### End-user type

No report states the end-user type. It is read from the line's deal description under
these definitions, and nothing else in the description changes it:

- **house** — our own sales team sourced the customer. Who priced, papered or closed the
  order does not matter, and a partner that only processed an order our team sourced is
  still a house line. House takes precedence over the other two types.
- **new** — the customer held no active subscription with us on the day of signature. A
  customer whose earlier subscription had already ended before signature is new, however
  long they were a customer before, and a trial that was never a paid subscription does
  not make them a renewal.
- **renewal** — the customer held an active subscription with us on the day of
  signature. Any order for such a customer is a renewal, whether it extends the term,
  changes the seat count, adds a product or moves the customer to a different plan.

## R1 — Standard rate by end-user type

| end-user type | standard rate |
|---|---|
| new | 8% |
| renewal | 4% |
| house | 0% |

A line whose reported rate does not match the standard rate for its end-user type is a
`RATE_MISMATCH`.

## R2 — Ledger match

Every commissionable line (standard or approved rate above 0%) must be matched to revenue
recognised for its deal in the run month before it is paid.

Net the run-month records for that deal in `netsuite_revenue_export.csv`. An amount in
parentheses is a reversal and counts as negative, so `($12,000)` is -12,000. A line is
matched when that net is above zero. Records in any other period are not part of this
run's net, whatever they say.

A commissionable line whose run-month net is zero or below, or whose deal has no run-month
record at all, is `UNMATCHED_TO_LEDGER`.

## R3 — Duplicate lines

The same `deal_id` must not appear in more than one partner report. A deal that does is a
`DUPLICATE_LINE` on every line it appears on.

## R4 — VP-approved rate overrides

Approvals are not a register. They are the VP approvals thread in `vp_approvals.md`, read in
the order the messages were sent, each carrying an `APR` number.

A message that grants a rate on a named deal puts that rate in force for the period the
message states. A later message naming the same deal governs over an earlier one: it may
correct the rate, end the approval on a date, or withdraw it altogether. A message that
names no deal, or that names a deal without granting a rate on it, changes nothing.

An approval is in force for this run when the period it stands for, after every later
message about that deal has been applied, covers any part of the run month, and when any
condition the approval attaches holds on this run's data. A deal with an approval in force
is paid at that rate instead of the standard rate for its end-user type, and for that deal
the approved rate is the rate R1 is read against. A deal with no approval in force is read
against the standard rate.

## Finding codes

`RATE_MISMATCH`, `UNMATCHED_TO_LEDGER`, `DUPLICATE_LINE`. A line with none of these is
compliant.

## Reporting the findings

A line carries every finding that applies to it. Where two rules both catch the same
line it appears once per finding in `commission_findings.csv`, and a line with no
finding appears in that file not at all.

## Figures

`total_lines` is the number of lines in the consolidated line list.

`rate_mismatch_count`, `unmatched_to_ledger_count` and `duplicate_line_count` are the
numbers of findings of each code, so a line caught by two rules is counted under both.

`compliant_lines` is the number of lines carrying no finding at all.
""", encoding="utf-8")

SOL = ROOT/"solution"/"files"
w_csv(SOL/"commission_findings.csv", rows, ["deal_id","source_report","finding_code"])
(SOL/"results.json").write_text(json.dumps(RESULTS, indent=2)+"\n", encoding="utf-8")

memo = ["# Commission reconciliation memo — June 2026 run", "",
 f"Consolidated {RESULTS['total_lines']} commission lines from the five partner reports and",
 "reconciled them against COMM-POL-6, the June NetSuite revenue export and the commission",
 f"VP approvals thread. {len(rows)} findings were raised across",
 f"{RESULTS['total_lines'] - RESULTS['compliant_lines']} lines; {RESULTS['compliant_lines']} lines are compliant.",
 "Rates were normalised to whole percent first: PartnerB files a decimal fraction, PartnerC",
 "files basis points and PartnerD writes a percent sign, so the reported rate is not",
 "comparable across reports until it is converted.", "",
 "## Rate mismatches", "",
 "R1 sets the standard rate by end-user type: new 8%, renewal 4%, house 0%. A line whose",
 "reported rate is not the rate R1 is read against is a `RATE_MISMATCH`. Where an approval is",
 "in force for the run month the approved rate is the rate R1 is read against, so the",
 "comparison is made against the approved rate and not the standard one.", ""]
for r in rows:
    if r["finding_code"] == "RATE_MISMATCH":
        ln = next(x for x in L if x[0] == r["deal_id"] and x[1] == r["source_report"])
        eff = APPROVED.get(ln[0], STANDARD[ln[2]])
        memo.append(f"- {r['deal_id']} ({r['source_report']}): {ln[2]} line reported at {ln[3]}%, "
                    f"rate applicable {eff}% — `RATE_MISMATCH`.")
memo += ["", "## Ledger matches", "",
 "R2 requires every commissionable line to be matched to a revenue record in the run month",
 "`2026-06`, and a line is commissionable when the standard or approved rate is above 0%.",
 "Whether the line is commissionable turns on that rate and not on the rate the partner",
 "reported, so a house line at 0% is out of scope for this rule even with no record at all.",
 "A record in `2026-05` is not a match for this run, so a deal whose only record sits in May",
 "is unmatched exactly as a deal with no record is, and a run-month reversal that takes back",
 "everything the run month recognised leaves a net of zero, which is not a match either.", ""]
for r in rows:
    if r["finding_code"] == "UNMATCHED_TO_LEDGER":
        ln = next(x for x in L if x[0] == r["deal_id"] and x[1] == r["source_report"])
        recs = LEDGER[ln[0]]
        if not recs:
            state = "no revenue record"
        elif not any(pd == RUN_PERIOD for pd, _ in recs):
            state = "a revenue record in 2026-05 only"
        else:
            state = f"a run-month net of {net_recognised(ln[0])} after the reversal"
        memo.append(f"- {r['deal_id']} ({r['source_report']}): commissionable at "
                    f"{APPROVED.get(ln[0], STANDARD[ln[2]])}%, {state} — `UNMATCHED_TO_LEDGER`.")
memo += ["", "## Duplicate lines", "",
 "R3 forbids the same `deal_id` appearing in more than one partner report, and a deal that",
 "does is a `DUPLICATE_LINE` on every occurrence rather than on the later one only. These",
 "are only visible once the five reports are consolidated.", ""]
for d in sorted(dup_deals):
    ps = [x[1] for x in L if x[0] == d]
    memo.append(f"- {d}: reported by {', '.join(ps)} — `DUPLICATE_LINE` on each of the {len(ps)} lines.")
memo += ["", "## Lines that look wrong and are not", "",
 "R4 lets a VP-approved rate override the standard mapping. These lines disagree with the",
 "standard rate for their end-user type and are compliant anyway, because an approval in the",
 "thread is in force for the run month and sets the rate they are paid at:", ""]
def compliant_anyway():
    """Lines carrying no finding whose rate is not the standard one for their type."""
    for deal, s in sorted(IN_FORCE.items()):
        if not any(x[0] == deal for x in L):
            continue
        ln = next(x for x in L if x[0] == deal)
        if s["rate"] != STANDARD[ln[2]] and not findings_for(ln):
            yield s["msg"], deal, s["rate"], ln
for msg, deal, rate, ln in compliant_anyway():
    memo.append(f"- {deal} ({ln[1]}): {ln[2]} line paid at {rate}% under {msg}, against a "
                f"standard {STANDARD[ln[2]]}% — compliant, not a rate mismatch.")
memo += ["", "## How the thread was read", "",
 "APR-0118 corrects APR-0088 rather than replacing it, so DEAL-081 stands at 12% and not 10%.",
 "APR-0147 lapses the DEAL-082 approval at the end of May, so June is read against the",
 "standard rate. APR-0158 withdraws APR-0150 in full, so DEAL-092 is read against the standard",
 "rate for the whole run and not for part of it. APR-0161 approves DEAL-087 from 1 July, which",
 "is after this run. APR-0141 and APR-0142 are conditional on what the run month recognises:",
 f"DEAL-090 recognises {net_recognised('DEAL-090')}, short of the 40,000 the approval requires,",
 f"so it is read against the standard rate; DEAL-091 recognises {net_recognised('DEAL-091')},",
 "which clears the 25,000 its approval requires, so it stands. APR-0136 and APR-0138 grant",
 "nothing; APR-0138 names a deal without approving a rate on it. APR-0163 approves a deal that",
 "no partner reported.", ""]
(SOL/"commission_memo.md").write_text("\n".join(memo), encoding="utf-8")
print(f"fixtures + gold written; memo {len(' '.join(memo).split())} words")

# ---- verifiers: one present/absent check per line per code --------------
def V(name, how, why, src, assertion):
    return OrderedDict(name=name, metadata=OrderedDict(how_justification=how, why_justification=why, tag="core"),
        source=OrderedDict(type="file", file=OrderedDict(type=src[0], command=src[1], arguments=src[2])),
        assertion=assertion)
def det(path, cmp, expected):
    return OrderedDict(type="deterministic", expected=expected, deterministic=OrderedDict(path=path, comparison=cmp))
def row_re(deal, partner, code):
    return (r"(?mi)^\x22?" + re.escape(deal) + r"\x22?\s*,\s*\x22?" + re.escape(partner) +
            r"\x22?\s*,\s*\x22?" + re.escape(code) + r"\x22?\s*\r?$")

FIND = ("csv", "extract_text", {"path": "commission_findings.csv"})
MEMO = ("md",  "extract_text", {"path": "commission_memo.md"})
RES  = ("json","read_file",    {"path": "results.json"})
EXIST = lambda p: ("filesystem", "check_path_exists", {"path": p})

vs = [
 V("findings_exist","Checks commission_findings.csv is present as a file.",
   "The findings table is in the submission.", EXIST("commission_findings.csv"), det("$.is_file","equals",True)),
 V("memo_exists","Checks commission_memo.md is present as a file.",
   "The memo is in the submission.", EXIST("commission_memo.md"), det("$.is_file","equals",True)),
 V("results_exists","Checks results.json is present as a file.",
   "The figures file is in the submission.", EXIST("results.json"), det("$.is_file","equals",True)),
 V("findings_header","Opens commission_findings.csv with csv.extract_text and applies regex_match.",
   "The instruction names the header and it is matched exactly.", FIND,
   det("$.text","regex_match", r"(?i)\A\x22?deal_id\x22?[ \t]*,[ \t]*\x22?source_report\x22?[ \t]*,[ \t]*\x22?finding_code\x22?[ \t]*\r?\n")),
]
for (deal, partner, ctype, rate, rev), f in per_line:
    for code in ORDER:
        present = code in f
        vs.append(V(
            f"line_{deal}_{partner}_{code.lower()}",
            f"Opens commission_findings.csv and {'requires' if present else 'forbids'} the "
            f"{deal}/{partner} row under {code}.",
            (f"{deal} on {partner} is a {code} under the policy." if present else
             f"{deal} on {partner} is not a {code}; flagging it would be a false positive."),
            FIND, det("$.text", "regex_match" if present else "not_regex_match", row_re(deal, partner, code))))
for k, v in RESULTS.items():
    vs.append(V(f"result_{k}", f"Reads results.json and compares $.{k}.",
                f"`{k}` is stated as the figures section of the policy defines it.",
                RES, det(f"$.{k}", "equals", v)))

# The memo checks pin facts the instruction asks the memo to carry. Each pattern
# is a single token with no `.*` between anchors, so a memo cannot satisfy one by
# putting two stock words on either side of a page of unrelated prose: the fact is
# either stated or it is not. Two groups, both taken straight from the instruction
# -- the three finding codes it names ("explaining each finding"), and, for every
# line that disagrees with its standard rate and is compliant anyway, that line and
# the register entry that makes it so ("with the rule that makes it so").
memo_facts = [
 ("memo_code_rate_mismatch", r"(?i)rate[\s_\-]?mismatch",
  "RATE_MISMATCH is one of the three codes the instruction names, and the memo explains each finding."),
 ("memo_code_unmatched_to_ledger", r"(?i)unmatched[\s_\-]?to[\s_\-]?ledger",
  "UNMATCHED_TO_LEDGER is one of the three codes the instruction names, and the memo explains each finding."),
 ("memo_code_duplicate_line", r"(?i)duplicate[\s_\-]?line",
  "DUPLICATE_LINE is one of the three codes the instruction names, and the memo explains each finding."),
]
for deal in sorted({r["deal_id"] for r in rows}):
    memo_facts.append((f"memo_finding_{deal.lower().replace('-','_')}",
                       r"(?i)\b" + re.escape(deal) + r"\b",
                       f"{deal} carries a finding, and the memo explains each finding."))
for msg, deal, rate, ln in compliant_anyway():
    memo_facts += [
     (f"memo_compliant_{deal.lower().replace('-','_')}", r"(?i)\b" + re.escape(deal) + r"\b",
      f"{deal} is paid at {rate}% against a standard {STANDARD[ln[2]]}%, so it is a line the "
      f"instruction requires the memo to account for by name."),
     (f"memo_rule_{msg.lower().replace('-','_')}", r"(?i)\b" + re.escape(msg) + r"\b",
      f"{msg} is the approval that makes {deal} compliant, and the instruction asks for "
      f"the rule that makes it so."),
    ]
for nm, pat, why in memo_facts:
    vs.append(V(nm, "Opens commission_memo.md with md.extract_text and applies regex_match "
                    "to a single token, with no wildcard between anchors.", why, MEMO,
                det("$.text","regex_match",pat)))

spec = OrderedDict(task_id="gen-g308-commission-report-reconciliation-audit", verifiers=vs)
for p in ("tests/verifier.json","tests/manifest.json"):
    (ROOT/p).write_text(json.dumps(spec, indent=1)+"\n", encoding="utf-8")
print(f"verifiers: {len(vs)}  ({len(L)} lines x 3 codes = {len(L)*3} line checks)")

# ---- golden trajectory: a required oracle asset this bundle lacked ------
steps = [{"name":"bash","arguments":{"command":f"cat input/{f.name}"}}
         for f in sorted(INP.iterdir())]
for name, marker in (("commission_findings.csv","FINDINGSEOF"),
                     ("commission_memo.md","MEMOEOF"),
                     ("results.json","RESULTSEOF")):
    steps.append({"name":"bash","arguments":{"command":
        f"cat > {name} << '{marker}'\n{(SOL/name).read_text()}{marker}"}})
steps.append({"name":"bash","arguments":{"command":
    "ls -la commission_findings.csv commission_memo.md results.json"}})
(ROOT/"solution"/"golden_trajectory.json").write_text(json.dumps(steps, indent=2)+"\n", encoding="utf-8")
print(f"golden_trajectory.json: {len(steps)} steps")
