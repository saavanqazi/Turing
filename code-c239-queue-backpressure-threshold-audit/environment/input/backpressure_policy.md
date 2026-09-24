# Queue backpressure policy (PLAT-31)

This decides whether a queue's in-flight load is compliant. Where a broker dashboard's own
health colour disagrees, this policy decides.

## 1. Configuration required

A queue with no entry in the backpressure config at all is `NO_BACKPRESSURE_CONFIGURED`.
This is checked first — there is no threshold to measure an unconfigured queue against.

## 2. In-flight threshold

| tier | in-flight threshold | max drain time |
|---|---|---|
| critical | 1,000 messages | 15 minutes |
| standard | 5,000 messages | 60 minutes |

A configured queue over its tier's in-flight threshold is `BACKPRESSURE_THRESHOLD_EXCEEDED`
— **unless** backpressure has already engaged for that queue, in which case the system
responded correctly and there is no finding, or the queue is marked inside a documented
scheduled-batch burst window, which exempts every check below for as long as the window
holds.

## 3. Drain time

A configured queue (not in a burst window) whose drain time exceeds its tier's maximum is
`DRAIN_TIME_EXCEEDED`.

## 4. Finding names

`NO_BACKPRESSURE_CONFIGURED`, `BACKPRESSURE_THRESHOLD_EXCEEDED`, `DRAIN_TIME_EXCEEDED`, or
`none`.
