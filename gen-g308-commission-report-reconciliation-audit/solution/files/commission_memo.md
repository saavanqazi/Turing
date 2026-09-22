# Commission reconciliation memo — June 2026 run

Consolidated 92 commission lines from the five partner reports and
reconciled them against COMM-POL-6, the June NetSuite revenue export and the commission
exceptions register. 31 findings were raised across
26 lines; 66 lines are compliant.
Rates were normalised to whole percent first: PartnerB files a decimal fraction, PartnerC
files basis points and PartnerD writes a percent sign, so the reported rate is not
comparable across reports until it is converted.

## Rate mismatches

R1 sets the standard rate by end-user type: new 8%, renewal 4%, house 0%. A line whose
reported rate is not the rate R1 is read against is a `RATE_MISMATCH`. Where an exception
window covers the run month the approved rate is the rate R1 is read against, so the
comparison is made against the approved rate and not the standard one.

- DEAL-061 (PartnerB): new line reported at 6%, rate applicable 8% — `RATE_MISMATCH`.
- DEAL-062 (PartnerC): renewal line reported at 8%, rate applicable 4% — `RATE_MISMATCH`.
- DEAL-063 (PartnerD): house line reported at 4%, rate applicable 0% — `RATE_MISMATCH`.
- DEAL-064 (PartnerE): new line reported at 4%, rate applicable 8% — `RATE_MISMATCH`.
- DEAL-065 (PartnerA): renewal line reported at 6%, rate applicable 4% — `RATE_MISMATCH`.
- DEAL-066 (PartnerB): house line reported at 8%, rate applicable 0% — `RATE_MISMATCH`.
- DEAL-067 (PartnerC): new line reported at 10%, rate applicable 8% — `RATE_MISMATCH`.
- DEAL-068 (PartnerD): renewal line reported at 2%, rate applicable 4% — `RATE_MISMATCH`.
- DEAL-075 (PartnerB): new line reported at 0%, rate applicable 8% — `RATE_MISMATCH`.
- DEAL-078 (PartnerA): new line reported at 6%, rate applicable 8% — `RATE_MISMATCH`.
- DEAL-078 (PartnerE): new line reported at 6%, rate applicable 8% — `RATE_MISMATCH`.
- DEAL-082 (PartnerC): renewal line reported at 6%, rate applicable 4% — `RATE_MISMATCH`.
- DEAL-083 (PartnerD): new line reported at 6%, rate applicable 8% — `RATE_MISMATCH`.
- DEAL-087 (PartnerD): new line reported at 10%, rate applicable 8% — `RATE_MISMATCH`.

## Ledger matches

R2 requires every commissionable line to be matched to a revenue record in the run month
`2026-06`, and a line is commissionable when the standard or approved rate is above 0%.
Whether the line is commissionable turns on that rate and not on the rate the partner
reported, so a house line at 0% is out of scope for this rule even with no record at all.
A record in `2026-05` is not a match for this run, so a deal whose only record sits in May
is unmatched exactly as a deal with no record is.

- DEAL-069 (PartnerE): commissionable at 8%, no revenue record — `UNMATCHED_TO_LEDGER`.
- DEAL-070 (PartnerA): commissionable at 4%, no revenue record — `UNMATCHED_TO_LEDGER`.
- DEAL-071 (PartnerB): commissionable at 8%, a revenue record in 2026-05 only — `UNMATCHED_TO_LEDGER`.
- DEAL-072 (PartnerC): commissionable at 4%, a revenue record in 2026-05 only — `UNMATCHED_TO_LEDGER`.
- DEAL-075 (PartnerB): commissionable at 8%, a revenue record in 2026-05 only — `UNMATCHED_TO_LEDGER`.
- DEAL-079 (PartnerC): commissionable at 4%, no revenue record — `UNMATCHED_TO_LEDGER`.
- DEAL-079 (PartnerD): commissionable at 4%, no revenue record — `UNMATCHED_TO_LEDGER`.
- DEAL-086 (PartnerB): commissionable at 3%, no revenue record — `UNMATCHED_TO_LEDGER`.

## Duplicate lines

R3 forbids the same `deal_id` appearing in more than one partner report, and a deal that
does is a `DUPLICATE_LINE` on every occurrence rather than on the later one only. These
are only visible once the five reports are consolidated.

- DEAL-076: reported by PartnerA, PartnerC — `DUPLICATE_LINE` on each of the 2 lines.
- DEAL-077: reported by PartnerB, PartnerD, PartnerE — `DUPLICATE_LINE` on each of the 3 lines.
- DEAL-078: reported by PartnerA, PartnerE — `DUPLICATE_LINE` on each of the 2 lines.
- DEAL-079: reported by PartnerC, PartnerD — `DUPLICATE_LINE` on each of the 2 lines.

## Lines that look wrong and are not

R4 lets a VP-approved rate override the standard mapping. These lines disagree with the
standard rate for their end-user type and are compliant anyway, because an exception whose
window covers the run month sets the rate they are paid at:

- DEAL-080 (PartnerB): renewal line paid at 6% under EXC-VP-02 (2026-01-01 to open ended), against a standard 4% — compliant, not a rate mismatch.
- DEAL-081 (PartnerA): new line paid at 12% under EXC-VP-07 (2025-07-01 to 2026-12-31), against a standard 8% — compliant, not a rate mismatch.
- DEAL-085 (PartnerA): house line paid at 3% under EXC-VP-18 (2026-02-01 to 2026-06-30), against a standard 0% — compliant, not a rate mismatch.

An exception whose window does not cover the run month does not displace the standard
rate, and an approved rate equal to the standard rate changes nothing.
