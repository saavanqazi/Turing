# Queue backpressure audit — snapshot 2026-09-17T01:50Z

24 queues in the broker snapshot, audited against PLAT-31. 8 are compliant and 16 carry a finding: 7 over threshold, 6 over their drain time, 3 with no backpressure config.

| Queue | Tier | In-flight load | Finding |
|---|---|---|---|
| `checkout.order-submit` | critical | 1,150 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `checkout.order-confirm` | critical | 900 | DRAIN_TIME_EXCEEDED |
| `checkout.coupon-validate` | — | 350 | NO_BACKPRESSURE_CONFIGURED |
| `payments.charge-commands` | critical | 3,500 | none |
| `payments.refund-commands` | critical | 1,300 | none |
| `payments.receipt-emails` | standard | 900 | DRAIN_TIME_EXCEEDED |
| `payments.settlement-report` | standard | 0 | none |
| `payouts.transfer-instructions` | critical | 8,000 | none |
| `payouts.fx-quotes` | critical | 850 | DRAIN_TIME_EXCEEDED |
| `search.autocomplete-requests` | critical | 1,600 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `search.index-updates` | standard | 7,200 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `search.synonym-reload` | — | 20 | NO_BACKPRESSURE_CONFIGURED |
| `identity.session-validate` | critical | 1,100 | none |
| `identity.login-otp` | standard | 5,400 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `identity.kyc-checks` | standard | 2,200 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `fraud.score-requests` | critical | 400 | DRAIN_TIME_EXCEEDED |
| `fraud.model-retrain` | standard | 6,200 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `fraud.case-review` | standard | 3,500 | DRAIN_TIME_EXCEEDED |
| `inventory.stock-reserve` | critical | 2,200 | none |
| `inventory.restock-feed` | standard | 300 | none |
| `inventory.price-sync` | standard | 650 | DRAIN_TIME_EXCEEDED |
| `notify.email-digest` | — | 12,000 | NO_BACKPRESSURE_CONFIGURED |
| `wallet.cashback-accrual` | critical | 1,800 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `wallet.balance-query` | critical | 1,000 | none |

## Findings

- `checkout.order-submit` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: in-flight load 1,150 (700 ready + 450 unacked) against a threshold of 1,000 (the critical default); publishers were not being throttled (publisher flow `running`).
- `checkout.order-confirm` — `DRAIN_TIME_EXCEEDED`: its drain time is 18 minutes (900 in flight over a net 50/min of acks); the critical max drain time is 15 minutes.
- `checkout.coupon-validate` — `NO_BACKPRESSURE_CONFIGURED`: it has no entry in the backpressure config.
- `payments.receipt-emails` — `DRAIN_TIME_EXCEEDED`: it is not draining (acks 40/min against publishes 40/min); the standard max drain time is 60 minutes.
- `payouts.fx-quotes` — `DRAIN_TIME_EXCEEDED`: its drain time is 28.3 minutes (850 in flight over a net 30/min of acks); the critical max drain time is 15 minutes.
- `search.autocomplete-requests` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: in-flight load 1,600 (900 ready + 700 unacked) against a threshold of 1,000 (the critical default); publishers were not being throttled (publisher flow `running`).
- `search.index-updates` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: in-flight load 7,200 (6,800 ready + 400 unacked) against a threshold of 5,000 (the standard default); publishers were not being throttled (publisher flow `running`).
- `search.synonym-reload` — `NO_BACKPRESSURE_CONFIGURED`: it has no entry in the backpressure config.
- `identity.login-otp` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: in-flight load 5,400 (3,000 ready + 2,400 unacked) against a threshold of 5,000 (the standard default); publishers were not being throttled (publisher flow `running`).
- `identity.kyc-checks` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: in-flight load 2,200 (1,200 ready + 1,000 unacked) against a threshold of 2,000 (its config override); publishers were not being throttled (publisher flow `running`).
- `fraud.score-requests` — `DRAIN_TIME_EXCEEDED`: it is not draining (acks 420/min against publishes 420/min); the critical max drain time is 15 minutes.
- `fraud.model-retrain` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: in-flight load 6,200 (5,900 ready + 300 unacked) against a threshold of 5,000 (the standard default); publishers were not being throttled (publisher flow `running`).
- `fraud.case-review` — `DRAIN_TIME_EXCEEDED`: its drain time is 87.5 minutes (3,500 in flight over a net 40/min of acks); the standard max drain time is 60 minutes.
- `inventory.price-sync` — `DRAIN_TIME_EXCEEDED`: it is not draining (acks 200/min against publishes 210/min); the standard max drain time is 60 minutes.
- `notify.email-digest` — `NO_BACKPRESSURE_CONFIGURED`: it has no entry in the backpressure config.
- `wallet.cashback-accrual` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: in-flight load 1,800 (1,500 ready + 300 unacked) against a threshold of 1,000 (the critical default); publishers were not being throttled (publisher flow `running`).

## Over threshold but no finding

- `payments.charge-commands` — `none`: in-flight load 3,500 is over its threshold of 1,000, but backpressure was engaged (publisher flow `flow`), and its drain time of 11.7 minutes is within the 15-minute maximum.
- `payouts.transfer-instructions` — `none`: in-flight load 8,000 is over its threshold of 1,000, but the BATCH-7 "Nightly payout run" window was open at the snapshot, which exempts it.
- `identity.session-validate` — `none`: in-flight load 1,100 is over its threshold of 1,000, but backpressure was engaged (publisher flow `flow`), and its drain time of 11 minutes is within the 15-minute maximum.
