#!/usr/bin/env python3
"""Generate the g308 fixtures AND derive the gold from the same data.

The line list and the exceptions register are declared here, the four policy
rules are implemented once, and every input fixture, all three gold
deliverables and the verifier pins are emitted from that single source, so the
gold cannot drift from the data it describes.
"""
import csv, io, json, re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INP  = ROOT / "environment" / "input"
STANDARD = {"new": 8, "renewal": 4, "house": 0}

# (deal_id, partner, customer_type, reported_rate, revenue, netsuite_matched)
# Built from a clean base plus deliberate edge rows; see TRAPS below.
L = []
def add(deal, partner, ctype, rate, rev, matched): L.append((deal, partner, ctype, rate, rev, matched))

PARTNERS = ["PartnerA","PartnerB","PartnerC","PartnerD","PartnerE"]
TYPES    = ["new","renewal","house"]

# --- 60 ordinary lines: correct rate, matched, unique --------------------
n = 0
for i in range(1, 61):
    t = TYPES[i % 3]
    add(f"DEAL-{i:03d}", PARTNERS[i % 5], t, STANDARD[t], 10000 + (i * 1370) % 90000, "yes")
    n += 1

# --- rate mismatches: reported disagrees with the standard for its type --
for i, (t, wrong) in enumerate([("new",6),("renewal",8),("house",4),("new",4),
                                ("renewal",6),("house",8),("new",10),("renewal",2)], start=61):
    add(f"DEAL-{i:03d}", PARTNERS[i % 5], t, wrong, 20000 + i * 900, "yes")

# --- ledger: commissionable and unmatched -> UNMATCHED_TO_LEDGER ---------
for i, t in enumerate(["new","renewal","new","renewal"], start=69):
    add(f"DEAL-{i:03d}", PARTNERS[i % 5], t, STANDARD[t], 25000 + i * 800, "no")

# --- house lines, rate 0, NOT matched: standard rate is 0 so R2 does not
#     reach them. Using the reported rate instead of the standard rate is
#     the mistake these punish.
for i in (73, 74):
    add(f"DEAL-{i:03d}", PARTNERS[i % 5], "house", 0, 12000 + i * 500, "no")

# --- a new line reported at 0% and unmatched: commissionable on the
#     STANDARD rate, so it carries a rate mismatch AND a ledger finding ---
add("DEAL-075", "PartnerB", "new", 0, 41000, "no")

# --- duplicates: same deal in more than one source report ---------------
add("DEAL-076", "PartnerA", "new",     8, 60000, "yes")
add("DEAL-076", "PartnerC", "new",     8, 60000, "yes")
add("DEAL-077", "PartnerB", "renewal", 4, 32000, "yes")
add("DEAL-077", "PartnerD", "renewal", 4, 32000, "yes")
add("DEAL-077", "PartnerE", "renewal", 4, 32000, "yes")      # three reports
add("DEAL-078", "PartnerA", "new",     6, 45000, "yes")      # duplicate AND mismatch
add("DEAL-078", "PartnerE", "new",     6, 45000, "yes")
add("DEAL-079", "PartnerC", "renewal", 4, 28000, "no")       # duplicate AND unmatched
add("DEAL-079", "PartnerD", "renewal", 4, 28000, "yes")

# --- exception-register interactions ------------------------------------
add("DEAL-080", "PartnerB", "renewal", 6, 35000, "yes")   # active exception at 6 -> compliant
add("DEAL-081", "PartnerA", "new",    12, 70000, "yes")   # active exception at 12 -> compliant
add("DEAL-082", "PartnerC", "renewal", 6, 26000, "yes")   # exception INACTIVE -> mismatch
add("DEAL-083", "PartnerD", "new",     6, 38000, "yes")   # exception active at 8 -> mismatch
add("DEAL-084", "PartnerE", "new",     8, 52000, "yes")   # approved == standard -> compliant
add("DEAL-085", "PartnerA", "house",   3, 16000, "yes")   # active exception at 3 -> compliant,
                                                          # and now commissionable, matched
