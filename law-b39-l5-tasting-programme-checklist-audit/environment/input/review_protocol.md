# Review protocol — tasting-programme checklist

Applies to every item in `checklist_items.csv`, read against `regulation_extract.md`
and `association_guide.md`.

## TP-701 Which document governs

The regulation extract governs every subject it addresses. Where the association guide and the regulation take different positions on a subject, the regulation governs and the guide gives way, whatever section the checklist item cites. The governing section of an item on a subject the regulation addresses is the regulation section on that subject, never a guide note (`TP-701`).

## TP-702 Subjects the regulation does not address

Where the regulation does not address a subject, the guide note on that subject governs and the item is judged under it. Where neither document addresses the subject, nothing governs: the item is UNADDRESSED and the governing section is `NONE`, whatever the draft says (`TP-702`).

## TP-703 How an item is judged

Under its governing section an item is REQUIRED where the section requires the thing the item describes and NOT_REQUIRED where the section says it is not required. The draft's own position never sets the status (`TP-703`).

## TP-704 When the draft is wrong

The draft has an item wrong where it marks as not needed a thing that is REQUIRED, or as needed a thing that is NOT_REQUIRED. An UNADDRESSED item is neither right nor wrong (`TP-704`).

## TP-705 The register

`governing_section` is the id of the regulation section or the guide note that governs the item, as it appears in the documents (`TP-705`).

## Figures

`required_count` is the number of items whose status is REQUIRED.
`not_required_count` is the number of items whose status is NOT_REQUIRED.
`unaddressed_count` is the number of items whose status is UNADDRESSED.
`draft_wrong_count` is the draft-wrong count: the items the draft got wrong under `TP-704`.
In the answer, `Checklist items the draft got wrong` is the number of items whose draft position is the
opposite of their status.
