#!/usr/bin/env python3
"""Generate the c239 fixtures AND derive the gold from the same data.

The queues, their config, the service catalogue, the batch schedule and the
broker event log are declared here, PLAT-31 is implemented once, and every input
fixture, all three gold deliverables, the verifier pins and the golden trajectory
are emitted from that single source, so the gold cannot drift from the data it
describes.

    python3 build_task.py          # build, then re-run the oracle
    python3 build_task.py --price  # also print what each single mistake costs

Nothing in a queue's row decides its tier. The tier is PLAT-31 §2 applied to what
the service catalogue says the queue does, and TIER below is that reading, made
once, by hand, per queue. `SURFACE` records the tier the queue's name or its
team's own priority label points to, where that differs, so the build can price
a solver who reads the label instead of the definition.
"""
import csv, io, json, re, sys
from collections import OrderedDict
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INP = ROOT / "environment" / "input"
SOL = ROOT / "solution" / "files"
TASK_ID = "code-c239-queue-backpressure-threshold-audit"

TIERS = OrderedDict(critical=(1000, 15), standard=(5000, 60))   # default threshold, max drain minutes
NOCFG, THRESH, DRAIN, NONE = ("NO_BACKPRESSURE_CONFIGURED", "BACKPRESSURE_THRESHOLD_EXCEEDED",
                              "DRAIN_TIME_EXCEEDED", "none")
CODES = (NOCFG, THRESH, DRAIN)
DAY = "2026-09-17"          # a Thursday; the export was taken during the incident

def ts(hms, day=DAY):
    return datetime.fromisoformat(f"{day}T{hms}+00:00")

# ---- data -----------------------------------------------------------------
# queue, owning service, sampled_at, in_flight, publish/min, ack/min, dashboard burst hint
EXPORT = [
    ("checkout.order-submit",         "checkout-api",   "01:36:00", 2400,  760,  900, False),
    ("checkout.order-confirm",        "checkout-api",   "01:36:30", 1350, 1000, 1300, False),
    ("checkout.analytics-events",     "checkout-api",   "01:45:00", 4200,  230,  300, False),
    ("checkout.abandoned-cart-emails","checkout-api",   "01:37:10",  800,   40,   60, False),
    ("checkout.coupon-validate",      "checkout-api",   "01:37:40",  300,  500,  520, False),
    ("fraud.score-requests",          "fraud-scoring",  "01:38:20", 1400,  420,  500, False),
    ("fraud.score-replies",           "fraud-scoring",  "01:38:50", 1000,  880,  950, False),
    ("fraud.model-retrain",           "fraud-scoring",  "01:58:00", 6200,  700,  760, False),
    ("fraud.case-review",             "fraud-scoring",  "01:39:30", 1900,   60,  110, False),
    ("payments.charge-commands",      "payments-core",  "01:39:00", 3100, 1150, 1400, False),
    ("payments.refund-commands",      "payments-core",  "01:40:10",  450,   20,   45, False),
    ("payments.receipt-emails",       "payments-core",  "01:40:40", 2600,  300,  380, False),
    ("payments.settlement-report",    "payments-core",  "02:12:00", 5600,  200,  180, True),
    ("payments.chargeback-events",    "payments-core",  "01:41:10",  700,   35,   30, False),
    ("payouts.transfer-instructions", "payouts",        "01:42:00", 8000, 1500, 1200, True),
    ("payouts.fx-rate-fetch",         "payouts",        "01:42:30",  600,   20,   40, False),
    ("payouts.fx-quotes",             "payouts",        "01:43:00",  700,  400,  430, False),
    ("search.autocomplete-requests",  "search",         "01:49:00", 1600,  450,  600, False),
    ("search.index-updates",          "search",         "01:52:00", 7200,  800,  900, True),
    ("devices.reputation-lookup",     "device-intel",   "01:44:00",  800,  200,  250, False),
    ("search.synonym-reload",         "search",         "01:44:30",   20,    0,    5, False),
    ("identity.login-otp",            "identity",       "01:45:30", 1200,  800,  850, False),
    ("identity.password-reset-emails","identity",       "01:46:00",  350,   30,   30, False),
    ("identity.session-validate",     "identity",       "01:50:00", 1300, 5000, 5600, False),
    ("identity.kyc-checks",           "identity",       "01:46:40", 2100,  120,  170, False),
    ("support.ticket-lookup",         "support-desk",   "01:47:10", 1150,  400,  450, False),
    ("payments.refund-status",        "payments-core",  "01:47:40", 5000,  300,  400, False),
    ("reports.priority-exports",      "bi-reports",     "01:48:10", 3400,  330,  400, False),
    ("reports.finance-daily",         "bi-reports",     "02:05:00", 9000,  100,   90, False),
    ("fraud.audit-trail",             "fraud-scoring",  "01:48:40",  900,   10,   25, False),
    ("inventory.stock-reserve",       "inventory",      "01:51:00", 2200,  620,  800, False),
    ("inventory.restock-feed",        "inventory",      "01:51:30", 5300,  400,  520, False),
    ("inventory.price-sync",          "inventory",      "01:52:30",  650,  210,  200, False),
    ("inventory.reservation-events",  "inventory",      "01:53:00", 1400,  300,  370, False),
    ("notify.email-digest",           "notify",         "01:53:20",12000,  900,  700, True),
    ("ledger.balance-snapshot",       "ledger",         "01:53:30", 1100,  900, 1000, False),
    ("wallet.topup-commands",         "wallet",         "01:54:00",  900,  300,  350, False),
    ("wallet.balance-query",          "wallet",         "02:03:00", 1150, 2000, 2400, False),
    ("wallet.cashback-accrual",       "wallet",         "01:55:00", 1800,  150,  300, True),
    ("wallet.statement-emails",       "wallet",         "01:55:30", 5400,   50,   60, True),
]
QUEUES = [e[0] for e in EXPORT]

