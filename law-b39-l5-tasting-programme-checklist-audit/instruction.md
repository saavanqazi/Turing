# Task

I run a marketing agency that stages tastings in licensed stores on a brand's behalf, and the compliance checklist my team drafted was built from the trade association's guide rather than from the regulation. Before the season starts I want every item settled. The items are numbered in `input/checklist_items.csv`; the regulation is in `input/regulation_extract.md`; the guide is `input/association_guide.md`; `input/review_protocol.md` says how the two are read together. Tell me for each item whether the thing it describes is required, not required, or addressed by neither document, and cite the section that governs. Write the review to `answer.md`, the verdict table to `checklist_audit.csv`, and the four totals to `results.json`: items required, items not required, items unaddressed, and items the draft got wrong (the draft-wrong count). Layout is in `input/submission_format.md`.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `answer.md` — The written review, giving how many checklist items the draft got wrong
    - `checklist_audit.csv` — One verdict row per checklist item: whether the thing is required, and the section that governs it
    - `results.json` — a JSON object with the keys `required_count`, `not_required_count`, `unaddressed_count`, `draft_wrong_count`
- The exact headers, key sets, allowed values and worked examples are specified in `input/submission_format.md` — follow it precisely.
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is `/app`, and it is writable.
- The read-only attachments referred to as `input/` are at `/app/input`.
- Write every deliverable into `/app`, at the exact filenames listed above.
