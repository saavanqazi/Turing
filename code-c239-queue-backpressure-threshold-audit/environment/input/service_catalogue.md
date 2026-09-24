# Service catalogue — messaging queues

Extract for the backpressure audit. Each section is written by the team that owns the
service. "Team priority" is that team's own label for its queues.

## checkout-api

Runs the storefront checkout. *Place order* goes out on `checkout.order-submit`, where the
order service picks it up, and the shopper's browser only gets its confirmation page once
the order service's confirmation has landed on `checkout.order-confirm`. Before it will confirm an order, checkout-api needs a
risk score, which it requests on `fraud.score-requests` and gets back on
`fraud.score-replies`, and a stock hold from inventory (see inventory). With the
confirmation page sent, it drops a purchase event on `checkout.analytics-events` for the
data team. An hour after a basket is abandoned it queues a reminder on
`checkout.abandoned-cart-emails`. Coupon codes typed at checkout are checked through
`checkout.coupon-validate`, launched last week and not yet onboarded to the backpressure
config.

Team priority: order-submit P1 · order-confirm P1 · analytics-events P1 ("the revenue
dashboards depend on it") · abandoned-cart-emails critical ("direct revenue") ·
coupon-validate P2.

## fraud-scoring

Scores orders from `fraud.score-requests` and answers on `fraud.score-replies`. We rate both
standard: most of what goes through them is the overnight rescoring of old orders. To score
a checkout order we first post a lookup on the shopper's device to
`devices.reputation-lookup`, and no score goes back until device-intel has answered it. Once a score has gone back, the decision
is appended to `fraud.audit-trail` for the compliance team. `fraud.model-retrain` carries
training jobs for the model refresh. `fraud.case-review` feeds the analyst console: when one
of our fraud analysts opens a flagged case, the console sits waiting for the case bundle to
come back on this queue.

Team priority: score-requests standard · score-replies standard · audit-trail P1
("regulators read it") · model-retrain P3 · case-review critical ("analysts are blocked
without it").

## device-intel

Keeps reputation data on devices. Other services post their lookups to
`devices.reputation-lookup` and we answer them. We have no customer-facing endpoints.

Team priority: reputation-lookup P3 ("internal lookups").

## payments-core

`payments.charge-commands` tells the card processor to charge the customer's card once an
order has been confirmed. `payments.refund-commands` carries the refunds the support team
issues, a few dozen a day. `payments.refund-status` answers "where has this refund got to?"
lookups from the support console (see support-desk). When a charge has gone through,
`payments.receipt-emails` sends the customer their receipt. `payments.settlement-report`
builds the nightly report of the day's settlements for finance.
`payments.chargeback-events` records chargebacks notified by the card schemes; it was added
during the incident and has not been onboarded yet.

Team priority: charge-commands P1 · refund-commands low · refund-status P1 · receipt-emails
P1 ("customers chase receipts fast") · settlement-report P2.

## payouts

Pays our merchants. Before the nightly payout run starts, it fetches the day's exchange
rates through `payouts.fx-rate-fetch` and waits until they are in; it then puts one transfer
instruction per merchant on `payouts.transfer-instructions`, which the bank connector
executes. When a merchant switches payout currency in the merchant app, payouts-api keeps
the app's call open until a live quote arrives on `payouts.fx-quotes`.

Team priority: fx-rate-fetch P1 ("no rates, no payouts") · transfer-instructions P3 ("it's
a batch job") · fx-quotes P2.

## search

Shoppers get type-ahead suggestions from search-api, which looks them up through
`search.autocomplete-requests` and does not answer the search box until they are back.
`search.index-updates` feeds catalogue changes into the search index a few minutes after
they are made. `search.synonym-reload` was created for a one-off synonym import and has no
config yet.

Team priority: autocomplete-requests P1 · index-updates critical ("stale results cost
sales").

## identity

The API gateway holds every call a customer's storefront or app makes until the caller's
session check has come back on `identity.session-validate`. When a customer asks for a login
code, the login API replies "code sent" at once, and the code goes out by SMS from
`identity.login-otp` a few seconds later. A password-reset request is answered "check your
email" at once, and the link goes out from `identity.password-reset-emails`. New customers'
identity checks are queued on `identity.kyc-checks` after the app has told them the result
will arrive by email within the hour.

Team priority: session-validate P1 · login-otp critical ("nobody can log in without it") ·
password-reset-emails P2 · kyc-checks P2.

## support-desk

`support.ticket-lookup` backs the agents' console: opening a ticket leaves the console
waiting until the customer's history is back on this queue. When an agent asks where a
customer's refund has got to, we look it up on `payments.refund-status` and the console
waits for the answer; nothing else uses that queue.

Team priority: ticket-lookup critical ("agents are blocked without it").

## bi-reports

`reports.priority-exports` produces the hourly exports the leadership team asked for "as a
priority". `reports.finance-daily` compiles the day's revenue and settlement figures for
finance.

Team priority: priority-exports P1 · finance-daily P2.

## inventory

While checkout-api is holding a shopper's *Place order*, it asks us to hold the stock by
putting a reservation on `inventory.stock-reserve`, and it cannot confirm until we have
picked the reservation up. Once we have taken a reservation we announce it on
`inventory.reservation-events`, which the warehouse systems read in their own time.
`inventory.restock-feed` imports supplier restock files. `inventory.price-sync` pushes price
changes out to the storefront cache.

Team priority: stock-reserve P1 · reservation-events P1 ("part of every order") ·
restock-feed P3 · price-sync P2.

## ledger

Holds the authoritative customer balances. Services that need one ask us, and we answer on
`ledger.balance-snapshot`.

Team priority: balance-snapshot P3 ("back-office service").

## notify

`notify.email-digest` sends the weekly digest; it has not been onboarded to the
backpressure config.

## wallet

`wallet.topup-commands` carries the instruction to add funds to a customer's wallet once
their card has been charged for a top-up. When a customer opens the balance screen,
wallet-api keeps the app's call open until the balance is back on `wallet.balance-query`;
to work that balance out, wallet-api first asks ledger for the latest snapshot and waits
for ledger's answer.
`wallet.cashback-accrual` carries the instruction to credit earned cashback into a
customer's wallet the day after a purchase. `wallet.statement-emails` sends the monthly
wallet statements.

Team priority: topup-commands P1 · balance-query P1 · cashback-accrual low ("best effort") ·
statement-emails P3.
