# RepoLens AI — Submission Checklist

## Product

- [ ] GitHub repository input works
- [ ] repository acquisition works
- [ ] discovery works
- [ ] analyzers run
- [ ] findings are generated
- [ ] AI review works or graceful no-AI mode exists
- [ ] HTML report works
- [ ] JSON/Markdown output works if included in MVP

## Code

- [ ] code is organized
- [ ] type hints present where appropriate
- [ ] error handling is explicit
- [ ] secrets are excluded
- [ ] tests pass
- [ ] no obvious dead/debug code remains

## GitHub

- [ ] repository is public as required
- [ ] README is complete
- [ ] commits are meaningful
- [ ] Conventional Commit style used
- [ ] branches used meaningfully
- [ ] PR/CI evidence captured
- [ ] final commit is pushed

## Documentation

- [ ] PROJECT_SPEC.md
- [ ] ARCHITECTURE.md
- [ ] DECISIONS.md
- [ ] ROADMAP.md
- [ ] DEVELOPMENT_WORKFLOW.md
- [ ] setup/run instructions
- [ ] screenshots selected

## Demo

- [ ] choose a public GitHub repository to analyze
- [ ] run the analysis
- [ ] show Evidence
- [ ] show Findings
- [ ] show AI review
- [ ] show final report

## Final Quality Gate

```text
Clone
→ Setup
→ Run
→ Analyze GitHub repository
→ View report
```

must work on a clean environment as far as the MVP permits.
