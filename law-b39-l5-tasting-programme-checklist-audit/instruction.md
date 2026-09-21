# Task

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
