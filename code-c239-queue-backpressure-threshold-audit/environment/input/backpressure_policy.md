# Queue backpressure policy (PLAT-31)

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
  a message it has put on this queue waits to be consumed — even if it then goes on waiting
  for a reply on another queue — or until an answer comes back to it on this queue. That
  covers a request the service sends on the customer's behalf while it holds the call, as
  well as the customer's own. It is enough that some of the queue's traffic is held this
  way. A queue a service publishes to only after it has answered does not count, and neither
  does a queue where the one kept waiting is a member of staff. Waiting that happens after
  the call has been answered — for an email or a text to arrive, say — is not a held call.
- **(b) It moves money.** A message on it instructs a movement of funds: a charge, a
  refund, a payout, a credit to or debit from a wallet, or a settlement transfer. A message
  that reports, reconciles, summarises or notifies about a movement that has already been
  made does not count.

A queue that meets either (a) or (b) is critical; the exclusions under (a) do not narrow
(b). Every other queue is **standard**.

## 3. Limits

| tier | default in-flight threshold | max drain time |
|---|---|---|
| critical | 1,000 messages | 15 minutes |
| standard | 5,000 messages | 60 minutes |

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
and 5 that applies to it, or `none` when none does. The finding names are
`NO_BACKPRESSURE_CONFIGURED`, `BACKPRESSURE_THRESHOLD_EXCEEDED`, `DRAIN_TIME_EXCEEDED` and
`none`.

## 8. Audit figures

- `flagged_count` — queues whose finding is not `none`.
- `threshold_exceeded_count`, `no_config_count`, `drain_exceeded_count` — queues carrying
  `BACKPRESSURE_THRESHOLD_EXCEEDED`, `NO_BACKPRESSURE_CONFIGURED` and `DRAIN_TIME_EXCEEDED`
  respectively.
- `compliant_count` — queues whose finding is `none`.

`flagged_count` and `compliant_count` together make up every queue in the broker export.
