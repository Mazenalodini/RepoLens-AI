# Coding Standards

## Python

Prefer:

- Type Hints
- clear names
- small focused functions
- explicit return types where useful
- immutable/value-like structures when appropriate
- dependency injection where it improves testability
- specific exceptions
- logging
- pathlib for filesystem work
- structured schemas for boundaries

Avoid:

- broad `except` blocks
- silent failures
- mutable global state
- hidden side effects
- duplicated logic
- large procedural functions
- premature abstraction
- unnecessary inheritance

## Style

Follow the project's configured formatter/linter.

Keep modules cohesive.

Comments should explain important decisions, not restate obvious code.

## Error Handling

Errors should preserve context without exposing secrets.

Expected failures should be handled explicitly.

Unexpected failures should be logged and surfaced appropriately.
