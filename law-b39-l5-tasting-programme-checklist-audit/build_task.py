#!/usr/bin/env python3
"""Generate the task fixtures AND derive the gold from the same data.

One source of truth: the register, the contexts and the mention export are
declared here, the audit policy is implemented here, and every input file,
the gold deliverables and the verifier pins are emitted from it. Gold cannot
drift from the fixtures because it is computed from them.

    python3 build_task.py
"""
import csv, io, json
from collections import OrderedDict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INP  = ROOT / "environment" / "input"

# --------------------------------------------------------------------------
# The register. A record governs a (district, subject) from its effective date
# until a later record on the same point displaces it. BR- records are the
# regulation, AG- records the trade guide; where both take effect on the same
# day for the same point, the regulation governs.
#
# holding: (context_field, value_that_makes_it_required) or None for an
# unconditional holding. required=True/False gives the unconditional reading.
# --------------------------------------------------------------------------
R = [
 # id      district subject             effective     required  condition                                  holding
 ("BR-201","D-ARD","brand_permit",      "2026-01-05", True,  None,
  "A brand whose products are offered at a tasting holds a state tasting permit for the tasting period."),
 ("AG-301","D-ARD","brand_permit",      "2025-11-10", True,  None,
  "The brand needs a state tasting permit covering the dates."),
 ("BR-202","D-ARD","server_permit",     "2026-02-02", True,  ("every_server_is_holder_employee","no"),
  "Any person who conducts a tasting and is not an employee of the permit holder holds a solicitor permit of their own; the holder's own employees are covered by the holder's permit."),
 ("AG-302","D-ARD","server_permit",     "2026-02-02", False, None,
  "Staff at the table work under the brand's permit and need no permit of their own."),
 ("BR-203","D-BEL","store_permit",      "2026-01-19", True,  None,
  "A retail store at which a tasting is held holds its own tasting permit."),
 ("BR-204","D-BEL","advance_notice",    "2026-01-19", True,  None,
  "Notice of each tasting is filed with the division before the tasting day."),
 ("AG-304","D-BEL","advance_notice",    "2026-03-16", False, None,
  "No advance notice of an event need be filed."),
 ("BR-205","D-COR","owner_consent",     "2026-02-09", True,  ("store_holds_own_permit","no"),
  "Where the store holds no tasting permit in its own name, the written consent of the store owner is filed and kept; where it does, that permit stands as its consent."),
 ("AG-305","D-COR","sample_size",       "2026-01-26", True,  ("tasting_open_to_public","yes"),
  "At a tasting open to the public every sample is kept within the prescribed size; at a trade-only tasting no size limit applies."),
 ("BR-206","D-ARD","brand_rep_present", "2026-02-16", False, None,
  "No representative of the brand need be present at a tasting."),
 ("BR-216","D-ARD","brand_rep_present", "2026-03-30", True,  ("every_server_is_holder_employee","no"),
  "A representative of the brand is present at any tasting not conducted by an employee of the permit holder."),
 ("BR-207","D-BEL","age_verification",  "2026-01-12", True,  None,
  "The age of every person served is verified before service."),
 ("BR-208","D-BEL","signage",           "2026-02-23", True,  ("every_server_is_holder_employee","no"),
  "A notice in the prescribed form is posted at the tasting table, unless every person serving is an employee of the permit holder."),
 ("AG-308","D-BEL","signage",           "2026-04-13", False, None,
  "No notice need be posted at the tasting table."),
 ("BR-209","D-COR","permit_per_store",  "2026-02-09", False, None,
  "One tasting permit covers every store at which the holder offers tastings in the permit period; no separate permit per store is issued."),
 ("AG-306","D-COR","tasting_log",       "2026-01-26", True,  None,
  "Keep a log of each tasting: date, store, product, servings."),
 ("AG-307","D-DUN","server_training",   "2026-02-02", True,  ("event_inside_licensed_area","no"),
  "A person serving at a tasting held outside the licensed area holds a current training certificate; inside it, none is needed."),
 ("BR-217","D-DUN","server_training",   "2026-04-20", False, None,
  "No training certificate is required of a person serving at a tasting."),
 ("AG-310","D-DUN","post_event_report", "2026-03-02", True,  None,
  "File a short report after each event."),
 ("BR-210","D-DUN","tasting_hours",     "2026-01-12", True,  None,
  "Tastings are held within the hours the permit states."),
 ("BR-211","D-COR","sealed_containers", "2026-03-09", True,  None,
  "Product for a tasting arrives in sealed containers opened at the table."),
 ("AG-311","D-ARD","tasting_hours",     "2026-02-16", True,  None,
  "Stay within the hours on the permit."),
 ("BR-218","D-BEL","store_permit",      "2026-04-27", False, None,
  "A store at which a tasting is held need not hold a permit of its own."),
 ("AG-312","D-DUN","insurance_filed",   "2026-05-18", True,  None,
  "File a certificate of insurance with the division."),
]
REC = {r[0]: dict(zip(("id","district","subject","effective","required","cond","holding"), r)) for r in R}

