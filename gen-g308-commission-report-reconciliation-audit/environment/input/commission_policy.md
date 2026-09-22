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

Every commissionable line (standard or approved rate above 0%) must be matched to a
NetSuite revenue record for the run month before it is paid. A line is matched when
`netsuite_revenue_export.csv` carries a record whose `deal_id` is the line's deal id and
whose `period` is the run month. A record in any other period is not a match for this
run. A commissionable line with no such record is `UNMATCHED_TO_LEDGER`.

## R3 — Duplicate lines

The same `deal_id` must not appear in more than one partner report. A deal that does is a
`DUPLICATE_LINE` on every line it appears on.

## R4 — VP-approved rate overrides

An exception in `commission_exceptions.csv` applies to this run when its window covers any
part of the run month: `effective_from` is on or before the last day of the run month, and
`effective_to` is either empty or on or after the first day. An exception that applies is
paid at the register's `approved_rate_pct` instead of the standard rate for its end-user
type, and for that deal the approved rate is the rate R1 is read against. An exception
whose window does not cover the run month does not displace the standard rate.

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