add("DEAL-086", "PartnerB", "house",   3, 18000, "no")    # approved 3 > 0 -> commissionable,
                                                          # unmatched -> ledger finding
EX = [
 ("EXC-VP-02","DEAL-080", 6,"active"),
 ("EXC-VP-07","DEAL-081",12,"active"),
 ("EXC-VP-09","DEAL-082", 6,"expired"),
 ("EXC-VP-11","DEAL-083", 8,"active"),
 ("EXC-VP-14","DEAL-084", 8,"active"),
 ("EXC-VP-18","DEAL-085", 3,"active"),
 ("EXC-VP-21","DEAL-086", 3,"active"),
 ("EXC-VP-25","DEAL-099", 5,"active"),   # names a deal that is not in the line list
]
APPROVED = {d: r for _, d, r, s in EX if s == "active"}

# ---- the four rules, implemented once -----------------------------------
dup_deals = {d for d in {x[0] for x in L} if sum(1 for y in L if y[0] == d) > 1}

def findings_for(line):
    deal, partner, ctype, rate, rev, matched = line
    out = []
    effective = APPROVED.get(deal, STANDARD[ctype])      # R4 displaces R1's rate
    if rate != effective:                                # R1
        out.append("RATE_MISMATCH")
    if effective > 0 and matched != "yes":               # R2, on the effective rate
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

w_csv(INP/"commission_lines.csv",
      [dict(deal_id=d, source_report=p, customer_id=f"CUST-{i+1:03d}", customer_type=t,
            reported_rate_pct=r, revenue_usd=v, netsuite_matched=m)
       for i, (d, p, t, r, v, m) in enumerate(L)],
      ["deal_id","source_report","customer_id","customer_type","reported_rate_pct","revenue_usd","netsuite_matched"])
w_csv(INP/"commission_exceptions.csv",
      [dict(exception_code=c, deal_id=d, approved_rate_pct=r, status=s) for c, d, r, s in EX],
      ["exception_code","deal_id","approved_rate_pct","status"])

pol = Path(INP/"commission_policy.md"); t = pol.read_text()
if "## Figures" not in t:
    t = t.rstrip() + """

## Reporting the findings

A line carries every finding that applies to it. Where two rules both catch the same
line it appears once per finding in `commission_findings.csv`, and a line with no
finding appears in that file not at all.

## Figures

`total_lines` is the number of lines in the consolidated line list.

`rate_mismatch_count`, `unmatched_to_ledger_count` and `duplicate_line_count` are the
numbers of findings of each code, so a line caught by two rules is counted under both.

`compliant_lines` is the number of lines carrying no finding at all.
"""
    pol.write_text(t, encoding="utf-8")

SOL = ROOT/"solution"/"files"
w_csv(SOL/"commission_findings.csv", rows, ["deal_id","source_report","finding_code"])
(SOL/"results.json").write_text(json.dumps(RESULTS, indent=2)+"\n", encoding="utf-8")

memo = ["# Commission reconciliation memo — June 2026 run", "",
 f"Consolidated {RESULTS['total_lines']} commission lines from the partner reports and",
 "reconciled them against COMM-POL-6, the NetSuite match flag recorded on each line and",
 f"the commission exceptions register. {len(rows)} findings were raised across",
 f"{RESULTS['total_lines'] - RESULTS['compliant_lines']} lines; {RESULTS['compliant_lines']} lines are compliant.", "",
 "## Rate mismatches", "",
 "R1 sets the standard rate by end-user type: new 8%, renewal 4%, house 0%. A line whose",
 "reported rate is not the rate R1 is read against is a `RATE_MISMATCH`. Where the deal",
 "carries an active exception the approved rate is the rate R1 is read against, so the",
 "comparison is made against the approved rate and not the standard one.", ""]
for r in rows:
    if r["finding_code"] == "RATE_MISMATCH":
        ln = next(x for x in L if x[0] == r["deal_id"] and x[1] == r["source_report"])
        eff = APPROVED.get(ln[0], STANDARD[ln[2]])
        memo.append(f"- {r['deal_id']} ({r['source_report']}): {ln[2]} line reported at {ln[3]}%, "
                    f"rate applicable {eff}% — `RATE_MISMATCH`.")
