---
name: unify-agents
description: Consolidate CLAUDE.md into AGENTS.md and symlink CLAUDE.md -> AGENTS.md.
---

# Unify Agents

Ensure the canonical agent instructions live in `AGENTS.md`, with `CLAUDE.md` as a symlink pointing to it. This lets multiple AI tools share a single source of truth.

## Step 1 — Find CLAUDE.md files

1. Run `find . -name CLAUDE.md -not -path '*/node_modules/*' -not -path '*/.git/*'` to locate all `CLAUDE.md` files in the repo.
2. If no `CLAUDE.md` files are found, **stop** and tell the user there is nothing to unify.

## Step 2 — Process each CLAUDE.md

For each `CLAUDE.md` found, in its containing directory:

1. **Check if it is already a symlink.** Run `test -L <path>/CLAUDE.md`. If it is already a symlink, skip it and report that it's already unified.

2. **Check if AGENTS.md exists in the same directory.**
   - **If AGENTS.md does NOT exist:**
     - Run `mv <path>/CLAUDE.md <path>/AGENTS.md` to move the content.
     - Run `ln -s AGENTS.md <path>/CLAUDE.md` to create the symlink.
   - **If AGENTS.md already exists:**
     - Show the user both files' contents and ask whether to:
       - (a) Merge CLAUDE.md content into AGENTS.md (append), then replace CLAUDE.md with a symlink.
       - (b) Keep AGENTS.md as-is, replace CLAUDE.md with a symlink (discarding CLAUDE.md content).
       - (c) Skip this directory.
     - Wait for the user's choice before proceeding.

3. Verify the symlink works: run `test -L <path>/CLAUDE.md && test -f <path>/AGENTS.md`.

## Step 3 — Stage changes

1. For each directory processed, run `git add <path>/AGENTS.md <path>/CLAUDE.md`.
2. Show `git status` so the user can review.
3. Do **not** commit automatically. Let the user decide.

## Rules

- Never overwrite or delete content without user confirmation.
- Use relative symlinks (`ln -s AGENTS.md CLAUDE.md`), not absolute paths.
- If `$ARGUMENTS` is a path, only process that specific directory instead of scanning the whole repo.
