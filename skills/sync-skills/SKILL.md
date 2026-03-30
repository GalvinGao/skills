---
name: sync-skills
description: "Sync locally installed skills from ~/.claude/skills to ~/Projects/skills repo. Use when the user wants to back up skills, push skills to git, sync skills, export skills, or share their skill collection. Trigger on: sync skills, push skills, back up skills, export skills to repo."
---

# Sync Skills

Copy skills from `~/.claude/skills/` to the `~/Projects/skills/skills/` git repo, review for privacy issues, then commit and push.

## Workflow

### 1. Discover installed skills

List everything in `~/.claude/skills/`. For each entry, determine whether it's:
- A **local skill** (a real directory) — these are candidates for syncing
- A **symlink** (points to `.agents/skills/` or similar) — skip these, they're managed externally

Present the list of local skills to the user, noting which ones already exist in `~/Projects/skills/skills/` (mark as "update") vs new (mark as "new"). Example:

```
Local skills available to sync:

  [new]    autoresearch
  [update] commit-push
  [update] issues-dump
  [new]    no-use-effect
  [update] resolve-issues
  [update] setup-superset
  [new]    sync-skills
  ...

Skipped (symlinks, managed externally):
  analyze-logs, baseline-ui, skill-creator, ...

Which skills do you want to sync? (all / comma-separated names / none)
```

### 2. Copy selected skills

For each selected skill, use `rsync -av --delete` to copy from `~/.claude/skills/<name>/` to `~/Projects/skills/skills/<name>/`. The `--delete` flag ensures removed files in the source are also removed in the destination.

### 3. Review changes

Run `git diff` and `git status` in `~/Projects/skills/` to see what changed.

Scan the diff for potential privacy concerns:
- API keys, tokens, secrets (patterns like `sk-`, `ghp_`, `AKIA`, `Bearer`, long hex/base64 strings)
- Personal paths containing usernames (e.g., `/Users/galvin/` is fine — it's the user's own repo)
- Email addresses, passwords, credentials
- `.env` files or similar

If anything looks sensitive, show the specific lines to the user and ask for confirmation before proceeding. If nothing looks concerning, say so and move on.

### 4. Update README.md

After copying, update `~/Projects/skills/README.md` so the skills table reflects the current contents of `skills/`.

- Add rows for any new skills
- Remove rows for skills that no longer exist in the directory
- For each skill, read the SKILL.md frontmatter `description` field and write a concise, direct description for the table. Don't say "updated with" or "synced from" — just describe what the skill does. Rewrite descriptions that are verbose or unclear.
- Keep the table sorted alphabetically

### 5. Commit and push

Stage all changes in `~/Projects/skills/`, generate a commit message listing what was added/updated, and push.

Commit message format:
```
sync: [list of skill names]

Added: skill-a, skill-b
Updated: skill-c
```