memo += ["", "## Ledger matches", "",
 "R2 requires every commissionable line to be matched to a June NetSuite revenue record",
 "before it is paid, and a line is commissionable when the standard or approved rate is",
 "above 0%. Whether the line is commissionable turns on that rate and not on the rate the",
 "partner reported, so a house line at 0% is out of scope for this rule even when the",
 "ledger flag is `no`.", ""]
for r in rows:
    if r["finding_code"] == "UNMATCHED_TO_LEDGER":
        ln = next(x for x in L if x[0] == r["deal_id"] and x[1] == r["source_report"])
        memo.append(f"- {r['deal_id']} ({r['source_report']}): commissionable at "
                    f"{APPROVED.get(ln[0], STANDARD[ln[2]])}%, no ledger match — `UNMATCHED_TO_LEDGER`.")
memo += ["", "## Duplicate lines", "",
 "R3 forbids the same `deal_id` appearing in more than one source report, and a deal that",
 "does is a `DUPLICATE_LINE` on every occurrence rather than on the later one only.", ""]
for d in sorted(dup_deals):
    ps = [x[1] for x in L if x[0] == d]
    memo.append(f"- {d}: reported by {', '.join(ps)} — `DUPLICATE_LINE` on each of the {len(ps)} lines.")
memo += ["", "## Lines that look wrong and are not", "",
 "R4 lets a VP-approved rate override the standard mapping. These lines disagree with the",
 "standard rate for their end-user type and are compliant anyway, because an active",
 "exception in the register sets the rate they are paid at:", ""]
for code, deal, rate, status in EX:
    if status == "active" and any(x[0] == deal for x in L):
        ln = next(x for x in L if x[0] == deal)
        if rate != STANDARD[ln[2]] and not findings_for(ln):
            memo.append(f"- {deal} ({ln[1]}): {ln[2]} line paid at {rate}% under {code}, "
                        f"against a standard {STANDARD[ln[2]]}% — compliant, not a rate mismatch.")
memo += ["", "An exception that is not active does not displace the standard rate, and an approved",
 "rate equal to the standard rate changes nothing.", ""]
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
for (deal, partner, ctype, rate, rev, matched), f in per_line:
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
for code, deal, rate, status in EX:
    if status != "active" or not any(x[0] == deal for x in L):
        continue
    ln = next(x for x in L if x[0] == deal)
    if rate == STANDARD[ln[2]] or findings_for(ln):
        continue                       # not a line that looks wrong and is not
    memo_facts += [
     (f"memo_compliant_{deal.lower().replace('-','_')}", r"(?i)\b" + re.escape(deal) + r"\b",
      f"{deal} is paid at {rate}% against a standard {STANDARD[ln[2]]}%, so it is a line the "
      f"instruction requires the memo to account for by name."),
     (f"memo_rule_{code.lower().replace('-','_')}", r"(?i)\b" + re.escape(code) + r"\b",
      f"{code} is the register entry that makes {deal} compliant, and the instruction asks for "
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
steps = [{"name":"bash","arguments":{"command":f"cat input/{f}"}} for f in
         ("commission_policy.md","commission_lines.csv","commission_exceptions.csv")]
for name, marker in (("commission_findings.csv","FINDINGSEOF"),
                     ("commission_memo.md","MEMOEOF"),
                     ("results.json","RESULTSEOF")):
    steps.append({"name":"bash","arguments":{"command":
        f"cat > {name} << '{marker}'\n{(SOL/name).read_text()}{marker}"}})
steps.append({"name":"bash","arguments":{"command":
    "ls -la commission_findings.csv commission_memo.md results.json"}})
(ROOT/"solution"/"golden_trajectory.json").write_text(json.dumps(steps, indent=2)+"\n", encoding="utf-8")
print(f"golden_trajectory.json: {len(steps)} steps")