def governs(district, subject, when):
    """Most recent record on the point effective on or before `when`.
    Regulation displaces guide on the same effective date."""
    live = [r for r in REC.values()
            if r["district"] == district and r["subject"] == subject and r["effective"] <= when]
    if not live:
        return None
    newest = max(r["effective"] for r in live)
    tied = [r for r in live if r["effective"] == newest]
    reg = [r for r in tied if r["id"].startswith("BR-")]
    return (reg or tied)[0]

# --------------------------------------------------------------------------
# Items. Each is one compliance position the agency's checklist takes.
#   (district, subject, event_date, draft, ctx_overrides, cites)
# draft: what the checklist asserts — "needed" / "not_needed"
# cites: the section the draft row cited (may differ from the governing one)
# --------------------------------------------------------------------------
CTX_FIELDS = ["every_server_is_holder_employee","store_holds_own_permit","tasting_open_to_public",
              "event_inside_licensed_area","product_sold_at_event","brand_products_only",
              "containers_sealed_on_arrival","inside_permitted_hours"]
CTX_DEFAULT = {"every_server_is_holder_employee":"no","store_holds_own_permit":"yes",
               "tasting_open_to_public":"yes","event_inside_licensed_area":"yes",
               "product_sold_at_event":"no","brand_products_only":"yes",
               "containers_sealed_on_arrival":"yes","inside_permitted_hours":"yes"}

