# Queue backpressure policy (PLAT-31)

This decides whether a queue's in-flight load is compliant. Where a broker dashboard's own
health colour disagrees, this policy decides.

## 1. Configuration required

A queue with no entry in the backpressure config at all is `NO_BACKPRESSURE_CONFIGURED`.
This is checked first, and it applies whatever else is true of the queue, a burst window
included: there is no threshold to measure an unconfigured queue against.

## 2. In-flight threshold

A configured queue is measured against the in-flight threshold and maximum drain time
recorded for it in the backpressure config. The config is set from these tier defaults:

| tier | in-flight threshold | max drain time |
|---|---|---|
| critical | 1,000 messages | 15 minutes |
| standard | 5,000 messages | 60 minutes |

A configured queue whose in-flight count is more than its threshold is
`BACKPRESSURE_THRESHOLD_EXCEEDED` (a count equal to the threshold is within it) — **unless**
backpressure has already engaged for that queue, in which case the system responded
correctly and there is no threshold finding. Engagement answers this section only; it does
not clear section 3.

## 3. Drain time

A configured queue whose drain time is more than its maximum drain time is
`DRAIN_TIME_EXCEEDED`.

## 4. Scheduled burst windows

A queue marked inside a documented scheduled-batch burst window is exempt from sections 2
and 3 for as long as the window holds. It is not exempt from section 1.

## 5. One finding per queue

Each queue carries exactly one finding: the first of sections 1, 2 and 3 that applies to
it, or `none` when none does. The finding names are `NO_BACKPRESSURE_CONFIGURED`,
`BACKPRESSURE_THRESHOLD_EXCEEDED`, `DRAIN_TIME_EXCEEDED` and `none`.

## 6. Audit figures

- `flagged_count` — queues whose finding is not `none`.
- `threshold_exceeded_count`, `no_config_count`, `drain_exceeded_count` — queues carrying
  `BACKPRESSURE_THRESHOLD_EXCEEDED`, `NO_BACKPRESSURE_CONFIGURED` and `DRAIN_TIME_EXCEEDED`
  respectively.
- `compliant_count` — queues whose finding is `none`.

`flagged_count` and `compliant_count` together make up every queue audited.
