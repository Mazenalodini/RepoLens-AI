# Testing Protocol

Every meaningful implementation change should be validated.

## Required Thinking

For each feature consider:

```text
Happy Path
Edge Cases
Invalid Input
Failure Handling
Regression
```

## Test Layers

### Unit

Use for:

- domain behavior
- finding rules
- analyzers
- parsers
- validators
- AI context building
- report rendering logic

### Integration

Use for:

- acquisition + analysis
- API + application
- persistence + application
- end-to-end analysis pipeline

## External Systems

Unit tests should isolate:

- GitHub
- filesystem
- database
- AI providers
- external analysis tools

Use fakes/mocks/stubs where appropriate.

## Test Claims

Never state tests passed unless they were actually executed and observed.

Never claim coverage unless measured.