# PLAT-31 §2 applied to the catalogue, one reading per configured queue
C, S = "critical", "standard"
TIER = {
    "checkout.order-submit": C, "checkout.order-confirm": C, "checkout.analytics-events": S,
    "checkout.abandoned-cart-emails": S,
    "fraud.score-requests": C, "fraud.score-replies": C, "fraud.model-retrain": S, "fraud.case-review": S,
    "payments.charge-commands": C, "payments.refund-commands": C, "payments.receipt-emails": S,
    "payments.settlement-report": S,
    "payouts.transfer-instructions": C, "payouts.fx-rate-fetch": S, "payouts.fx-quotes": C,
    "search.autocomplete-requests": C, "search.index-updates": S, "devices.reputation-lookup": C,
    "identity.login-otp": S, "identity.password-reset-emails": S, "identity.session-validate": C,
    "identity.kyc-checks": S,
    "support.ticket-lookup": S, "payments.refund-status": S,
    "reports.priority-exports": S, "reports.finance-daily": S, "inventory.reservation-events": S,
    "inventory.stock-reserve": C, "inventory.restock-feed": S, "inventory.price-sync": S,
    "ledger.balance-snapshot": C, "fraud.audit-trail": S,
    "wallet.topup-commands": C, "wallet.balance-query": C, "wallet.cashback-accrual": C,
    "wallet.statement-emails": S,
}
# where the name or the team's own label points the other way
SURFACE = {
    "checkout.analytics-events": C, "checkout.abandoned-cart-emails": C, "fraud.score-requests": S,
    "fraud.score-replies": S, "fraud.case-review": C, "payments.refund-commands": S,
    "payments.receipt-emails": C, "payouts.transfer-instructions": S, "search.index-updates": C,
    "identity.login-otp": C, "support.ticket-lookup": C, "reports.priority-exports": C,
    "wallet.cashback-accrual": S, "devices.reputation-lookup": S, "ledger.balance-snapshot": S,
    "fraud.audit-trail": C, "inventory.reservation-events": C, "payouts.fx-rate-fetch": C,
    "payments.refund-status": C,
}
OVERRIDE = {"fraud.score-requests": 1500, "reports.priority-exports": 3000, "inventory.stock-reserve": 2500}
DECOMMISSIONED = ["legacy.order-sync"]            # configured, no longer in the export
UNCONFIGURED = {"checkout.coupon-validate", "payments.chargeback-events", "search.synonym-reload",
                "notify.email-digest"}
assert set(TIER) == set(QUEUES) - UNCONFIGURED

