---
name: resolve-issues
description: Fix GitHub issues one by one, each with a commit that closes it. Accepts issue numbers (#123), ranges (#123-125), or fixes all open issues.
---

# Resolve Issues

Fix GitHub issues from this repository, one at a time, each with its own commit.

## Step 1 — Determine which issues to fix

Parse `$ARGUMENTS`:

- **Specific issues**: `#123` or `123` — fix that one issue.
- **Range**: `#123-125` or `123-125` — fix issues #123, #124, #125.
- **Comma-separated**: `#1, #3, #7` — fix those specific issues.
- **Empty / no arguments**: Fix ALL open issues. Run `gh issue list --state open --json number,title,body --limit 100` to get them.

## Step 2 — Fix issues one by one

For each issue, in order from lowest to highest number:

1. **Read the issue**: `gh issue view <number> --json number,title,body,labels` to understand what needs to be done.
2. **Fix it**: Read relevant code, understand the problem, and make the fix.
3. **Commit**: Stage the changed files and commit. The commit message must include `Closes #<number>` so GitHub auto-closes the issue on push.
   ```
   git add <specific files>
   git commit -m "$(cat <<'EOF'
   <concise description of the fix>

   Closes #<number>
   EOF
   )"
   ```
4. **Move to the next issue.** Do not push between issues — just commit.

## Rules

- Fix one issue per commit. Do not batch multiple issues into one commit.
- Do not push. The user will push when ready.
- Do not ask for confirmation between issues. Just keep going.
- If an issue is unclear or cannot be fixed from the code alone, skip it and note it at the end.
- If a fix for one issue naturally resolves another issue in the list, mention it but still make separate commits if the list includes both.
- At the end, print a summary: which issues were fixed (with commit hashes) and which were skipped.
