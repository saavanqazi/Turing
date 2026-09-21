#!/usr/bin/env python3
"""Generate the fixtures AND derive the gold from the same data.

The register, the contexts and the mention export are declared here, the audit
policy is implemented here, and every input file, both gold deliverables and the
verifier pins are emitted from it, so gold cannot drift from the fixtures.
"""
import csv, io, json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INP  = ROOT / "environment" / "input"

# Each subject has two opposed positions. A holding yields one of them; a
# checklist item asserts one of them; agreement is SUPPORTED, opposition
# CONTRADICTED.
OPPOSITE = {
 "own_permit_required":"covered_by_holder",  "covered_by_holder":"own_permit_required",
 "store_permit_required":"no_store_permit",  "no_store_permit":"store_permit_required",
 "brand_permit_required":"no_brand_permit",  "no_brand_permit":"brand_permit_required",
 "notice_required":"no_notice",              "no_notice":"notice_required",
 "consent_on_file":"permit_is_consent",      "permit_is_consent":"consent_on_file",
 "size_limited":"no_size_limit",             "no_size_limit":"size_limited",
 "certificate_required":"no_certificate",    "no_certificate":"certificate_required",
 "rep_attends":"no_rep",                     "no_rep":"rep_attends",
 "signage_posted":"no_signage",              "no_signage":"signage_posted",
 "one_permit_covers":"permit_per_store",     "permit_per_store":"one_permit_covers",
 "log_required":"no_log",                    "no_log":"log_required",
 "report_required":"no_report",              "no_report":"report_required",
 "age_checked":"no_age_check",               "no_age_check":"age_checked",
 "hours_observed":"no_hours_limit",          "no_hours_limit":"hours_observed",
 "sealed_on_arrival":"no_seal_needed",       "no_seal_needed":"sealed_on_arrival",
}

