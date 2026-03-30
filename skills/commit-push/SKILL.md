---
name: commit-push
description: Analyze staged/unstaged changes, commit with a generated message, and push.
---

# Commit & Push

When invoked, analyze the current changes in the working tree, create a well-crafted commit, and push to the remote.

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Step 1 — Stage changes

1. If there are no changes at all (nothing staged, nothing modified), stop and inform the user there is nothing to commit.
2. If there are unstaged changes but nothing is staged, stage all changes with `git add -A`.
3. If some changes are already staged and there are also unstaged changes, ask the user whether to commit only the staged changes or stage everything first.
4. Never stage files that likely contain secrets (`.env`, `credentials.json`, `*.pem`, etc.) — warn the user if such files are present.

## Step 2 — Commit

1. Analyze the staged diff and the recent commit log (both provided in Context above) to understand the change and match the repository's existing commit style.
2. Draft a concise commit message:
   - First line: imperative mood summary, under 72 characters.
   - If the change is non-trivial, add a blank line followed by a short body explaining **why** the change was made.
3. Commit immediately with the generated message. Do **not** ask the user for confirmation.

## Step 3 — Push

1. Push the branch to the remote:
   ```
   git push -u origin HEAD
   ```
2. If the push fails, report the error and stop.
3. If `$ARGUMENTS` contains "no push" or similar, skip this step.

## Rules

- Never force-push or amend existing commits unless the user explicitly asks.
- Never skip pre-commit hooks (no `--no-verify`).
- If a pre-commit hook fails, report the error and stop. Do not retry automatically.
- If `$ARGUMENTS` is provided, use it as a hint or instruction for the commit message rather than ignoring it.
