# Queue backpressure audit — incident night, 2026-09-17

40 queues in the broker export, audited against PLAT-31. 21 are compliant and 19 carry a finding: 8 over threshold, 7 over their drain time, 4 with no backpressure config.

| Queue | Tier | In-flight | Finding |
|---|---|---|---|
| `checkout.order-submit` | critical | 2,400 | DRAIN_TIME_EXCEEDED |
| `checkout.order-confirm` | critical | 1,350 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `checkout.analytics-events` | standard | 4,200 | none |
| `checkout.abandoned-cart-emails` | standard | 800 | none |
| `checkout.coupon-validate` | — | 300 | NO_BACKPRESSURE_CONFIGURED |
| `fraud.score-requests` | critical | 1,400 | DRAIN_TIME_EXCEEDED |
| `fraud.score-replies` | critical | 1,000 | none |
| `fraud.model-retrain` | standard | 6,200 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `fraud.case-review` | standard | 1,900 | none |
| `payments.charge-commands` | critical | 3,100 | none |
| `payments.refund-commands` | critical | 450 | DRAIN_TIME_EXCEEDED |
| `payments.receipt-emails` | standard | 2,600 | none |
| `payments.settlement-report` | standard | 5,600 | none |
| `payments.chargeback-events` | — | 700 | NO_BACKPRESSURE_CONFIGURED |
| `payouts.transfer-instructions` | critical | 8,000 | none |
| `payouts.statement-render` | standard | 1,700 | none |
| `payouts.fx-quotes` | critical | 700 | DRAIN_TIME_EXCEEDED |
| `search.autocomplete-requests` | critical | 1,600 | none |
| `search.index-updates` | standard | 7,200 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `search.click-logs` | standard | 3,900 | none |
| `search.synonym-reload` | — | 20 | NO_BACKPRESSURE_CONFIGURED |
| `identity.login-otp` | standard | 1,200 | none |
| `identity.password-reset-emails` | standard | 350 | DRAIN_TIME_EXCEEDED |
| `identity.session-validate` | critical | 1,300 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `identity.kyc-checks` | standard | 2,100 | none |
| `support.ticket-lookup` | standard | 1,150 | none |
| `support.ticket-events` | standard | 5,000 | none |
| `reports.priority-exports` | standard | 3,400 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `reports.finance-daily` | standard | 9,000 | none |
| `reports.tax-summaries` | standard | 900 | none |
| `inventory.stock-reserve` | critical | 2,200 | none |
| `inventory.restock-feed` | standard | 5,300 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `inventory.price-sync` | standard | 650 | DRAIN_TIME_EXCEEDED |
| `notify.push` | standard | 4,800 | none |
| `notify.email-digest` | — | 12,000 | NO_BACKPRESSURE_CONFIGURED |
| `notify.sms` | standard | 300 | none |
| `wallet.topup-commands` | critical | 900 | DRAIN_TIME_EXCEEDED |
| `wallet.balance-query` | critical | 1,150 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `wallet.cashback-accrual` | critical | 1,800 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| `wallet.statement-emails` | standard | 5,400 | none |

## Findings