# Register. `yields` is the position the holding gives; where `cond` is set the
# holding gives that position only when the recorded fact matches, and the
# opposite otherwise.
R = [
 ("BR-201","D-ARD","brand_permit",     "2026-01-05","brand_permit_required",None,
  "A brand whose products are offered at a tasting holds a state tasting permit for the tasting period."),
 ("AG-301","D-ARD","brand_permit",     "2025-11-10","brand_permit_required",None,
  "The brand needs a state tasting permit covering the dates."),
 ("BR-202","D-ARD","server_permit",    "2026-02-02","own_permit_required",("every_server_is_holder_employee","no"),
  "Any person who conducts a tasting and is not an employee of the permit holder holds a solicitor permit of their own; the holder's own employees are covered by the holder's permit."),
 ("AG-302","D-ARD","server_permit",    "2026-02-02","covered_by_holder",None,
  "Staff at the table work under the brand's permit and need no permit of their own."),
 ("BR-203","D-BEL","store_permit",     "2026-01-19","store_permit_required",None,
  "A retail store at which a tasting is held holds its own tasting permit."),
 ("BR-218","D-BEL","store_permit",     "2026-04-27","no_store_permit",None,
  "A store at which a tasting is held need not hold a permit of its own."),
 ("BR-204","D-BEL","advance_notice",   "2026-01-19","notice_required",None,
  "Notice of each tasting is filed with the division before the tasting day."),
 ("AG-304","D-BEL","advance_notice",   "2026-03-16","no_notice",None,
  "No advance notice of an event need be filed."),
 ("BR-205","D-COR","owner_consent",    "2026-02-09","consent_on_file",("store_holds_own_permit","no"),
  "Where the store holds no tasting permit in its own name, the written consent of the store owner is filed and kept; where it does, that permit stands as its consent."),
 ("AG-305","D-COR","sample_size",      "2026-01-26","size_limited",("tasting_open_to_public","yes"),
  "At a tasting open to the public every sample is kept within the prescribed size; at a trade-only tasting no size limit applies."),
 ("BR-206","D-ARD","brand_rep",        "2026-02-16","no_rep",None,
  "No representative of the brand need be present at a tasting."),
 ("BR-216","D-ARD","brand_rep",        "2026-03-30","rep_attends",("every_server_is_holder_employee","no"),
  "A representative of the brand is present at any tasting not conducted by an employee of the permit holder."),
 ("BR-207","D-BEL","age_check",        "2026-01-12","age_checked",None,
  "The age of every person served is verified before service."),
 ("BR-208","D-BEL","signage",          "2026-02-23","signage_posted",("every_server_is_holder_employee","no"),
  "A notice in the prescribed form is posted at the tasting table, unless every person serving is an employee of the permit holder."),
 ("AG-308","D-BEL","signage",          "2026-04-13","no_signage",None,
  "No notice need be posted at the tasting table."),
 ("BR-209","D-COR","permit_scope",     "2026-02-09","one_permit_covers",None,
  "One tasting permit covers every store at which the holder offers tastings in the permit period; no separate permit per store is issued."),
 ("AG-306","D-COR","tasting_log",      "2026-01-26","log_required",None,
  "Keep a log of each tasting: date, store, product, servings."),
 ("AG-307","D-DUN","server_training",  "2026-02-02","certificate_required",("event_inside_licensed_area","no"),
  "A person serving at a tasting held outside the licensed area holds a current training certificate; inside it, none is needed."),
 ("BR-217","D-DUN","server_training",  "2026-04-20","no_certificate",None,
  "No training certificate is required of a person serving at a tasting."),
 ("AG-310","D-DUN","post_event_report","2026-03-02","report_required",None,
  "File a short report after each event."),
 ("BR-210","D-DUN","tasting_hours",    "2026-01-12","hours_observed",None,
  "Tastings are held within the hours the permit states."),
 ("AG-311","D-ARD","tasting_hours",    "2026-02-16","hours_observed",None,
  "Stay within the hours on the permit."),
 ("BR-211","D-COR","sealed_product",   "2026-03-09","sealed_on_arrival",None,
  "Product for a tasting arrives in sealed containers opened at the table."),
 ("AG-312","D-DUN","insurance",        "2026-05-18","insurance_filed",None,
  "File a certificate of insurance with the division."),
]
REC = {r[0]: dict(zip(("id","district","subject","effective","yields","cond","holding"), r)) for r in R}

def governs(district, subject, when):
    live = [r for r in REC.values() if r["district"]==district and r["subject"]==subject
            and r["effective"] <= when]
    if not live: return None
    newest = max(r["effective"] for r in live)
    tied = [r for r in live if r["effective"] == newest]
    return (([t for t in tied if t["id"].startswith("BR-")]) or tied)[0]

CTX_FIELDS = ["every_server_is_holder_employee","store_holds_own_permit","tasting_open_to_public",
              "event_inside_licensed_area","product_sold_at_event","brand_products_only",
              "containers_sealed_on_arrival","inside_permitted_hours"]
CTX_DEFAULT = {"every_server_is_holder_employee":"no","store_holds_own_permit":"yes",
               "tasting_open_to_public":"yes","event_inside_licensed_area":"yes",
               "product_sold_at_event":"no","brand_products_only":"yes",
               "containers_sealed_on_arrival":"yes","inside_permitted_hours":"yes"}