ITEMS = [
 # --- straightforward, spread over the register's dates ------------------
 ("D-ARD","brand_permit",      "2026-03-07","needed",     {}, "BR-201"),
 ("D-BEL","store_permit",      "2026-03-08","needed",     {}, "AG-303"),
 ("D-BEL","age_verification",  "2026-03-08","needed",     {}, "BR-207"),
 ("D-DUN","tasting_hours",     "2026-03-14","needed",     {}, "BR-210"),
 ("D-ARD","tasting_hours",     "2026-03-14","needed",     {}, "AG-311"),
 ("D-COR","tasting_log",       "2026-03-15","needed",     {}, "AG-306"),
 ("D-COR","permit_per_store",  "2026-03-15","needed",     {}, "BR-209"),
 ("D-COR","sealed_containers", "2026-03-21","needed",     {}, "BR-211"),
 # --- the guide-vs-regulation conflict, now settled by date --------------
 ("D-ARD","server_permit",     "2026-03-07","not_needed", {}, "AG-302"),
 ("D-ARD","server_permit",     "2026-02-01","not_needed", {}, "AG-302"),   # BEFORE either took effect
 # --- superseded records: the answer depends on WHEN ---------------------
 ("D-ARD","brand_rep_present", "2026-03-01","needed",     {}, "BR-206"),   # BR-206 still in force
 ("D-ARD","brand_rep_present", "2026-04-05","needed",     {}, "BR-206"),   # BR-216 has displaced it
 ("D-BEL","advance_notice",    "2026-03-01","not_needed", {}, "AG-304"),   # BR-204 in force
 ("D-BEL","advance_notice",    "2026-03-22","not_needed", {}, "AG-304"),   # AG-304 now displaces it
 ("D-BEL","signage",           "2026-03-08","not_needed", {}, "BR-208"),
 ("D-BEL","signage",           "2026-04-19","not_needed", {}, "BR-208"),   # AG-308 displaces
 ("D-DUN","server_training",   "2026-03-14","not_needed", {}, "AG-307"),
 ("D-DUN","server_training",   "2026-04-26","not_needed", {}, "AG-307"),   # BR-217 displaces
 ("D-BEL","store_permit",      "2026-05-03","needed",     {}, "AG-303"),   # BR-218 displaces
 # --- context decides ----------------------------------------------------
 ("D-COR","owner_consent",     "2026-03-15","needed",     {"store_holds_own_permit":"no"}, "BR-205"),
 ("D-COR","owner_consent",     "2026-03-21","needed",     {}, "BR-205"),
 ("D-COR","sample_size",       "2026-03-15","needed",     {"tasting_open_to_public":"yes"}, "AG-305"),
 ("D-COR","sample_size",       "2026-03-21","needed",     {"tasting_open_to_public":"no"}, "AG-305"),
 ("D-ARD","server_permit",     "2026-03-28","not_needed", {"every_server_is_holder_employee":"yes"}, "AG-302"),
 ("D-BEL","signage",           "2026-03-15","not_needed", {"every_server_is_holder_employee":"yes"}, "BR-208"),
 ("D-DUN","server_training",   "2026-03-21","not_needed", {"every_server_is_holder_employee":"yes"}, "AG-307"),
 # --- nothing governs: no record on the point, or none yet in force ------
 ("D-DUN","insurance_filed",   "2026-03-14","needed",     {}, "BR-299"),   # AG-312 not yet effective
 ("D-ARD","server_id_card",    "2026-03-07","needed",     {}, "BR-298"),   # no record at all
 ("D-COR","local_ordinance",   "2026-03-15","needed",     {}, "AG-399"),
 ("D-BEL","insurance_filed",   "2026-03-08","needed",     {}, "BR-299"),
 ("D-ARD","post_event_report", "2026-03-07","not_needed", {}, "AG-310"),   # AG-310 is D-DUN only
 ("D-DUN","post_event_report", "2026-03-14","not_needed", {}, "AG-310"),
 ("D-DUN","post_event_report", "2026-02-20","not_needed", {}, "AG-310"),   # before AG-310 took effect
 ("D-COR","brand_permit",      "2026-03-21","needed",     {}, "BR-201"),   # BR-201 is D-ARD only
 ("D-BEL","tasting_log",       "2026-03-08","needed",     {}, "AG-306"),   # AG-306 is D-COR only
]

# Extra mentions: some positions are recorded in more than one checklist
# section, sometimes citing a different section the second time.
EXTRA = {2:[("AG-303",)], 5:[("AG-306",)], 8:[("AG-302",),("BR-202",)], 11:[("BR-216",)],
         13:[("AG-304",)], 15:[("AG-308",)], 17:[("BR-217",)], 19:[("BR-205",)],
         22:[("AG-305",)], 26:[("BR-299",)], 28:[("AG-399",)], 31:[("AG-310",)],
         33:[("BR-201",)], 0:[("AG-301",)], 6:[("BR-209",)]}
SECTIONS = ["Permits","Staffing","At the table","Records","Closing"]

# What each subject is about, so the register reads as a register.
SUBJ = {
 "brand_permit":"a state tasting permit held by the brand",
 "server_permit":"a solicitor permit held by each person serving",
 "store_permit":"a tasting permit held by the store in its own name",
 "advance_notice":"notice of the tasting filed with the division beforehand",
 "owner_consent":"the store owner's written consent on file",
 "sample_size":"each sample kept within the prescribed size",
 "brand_rep_present":"a representative of the brand present at the table",
 "age_verification":"the age of every person served verified before service",
 "signage":"a notice in the prescribed form posted at the tasting table",
 "permit_per_store":"a separate tasting permit for each store",
 "tasting_log":"a log of each tasting kept by the holder",
 "server_training":"a current training certificate held by each server",
 "post_event_report":"a report filed with the division after the event",
 "tasting_hours":"the tasting held within the hours the permit states",
 "sealed_containers":"product arriving in sealed containers opened at the table",
 "insurance_filed":"a certificate of insurance filed with the division",
 "server_id_card":"a state identification card carried by each server",
 "local_ordinance":"the municipality's ordinance reviewed for the store",
}

