# ADR 005: Message Bus Coupling for Balance Service and Transition to WebSocket

## Context
Currently, the service is tightly coupled to the message bus for testing a working implementation. This setup allows for handling events and commands efficiently within the existing infrastructure.

## Decision
The current implementation relies on the message bus to facilitate communication between components. However, the next steps involve transitioning to a WebSocket connection to the trades received table. This change aims to reduce latency by not relying on the core service's resources.

## Consequences
- **Pros:**
  - Decreased latency as the WebSocket connection will provide real-time updates without burdening the core service.
  - Improved scalability by offloading some of the processing to the WebSocket connection.

- **Cons:**
  - If the database table is out of sync, our internal state will also be incorrect.
  - Additional complexity in managing WebSocket connections and ensuring data consistency.

## Mitigation
To address the potential issue of data inconsistency, we plan to implement a reconciliation process over a fixed interval. This will ensure that any discrepancies between the database table and our internal state are corrected in a timely manner.

## Alternatives Considered
- Continuing with the message bus for all operations, which would maintain the current level of latency and resource usage.
- Implementing a hybrid approach that uses both the message bus and WebSocket connections, balancing the trade-offs of each method. 