# Items. Each asserts a position in its own words.
#   (district, subject, event_date, asserted_position, ctx_overrides, cites, text)
I = [
 ("D-ARD","brand_permit","2026-03-07","brand_permit_required",{},"BR-201",
  "In Ardenne the brand must hold a state tasting permit covering the tasting period."),
 ("D-BEL","store_permit","2026-03-08","store_permit_required",{},"AG-303",
  "Belmont requires each store to hold a tasting permit in its own name."),
 ("D-BEL","store_permit","2026-05-03","store_permit_required",{},"BR-203",
  "Belmont still requires the store to hold its own permit on the May dates."),
 ("D-BEL","age_check","2026-03-08","age_checked",{},"BR-207",
  "Belmont requires the age of every person served to be verified before service."),
 ("D-DUN","tasting_hours","2026-03-14","hours_observed",{},"BR-210",
  "Dunmore requires a tasting to be held within the hours the permit states."),
 ("D-ARD","tasting_hours","2026-03-14","no_hours_limit",{},"AG-311",
  "Ardenne imposes no hours restriction on a tasting."),
 ("D-COR","tasting_log","2026-03-15","log_required",{},"AG-306",
  "Corvane requires a log of each tasting to be kept."),
 ("D-COR","permit_scope","2026-03-15","permit_per_store",{},"BR-209",
  "Corvane requires a separate tasting permit for each store."),
 ("D-COR","sealed_product","2026-03-21","sealed_on_arrival",{},"BR-211",
  "Corvane requires product to arrive in sealed containers opened at the table."),
 # the guide-vs-regulation conflict, settled by date
 ("D-ARD","server_permit","2026-03-07","covered_by_holder",{},"AG-302",
  "In Ardenne staff at the table are covered by the brand's permit and need none of their own."),
 ("D-ARD","server_permit","2026-02-01","covered_by_holder",{},"AG-302",
  "In the pre-season week Ardenne required no permit of staff at the table."),
 ("D-ARD","server_permit","2026-03-28","covered_by_holder",{"every_server_is_holder_employee":"yes"},"BR-202",
  "On the brand-staffed date Ardenne required no separate permit of the servers."),
 # superseded records: the answer depends on WHEN
 ("D-ARD","brand_rep","2026-03-01","no_rep",{},"BR-206",
  "Ardenne requires no representative of the brand at a tasting in March."),
 ("D-ARD","brand_rep","2026-04-05","no_rep",{},"BR-206",
  "Ardenne requires no representative of the brand at a tasting in April."),
 ("D-BEL","advance_notice","2026-03-01","notice_required",{},"AG-304",
  "Belmont requires notice of a March event to be filed with the division beforehand."),
 ("D-BEL","advance_notice","2026-03-22","notice_required",{},"BR-204",
  "Belmont requires notice of a late-March event to be filed with the division beforehand."),
 ("D-BEL","signage","2026-03-08","signage_posted",{},"BR-208",
  "Belmont requires the prescribed notice to be posted at the tasting table."),
 ("D-BEL","signage","2026-04-19","signage_posted",{},"BR-208",
  "Belmont requires the prescribed notice to be posted at an April tasting too."),
 ("D-BEL","signage","2026-03-15","signage_posted",{"every_server_is_holder_employee":"yes"},"BR-208",
  "Belmont requires the prescribed notice to be posted on the brand-staffed date."),
 ("D-DUN","server_training","2026-03-14","no_certificate",{},"AG-307",
  "Dunmore requires no training certificate of a person serving at these sessions."),
 ("D-DUN","server_training","2026-04-26","no_certificate",{},"AG-307",
  "Dunmore requires no training certificate at the late-April session."),
 ("D-DUN","server_training","2026-03-21","no_certificate",{"event_inside_licensed_area":"no"},"AG-307",
  "Dunmore requires no training certificate at the marquee session outside the licensed area."),
 # context decides
 ("D-COR","owner_consent","2026-03-15","consent_on_file",{"store_holds_own_permit":"no"},"BR-205",
  "Corvane requires the owner's written consent to be filed for the Oakfield date."),
 ("D-COR","owner_consent","2026-03-21","consent_on_file",{},"BR-205",
  "Corvane requires the owner's written consent to be filed for the Kingsway date."),
 ("D-COR","sample_size","2026-03-15","size_limited",{},"AG-305",
  "Corvane requires every sample to be kept within the prescribed size."),
 ("D-COR","sample_size","2026-03-21","size_limited",{"tasting_open_to_public":"no"},"AG-305",
  "Corvane requires samples at the trade morning to be kept within the prescribed size."),
 # nothing governs
 ("D-DUN","insurance","2026-03-14","insurance_filed",{},"BR-299",
  "Dunmore requires a certificate of insurance to be filed with the division."),
 ("D-ARD","server_id","2026-03-07","id_card_required",{},"BR-298",
  "Ardenne requires each server to carry a state identification card."),
 ("D-COR","local_ordinance","2026-03-15","ordinance_reviewed",{},"AG-399",
  "Corvane requires the municipality's ordinance to be reviewed for each store."),
 ("D-BEL","insurance","2026-03-08","insurance_filed",{},"BR-299",
  "Belmont requires a certificate of insurance to be filed with the division."),
 ("D-ARD","post_event_report","2026-03-07","report_required",{},"AG-310",
  "Ardenne requires a short report to be filed after each event."),
 ("D-DUN","post_event_report","2026-03-14","report_required",{},"AG-310",
  "Dunmore requires a short report to be filed after each event."),
 ("D-DUN","post_event_report","2026-02-20","report_required",{},"AG-310",
  "Dunmore required a short report after the February pilot as well."),
 ("D-COR","brand_permit","2026-03-21","brand_permit_required",{},"BR-201",
  "Corvane requires the brand to hold a state tasting permit for the period."),
 ("D-BEL","tasting_log","2026-03-08","log_required",{},"AG-306",
  "Belmont requires a log of each tasting to be kept."),
 # items asserting that the register is silent
 ("D-COR","insurance","2026-03-15","no_record",{},"BR-299",
  "The register carries no record on insurance in Corvane."),
 ("D-ARD","signage","2026-03-07","no_record",{},"BR-208",
  "The register carries no record on table signage in Ardenne."),
 ("D-BEL","permit_scope","2026-03-08","no_record",{},"BR-209",
  "The register carries no record on permit scope in Belmont."),
 ("D-DUN","tasting_hours","2026-03-14","no_record",{},"BR-210",
  "The register carries no record on hours in Dunmore."),
]