# BATCH-7: job, queue, days, start, end (UTC), status
SCHEDULE = [
    ("Nightly payout run",        "payouts.transfer-instructions", "daily",    "01:00", "02:00", "active"),
    ("Search full reindex",       "search.index-updates",          "daily",    "23:30", "01:45", "active"),
    ("Finance daily compile",     "reports.finance-daily",         "daily",    "01:15", "02:45", "active"),
    ("Fraud model retrain",       "fraud.model-retrain",           "Wed, Sun", "01:30", "03:00", "active"),
    ("Weekly digest send",        "notify.email-digest",           "Thu",      "01:00", "03:00", "active"),
    ("Settlement report build",   "payments.settlement-report",    "daily",    "00:30", "02:30", "active"),
    ("Wallet statement batch",    "wallet.statement-emails",       "daily",    "01:00", "04:00", "active"),
    ("Cashback accrual batch",    "wallet.cashback-accrual",       "daily",    "01:00", "03:00", "retired 2026-08-31"),
    ("Restock supplier import",   "inventory.restock-feed",        "Mon",      "01:00", "02:30", "active"),
]
# broker event log: (day, time, broker, queue, event, detail)
EVENTS = [
    ("2026-09-16", "22:10:04", "broker-1", "inventory.reservation-events", "BACKPRESSURE_ENGAGED",  "in_flight=5310"),
    ("2026-09-16", "22:48:51", "broker-1", "inventory.reservation-events", "BACKPRESSURE_RELEASED", "in_flight=1204"),
    ("2026-09-16", "23:30:02", "broker-3", "search.index-updates",         "CONSUMER_JOINED",       "consumers=8"),
    ("2026-09-17", "00:55:17", "broker-2", "payments.settlement-report",   "CONSUMER_LEFT",         "consumers=1"),
    ("2026-09-17", "01:20:40", "broker-2", "identity.session-validate",    "BACKPRESSURE_ENGAGED",  "in_flight=1890"),
    ("2026-09-17", "01:25:12", "broker-1", "payments.charge-commands",     "BACKPRESSURE_ENGAGED",  "in_flight=2950"),
    ("2026-09-17", "01:31:10", "broker-1", "checkout.order-submit",        "BACKPRESSURE_ENGAGED",  "in_flight=2210"),
    ("2026-09-17", "01:33:05", "broker-3", "checkout.analytics-events",    "BACKPRESSURE_ENGAGED",  "in_flight=4010"),
    ("2026-09-17", "01:34:48", "broker-2", "wallet.cashback-accrual",      "CONSUMER_LEFT",         "consumers=2"),
    ("2026-09-17", "01:38:00", "broker-1", "fraud.score-requests",         "POLICY_RELOAD",         "policy=PLAT-31"),
    ("2026-09-17", "01:40:26", "broker-3", "search.autocomplete-requests", "BACKPRESSURE_ENGAGED",  "in_flight=1480"),
    ("2026-09-17", "01:44:09", "broker-2", "identity.session-validate",    "BACKPRESSURE_RELEASED", "in_flight=610"),
    ("2026-09-17", "01:47:55", "broker-1", "support.ticket-lookup",        "CONSUMER_JOINED",       "consumers=4"),
    ("2026-09-17", "02:07:31", "broker-2", "wallet.balance-query",         "BACKPRESSURE_ENGAGED",  "in_flight=1620"),
    ("2026-09-17", "02:15:44", "broker-1", "payments.charge-commands",     "BACKPRESSURE_RELEASED", "in_flight=380"),
]

# ---- PLAT-31, implemented once ---------------------------------------------
# `mistakes` switches in one misreading at a time; the gold passes none.
def tier(q, m=frozenset()):
    if "surface_tier" in m or f"flip:{q}" in m:
        return SURFACE.get(q, TIER[q]) if "surface_tier" in m else ({C: S, S: C}[TIER[q]])
    return TIER[q]

def limits(q, m=frozenset()):
    t, d = TIERS[tier(q, m)]
    if q in OVERRIDE and "ignore_override" not in m:
        t = OVERRIDE[q]
    return t, d

WD = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

def window_for(q, at, m=frozenset()):
    """The BATCH-7 job whose window holds for q at `at`, else None (§6)."""
    for job, wq, days, start, end, status in SCHEDULE:
        if wq != q or (status != "active" and "ignore_retired" not in m):
            continue
        for back in (0, 1):                               # a window that began yesterday may still hold
            d0 = at.date() - timedelta(days=back)
            if days != "daily" and WD[d0.weekday()] not in days and "ignore_weekday" not in m:
                continue
            s = datetime.fromisoformat(f"{d0}T{start}:00+00:00")
            e = datetime.fromisoformat(f"{d0}T{end}:00+00:00")
            if e <= s:
                e += timedelta(days=1)
            if s <= at < e:
                return job
    return None

def engaged(q, at, m=frozenset()):
    """§4: the latest ENGAGED/RELEASED event for q at or before `at` is ENGAGED."""
    state = False
    for day, hms, _b, eq, ev, _d in EVENTS:
        if eq != q or ev not in ("BACKPRESSURE_ENGAGED", "BACKPRESSURE_RELEASED"):
            continue
        if ts(hms, day) > at and "ignore_event_time" not in m:
            continue
        if ev == "BACKPRESSURE_ENGAGED":
            state = True
        elif "ignore_release" not in m:
            state = False
    return state

def drain_minutes(n, pub, ack):
    """§5: in-flight over the net drain rate; None when the queue is not draining."""
    return Fraction(n, ack - pub) if ack > pub else None

def audit(row, m=frozenset()):
    q, _svc, hms, n, pub, ack, hint = row
    at = ts(hms)
    if q in UNCONFIGURED and not (("burst_clears_config" in m) and window_for(q, at, m)):
        return NOCFG, "no_config", None
    if q in UNCONFIGURED:
        return NONE, "burst", window_for(q, at, m)
    job = ("dashboard hint" if hint else None) if "dashboard_hint" in m else window_for(q, at, m)
    t, dmax = limits(q, m)
    over = n >= t if "ge_threshold" in m else n > t
    if job:
        return NONE, ("burst" if over else "clean"), job
    dm = drain_minutes(n, pub, ack)
    drain_over = (dm is None and "not_draining_ok" not in m) or (dm is not None and dm > dmax)
    if over:
        if not engaged(q, at, m):
            return THRESH, "threshold", None
        if "engaged_clears_all" in m:
            return NONE, "engaged", None
    if drain_over:
        return DRAIN, "drain", dm
    return NONE, ("engaged" if over else "clean"), dm

