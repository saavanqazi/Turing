# Tasting-programme checklist audit policy (TP-9)

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
