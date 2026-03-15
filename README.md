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
| [commit-push](./skills/commit-push/SKILL.md) | Analyze staged/unstaged changes, commit with a generated message, and push |
| [issues-dump](./skills/issues-dump/SKILL.md) | Convert informal issue dumps into GitHub issues via `gh` CLI |
| [mediainfo](./skills/mediainfo/SKILL.md) | Inspect image/video assets with `ffprobe` for frontend work |
| [resolve-issues](./skills/resolve-issues/SKILL.md) | Fix GitHub issues one by one, each with a commit that closes it |
| [setup-superset](./skills/setup-superset/SKILLS.md) | Create `.superset/config.json` with setup and teardown scripts |
