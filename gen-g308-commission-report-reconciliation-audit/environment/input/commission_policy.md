# Commission recognition policy (COMM-POL-6)

Binding for the June 2026 commission run once the partner reports and the NetSuite ledger
extract are consolidated into one line list. Where a partner report and this policy
disagree, this policy wins.

## R1 — Standard rate by end-user type

| end-user type | standard rate |
|---|---|
| new | 8% |
| renewal | 4% |
| house | 0% |

A line whose reported rate does not match the standard rate for its end-user type is a
`RATE_MISMATCH`.

## R2 — Ledger match

Every commissionable line (standard or approved rate above 0%) must be matched to a June
NetSuite revenue record before it is paid. A commissionable line with no ledger match is
`UNMATCHED_TO_LEDGER`.

## R3 — Duplicate lines

The same `deal_id` must not appear in more than one source report. A deal that does is a
`DUPLICATE_LINE` on every occurrence.

## R4 — VP-approved rate overrides

A deal named in the commission exceptions register with `status = active` is paid at the
register's approved rate instead of the standard rate for its end-user type. For that deal
the approved rate is the rate R1 is read against. An exception that is not `active` does
not displace the standard rate.

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