items, contexts, mentions = [], [], []
for i, (dist, subj, when, draft, over, cites) in enumerate(ITEMS):
    iid, cid = f"IT-{101+i}", f"CX-{201+i}"
    ctx = dict(CTX_DEFAULT); ctx.update(over)
    items.append(dict(item_id=iid, district=dist, subject=subj, event_date=when,
                      draft=draft, context_id=cid))
    contexts.append(dict(context_id=cid, **ctx))
    for n, cite in enumerate([(cites,)] + EXTRA.get(i, [])):
        mentions.append(dict(mention_ref=f"MR-{len(mentions)+1:03d}", item_id=iid,
                             checklist_section=SECTIONS[(i + n) % len(SECTIONS)],
                             event_date=when, district=dist, subject=subj,
                             draft_position=draft, cited_section=cite[0], context_id=cid))

# --------------------------------------------------------------------------
# The audit policy, implemented once.
# --------------------------------------------------------------------------
def status_of(it):
    rec = governs(it["district"], it["subject"], it["event_date"])
    if rec is None:
        return "UNADDRESSED", "NONE"
    if rec["cond"] is None:
        return ("REQUIRED" if rec["required"] else "NOT_REQUIRED"), rec["id"]
    field, trigger = rec["cond"]
    ctx = next(c for c in contexts if c["context_id"] == it["context_id"])
    hit = ctx[field] == trigger
    return ("REQUIRED" if hit == rec["required"] else "NOT_REQUIRED"), rec["id"]

rows, wrong, corrected = [], [], []
for it in items:
    st, sec = status_of(it)
    mine = [m for m in mentions if m["item_id"] == it["item_id"]]
    rows.append(dict(item_id=it["item_id"], mention_count=len(mine),
                     status=st, governing_section=sec))
    if (it["draft"] == "not_needed" and st == "REQUIRED") or (it["draft"] == "needed" and st == "NOT_REQUIRED"):
        wrong.append(it["item_id"])
    if sec != "NONE" and any(m["cited_section"] != sec for m in mine):
        corrected.append(it["item_id"])

RESULTS = OrderedDict([
 ("required_count",                 sum(1 for r in rows if r["status"]=="REQUIRED")),
 ("not_required_count",             sum(1 for r in rows if r["status"]=="NOT_REQUIRED")),
 ("unaddressed_count",              sum(1 for r in rows if r["status"]=="UNADDRESSED")),
 ("draft_wrong_count",              len(wrong)),
 ("corrected_citation_count",       len(corrected)),
 ("distinct_governing_section_count", len({r["governing_section"] for r in rows if r["governing_section"]!="NONE"})),
 ("distinct_item_count",            len(rows)),
 ("checklist_mention_count",        len(mentions)),
])

def w_csv(path, rows, cols):
    o = io.StringIO(); wr = csv.DictWriter(o, fieldnames=cols, lineterminator="\n")
    wr.writeheader(); wr.writerows([{k: r[k] for k in cols} for r in rows])
    Path(path).write_text(o.getvalue(), encoding="utf-8")

INP.mkdir(parents=True, exist_ok=True)
for stale in ("checklist_items.csv","regulation_extract.md","association_guide.md",
              "review_protocol.md","submission_format.md","tasting_schedule.csv"):
    (INP / stale).unlink(missing_ok=True)

w_csv(INP/"checklist_mentions.csv", mentions,
      ["mention_ref","item_id","checklist_section","event_date","district","subject",
       "draft_position","cited_section","context_id"])
w_csv(INP/"tasting_context.csv", contexts, ["context_id"] + CTX_FIELDS)
w_csv(INP/"citation_manifest.csv",
      [dict(cited_section=s, record_on_file=("yes" if s in REC else "no"),
            batch=f"B-{(n%3)+1}", received_on="2026-05-04")
       for n, s in enumerate(sorted({m["cited_section"] for m in mentions}))],
      ["cited_section","record_on_file","batch","received_on"])
w_csv(INP/"district_control_totals.csv",
      [dict(district=d,
            mentions_reported=sum(1 for m in mentions if m["district"]==d),
            items_reported=sum(1 for i in items if i["district"]==d),
            contexts_attached=sum(1 for i in items if i["district"]==d))
       for d in sorted({i["district"] for i in items})],
      ["district","mentions_reported","items_reported","contexts_attached"])

reg = ["# Source register — tastings at retail", "",
       "Every record the programme holds. A record carries the licensing district it",
       "applies in, the subject it speaks to, and the date it took effect; the holding is",
       "what the record holds. `BR-` records are the beverage-control regulation, `AG-`",
       "records the trade association's guide.", ""]