SECTIONS = ["Permits","Staffing","At the table","Records","Closing"]
EXTRA = {0:["AG-301"], 2:["BR-218"], 5:["AG-311"], 7:["BR-209"], 9:["AG-302","BR-202"],
         13:["BR-216"], 15:["AG-304"], 17:["AG-308"], 19:["BR-217"], 22:["BR-205"],
         24:["AG-305"], 27:["BR-298"], 30:["AG-310"], 33:["BR-201"], 35:["BR-299"]}

items, contexts, mentions = [], [], []
for i, (dist, subj, when, pos, over, cites, text) in enumerate(I):
    iid, cid = f"IT-{101+i}", f"CX-{201+i}"
    ctx = dict(CTX_DEFAULT); ctx.update(over)
    items.append(dict(item_id=iid, district=dist, subject=subj, event_date=when,
                      position=pos, context_id=cid, text=text))
    contexts.append(dict(context_id=cid, **ctx))
    for n, cite in enumerate([cites] + EXTRA.get(i, [])):
        mentions.append(dict(mention_ref=f"MR-{len(mentions)+1:03d}", item_id=iid,
                             checklist_section=SECTIONS[(i+n) % len(SECTIONS)], event_date=when,
                             district=dist, subject=subj, asserted_position=pos,
                             cited_section=cite, context_id=cid, item=text))

def audit(it):
    """Policy sections 1-4, implemented once."""
    rec = governs(it["district"], it["subject"], it["event_date"])
    if it["position"] == "no_record":                       # section 2
        return ("SUPPORTED" if rec is None else "CONTRADICTED"), (rec["id"] if rec else "NONE")
    if rec is None:
        return "UNSUPPORTED", "NONE"                        # section 2
    yielded = rec["yields"]
    if rec["cond"]:                                          # section 4
        f, v = rec["cond"]
        ctx = next(c for c in contexts if c["context_id"] == it["context_id"])
        if ctx[f] != v:
            yielded = OPPOSITE[yielded]
    if yielded == it["position"]:                 return "SUPPORTED",    rec["id"]
    if OPPOSITE.get(yielded) == it["position"]:   return "CONTRADICTED", rec["id"]
    return "CONTRADICTED", rec["id"]

