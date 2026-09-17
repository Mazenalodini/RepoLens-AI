# RepoLens AI — Development Workflow

## 1. Core Loop

```text
Issue
→ Branch
→ Agent Plan
→ Implementation
→ Tests
→ Diff Review
→ Human Acceptance
→ Commit
→ Push
→ PR
→ CI
→ Merge
```

---

## 2. Before an Agent Task

The human developer should:

1. Confirm the repository is clean enough for the task.
2. Ensure the current branch is known.
3. Define one bounded task.
4. Confirm the relevant specification.
5. Ask the Agent to plan before implementation when the task is non-trivial.

---

## 3. Agent Work

The Agent should:

- inspect relevant files
- avoid unrelated edits
- implement the smallest coherent change
- run appropriate tests
- review its diff
- report completion

---

## 4. Human Git Checkpoint

The user should inspect:

```powershell
git status
git diff
```

Then, when satisfied:

```powershell
git add .
git commit -m "..."
git push
```

---

## 5. Conventional Commits

Examples:

```text
feat: add github repository source
fix: handle invalid repository urls
refactor: extract analyzer registry
test: add repository discovery tests
docs: document analysis architecture
chore: configure github actions
```

---

## 6. Screenshot Checkpoints

Capture screenshots for meaningful milestones:

- repository initialization
- branch creation
- first successful test run
- feature completion
- important terminal output
- Git diff
- commit
- GitHub push
- PR
- CI
- application running
- final report
- final repository

Avoid capturing every insignificant step.

---

## 7. Definition of Done

A meaningful feature should satisfy:

```text
Code
+
Tests
+
Review
+
Documentation where needed
+
Git checkpoint
```

---

## 8. Blocked State

If implementation is blocked by:

- missing credentials
- ambiguous requirement
- architecture conflict
- unavailable external dependency
- unsafe execution request

the Agent must stop, explain the blocker, and request a decision or manual action.

---

## 9. Scope Discipline

Discovering additional work does not automatically authorize implementing it.

Record it as:

```text
Follow-up
```

and continue with the current task.
