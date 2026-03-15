# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A collection of reusable AI agent skills, installable via `npx skills add GalvinGao/skills`. Each skill is a standalone Markdown file that teaches an AI agent how to perform a specific task.

## Repository Structure

```
skills/
  <skill-name>/
    SKILL.md    # Skill definition (the only required file)
```

Each skill lives in its own directory under `skills/` and contains a single `SKILL.md` file. There is no build step, no dependencies, and no runtime code — skills are pure Markdown instructions.

## Writing Skills

A skill file uses YAML frontmatter for metadata followed by Markdown instructions:

- **Frontmatter fields**: `name`, `description`, `$ARGUMENTS` usage
- **Body**: Step-by-step procedural instructions the agent follows
- **Convention**: Use `$ARGUMENTS` to reference user-provided arguments passed to the skill

When creating or editing skills:
- Keep instructions procedural and concrete — tell the agent exactly what commands to run and in what order
- Include guard rails (e.g., "never force-push", "skip if unclear") as explicit rules
- Use the existing skills as templates for tone and structure
- File should be named `SKILL.md` (not `SKILLS.md`)
- **Always update `README.md`** when adding a new skill or updating an existing one — keep the skills table in alphabetical order with a link and short description