rows, corrected = [], []
for it in items:
    st, sec = audit(it)
    mine = [m for m in mentions if m["item_id"] == it["item_id"]]
    rows.append(dict(item_id=it["item_id"], mention_count=len(mine), status=st, governing_section=sec))
    if sec != "NONE" and any(m["cited_section"] != sec for m in mine):
        corrected.append(it["item_id"])

RESULTS = OrderedDict([
 ("supported_count",      sum(1 for r in rows if r["status"]=="SUPPORTED")),
 ("contradicted_count",   sum(1 for r in rows if r["status"]=="CONTRADICTED")),
 ("unsupported_count",    sum(1 for r in rows if r["status"]=="UNSUPPORTED")),
 ("corrected_citation_count", len(corrected)),
 ("distinct_governing_section_count", len({r["governing_section"] for r in rows if r["governing_section"]!="NONE"})),
 ("distinct_item_count",  len(rows)),
 ("checklist_mention_count", len(mentions)),
])
print("items=%d mentions=%d records=%d" % (len(items), len(mentions), len(REC)))
print("results:", json.dumps(RESULTS))

def w_csv(path, rows, cols):
    o = io.StringIO(); wr = csv.DictWriter(o, fieldnames=cols, lineterminator="\n")
    wr.writeheader(); wr.writerows([{k: r[k] for k in cols} for r in rows])
    Path(path).write_text(o.getvalue(), encoding="utf-8")

INP.mkdir(parents=True, exist_ok=True)
for s in ("checklist_items.csv","regulation_extract.md","association_guide.md","review_protocol.md",
          "submission_format.md","tasting_schedule.csv","district_control_totals.csv"):
    (INP/s).unlink(missing_ok=True)

w_csv(INP/"checklist_mentions.csv", mentions,
      ["mention_ref","item_id","checklist_section","event_date","district","subject",
       "asserted_position","cited_section","context_id","item"])
w_csv(INP/"tasting_context.csv", contexts, ["context_id"] + CTX_FIELDS)
w_csv(INP/"citation_manifest.csv",
      [dict(cited_section=s, record_on_file=("yes" if s in REC else "no"),
            batch=f"B-{(n%3)+1}", received_on="2026-05-04")
       for n, s in enumerate(sorted({m["cited_section"] for m in mentions}))],
      ["cited_section","record_on_file","batch","received_on"])
w_csv(INP/"district_control_totals.csv",
      [dict(district=d, mentions_reported=sum(1 for m in mentions if m["district"]==d),
            items_reported=sum(1 for i in items if i["district"]==d),
            contexts_attached=sum(1 for i in items if i["district"]==d))
       for d in sorted({i["district"] for i in items})],
      ["district","mentions_reported","items_reported","contexts_attached"])

reg = ["# Source register — tastings at retail", "",
       "Every record the programme holds. A record carries the licensing district it applies",
       "in, the subject it speaks to and the date it took effect; the holding is what the",
       "record holds. `BR-` records are the beverage-control regulation, `AG-` records the",
       "trade association's guide.", ""]
for head, pref in (("Regulation","BR-"), ("Association guide","AG-")):
    reg.append(f"## {head}\n")
    for r in sorted((x for x in REC.values() if x["id"].startswith(pref)), key=lambda x: x["effective"]):
        reg.append(f"### {r['id']} — {r['district']}, {r['effective']} — subject `{r['subject']}`\n")
        reg.append(r["holding"] + "\n")
(INP/"source_register.md").write_text("\n".join(reg), encoding="utf-8")

(INP/"delivery_note.md").write_text(f"""# Delivery note: tasting-programme checklist extract

Prepared by the compliance team. Dates are ISO `YYYY-MM-DD`. The extract was taken on
2026-05-04, before the season opens.

`checklist_mentions.csv`: the positions recorded in the checklist at the extract date.
Columns: `mention_ref`, `item_id`, `checklist_section`, `event_date`, `district`,
`subject`, `asserted_position`, `cited_section`, `context_id`, `item`.

`district_control_totals.csv`: what each district section reports it contains.
Columns: `district`, `mentions_reported`, `items_reported`, `contexts_attached`.

`citation_manifest.csv`: the sections the checklist cites, as recorded by the team.
Columns: `cited_section`, `record_on_file`, `batch`, `received_on`.

`tasting_context.csv`: the facts recorded for each position by the events team.
Columns: `context_id`, {", ".join('`'+c+'`' for c in CTX_FIELDS)}.
""", encoding="utf-8")

