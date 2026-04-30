# Development workflow

How features get from an idea to `main` in this project.

## Branching model

- `main` is the only long-lived branch. It is **protected** — nothing lands there except via a PR.
- All work happens on short-lived branches. Naming follows the conventional commit prefix:
  - `feat/<topic>` — new functionality (e.g. `feat/user-models`, `feat/celery-email`, `feat/llm`).
  - `fix/<topic>` — bug fixes (e.g. `fix/llm-timeouts`).
  - `chore/<topic>` — tooling, dev infra, or housekeeping (e.g. `chore/dev-test-setup`).
- Branches live only as long as the PR is open. They get deleted right after squash-merge.

## PR-only workflow

There is no "push to main" path on this project. Every change goes through:

1. Create a branch from a fresh `main`.
2. Push the branch and open a PR.
3. CI (lint + types + tests) must be green.
4. Squash-merge into `main`.
5. CD picks up the merge and rolls out the new image.

This is enforced via GitHub branch protection on `main`:

- **Require a pull request before merging.**
- **Require status checks to pass:** all three CI jobs.
- **Allow only squash-merge.** Merge commits and rebase merges are disabled.
- **No force pushes, no deletions.**

There are no required reviewers — this is a solo project. The bar is "green CI" instead of "human approval".

## Conventional commits

The repo uses [conventional commits](https://www.conventionalcommits.org). Examples from `git log`:

```
feat: LLM portrait generation via Ollama with rate-limit (#18)
feat: portrait page with profile CRUD and friends list (#17)
feat: celery + redis + welcome and password-reset emails via mailhog (#16)
fix: extend LLM timeouts to 10 minutes and fix nginx domain (#19)
fix: smoke test now hits HTTPS via domain instead of HTTP via IP (#11)
chore: set up dev image target and in-container test runner (#13)
```

Why this style: PR titles become squash-merge commit messages on `main`, so `main`'s history reads as a clean changelog. Prefixes also make it obvious from a glance what kind of change happened.

## The squash-merge gotcha

Because every PR is squashed, the branch's individual commits don't survive into `main`. After a squash-merge:

- The squash commit on `main` has a **new SHA** that doesn't match anything on the source branch.
- The source branch still has its old commits with their old SHAs.
- Git can't tell that "PR #18 squash" and "the three commits on `feat/llm`" are the same set of changes.

Practical consequence: **after a squash-merge, the branch is dead.** Don't keep working on it. The standard next-PR sequence is:

```bash
git checkout main
git pull origin main
git checkout -b feat/<next-thing>
```

If you forget and add another commit on the just-merged branch, then try to open another PR from it, GitHub will (correctly) complain about conflicts even though the diffs look like duplicates. The fix is exactly the snippet above — branch from fresh `main`, pick / re-do the work, open a clean PR.

## What a typical PR looks like

1. `git checkout main && git pull && git checkout -b feat/<topic>`.
2. Write the code, run `make test` and `make lint` locally (or just `make check`).
3. Commit. Pre-commit will run ruff and basic file hygiene.
4. Push. GitHub prints a "create PR" URL.
5. Open the PR with a conventional-commit title (`feat: …`) and a body containing:
   - **Summary** — what changed and why.
   - **Verification** — how to test it (manual steps, what to expect).
6. Wait for CI. If red, fix and push again — CI re-runs.
7. Once green, squash-merge via GitHub UI. Delete the branch.
8. Wait for CD to finish (~3–5 minutes). Confirm the smoke test in CD output is green and / or `curl` `/health/` manually.
9. If the change touched `docker-compose.prod.yml`, `docker/nginx.conf`, or `.env`, also push those manually to EC2 — see [`deployment/ec2.md`](../deployment/ec2.md).