- `checkout.order-submit` — `DRAIN_TIME_EXCEEDED`: its drain time is 17.1 minutes (2,400 in flight over a net 140/min); the critical max drain time is 15 minutes.
- `checkout.order-confirm` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: 1,350 in flight against a threshold of 1,000 (the critical default; the queue is critical), and backpressure was not engaged when it was sampled at 01:36:30 UTC.
- `checkout.coupon-validate` — `NO_BACKPRESSURE_CONFIGURED`: it has no entry in the backpressure config, so there is no threshold to measure its 300 in-flight messages against.
- `fraud.score-requests` — `DRAIN_TIME_EXCEEDED`: its drain time is 17.5 minutes (1,400 in flight over a net 80/min); the critical max drain time is 15 minutes.
- `fraud.model-retrain` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: 6,200 in flight against a threshold of 5,000 (the standard default; the queue is standard), and backpressure was not engaged when it was sampled at 01:58:00 UTC.
- `payments.refund-commands` — `DRAIN_TIME_EXCEEDED`: its drain time is 18 minutes (450 in flight over a net 25/min); the critical max drain time is 15 minutes.
- `payments.chargeback-events` — `NO_BACKPRESSURE_CONFIGURED`: it has no entry in the backpressure config, so there is no threshold to measure its 700 in-flight messages against.
- `payouts.fx-quotes` — `DRAIN_TIME_EXCEEDED`: its drain time is 23.3 minutes (700 in flight over a net 30/min); the critical max drain time is 15 minutes.
- `search.index-updates` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: 7,200 in flight against a threshold of 5,000 (the standard default; the queue is standard), and backpressure was not engaged when it was sampled at 01:52:00 UTC.
- `search.synonym-reload` — `NO_BACKPRESSURE_CONFIGURED`: it has no entry in the backpressure config, so there is no threshold to measure its 20 in-flight messages against.
- `identity.password-reset-emails` — `DRAIN_TIME_EXCEEDED`: it is not draining (acks 30/min against publishes 30/min), which exceeds any maximum; the standard max drain time is 60 minutes.
- `identity.session-validate` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: 1,300 in flight against a threshold of 1,000 (the critical default; the queue is critical), and backpressure was not engaged when it was sampled at 01:50:00 UTC.
- `reports.priority-exports` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: 3,400 in flight against a threshold of 3,000 (its config override; the queue is standard), and backpressure was not engaged when it was sampled at 01:48:10 UTC.
- `inventory.restock-feed` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: 5,300 in flight against a threshold of 5,000 (the standard default; the queue is standard), and backpressure was not engaged when it was sampled at 01:51:30 UTC.
- `inventory.price-sync` — `DRAIN_TIME_EXCEEDED`: it is not draining (acks 200/min against publishes 210/min), which exceeds any maximum; the standard max drain time is 60 minutes.
- `notify.email-digest` — `NO_BACKPRESSURE_CONFIGURED`: it has no entry in the backpressure config, so there is no threshold to measure its 12,000 in-flight messages against.
- `wallet.topup-commands` — `DRAIN_TIME_EXCEEDED`: its drain time is 18 minutes (900 in flight over a net 50/min); the critical max drain time is 15 minutes.
- `wallet.balance-query` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: 1,150 in flight against a threshold of 1,000 (the critical default; the queue is critical), and backpressure was not engaged when it was sampled at 02:03:00 UTC.
- `wallet.cashback-accrual` — `BACKPRESSURE_THRESHOLD_EXCEEDED`: 1,800 in flight against a threshold of 1,000 (the critical default; the queue is critical), and backpressure was not engaged when it was sampled at 01:55:00 UTC.

## Over threshold but no finding

- `payments.charge-commands` — `none`: 3,100 in flight is over its threshold of 1,000, but backpressure was already engaged when it was sampled at 01:39:00 UTC, so the system responded correctly; its drain time of 12.4 minutes is within the 15-minute maximum.
- `payments.settlement-report` — `none`: 5,600 in flight is over its threshold of 5,000, but the BATCH-7 "Settlement report build" burst window held when it was sampled at 02:12:00 UTC, which exempts it from the threshold and drain checks.
- `payouts.transfer-instructions` — `none`: 8,000 in flight is over its threshold of 1,000, but the BATCH-7 "Nightly payout run" burst window held when it was sampled at 01:42:00 UTC, which exempts it from the threshold and drain checks.
- `search.autocomplete-requests` — `none`: 1,600 in flight is over its threshold of 1,000, but backpressure was already engaged when it was sampled at 01:49:00 UTC, so the system responded correctly; its drain time of 10.7 minutes is within the 15-minute maximum.
- `reports.finance-daily` — `none`: 9,000 in flight is over its threshold of 5,000, but the BATCH-7 "Finance daily compile" burst window held when it was sampled at 02:05:00 UTC, which exempts it from the threshold and drain checks.
- `wallet.statement-emails` — `none`: 5,400 in flight is over its threshold of 5,000, but the BATCH-7 "Wallet statement batch" burst window held when it was sampled at 01:55:30 UTC, which exempts it from the threshold and drain checks.