def run(m=frozenset()):
    rows = [(r, *audit(r, m)) for r in EXPORT]
    res = OrderedDict(
        flagged_count=sum(f != NONE for _r, f, *_ in rows),
        threshold_exceeded_count=sum(f == THRESH for _r, f, *_ in rows),
        no_config_count=sum(f == NOCFG for _r, f, *_ in rows),
        drain_exceeded_count=sum(f == DRAIN for _r, f, *_ in rows),
        compliant_count=sum(f == NONE for _r, f, *_ in rows),
    )
    return rows, res

rows, RESULTS = run()
assert RESULTS["flagged_count"] + RESULTS["compliant_count"] == len(EXPORT)

# ---- fixtures ---------------------------------------------------------------
def w_csv(path, header, body):
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(header)
    wr.writerows(body)
    path.write_text(buf.getvalue(), encoding="utf-8")

def health(n):
    return "red" if n >= 5000 else "amber" if n >= 1000 else "green"

INP.mkdir(parents=True, exist_ok=True)
for stale in INP.iterdir():
    stale.unlink()
w_csv(INP / "queue_status.csv",
      ["queue_id", "sampled_at", "in_flight_count", "publish_rate_per_min", "ack_rate_per_min",
       "dashboard_health", "dashboard_burst_hint"],
      [(q, f"{DAY}T{hms}Z", n, p, a, health(n), str(h).lower())
       for q, _s, hms, n, p, a, h in sorted(EXPORT, key=lambda e: e[2])])
svc = {q: s for q, s, *_ in EXPORT}
svc["legacy.order-sync"] = "checkout-api"
cfg_q = sorted([q for q in QUEUES if q not in UNCONFIGURED] + DECOMMISSIONED, key=lambda q: (svc[q], q))
w_csv(INP / "backpressure_config.csv", ["queue_id", "owning_service", "in_flight_threshold_override"],
      [(q, svc[q], OVERRIDE.get(q, "")) for q in cfg_q])

sched = "\n".join(f"| {j} | `{q}` | {d} | {s} | {e} | {st} |" for j, q, d, s, e, st in SCHEDULE)
(INP / "batch_schedule.md").write_text(f"""# Scheduled batch windows (BATCH-7)

Burst windows agreed with the platform team for scheduled batch work. All times are UTC.
`daily` runs every day; otherwise the window opens on the days listed. A window whose end
is earlier than its start runs past midnight and closes the next day.

| job | queue | days | opens | closes | status |
|---|---|---|---|---|---|
{sched}
""", encoding="utf-8")

(INP / "broker_events.log").write_text(
    "".join(f"{d}T{h}Z {b} queue={q} event={ev} {dt}\n" for d, h, b, q, ev, dt in EVENTS), encoding="utf-8")

CATALOGUE = """# Service catalogue — messaging queues

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
"""
(INP / "service_catalogue.md").write_text(CATALOGUE, encoding="utf-8")
for q in QUEUES:
    assert f"`{q}`" in CATALOGUE, f"catalogue never names {q}"

