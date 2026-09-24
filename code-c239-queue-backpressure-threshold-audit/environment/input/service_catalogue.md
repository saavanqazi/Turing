# Service catalogue — messaging queues

Extract for the backpressure audit. Each section is written by the team that owns the
service. "Team priority" is that team's own label for its queues.

## checkout-api

Serves the storefront checkout. When a customer presses *Place order*, checkout-api
publishes the order to `checkout.order-submit` and keeps the customer's request open until
the order service's confirmation comes back on `checkout.order-confirm`; only then is the
confirmation page returned. Before it confirms, checkout-api also puts a scoring request on
`fraud.score-requests` and does not answer the customer until the score has come back on
`fraud.score-replies`, and it reserves stock through `inventory.stock-reserve` (see
inventory). Once the confirmation page has gone back to the customer, checkout-api publishes
a purchase event to `checkout.analytics-events` for the data team. An hour after a basket is
abandoned it publishes a reminder to `checkout.abandoned-cart-emails`. Coupon codes typed at
checkout are checked through `checkout.coupon-validate`, launched last week and not yet
onboarded to the backpressure config.

Team priority: order-submit P1 · order-confirm P1 · analytics-events P1 ("the revenue
dashboards depend on it") · abandoned-cart-emails critical ("direct revenue") ·
coupon-validate P2.

## fraud-scoring

Consumes `fraud.score-requests` and answers on `fraud.score-replies`. The team rates both
standard: most of the traffic on them is the overnight rescoring of old orders.
`fraud.model-retrain` carries training jobs for the model refresh. `fraud.case-review` feeds
the analyst console: when one of our fraud analysts opens a flagged case, the console waits
for the case bundle to come back on this queue.

Team priority: score-requests standard · score-replies standard · model-retrain P3 ·
case-review critical ("analysts are blocked without it").

## payments-core

`payments.charge-commands` carries the instruction to charge a customer's card once an
order has been confirmed. `payments.refund-commands` carries the refund instructions the
support team issues; there are a few dozen a day. When a charge has gone through,
`payments.receipt-emails` sends the customer their receipt. `payments.settlement-report`
builds the nightly report of the day's settlements for finance.
`payments.chargeback-events` records chargebacks notified by the card schemes; it was added
during the incident and has not been onboarded yet.

Team priority: charge-commands P1 · refund-commands low · receipt-emails P1 ("customers
chase receipts fast") · settlement-report P2.

## payouts

Pays our merchants. The nightly payout run puts one transfer instruction per merchant on
`payouts.transfer-instructions`, which the bank connector executes. `payouts.statement-render`
renders the PDF statements merchants download the next morning. When a merchant switches
payout currency in the merchant app, payouts-api holds the app's call until a live quote
comes back on `payouts.fx-quotes`.

Team priority: transfer-instructions P3 ("it's a batch job") · statement-render P2 ·
fx-quotes P2.

## search

`search.autocomplete-requests` carries the suggestions a shopper sees while typing:
search-api takes the search box's call, sends the lookup through this queue and holds the
call until the suggestions come back on it. `search.index-updates` feeds catalogue changes into the search index a few minutes
after they are made. `search.click-logs` collects click-through events for ranking.
`search.synonym-reload` was created for a one-off synonym import and has no config yet.

Team priority: autocomplete-requests P1 · index-updates critical ("stale results cost
sales") · click-logs P3.

## identity

The API gateway holds every call a customer's storefront or app makes until the caller's
session check has come back on `identity.session-validate`. When a customer asks for a
login code, the login API replies "code sent" straight away and the code is sent by SMS
from `identity.login-otp` a few seconds later. When a customer asks for a password reset,
the login API replies "check your email" straight away and the link goes out from
`identity.password-reset-emails`. New customers' identity checks are queued on
`identity.kyc-checks` after the app has told them the result will arrive by email within
the hour.

Team priority: session-validate P1 · login-otp critical ("nobody can log in without it") ·
password-reset-emails P2 · kyc-checks P2.

## support-desk

`support.ticket-lookup` backs the support agents' console: when an agent opens a ticket,
the console waits for the customer's history to come back on this queue.
`support.ticket-events` streams ticket updates to the data warehouse.

Team priority: ticket-lookup critical ("agents are blocked without it") · ticket-events P3.

## bi-reports

`reports.priority-exports` produces the hourly exports the leadership team asked for "as a
priority". `reports.finance-daily` compiles the day's revenue and settlement figures for
finance. `reports.tax-summaries` compiles the quarterly tax summaries.

Team priority: priority-exports P1 · finance-daily P2 · tax-summaries P3.

## inventory

`inventory.stock-reserve` holds stock for an order: checkout-api, while it is holding the
customer's *Place order* request, puts a reservation on this queue and waits for it to be
consumed. `inventory.restock-feed` imports supplier restock files.
`inventory.price-sync` pushes price changes out to the storefront cache.

Team priority: stock-reserve P1 · restock-feed P3 · price-sync P2.

## notify

`notify.push` sends app push notifications. `notify.sms` sends marketing and service texts
(login codes are sent by identity, not from here). `notify.email-digest` sends the weekly
digest; it has not been onboarded to the backpressure config.

Team priority: push P2 · sms P2.

## wallet

`wallet.topup-commands` carries the instruction to add funds to a customer's wallet once
their card has been charged for a top-up. When a customer opens the balance screen, wallet-api holds the app's call
until the balance comes back on `wallet.balance-query`. `wallet.cashback-accrual` carries
the instruction to credit earned cashback into a customer's wallet the day after a
purchase. `wallet.statement-emails` sends the monthly wallet
statements.

Team priority: topup-commands P1 · balance-query P1 · cashback-accrual low ("best effort") ·
statement-emails P3.