for head, pref in (("Regulation","BR-"), ("Association guide","AG-")):
    reg.append(f"## {head}\n")
    for r in sorted((x for x in REC.values() if x["id"].startswith(pref)), key=lambda x: x["effective"]):
        reg.append(f"### {r['id']} — {r['district']}, {r['effective']} — subject `{r['subject']}`\n")
        reg.append(r["holding"] + "\n")
(INP/"source_register.md").write_text("\n".join(reg), encoding="utf-8")

(INP/"delivery_note.md").write_text(f"""# Delivery note: tasting-programme checklist extract

Prepared by the compliance team. Dates are ISO `YYYY-MM-DD`. The extract was taken
on 2026-05-04, before the season opens.

`checklist_mentions.csv`: the positions recorded in the checklist at the extract date.
Columns: `mention_ref`, `item_id`, `checklist_section`, `event_date`, `district`,
`subject`, `draft_position`, `cited_section`, `context_id`.

`district_control_totals.csv`: what each district section reports it contains.
Columns: `district`, `mentions_reported`, `items_reported`, `contexts_attached`.

`citation_manifest.csv`: the sections the checklist cites, as recorded by the team.
Columns: `cited_section`, `record_on_file`, `batch`, `received_on`.

`tasting_context.csv`: the facts recorded for each position by the events team.
Columns: `context_id`, {", ".join('`'+c+'`' for c in CTX_FIELDS)}.
""", encoding="utf-8")

(INP/"audit_protocol.md").write_text("""# Tasting-programme checklist audit policy (TP-8)

This is revision 8 of the reference for whether a checklist position complies with
the source register before the season opens.

## 0. What is audited

The unit of audit is the checklist item: one position the checklist has recorded
under an `item_id`.

## 1. Governing record

A checklist item is governed by the most recent record for its district and subject
that took effect on or before the item's event date. A later record does not apply
early, and a newer record displaces an older record on the same point. Where a
regulation record and a guide record take effect on the same day for the same point,
the regulation governs.

## 2. Items nothing governs

Where no record governs an item, its status is `UNADDRESSED` and its governing
section is `NONE`, whatever the checklist cites.

## 3. How an item is judged

The governing record's holding is applied to the context recorded for the item. An
item is `REQUIRED` where the holding requires the thing on those facts and
`NOT_REQUIRED` where it does not. The draft's own position never sets the status.

## 4. When the draft is wrong

The draft has an item wrong where it marks as not needed a thing that is `REQUIRED`,
or as needed a thing that is `NOT_REQUIRED`. An `UNADDRESSED` item is neither.

## 5. Corrected citations

An item governed by a record other than `NONE` is a corrected-citation item where any
section cited by its mentions differs from its governing section.

## 6. The audit table

The table carries one row per checklist item, in the order each `item_id` first
appears in the mention export. `mention_count` is the number of mention rows
carrying that `item_id`.

## 7. The figures

`required_count`, `not_required_count` and `unaddressed_count` are the numbers of
items whose status is each of those; together they are every item.

`draft_wrong_count` is the number of items the draft has wrong under section 4.

`corrected_citation_count` is the number of corrected-citation items under section 5.

`distinct_governing_section_count` counts the different governing sections the
table carries. `NONE` is not a section and is not counted.

`distinct_item_count` is the number of items, that is the number of rows in the
table. `checklist_mention_count` is the number of mention rows in the export.
""", encoding="utf-8")

# --------------------------------------------------------------------------
# Gold deliverables — no prose deliverable, following the reference bundle.
# --------------------------------------------------------------------------
SOL = ROOT / "solution" / "files"; SOL.mkdir(parents=True, exist_ok=True)
for stale in ("answer.md",): (SOL / stale).unlink(missing_ok=True)
w_csv(SOL/"checklist_audit.csv", rows, ["item_id","mention_count","status","governing_section"])
(SOL/"results.json").write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")