tier_rows = "\n".join(f"| {t} | {n:,} messages | {d} minutes |" for t, (n, d) in TIERS.items())
POLICY = f"""# Queue backpressure policy (PLAT-31)

This decides whether a queue's in-flight load was compliant at the moment the queue was
sampled. Where a broker dashboard disagrees — its health colour or its burst hint — this
policy decides.

## 1. Configuration required

A queue with no entry in the backpressure config at all is `NO_BACKPRESSURE_CONFIGURED`.
This is checked first, and it applies whatever else is true of the queue, a burst window
included: there is no threshold to measure an unconfigured queue against.

## 2. Tier

Every configured queue has a tier, and this section decides it — not the queue's name, not
its owning team's priority label, and not its volume. The service catalogue says what each
queue does.

A queue is **critical** when either of these holds:

- **(a) A customer's call is held on it.** A service answering a customer — a web, app or
  API call from someone outside the company, merchants included — holds that call open while
  a message it has put on this queue waits to be consumed, or until an answer comes back to
  it on this queue, even if it goes on waiting on other queues as well. The hold carries
  down a chain: when the service holding a customer's call is itself waiting on a second
  service, and that service cannot answer until a message it has put on a queue has been
  consumed or an answer has come back to it on a queue, the customer's call is held on that
  queue too, however many services lie in between. It is enough that some of the queue's
  traffic is held this way. A queue a service publishes to only after it has answered does
  not count, and neither does a queue where the one kept waiting is a member of staff or a
  scheduled job rather than a customer. Waiting that happens after the call has been
  answered — for an email or a text to arrive, say — is not a held call.
- **(b) It moves money.** A message on it instructs a movement of funds: a charge, a
  refund, a payout, a credit to or debit from a wallet, or a settlement transfer. A message
  that reports, reconciles, summarises or notifies about a movement that has already been
  made does not count.

A queue that meets either (a) or (b) is critical; the exclusions under (a) do not narrow
(b). Every other queue is **standard**.

## 3. Limits

| tier | default in-flight threshold | max drain time |
|---|---|---|
{tier_rows}

A queue's in-flight threshold is its `in_flight_threshold_override` in the backpressure
config when one is set, and its tier default otherwise. Its max drain time is always its
tier's.

## 4. In-flight threshold

A configured queue whose in-flight count is more than its threshold is
`BACKPRESSURE_THRESHOLD_EXCEEDED` (a count equal to the threshold is within it) — **unless**
backpressure was engaged for that queue at the moment it was sampled, in which case the
system responded correctly and there is no threshold finding. The broker event log is the
record: a queue is engaged at a moment when the latest `BACKPRESSURE_ENGAGED` or
`BACKPRESSURE_RELEASED` event for it at or before that moment is `BACKPRESSURE_ENGAGED`.
Engagement answers this section only; it does not clear section 5.

## 5. Drain time

A queue's drain time is its in-flight count divided by its net drain rate, the ack rate
less the publish rate, both per minute. A queue whose ack rate is not above its publish rate
is not draining, and its drain time exceeds any maximum. Drain time is compared with the
maximum exactly, without rounding. A configured queue whose drain time
is more than its max drain time is `DRAIN_TIME_EXCEEDED`.

## 6. Scheduled burst windows

A configured queue is exempt from sections 4 and 5 while a burst window documented for that
queue in the batch schedule (BATCH-7) holds at the moment it was sampled. A window holds
from its opening time up to, but not including, its closing time. Only an active BATCH-7
entry documents a window: a retired entry documents none, and the broker export's
`dashboard_burst_hint` documents nothing. A window exempts only the queue it names. No
window exempts a queue from section 1.

## 7. One finding per queue

Each queue in the broker export carries exactly one finding: the first of sections 1, 4
and 5 that applies to it, with the exemptions in sections 4 and 6 taken into account, or
`none` when none does. The finding names are
`NO_BACKPRESSURE_CONFIGURED`, `BACKPRESSURE_THRESHOLD_EXCEEDED`, `DRAIN_TIME_EXCEEDED` and
`none`.

## 8. Audit figures

- `flagged_count` — queues whose finding is not `none`.
- `threshold_exceeded_count`, `no_config_count`, `drain_exceeded_count` — queues carrying
  `BACKPRESSURE_THRESHOLD_EXCEEDED`, `NO_BACKPRESSURE_CONFIGURED` and `DRAIN_TIME_EXCEEDED`
  respectively.
- `compliant_count` — queues whose finding is `none`.

`flagged_count` and `compliant_count` together make up every queue in the broker export.
"""
(INP / "backpressure_policy.md").write_text(POLICY, encoding="utf-8")

# ---- gold -------------------------------------------------------------------
def fmt_drain(dm):
    return f"{float(dm):.1f}".rstrip("0").rstrip(".")

def explain(row, f, why, extra):
    q, _s, hms, n, pub, ack, _h = row
    if why == "no_config":
        return f"- `{q}` — `{f}`: it has no entry in the backpressure config, so there is no threshold to measure its {n:,} in-flight messages against."
    t, dmax = limits(q)
    tr = tier(q)
    src = "its config override" if q in OVERRIDE else f"the {tr} default"
    if why == "threshold":
        return (f"- `{q}` — `{f}`: {n:,} in flight against a threshold of {t:,} ({src}; the queue is {tr}), "
                f"and backpressure was not engaged when it was sampled at {hms} UTC.")
    if why == "drain":
        how = ("it is not draining (acks {0}/min against publishes {1}/min), which exceeds any maximum"
               .format(ack, pub) if extra is None else
               f"its drain time is {fmt_drain(extra)} minutes ({n:,} in flight over a net {ack - pub}/min)")
        return f"- `{q}` — `{f}`: {how}; the {tr} max drain time is {dmax} minutes."
    if why == "burst":
        return (f"- `{q}` — `none`: {n:,} in flight is over its threshold of {t:,}, but the BATCH-7 "
                f"\"{extra}\" burst window held when it was sampled at {hms} UTC, which exempts it from the "
                f"threshold and drain checks.")
    if why == "engaged":
        dm = drain_minutes(n, pub, ack)
        return (f"- `{q}` — `none`: {n:,} in flight is over its threshold of {t:,}, but backpressure was already "
                f"engaged when it was sampled at {hms} UTC, so the system responded correctly; its drain time of "
                f"{fmt_drain(dm)} minutes is within the {dmax}-minute maximum.")
    return None

def over_threshold_none(row, f, why):
    return f == NONE and why in ("burst", "engaged")

