# Queue backpressure audit — 6 queues

6 queues checked against PLAT-31. 3 are compliant and 3 carry a finding.

| Queue | In-flight | Drain (min) | Finding |
|---|---|---|---|
| Q-01 | 800 | 10 | none |
| Q-02 | 1,500 | 10 | BACKPRESSURE_THRESHOLD_EXCEEDED |
| Q-03 | 6,000 | 50 | none |
| Q-04 | 2,000 | 10 | NO_BACKPRESSURE_CONFIGURED |
| Q-05 | 4,500 | 90 | DRAIN_TIME_EXCEEDED |
| Q-06 | 1,200 | 10 | none |

## Findings

- **Q-02** — `BACKPRESSURE_THRESHOLD_EXCEEDED`. 1,500 in flight against the critical threshold of 1,000, and backpressure has not engaged.
- **Q-04** — `NO_BACKPRESSURE_CONFIGURED`. Q-04 has no entry in the backpressure config, so there is no threshold to measure its 2,000 in-flight messages against.
- **Q-05** — `DRAIN_TIME_EXCEEDED`. Drain time of 90 minutes against the standard maximum of 60 minutes.

## Over threshold but no finding

- **Q-03** — `none`. 6,000 in flight is over the standard threshold of 5,000, but the queue is marked inside a documented scheduled-batch burst window, which exempts it from the threshold and drain checks while the window holds.
- **Q-06** — `none`. 1,200 in flight is over the critical threshold of 1,000, but backpressure has already engaged, so the system responded correctly. Its drain time of 10 minutes is within the 15-minute maximum.
