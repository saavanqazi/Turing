# Queue backpressure audit — 6 queues

6 queues checked against PLAT-31. 3 are compliant and 3 carry a
finding.

| Queue | In-flight | Drain (min) | Finding |
|---|---|---|---|
| Q-01 | 800 | 10 | none |
| Q-02 | 1500 | 10 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| Q-03 | 6000 | 50 | none |
| Q-04 | 2000 | 10 | NO_BACKPRESSURE_CONFIGURED |
| Q-05 | 4500 | 90 | DRAIN_TIME_EXCEEDED |
| Q-06 | 1200 | 10 | none |

## Q-03 is not a threshold breach

Q-03 carries 6,000 in-flight messages, over the standard tier's 5,000 threshold, which looks
like a breach. The queue is marked inside a documented scheduled-batch burst window, and the
policy exempts every check for a queue in that window. The finding is `none`.

## Other findings

Q-02 carries 1,500 in-flight messages over its critical threshold with backpressure not yet
engaged: `BACKPRESSURE_THRESHOLD_EXCEEDED`. Q-04 has no entry in the backpressure config at
all: `NO_BACKPRESSURE_CONFIGURED`. Q-05's drain time of 90 minutes exceeds the standard
tier's 60-minute maximum: `DRAIN_TIME_EXCEEDED`. Q-06 exceeds its critical threshold too, but
backpressure has already engaged, so the system responded correctly and the finding is
`none`.
