# 002-fletcher-and-websockets-timing.md](002-fletcher-and-websockets-timing

## Context
When running two websockets asynchronously we need to process data from each websocket without hogging resources. We 
need to maintain accurate timestamp to test our code is running with minimum delay possible. 

## Decision
**Summary**
We will use datetime.now() for human-readable logging of when messages are received. For measuring internal latency 
(e.g., between receiving two messages, or processing steps), we will use time.monotonic() to avoid issues with 
wall-clock adjustments

**Drawbacks**
- Subject to clock drift: datetime.now() is wall-clock time and can jump forward or backward if the system time changes
(e.g., NTP sync, manual change).

- Lower precision: Not monotonic and not guaranteed to be high-resolution.
This can affect fine-grained timing comparisons (e.g., microsecond-level latency).

- Timezone handling: datetime.now() without timezone info returns a naive datetime object,
which can cause issues if your code interacts with timezone-aware datetimes elsewhere.

## Alternatives Considered

### 1. Use asyncio.get_event_loop().time()
**Summary**
**Drawbacks**
- Complexity
- 
### 2. Use timestamp object from polymarket messages for logging polymarket data related times


