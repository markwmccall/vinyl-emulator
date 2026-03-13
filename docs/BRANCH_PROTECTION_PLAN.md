# Plan: Branch Protection & PR Workflow (Issue #27)

## Goal

Prevent direct commits to `main`. All changes go through a feature/bug branch
and are merged via a Pull Request. PRs should reference an existing issue.

## What We're Adding

### 1. GitHub Actions — PR Test Workflow

File: `.github/workflows/pr-checks.yml`

Runs `pytest` against every PR targeting `main`. This gives branch protection
a status check to require before merging.

```yaml
name: PR Checks

on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v
```

### 2. PR Template

File: `.github/pull_request_template.md`

Prompts author to link an issue. Not enforced programmatically — convention
is enough for a solo project. A hard-fail workflow for missing issue links
adds friction without meaningful benefit when you're the only contributor.

```markdown
## What

<!-- Brief description of the change -->

## Why

Closes #<!-- issue number -->

## Test plan

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Tested on Pi (if hardware-related)
```

### 3. Branch Protection Rules (Manual — GitHub Settings)

Go to **Settings → Branches → Add rule** for `main`:

| Setting | Value |
|---|---|
| Require a pull request before merging | ✅ |
| Required approvals | 1 (self-approve as sole maintainer) |
| Require status checks to pass | ✅ |
| Required status check | `test` (from pr-checks workflow) |
| Require branches to be up to date | ✅ |
| Do not allow bypassing the above settings | optional — leave off so you can emergency-hotfix |
| Restrict who can push to matching branches | optional |

> **Note**: "Do not allow bypassing" prevents even admins from force-pushing.
> Leave it off for now — you can enable it later if you want stricter enforcement.

## Migration Notes

- Finish and merge any in-flight direct-to-main work (HTTPS/SSL setup.sh
  changes, issue #20) **before** enabling protection rules.
- After protection is on, the workflow is: `git checkout -b fix/issue-N`, commit,
  push branch, open PR, merge.
- The existing commits to `main` are unaffected — protection only applies going
  forward.

## What This Does NOT Do

- Does not require issue references programmatically. The PR template is a
  prompt, not a gate. GitHub has no native enforcement for this; a workflow
  check is possible but adds noise for a solo project.
- Does not block force-push (unless you enable "Do not allow bypassing").
- Does not require code review from another person (self-approve satisfies the
  1-approval requirement).

## Implementation Steps

1. Create `.github/workflows/pr-checks.yml`
2. Create `.github/pull_request_template.md`
3. Open a PR with these two files (to test the workflow end-to-end)
4. Merge that PR
5. Enable branch protection rules in GitHub Settings
