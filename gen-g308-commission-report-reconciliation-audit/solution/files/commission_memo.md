# June 2026 commission reconciliation — 8 lines

8 consolidated lines checked against COMM-POL-6. 5 lines are
compliant and 3 carry at least one finding.

| Deal | Source | Finding |
|---|---|---|
| DEAL-03 | PartnerB | RATE_MISMATCH |
| DEAL-04 | PartnerB | UNMATCHED_TO_LEDGER |
| DEAL-06 | PartnerA | DUPLICATE_LINE |
| DEAL-06 | PartnerC | DUPLICATE_LINE |

## DEAL-07 is not a rate mismatch

DEAL-07 is tagged `renewal`, whose standard rate is 4%, but it is
reported at 6%. The commission exceptions register lists an active rate override,
`EXC-VP-02`, for DEAL-07 with an approved rate of 6%, which this policy pays instead of the
standard renewal rate. Reporting 6% is correct, and flagging the gap against the standard
mapping is the false positive this reconciliation is built to catch.

## Other findings

DEAL-03 is tagged `new` and should be paid at 8%, but is reported at 6%:
a rate mismatch. DEAL-04 is a commissionable renewal with no matching entry in the June
ledger, so it fails the ledger match rule until it ties out.
DEAL-06 appears in both the PartnerA and PartnerC reports with the same deal id, a
duplicate line on both occurrences.
