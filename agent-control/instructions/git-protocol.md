# Git Protocol

## Default

The Agent may inspect Git but does not create commits or push without explicit user instruction.

Preferred user workflow:

```powershell
git status
git diff
git add .
git commit -m "type: message"
git push
```

## Branches

Feature branches should be named clearly, for example:

```text
feature/github-acquisition
feature/repository-discovery
feature/findings-engine
feature/ai-review
feature/report-engine
```

## Commit Types

```text
feat
fix
refactor
test
docs
chore
perf
```

Do not create meaningless commits just to increase commit count.

## History Safety

Never use destructive history rewrites automatically.

Do not use:

```text
git reset --hard
git clean -fd
git push --force
```

unless explicitly authorized and the user understands the consequence.

## PR

A PR should explain:

- what changed
- why
- tests
- risks
- limitations