# --------------------------------------------------------------------------
# Instruction — a colleague's request, no recipe, no /app/input paths dumped.
# --------------------------------------------------------------------------
(ROOT/"instruction.md").write_text("""# Task

The compliance team needs the season's checklist position settled before the
programme opens. Work from the checklist mention export, the district control
totals, the citation manifest, the tasting context file and the delivery note
that came with them, and apply the checklist audit policy and source register.
Save `checklist_audit.csv` with one row per checklist item and the columns
`item_id`, `mention_count`, `status`, `governing_section`.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `checklist_audit.csv`: Checklist item audit table
    - `results.json`: a JSON object with the keys `required_count`, `not_required_count`, `unaddressed_count`, `draft_wrong_count`, `corrected_citation_count`, `distinct_governing_section_count`, `distinct_item_count`, `checklist_mention_count`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
""", encoding="utf-8")

# --------------------------------------------------------------------------
# Verifiers: every check core, one per figure, following the reference.
# --------------------------------------------------------------------------
def V(name, why, src, assertion):
    return OrderedDict(name=name, metadata=OrderedDict(how_justification=src[2],
                       why_justification=why, tag="core"),
                       source=OrderedDict(type="file", file=OrderedDict(
                           type=src[0], command=src[1], arguments=src[3])),
                       assertion=assertion)
def det(path, cmp, expected):
    return OrderedDict(type="deterministic", expected=expected,
                       deterministic=OrderedDict(path=path, comparison=cmp))

TRAP = rows[11]["item_id"]                     # superseded-record item
# table_equals compares cells as strings
tbl  = {r["item_id"]: {"mention_count": str(r["mention_count"]), "status": r["status"],
                       "governing_section": r["governing_section"]} for r in rows}
vs = [
 V("register_exists","The audit table is in the submission.",
   ("filesystem","check_path_exists","Checks checklist_audit.csv is present as a file.",{"path":"checklist_audit.csv"}),
   det("$.is_file","equals",True)),
 V("register_header","The layout names the header and it is matched exactly.",
   ("csv","extract_text","Opens checklist_audit.csv with csv.extract_text and applies regex_match.",{"path":"checklist_audit.csv"}),
   det("$.text","regex_match",
       r"(?i)\A\x22?item_id\x22?[ \t]*,[ \t]*\x22?mention_count\x22?[ \t]*,[ \t]*\x22?status\x22?[ \t]*,[ \t]*\x22?governing_section\x22?[ \t]*\r?\n")),
 V("register_table_trap_superseded",
   "The item whose governing record was displaced by a later one, graded cell by cell.",
   ("csv","read_rows","Parses checklist_audit.csv and applies table_equals to the trap row.",{"path":"checklist_audit.csv"}),
   det("$","table_equals",OrderedDict(id_column="item_id", rows={TRAP: tbl[TRAP]},
        cell_types=OrderedDict(governing_section="id")))),
 V("register_table","One row per item in first-appearance order, every graded cell compared.",
   ("csv","read_rows","Parses checklist_audit.csv and applies table_equals to every graded cell.",{"path":"checklist_audit.csv"}),
   det("$","table_equals",OrderedDict(id_column="item_id",
        rows={k: v for k, v in tbl.items() if k != TRAP},
        row_set=[r["item_id"] for r in rows], row_set_ordered=True,
        columns=["item_id","mention_count","status","governing_section"],
        cell_types=OrderedDict(governing_section="id")))),
 V("results_exists","The figures file is in the submission.",
   ("filesystem","check_path_exists","Checks results.json is present as a file.",{"path":"results.json"}),
   det("$.is_file","equals",True)),
 V("results_shape","The object carries exactly the listed keys and nothing else.",
   ("json","read_file","Reads results.json and applies object_equals over the key set.",{"path":"results.json"}),
   det("$","object_equals",OrderedDict(
       keys={k: OrderedDict(value=v, tolerance=None) for k, v in RESULTS.items()}, closed=True))),
]
for k, v in RESULTS.items():
    vs.append(V(f"result_{k}", f"`{k}` is stated as the figure the policy defines.",
                ("json","read_file",f"Reads results.json and compares $.{k}.",{"path":"results.json"}),
                det(f"$.{k}","equals",v)))

spec = OrderedDict(task_id="law-b39_l5-tasting-programme-checklist-audit", verifiers=vs)
for p in ("tests/verifier.json","tests/manifest.json"):
    (ROOT/p).write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")

print(f"items={len(items)} mentions={len(mentions)} records={len(REC)} verifiers={len(vs)}")
print("results:", json.dumps(RESULTS))
print("trap row:", TRAP, tbl[TRAP])
