# Commission recognition policy (COMM-POL-6)

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

Partners label the end-user type differently. These are the same type:

| in a partner report | end-user type |
|---|---|
| `new`, `New`, `New Business` | new |
| `renewal`, `Renewal` | renewal |
| `house`, `House`, `House Account` | house |

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
