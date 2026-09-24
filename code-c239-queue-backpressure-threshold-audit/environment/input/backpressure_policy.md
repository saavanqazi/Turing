# Queue backpressure policy (PLAT-31)

This decides whether a queue's in-flight load was compliant at the moment the queue was
sampled. Where a broker dashboard's own health colour disagrees, this policy decides.

## 1. Configuration required

A queue with no entry in the backpressure config at all is `NO_BACKPRESSURE_CONFIGURED`.
This is checked first: there is no threshold to measure an unconfigured queue against.

## 2. Tier

Every configured queue has a tier, decided by this section from what the service catalogue
says the queue does. A queue is **critical** when either of these holds:

- **(a) A customer's call is held on it.** A service answering a customer — a web, app or
  API call from someone outside the company, merchants included — does not answer until a
  message it has put on this queue has been consumed, or until an answer has come back to
  it on this queue, even if it then goes on waiting on other queues as well. The hold
  carries down a chain: when the service holding a customer's call is waiting on a second
  service, and that service does not answer until a message it has put on a queue has been
  consumed or an answer has come back to it on a queue, the customer's call is held on that
  queue too, however many services lie in between. It is enough that some of the queue's
  traffic is held this way.
- **(b) It moves money.** A message on it instructs a movement of funds: a charge, a
  refund, a payout, a credit to or debit from a wallet, or a settlement transfer.

Every other queue is **standard**.

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
`BACKPRESSURE_THRESHOLD_EXCEEDED`, unless backpressure was engaged for that queue at the
moment it was sampled, in which case there is no threshold finding. The broker event log is
the record: a queue is engaged at a moment when the latest `BACKPRESSURE_ENGAGED` or
`BACKPRESSURE_RELEASED` event for it at or before that moment is `BACKPRESSURE_ENGAGED`.

## 5. Drain time

A queue's drain time is its in-flight count divided by its net drain rate, the ack rate
less the publish rate, both per minute. A queue whose ack rate is not above its publish rate
is not draining, and its drain time exceeds any maximum. Drain time is compared with the
maximum exactly, without rounding. A configured queue whose drain time is more than its max
drain time is `DRAIN_TIME_EXCEEDED`.

## 6. Scheduled burst windows

A configured queue is exempt from sections 4 and 5 while a burst window documented for it
in the batch schedule (BATCH-7) holds at the moment it was sampled. A window holds from its
opening time up to, but not including, its closing time. Only an active BATCH-7 entry
documents a window.

## 7. One finding per queue

Each queue in the broker export carries exactly one finding: the first of sections 1, 4
and 5 that applies to it, with the exemptions in sections 4 and 6 taken into account, or
`none` when none does. The finding names are `NO_BACKPRESSURE_CONFIGURED`,
`BACKPRESSURE_THRESHOLD_EXCEEDED`, `DRAIN_TIME_EXCEEDED` and `none`.

## 8. Audit figures

- `flagged_count` — queues whose finding is not `none`.
- `threshold_exceeded_count`, `no_config_count`, `drain_exceeded_count` — queues carrying
  `BACKPRESSURE_THRESHOLD_EXCEEDED`, `NO_BACKPRESSURE_CONFIGURED` and `DRAIN_TIME_EXCEEDED`
  respectively.
- `compliant_count` — queues whose finding is `none`.

`flagged_count` and `compliant_count` together make up every queue in the broker export.
