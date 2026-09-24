# Scheduled batch windows (BATCH-7)

Burst windows agreed with the platform team for scheduled batch work. Times are UTC. `daily`
runs every day; otherwise the window opens on the days listed. A window whose closing time is
earlier than its opening time runs past midnight and closes the next day.

| job | queue | days | opens | closes | status |
|---|---|---|---|---|---|
| Nightly payout run | `payouts.transfer-instructions` | daily | 01:00 | 02:00 | active |
| Search full reindex | `search.index-updates` | daily | 23:30 | 01:45 | active |
| Fraud model retrain | `fraud.model-retrain` | Wed, Sun | 01:30 | 03:00 | active |
| Weekly digest send | `notify.email-digest` | Thu | 01:00 | 03:00 | active |
| Cashback accrual batch | `wallet.cashback-accrual` | daily | 01:00 | 03:00 | retired 2026-08-31 |