flagged = [explain(r, f, w, x) for r, f, w, x in rows if f != NONE]
cleared = [explain(r, f, w, x) for r, f, w, x in rows if over_threshold_none(r, f, w)]
table = "\n".join(f"| `{r[0]}` | {tier(r[0]) if r[0] in TIER else '—'} | {r[3]:,} | {f} |" for r, f, _w, _x in rows)

SOL.mkdir(parents=True, exist_ok=True)
w_csv(SOL / "backpressure_audit.csv", ["queue_id", "tier", "in_flight_count", "finding"],
      [(r[0], tier(r[0]) if r[0] in TIER else "", r[3], f) for r, f, _w, _x in rows])
(SOL / "results.json").write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")
MEMO = f"""# Queue backpressure audit — incident night, {DAY}

{len(rows)} queues in the broker export, audited against PLAT-31. {RESULTS['compliant_count']} are compliant and \
{RESULTS['flagged_count']} carry a finding: {RESULTS['threshold_exceeded_count']} over threshold, \
{RESULTS['drain_exceeded_count']} over their drain time, {RESULTS['no_config_count']} with no backpressure config.

| Queue | Tier | In-flight | Finding |
|---|---|---|---|
{table}

## Findings

{chr(10).join(flagged)}

## Over threshold but no finding

{chr(10).join(cleared)}
"""
(SOL / "backpressure_memo.md").write_text(MEMO, encoding="utf-8")

# ---- verifiers --------------------------------------------------------------
def V(name, how, why, src, assertion):
    return OrderedDict(name=name, metadata=OrderedDict(how_justification=how, why_justification=why, tag="core"),
                       source=OrderedDict(type="file", file=OrderedDict(type=src[0], command=src[1], arguments=src[2])),
                       assertion=assertion)

def det(path, cmp, expected):
    return OrderedDict(type="deterministic", expected=expected, deterministic=OrderedDict(path=path, comparison=cmp))

def cell(value):
    """A whole CSV cell equal to value, in any column: bounded by a comma or the line's ends."""
    return r"(?:^|,)[ \t]*\x22?" + re.escape(value) + r"\x22?[ \t]*(?:,|\r?$)"

def row_with(q):
    return r"(?mi)^(?=[^\n]*" + cell(q) + r")"

def key(q):
    return q.replace(".", "_").replace("-", "_")

AUDIT = ("csv", "extract_text", {"path": "backpressure_audit.csv"})
MEMO_SRC = ("md", "extract_text", {"path": "backpressure_memo.md"})
RES = ("json", "read_file", {"path": "results.json"})
EXIST = lambda p: ("filesystem", "check_path_exists", {"path": p})

vs = [
    V("audit_exists", "Checks backpressure_audit.csv is present as a file.",
      "The audit is a named deliverable.", EXIST("backpressure_audit.csv"), det("$.is_file", "equals", True)),
    V("memo_exists", "Checks backpressure_memo.md is present as a file.",
      "The memo is a named deliverable.", EXIST("backpressure_memo.md"), det("$.is_file", "equals", True)),
    V("results_exists", "Checks results.json is present as a file.",
      "The figures file is a named deliverable.", EXIST("results.json"), det("$.is_file", "equals", True)),
    V("audit_header",
      "Opens backpressure_audit.csv and requires a header row with a queue_id cell and a finding cell, in either order.",
      "The instruction asks for a queue_id and a finding column; any other columns are the solver's choice.",
      AUDIT, det("$.text", "regex_match",
                 r"(?mi)\A(?=[^\n]*" + cell("queue_id") + r")(?=[^\n]*" + cell("finding") + r")")),
]
for r, f, _w, _x in rows:
    q = r[0]
    others = [c for c in (*CODES, NONE) if c != f]
    vs.append(V(f"row_{key(q)}_finding",
                f"Opens backpressure_audit.csv and requires a row with a {q} cell and a finding cell equal to {f}.",
                f"{q}'s finding under PLAT-31 is {f}.",
                AUDIT, det("$.text", "regex_match", row_with(q) + r"(?=[^\n]*" + cell(f) + r")")))
    vs.append(V(f"row_{key(q)}_no_other_finding",
                f"Opens backpressure_audit.csv and forbids any row with a {q} cell from also carrying a cell equal to "
                f"{', '.join(others)}.",
                f"Each queue carries exactly one finding (PLAT-31 §7); a {q} row naming another contradicts it.",
                AUDIT, det("$.text", "not_regex_match",
                           row_with(q) + r"(?=[^\n]*(?:" + "|".join(cell(o) for o in others) + r"))")))
for k, v in RESULTS.items():
    vs.append(V(f"result_{k}", f"Reads results.json and compares $.{k}.",
                f"`{k}` as PLAT-31 §8 defines it.", RES, det(f"$.{k}", "equals", v)))

