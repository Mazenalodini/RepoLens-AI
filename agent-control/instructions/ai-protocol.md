# AI Engineering Protocol

## Principle

Evidence First, AI Assisted.

## AI Input

Prefer structured evidence:

```text
Repository Metadata
Analyzer Results
Findings
Selected Code Context
Test Evidence
Git Evidence
Documentation Evidence
```

Do not blindly send the complete repository.

## AI Responsibilities

AI may:

- summarize
- interpret
- correlate
- explain
- recommend
- draft executive review

## AI Restrictions

AI must not invent:

- test execution
- coverage
- vulnerabilities
- file locations
- metrics
- architecture facts
- repository facts

## Structured Output

Prefer schema-validated output.

Validate model responses before persistence or report generation.

## Failure

AI failure should degrade gracefully.

The system should support a clear no-AI or partial-AI state when practical.

## Prompt Versioning

Important prompts should be centralized and versionable.

Avoid scattering prompt strings across arbitrary service code.