(INP/"audit_protocol.md").write_text("""# Tasting-programme checklist audit policy (TP-9)

This is revision 9 of the reference for whether a checklist position complies with
the source register before the season opens.

## 0. What is audited

The unit of audit is the checklist item: one position the checklist has recorded
under an `item_id`. An item states what the register requires in the item's
district, not what the programme did; a position about conduct is not audited
here.

## 1. Governing record

A checklist item is governed by the most recent record for its district and subject
that took effect on or before the item's event date. A later record does not apply
early, and a newer record displaces an older record on the same point. Where a
regulation record and a guide record take effect on the same day for the same point,
the regulation governs.

## 2. Items that say no record exists

A checklist item that says no record exists is `SUPPORTED` where no record governs
and `CONTRADICTED` where a record governs. An item asserting anything else for which
no record governs is `UNSUPPORTED`.

## 3. How an item is judged

The governing record's holding is applied to the facts recorded for the item. That
gives one position on the item's subject. An item asserting that position is
`SUPPORTED`; an item asserting the opposing position on the same subject is
`CONTRADICTED`. Every subject has two opposing positions and no third.

## 4. Factual context

Where a holding turns on a fact, the fact recorded for the item decides which position
the holding gives. Where it turns on no fact, the holding gives the same position
whatever is recorded.

## 5. Status names

`SUPPORTED`, `CONTRADICTED` or `UNSUPPORTED`. An item carries exactly one status.

## 6. Corrected citations

An item governed by a record other than `NONE` is a corrected-citation item where any
section cited by its mentions differs from its governing section.

## 7. The audit table

The table carries one row per checklist item, in the order each `item_id` first appears
in the mention export. `mention_count` is the number of mention rows carrying that
`item_id`.

## 8. The figures

`supported_count`, `contradicted_count` and `unsupported_count` are the numbers of
items carrying each status; together they are every item.

`corrected_citation_count` is the number of corrected-citation items under section 6.

`distinct_governing_section_count` counts the different governing sections the table
carries. `NONE` is not a section and is not counted.

`distinct_item_count` is the number of rows in the table. `checklist_mention_count` is
the number of mention rows in the export.
""", encoding="utf-8")

SOL = ROOT/"solution"/"files"; SOL.mkdir(parents=True, exist_ok=True)
(SOL/"answer.md").unlink(missing_ok=True)
w_csv(SOL/"checklist_audit.csv", rows, ["item_id","mention_count","status","governing_section"])
(SOL/"results.json").write_text(json.dumps(RESULTS, indent=2)+"\n", encoding="utf-8")

(ROOT/"instruction.md").write_text("""# Task

The compliance team needs the season's checklist position settled before the
programme opens. Work from the checklist mention export, the district control
totals, the citation manifest, the tasting context file and the delivery note that
came with them, and apply the checklist audit policy and source register. Save
`checklist_audit.csv` with one row per checklist item and the columns `item_id`,
`mention_count`, `status`, `governing_section`.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `checklist_audit.csv`: Checklist item audit table
    - `results.json`: a JSON object with the keys `supported_count`, `contradicted_count`, `unsupported_count`, `corrected_citation_count`, `distinct_governing_section_count`, `distinct_item_count`, `checklist_mention_count`
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
""", encoding="utf-8")

def V(name, why, src, assertion):
    return OrderedDict(name=name, metadata=OrderedDict(how_justification=src[2],
        why_justification=why, tag="core"), source=OrderedDict(type="file",
        file=OrderedDict(type=src[0], command=src[1], arguments=src[3])), assertion=assertion)
