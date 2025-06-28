# 004 Account Balances in Clients

## Context
In our architecture, we need to retrieve account balances from various platforms. This operation involves direct interaction with API endpoints, which is an infrastructure concern.

## Decision
We decided to implement the logic for retrieving account balances directly within the client classes. This approach ensures 
that the infrastructure-related logic is encapsulated within the clients, keeping the domain logic clean and focused on business rules.

## Alternatives Considered

### 1. Centralized Balance Service
**Summary**
A separate service that aggregates balance information from all clients.
**Drawbacks**
- Introduces additional complexity in managing a centralized service.
- Increases latency due to additional network hops.

### 2. Domain Layer Logic
**Summary**
Incorporate balance retrieval logic in the domain layer.
**Drawbacks**
- Violates the separation of concerns by mixing domain logic with infrastructure details.

## Sources
- Domain-Driven Design principles
- Infrastructure as Code best practices
