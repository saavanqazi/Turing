# Tasting-programme checklist audit policy (TP-8)

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