def det(path, cmp, expected):
    return OrderedDict(type="deterministic", expected=expected,
                       deterministic=OrderedDict(path=path, comparison=cmp))

TRAP = rows[13]["item_id"]
tbl = {r["item_id"]: {"mention_count": str(r["mention_count"]), "status": r["status"],
                      "governing_section": r["governing_section"]} for r in rows}
vs = [
 V("register_exists","The audit table is in the submission.",
   ("filesystem","check_path_exists","Checks checklist_audit.csv is present as a file.",{"path":"checklist_audit.csv"}),
   det("$.is_file","equals",True)),
 V("register_header","The layout names the header and it is matched exactly.",
   ("csv","extract_text","Opens checklist_audit.csv with csv.extract_text and applies regex_match.",{"path":"checklist_audit.csv"}),
   det("$.text","regex_match",
       r"(?i)\A\x22?item_id\x22?[ \t]*,[ \t]*\x22?mention_count\x22?[ \t]*,[ \t]*\x22?status\x22?[ \t]*,[ \t]*\x22?governing_section\x22?[ \t]*\r?\n")),
 V("register_table_trap_superseded","The item whose governing record was displaced by a later one.",
   ("csv","read_rows","Parses checklist_audit.csv and applies table_equals to the trap row.",{"path":"checklist_audit.csv"}),
   det("$","table_equals",OrderedDict(id_column="item_id", rows={TRAP: tbl[TRAP]},
        cell_types=OrderedDict(governing_section="id")))),
 V("register_table","One row per item in first-appearance order, every graded cell compared.",
   ("csv","read_rows","Parses checklist_audit.csv and applies table_equals to every graded cell.",{"path":"checklist_audit.csv"}),
   det("$","table_equals",OrderedDict(id_column="item_id",
        rows={k:v for k,v in tbl.items() if k != TRAP},
        row_set=[r["item_id"] for r in rows], row_set_ordered=True,
        columns=["item_id","mention_count","status","governing_section"],
        cell_types=OrderedDict(governing_section="id")))),
 V("results_exists","The figures file is in the submission.",
   ("filesystem","check_path_exists","Checks results.json is present as a file.",{"path":"results.json"}),
   det("$.is_file","equals",True)),
 V("results_shape","The object carries exactly the listed keys and nothing else.",
   ("json","read_file","Reads results.json and applies object_equals over the key set.",{"path":"results.json"}),
   det("$","object_equals",OrderedDict(keys={k:OrderedDict(value=v,tolerance=None) for k,v in RESULTS.items()}, closed=True))),
]
for k, v in RESULTS.items():
    vs.append(V(f"result_{k}", f"`{k}` is stated as the figure section 8 defines.",
                ("json","read_file",f"Reads results.json and compares $.{k}.",{"path":"results.json"}),
                det(f"$.{k}","equals",v)))
spec = OrderedDict(task_id="law-b39_l5-tasting-programme-checklist-audit", verifiers=vs)
for p in ("tests/verifier.json","tests/manifest.json"):
    (ROOT/p).write_text(json.dumps(spec, indent=1)+"\n", encoding="utf-8")

steps = [{"name":"bash","arguments":{"command":f"cat input/{f}"}} for f in
         ("checklist_mentions.csv","tasting_context.csv","citation_manifest.csv",
          "district_control_totals.csv","source_register.md","audit_protocol.md","delivery_note.md")]
for n, m in (("checklist_audit.csv","AUDITEOF"), ("results.json","RESULTSEOF")):
    steps.append({"name":"bash","arguments":{"command":f"cat > {n} << '{m}'\n{(SOL/n).read_text()}{m}"}})
steps.append({"name":"bash","arguments":{"command":"ls -la checklist_audit.csv results.json"}})
(ROOT/"solution"/"golden_trajectory.json").write_text(json.dumps(steps, indent=2)+"\n")
print(f"verifiers={len(vs)} trap={TRAP} {tbl[TRAP]}")
leak = [c for c in CTX_FIELDS if c in (INP/"source_register.md").read_text()]
print("context columns leaking into register:", leak or "none")
