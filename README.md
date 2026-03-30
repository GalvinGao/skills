# Skills

Reusable AI agent skills for frontend and media workflows.

## Install

```bash
npx skills add GalvinGao/skills
```

Or install a specific skill:

```bash
npx skills add GalvinGao/skills/mediainfo
```

### Global install

To make skills available across all projects:

```bash
npx skills add -g GalvinGao/skills
```

## Skills

| Skill | Description |
|-------|-------------|
| [autoresearch](./skills/autoresearch/SKILL.md) | Autonomously optimize any skill by running it repeatedly, scoring outputs against binary evals, mutating the prompt, and keeping improvements |
| [baseline-ui](./skills/baseline-ui/SKILL.md) | Validate animation, typography, accessibility, and Tailwind UI baseline constraints |
| [bootstrap-ts-project](./skills/bootstrap-ts-project/SKILL.md) | Scaffold a new TypeScript project with pnpm, oxlint, oxfmt, prek git hooks, and CI |
| [commit-push](./skills/commit-push/SKILL.md) | Analyze staged/unstaged changes, commit with a generated message, and push |
| [fix-ci](./skills/fix-ci/SKILL.md) | Diagnose failing GitHub Actions runs, apply fixes, push, and iterate until CI passes |
| [fix-pr-comments](./skills/fix-pr-comments/SKILL.md) | Read unresolved PR comments, plan fixes, implement, and resolve addressed threads |
| [frontend-design](./skills/frontend-design/SKILL.md) | Build distinctive, production-grade frontend interfaces with intentional visual direction |
| [issues-dump](./skills/issues-dump/SKILL.md) | Convert informal issue dumps into GitHub issues via `gh` CLI |
| [mediainfo](./skills/mediainfo/SKILL.md) | Inspect image/video assets with `ffprobe` for frontend work |
| [no-use-effect](./skills/no-use-effect/SKILL.md) | Ban direct `useEffect` calls in React — use derived state, event handlers, data-fetching libraries, or `useMountEffect` instead |
| [preheat](./skills/preheat/SKILL.md) | Explore a project and produce a local setup checklist (toolchain, deps, services, and manual steps) |
| [ready](./skills/ready/SKILL.md) | Commit, push, and create a draft PR with summary and verification checklist |
| [resolve-issues](./skills/resolve-issues/SKILL.md) | Fix GitHub issues one by one, each with a commit that closes it |
| [setup-superset](./skills/setup-superset/SKILL.md) | Create `.superset/config.json` with setup and teardown scripts for Superset workspaces |
| [summarize-pr](./skills/summarize-pr/SKILL.md) | Summarize PR changes in Simplified Chinese for non-technical stakeholders |
| [swiftui-ui-patterns](./skills/swiftui-ui-patterns/SKILL.md) | Apply best-practice SwiftUI patterns for views, TabView architecture, and sheet flows |
| [sync-simplelocalize](./skills/sync-simplelocalize/SKILL.md) | Push i18n translation keys/values from the current branch to SimpleLocalize, then revert local i18n diffs |
| [sync-skills](./skills/sync-skills/SKILL.md) | Copy local skills from `~/.claude/skills/` to a git repo, review for privacy issues, then commit and push |
| [unify-agents](./skills/unify-agents/SKILL.md) | Consolidate `CLAUDE.md` into `AGENTS.md` and replace `CLAUDE.md` with a symlink |
