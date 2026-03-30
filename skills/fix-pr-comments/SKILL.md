---
name: fix-pr-comments
description: Read PR comments on the current branch and address each one through plan mode.
---

# Fix PR Comments

When invoked, read all review comments on the current branch's pull request and systematically address every concern.

## Step 1 — Find the PR

1. Run `git rev-parse --abbrev-ref HEAD` to get the current branch name.
2. Run `gh pr view --json number,title,url` to find the PR associated with this branch.
3. If no PR exists for this branch, **stop** and tell the user.

## Step 2 — Collect all comments

1. Run `gh pr view --json comments,reviews,reviewDecision` to get top-level PR comments and review status.
2. Fetch **only unresolved** inline review comments using the GraphQL API (the REST API does not expose resolved state):
   ```
   gh api graphql -f query='
     query($owner: String!, $repo: String!, $pr: Int!) {
       repository(owner: $owner, name: $repo) {
         pullRequest(number: $pr) {
           reviewThreads(first: 100) {
             nodes {
               id
               isResolved
               comments(first: 10) {
                 nodes {
                   id
                   databaseId
                   body
                   path
                   line
                   author { login }
                   createdAt
                 }
               }
             }
           }
         }
       }
     }' -f owner='{owner}' -f repo='{repo}' -F pr={number}
   ```
   Filter to only threads where `isResolved` is `false`.
3. Group and organize the unresolved comments by file and thread.
4. Present a numbered summary of every unresolved comment/concern to the user.

## Step 3 — Plan (MANDATORY)

You **must** enter plan mode before making any changes. Do not skip this step.

1. Enter plan mode.
2. For each comment, plan how to address it:
   - If the fix is straightforward (typo, missing null check, rename, style issue), include the concrete fix in the plan.
   - If the comment involves a **design decision, architectural choice, or ambiguous request**, do **not** guess — use `AskUserQuestion` to ask the user for clarification before finalizing that part of the plan.
   - If a comment is a question or informational (no code change needed), note the planned response.
3. The plan must address **every** open comment individually. Do not skip or batch unrelated comments together.
4. Exit plan mode and wait for user approval before proceeding.

## Step 4 — Implement fixes

1. Work through the approved plan, addressing each comment one by one.
2. After all code changes are made, run any relevant tests or linters if configured.

## Step 5 — Commit and push

1. Stage all changed files and commit with a clear message summarizing the PR comment fixes.
2. Push to the remote with `git push`.

## Step 6 — Resolve comments

For each review thread that was addressed with a code change:

1. **Verify the fix actually addresses the comment.** Compare the comment's request against the diff you produced. Only resolve if the change directly addresses what the reviewer asked for. If the fix is tangential or partial, do NOT resolve — just react with 👍.
2. **Check that the user approved the fix.** If the user declined to fix a comment (e.g., disagreed, deferred, or skipped it during plan approval), do NOT resolve it.
3. If both checks pass, resolve the thread using the GraphQL API:
   ```
   gh api graphql -f query='
     mutation($threadId: ID!) {
       resolveReviewThread(input: {threadId: $threadId}) {
         thread { isResolved }
       }
     }' -f threadId='{thread_node_id}'
   ```
   The `thread_node_id` is the `id` of the `reviewThread` node from the Step 2 GraphQL query. Make sure you capture thread-level node IDs (not comment IDs) during Step 2.
4. For comments that were addressed but not resolved (informational replies, partial fixes), react with 👍 instead:
   ```
   gh api repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions -f content="+1"
   ```

## Step 7 — Done

1. Present a summary of all changes made, mapped back to the original comments.
2. List which threads were resolved vs. only reacted to, and why.

## Rules

- Never skip plan mode. Always plan first, then implement.
- Never guess on design decisions. Ask the user.
- Address every comment — do not silently skip any.
- If `$ARGUMENTS` is provided, use it to filter or prioritize specific comments.
