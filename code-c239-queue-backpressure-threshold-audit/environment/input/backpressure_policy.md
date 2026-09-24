# Queue backpressure policy (PLAT-31)

This decides whether a queue was compliant at the moment its broker snapshot was taken. Where
a broker dashboard disagrees, this policy decides. Terms in *italics* are defined in section 6.

## 1. Configuration required

A queue with no entry in the backpressure config is `NO_BACKPRESSURE_CONFIGURED`. This is
checked first: there is nothing to measure an unconfigured queue against.

## 2. In-flight threshold

A configured queue whose *in-flight load* is more than its *threshold* is
`BACKPRESSURE_THRESHOLD_EXCEEDED`, unless backpressure is *engaged* on it, in which case there
is no threshold finding.

## 3. Drain time

A configured queue that *holds work* and whose *drain time* is more than its tier's max drain
time is `DRAIN_TIME_EXCEEDED`.

## 4. Scheduled batch windows

A configured queue inside an *open batch window* is exempt from sections 2 and 3.

## 5. Findings and figures

Each queue in the snapshot carries exactly one finding: the first of sections 1, 2 and 3 that
applies to it, or `none`. `flagged_count` counts queues whose finding is not `none`;
`threshold_exceeded_count`, `no_config_count` and `drain_exceeded_count` count queues carrying
`BACKPRESSURE_THRESHOLD_EXCEEDED`, `NO_BACKPRESSURE_CONFIGURED` and `DRAIN_TIME_EXCEEDED`;
`compliant_count` counts queues whose finding is `none`.

## 6. Terms

| tier | default threshold | max drain time |
|---|---|---|
| critical | 1,000 messages | 15 minutes |
| standard | 5,000 messages | 60 minutes |

- *In-flight load*: the messages a queue holds that have not been acknowledged, those ready
  for delivery and those delivered and awaiting acknowledgement together.
- *Threshold*: the queue's `in_flight_threshold_override` in the backpressure config when one
  is set, otherwise its tier's default threshold.
- *Engaged*: the broker is throttling the queue's publishers, which it reports as a publisher
  flow state of `flow` or `blocked`.
- *Holds work*: the queue's in-flight load is above zero.
- *Drain time*: in-flight load divided by the ack rate less the publish rate, per minute,
  compared exactly without rounding. A queue whose ack rate is not above its publish rate is
  not draining, and its drain time exceeds any maximum.
- *Open batch window*: an active BATCH-7 entry for the queue whose window contains the
  snapshot time, from its opening time up to but not including its closing time.
