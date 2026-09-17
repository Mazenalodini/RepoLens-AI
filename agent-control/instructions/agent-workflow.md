# Agent Workflow Protocol

For each bounded task:

## Step 1 — Read

Read:

- `AGENTS.md`
- relevant files
- relevant docs
- related tests

## Step 2 — Understand

Explain:

- current behavior
- desired behavior
- likely impact

## Step 3 — Plan

Provide a short implementation plan.

## Step 4 — Implement

Modify only what is necessary.

## Step 5 — Test

Run focused tests first.

Run broader validation when appropriate.

## Step 6 — Review

Inspect:

```text
git diff
```

Check:

- accidental changes
- duplicated logic
- API breakage
- security concerns
- missing tests

## Step 7 — Report

Use the reporting protocol.

## Step 8 — Stop

Do not continue into the next feature unless requested.
