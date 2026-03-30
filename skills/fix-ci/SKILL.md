---
name: fix-ci
description: Check GitHub Actions status, diagnose failures from logs, fix, push, and loop until CI passes.
---

# Fix CI

When invoked, check the latest GitHub Actions run for the current branch. If any jobs failed, diagnose, fix, push, then watch CI and repeat until green.

## Step 1 — Identify the current branch and repo

1. Run `git rev-parse --abbrev-ref HEAD` to get the current branch.
2. Run `gh repo view --json nameWithOwner -q .nameWithOwner` to confirm the repo.

## Step 2 — Get the latest workflow run status

1. Run `gh run list --branch <branch> --limit 5 --json databaseId,status,conclusion,name,event,headBranch` to get recent runs for this branch.
2. If there are no runs, **stop** and tell the user no CI runs were found for this branch.
3. If all runs succeeded, **stop** and tell the user CI is green.
4. Identify all runs with `conclusion` of `failure` (focus on the most recent failed run).

## Step 3 — Get failed job details

1. Run `gh run view <run-id> --json jobs` to list all jobs in the failed run.
2. Identify which specific jobs failed.
3. For each failed job, run `gh run view <run-id> --log-failed` to fetch the failure logs.
4. If the failed log output is too large, focus on the last 200 lines per failed job to find the relevant error messages.

## Step 4 — Diagnose failures

1. Analyze the log output to identify the root cause of each failure. Common categories:
   - **Test failures**: extract the failing test names, assertion errors, and stack traces.
   - **Build errors**: extract compiler/bundler errors with file paths and line numbers.
   - **Lint/format errors**: extract the specific violations and files.
   - **Dependency issues**: extract missing or conflicting packages.
   - **Environment/config issues**: extract misconfiguration details.
2. For each failure, read the relevant source files in the local codebase to understand context.

## Step 5 — Output a fix plan

1. Enter plan mode.
2. For each failure, propose a concrete fix:
   - Reference the exact file(s) and line(s) that need changes.
   - Explain why the CI failed and what the fix does.
   - If a fix involves a design decision or is ambiguous, use `AskUserQuestion` to clarify.
3. Exit plan mode and wait for user approval before making any changes.

## Step 6 — Implement fixes and push

1. Apply the approved fixes.
2. Run any relevant local checks (tests, lint, build) if possible to verify the fix locally.
3. Commit the fixes with a descriptive message referencing the CI failures.
4. Push to the current branch.

## Step 7 — Watch CI and loop

1. Run `gh run list --branch <branch> --limit 1 --json databaseId,status` to find the new run triggered by the push.
2. If a run is `in_progress` or `queued`, run `gh run watch <run-id> --exit-status` to block until it completes.
3. Check the exit status:
   - **If CI passed (exit 0):** Go to Step 8.
   - **If CI failed (non-zero exit):** Go back to **Step 3** with the new run ID and repeat the diagnose-fix-push-watch cycle.
4. If the same failure persists after 3 attempts, **stop** and ask the user for guidance instead of looping further.

## Step 8 — Done

1. Tell the user CI is green.
2. Summarize all changes made across all fix iterations, mapped back to the original CI failures.

## Rules

- Always plan before implementing. Never skip plan mode.
- Never guess on ambiguous failures. Ask the user.
- If `$ARGUMENTS` is provided (e.g., a specific run ID or job name), use it to narrow the scope.
- If multiple runs failed, focus on the most recent one unless the user specifies otherwise.
- Cap the fix loop at 3 iterations to avoid infinite cycles. Escalate to the user after that.