# The memo is graded on the facts the instruction asks it to carry, never on
# phrasing: for a threshold finding, the in-flight figure and the threshold; for a
# drain finding, the max drain time it was measured against (the drain figure
# itself is a quotient a writer may round any way, so it is not pinned); for a
# queue with no config, the queue; for a queue over its threshold that comes out
# none, what clears it. Each fact must sit within 400 characters of the queue id,
# either order, with no other queue id in between.
def qid(q):
    return r"(?<![\w.-])" + re.escape(q) + r"(?![\w-]|\.\w)"

ANY_Q = "(?:" + "|".join(qid(q) for q in QUEUES) + ")"
GAP = r"(?:(?!" + ANY_Q + r").){0,400}?"

def near(q, fact):
    return r"(?is)(?:" + qid(q) + GAP + fact + r"|" + fact + GAP + qid(q) + r")"

def num(n):
    """n with or without a thousands comma, optionally .0, not part of a longer number."""
    return r"(?<![\d.,])" + f"{n:,}".replace(",", ",?") + r"(?:\.0+)?(?![\d]|[.,]\d)"

REASON = {"burst": r"(?:burst|BATCH-7|batch window)", "engaged": r"engag"}
for r, f, why, extra in rows:
    q = r[0]
    if why == "no_config":
        vs.append(V(f"memo_{key(q)}_named", f"Opens backpressure_memo.md and requires the queue id {q}.",
                    f"{q} is flagged {f}, and the memo explains each finding.",
                    MEMO_SRC, det("$.text", "regex_match", qid(q))))
    elif why == "threshold":
        t, _d = limits(q)
        for tag, v in (("figure", r[3]), ("limit", t)):
            vs.append(V(f"memo_{key(q)}_{tag}",
                        f"Opens backpressure_memo.md and requires {v:,} within 400 characters of {q}, either order, "
                        f"with no other queue id in between.",
                        f"{q} is flagged {f} at {r[3]:,} in flight against a threshold of {t:,}; the instruction asks "
                        f"the memo for the figure and the limit.",
                        MEMO_SRC, det("$.text", "regex_match", near(q, num(v)))))
    elif why == "drain":
        _t, dmax = limits(q)
        vs.append(V(f"memo_{key(q)}_limit",
                    f"Opens backpressure_memo.md and requires {dmax} within 400 characters of {q}, either order, "
                    f"with no other queue id in between.",
                    f"{q} is flagged {f} against a max drain time of {dmax} minutes; the instruction asks the memo "
                    f"for the limit.",
                    MEMO_SRC, det("$.text", "regex_match", near(q, num(dmax)))))
    elif over_threshold_none(r, f, why):
        vs.append(V(f"memo_{key(q)}_cleared",
                    f"Opens backpressure_memo.md and requires {REASON[why]!r} within 400 characters of {q}, either "
                    f"order, with no other queue id in between.",
                    f"{q} is over its threshold and comes out none because "
                    f"{'a BATCH-7 burst window held' if why == 'burst' else 'backpressure was engaged'}; the "
                    f"instruction asks the memo to say what clears it.",
                    MEMO_SRC, det("$.text", "regex_match", near(q, REASON[why]))))

