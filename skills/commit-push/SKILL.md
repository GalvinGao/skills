---
name: commit-push
description: Analyze staged/unstaged changes, commit with a generated message, and push.
---

# Commit & Push

When invoked, analyze the current changes in the working tree, create a well-crafted commit, and push to the remote.

## Step 1 — Assess changes

1. Run `git status` to identify staged and unstaged changes.
2. Run `git diff` and `git diff --cached` to understand what will be committed.
3. If there are no changes at all (nothing staged, nothing modified), stop and inform the user there is nothing to commit.

## Step 2 — Stage changes

1. If there are unstaged changes but nothing is staged, stage all changes with `git add -A`.
2. If some changes are already staged and there are also unstaged changes, ask the user whether to commit only the staged changes or stage everything first.
3. Never stage files that likely contain secrets (`.env`, `credentials.json`, `*.pem`, etc.) — warn the user if such files are present.

## Step 3 — Commit

1. Analyze the full diff of what is staged (`git diff --cached`).
2. Review recent commit messages (`git log --oneline -10`) to match the repository's existing style and conventions.
3. Draft a concise commit message:
   - First line: imperative mood summary, under 72 characters.
   - If the change is non-trivial, add a blank line followed by a short body explaining **why** the change was made.
4. Commit immediately with the generated message. Do **not** ask the user for confirmation.

## Step 4 — Push

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
