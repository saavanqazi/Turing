# Submission format

Deliver exactly these files, in your working directory:

- `answer.md` — The written review, giving how many checklist items the draft got wrong
- `checklist_audit.csv` — One verdict row per checklist item: whether the thing is required, and the section that governs it
- `results.json` — a JSON object; see below.

## `answer.md`

`answer.md` states `Checklist items the draft got wrong: <count>` — the figure beside its label, in the sentence that names it. At least sixty words of prose. Each figure stands beside its label once, stated as the finding — not offered as one of two candidates.

## `checklist_audit.csv`

Header, exactly: `item_id,status,governing_section`
One row per record, keyed by `item_id`.
`status` takes exactly one of: `REQUIRED`, `NOT_REQUIRED`, `UNADDRESSED`.
Keep the items of `input/checklist_items.csv` in their numbered order, one verdict row each, carrying the status and the governing section (`BR-…` or `AG-…`; `NONE` where neither document addresses the subject).

Example (placeholder values):

```
item_id,status,governing_section
IT-100,REQUIRED,BR-200
```

## `results.json`

A JSON object with exactly these keys and nothing else:

- `required_count` — number
- `not_required_count` — number
- `unaddressed_count` — number
- `draft_wrong_count` — number

Shape example (placeholder values):

```json
{
  "required_count": 0,
  "not_required_count": 0,
  "unaddressed_count": 0,
  "draft_wrong_count": 0
}
```
