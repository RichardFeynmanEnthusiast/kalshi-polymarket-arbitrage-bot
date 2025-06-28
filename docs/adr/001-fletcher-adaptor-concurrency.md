# 001 Use create_task for web socket concurrency

## Context
We are building a WebSocketAdapter that processes messages from multiple WebSocket clients. Following the principles of Domain-Driven Design and Cosmic Python, we want to ensure our domain logic is decoupled from infrastructure details.

## Decision
We will use the create task method from the asyncio library 

## Alternatives Considered

### 1. Use asyncio gather
**Summary**
Waits for all coroutines to complete, and then returns their respective results (or raises an exception if any of them raised one
**Drawbacks**
- Less control over error handling 
- Less control over shutdown 

**Sources**
https://stackoverflow.com/questions/52245922/is-it-more-efficient-to-use-create-task-or-gather