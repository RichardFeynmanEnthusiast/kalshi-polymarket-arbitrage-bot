# ADR: Use Lazy String Formatting for Logging Instead of f-strings

**Date:** 2025-07-01

## Context

In our codebase, logging statements are critical for monitoring and debugging. Many log statements include dynamic data that is formatted into log messages. Two common approaches to string formatting in Python logging are:

- Using **f-strings** (e.g., `logger.info(f"User {user.id} logged in")`)
- Using **lazy formatting** with `%`-style placeholders (e.g., `logger.info("User %s logged in", user.id)`)

## Decision

We will use **lazy string formatting** with `%`-style placeholders in all logging statements instead of f-strings.

For example, prefer:

```python
logger.info("Processed event %s", event.id)
```
over 
logger.info(f"Processed event {event.id}")
