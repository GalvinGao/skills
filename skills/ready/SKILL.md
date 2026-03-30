---
name: ready
description: Commit, push, and create a PR with summary and test checklist.
---

# Ready

When invoked, prepare the current branch for review by committing, pushing, and creating a pull request.

Follow these steps strictly and in order. Stop immediately if any step fails.

## Step 1 — Validate branch

1. Run `git rev-parse --abbrev-ref HEAD` to get the current branch name.
2. Run `git remote show origin` (or the configured remote) to determine the default branch.
3. If the current branch **is** the default branch (e.g. `main`, `master`), **stop** and tell the user:
   > "You are on the default branch. Create a feature branch first."

## Step 2 — Commit changes

1. Run `git status --porcelain` to check for uncommitted changes (staged, unstaged, or untracked).
2. If there are changes:
   - Run `git add -A` to stage everything.
   - Analyze the diff with `git diff --cached` and write a concise, meaningful commit message that describes **why** the changes were made, not just what changed.
   - Run `git commit` with that message.
3. If there are no changes, skip this step (there must be at least one commit ahead of the default branch).

## Step 3 — Push to remote

1. Push the branch to the remote:
   ```
   git push -u origin HEAD
   ```
2. If the push fails, **stop** and report the error.

## Step 4 — Create the Pull Request

1. Run `git log --oneline origin/<default-branch>..HEAD` to collect all commits being introduced.
2. Run `git diff origin/<default-branch>...HEAD` to understand the full scope of changes.
3. Compose a PR body with this structure:

   ```
   ## Summary
   <2-5 bullet points describing what changed and why>

   ## Test checklist
   - [ ] <actionable step to verify the change>
   - [ ] <another step>
   ...
   ```

   The **Summary** should be derived from the commits and diff.
   The **Test checklist** should list concrete, ordered steps someone can follow to manually verify this PR works correctly. Be specific — reference endpoints, pages, CLI commands, or test suites where applicable.

4. Create a **draft** PR using the `gh` CLI:
   ```
   gh pr create --draft --title "<concise title>" --body "<body from above>"
   ```
   Use a HEREDOC for the body to preserve formatting.

5. Output the resulting PR URL so the user can access it.