spec = OrderedDict(task_id=TASK_ID, verifiers=vs)
(ROOT / "tests" / "verifier.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

def failed_checks(files):
    """Pin names a submission fails, evaluated here exactly as the engine does (re.search / equals)."""
    bad = []
    for v in vs:
        a, src = v["assertion"], v["source"]["file"]
        path, cmp = src["arguments"]["path"], a["deterministic"]["comparison"]
        if src["type"] == "filesystem":
            ok = path in files
        elif src["type"] == "json":
            ok = json.loads(files[path]).get(a["deterministic"]["path"][2:]) == a["expected"]
        else:
            ok = bool(re.search(a["expected"], files[path])) == (cmp == "regex_match")
        if not ok:
            bad.append(v["name"])
    return bad

GOLD = {p.name: p.read_text(encoding="utf-8") for p in SOL.iterdir()}
assert failed_checks(GOLD) == [], failed_checks(GOLD)

# ---- golden trajectory ------------------------------------------------------
steps = [{"name": "bash", "arguments": {"command": f"cat input/{f.name}"}} for f in sorted(INP.iterdir())]
for name, marker in (("backpressure_audit.csv", "AUDITEOF"), ("backpressure_memo.md", "MEMOEOF"),
                     ("results.json", "RESULTSEOF")):
    steps.append({"name": "bash", "arguments": {"command": f"cat > {name} << '{marker}'\n{GOLD[name]}{marker}"}})
steps.append({"name": "bash", "arguments": {"command": "ls -la backpressure_audit.csv backpressure_memo.md results.json"}})
for s in steps:
    mt = re.match(r"cat > (\S+) << '(\w+)'\n(.*)\2\Z", s["arguments"]["command"], re.S)
    if mt:
        assert mt.group(3) == GOLD[mt.group(1)], mt.group(1)
(ROOT / "solution" / "golden_trajectory.json").write_text(json.dumps(steps, indent=2) + "\n", encoding="utf-8")

tally = OrderedDict((c, [r[0] for r, f, _w, _x in rows if f == c]) for c in (*CODES, NONE))
print(f"{len(rows)} queues; figures {dict(RESULTS)}")
print(f"verifiers: {len(vs)} (all core); golden_trajectory: {len(steps)} steps")

# ---- what each single misreading costs --------------------------------------
if "--price" in sys.argv:
    MISTAKES = ["surface_tier", "dashboard_hint", "ignore_override", "ge_threshold", "ignore_release",
                "ignore_event_time", "ignore_weekday", "ignore_retired", "engaged_clears_all",
                "burst_clears_config", "not_draining_ok"] + [f"flip:{q}" for q in TIER]
    print(f"\n{'misreading':42s} queues changed  checks failed / {len(vs)}")
    for mk in MISTAKES:
        mrows, mres = run(frozenset([mk]))
        changed = [r[0] for (r, f, *_), (_r2, g, *_) in zip(mrows, rows) if f != g]
        if not changed:
            print(f"{mk:42s} (no effect)")
            continue
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows(
            [("queue_id", "finding")] + [(r[0], f) for r, f, *_ in mrows])
        sub = {**GOLD, "backpressure_audit.csv": buf.getvalue(), "results.json": json.dumps(mres)}
        n_bad = len(failed_checks(sub))
        print(f"{mk:42s} {len(changed):>3}            {n_bad:>3}   {', '.join(changed)}")

# ---- probe submissions: known answers for the grader ------------------------
# `--probes DIR` writes one folder per probe; tools/c239_probes.py grades each in
# the task image. A name ending in `_ok` must score 1.0; every other must not.
if "--probes" in sys.argv:
    import shutil
    out = Path(sys.argv[sys.argv.index("--probes") + 1])
    shutil.rmtree(out, ignore_errors=True)

    def write(name, files):
        d = out / name
        d.mkdir(parents=True)
        for fn, text in files.items():
            (d / fn).write_bytes(text.encode("utf-8"))

    def audit_csv(pairs, header=("queue_id", "finding")):
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows([header, *pairs])
        return buf.getvalue()

    gold_pairs = [(r[0], f) for r, f, *_ in rows]
    write("gold_ok", GOLD)
    # Correct, written differently: finding first, quoted, notes column, CRLF, BOM;
    # a memo with no thousands commas, each fact stated before the queue id.
    alt_csv = "﻿" + "".join(f'"{f}","{q}","see memo"\r\n' for q, f in
                                 [("queue_id", "finding"), *gold_pairs]).replace('"queue_id","see memo"', '"queue_id","notes"')
    lines = ["Backpressure audit notes", ""]
    for r, f, why, extra in rows:
        q, n = r[0], r[3]
        t, dmax = limits(q) if q in TIER else (None, None)
        if why == "no_config":
            lines.append(f"No config row at all -> {q}: {f}.")
        elif why == "threshold":
            lines.append(f"Limit {t}, measured {n} in flight, backpressure off: {q} is {f}.")
        elif why == "drain":
            lines.append(f"Allowed {dmax} min to drain; it does not: {q} is {f}.")
        elif why == "burst":
            lines.append(f"Scheduled Burst Window ({extra}) was open: {q} is exempt, none.")
        elif why == "engaged":
            lines.append(f"Backpressure had engaged, so {q} is none.")
        lines.append("")
    write("correct_alt_format_ok", {**GOLD, "backpressure_audit.csv": alt_csv, "backpressure_memo.md": "\n".join(lines)})
    # The exploits the mined grader passed.
    every = " ".join((*CODES, NONE))
    write("hack_all_codes_one_cell", {**GOLD, "backpressure_audit.csv": audit_csv([(q, every) for q in QUEUES])})
    write("hack_all_codes_four_cells", {**GOLD, "backpressure_audit.csv": audit_csv(
        [(q, *CODES, NONE) for q in QUEUES], header=("queue_id", "finding", "f2", "f3", "f4"))})
    write("hack_duplicate_rows", {**GOLD, "backpressure_audit.csv": audit_csv(
        [(q, c) for q in QUEUES for c in (*CODES, NONE)])})
    write("hack_stub_memo", {**GOLD, "backpressure_memo.md": " ".join(QUEUES) + " burst window engaged\n"})
    write("memo_without_figures", {**GOLD, "backpressure_memo.md": re.sub(r"(?<![\w.-])\d[\d,.]*", "N", GOLD["backpressure_memo.md"])})
    # One misreading each.
    for mk in ("surface_tier", "dashboard_hint", "ignore_override", "ignore_weekday", "engaged_clears_all",
               "flip:wallet.cashback-accrual"):
        mrows, mres = run(frozenset([mk]))
        write("mistake_" + re.sub(r"\W", "_", mk), {**GOLD, "results.json": json.dumps(mres),
                                                    "backpressure_audit.csv": audit_csv([(r[0], f) for r, f, *_ in mrows])})
    print(f"probes written to {out}")
