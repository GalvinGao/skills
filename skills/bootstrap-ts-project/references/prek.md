# Prek Reference — Git Pre-Commit Hooks

Prek is a fast, Rust-based pre-commit hook manager. Drop-in replacement for the Python pre-commit tool.

## Installation

```bash
# Via npm/pnpm (recommended for JS/TS projects)
pnpm add -D @j178/prek

# Or standalone
brew install prek
```

## Setup

```bash
# Install git hooks (creates .git/hooks/pre-commit)
npx prek install

# Run all hooks manually
npx prek run --all-files

# Run specific hook
npx prek run oxlint
```

## Configuration: `prek.toml`

Native TOML format (recommended over .pre-commit-config.yaml for new projects).

### Remote hooks (from GitHub mirrors)

```toml
[[repos]]
repo = "https://github.com/oxc-project/mirrors-oxlint"
rev = "v1.46.0"
hooks = [{ id = "oxlint" }]
```

### Local hooks (using project-installed tools)

```toml
[[repos]]
repo = "local"

[[repos.hooks]]
id = "oxlint"
name = "oxlint"
language = "system"
entry = "npx oxlint"
files = "\\.(js|jsx|ts|tsx|mjs|cjs|mts|cts|vue|svelte|astro)$"

[[repos.hooks]]
id = "oxfmt"
name = "oxfmt"
language = "system"
entry = "npx oxfmt --write"
files = "\\.(js|jsx|ts|tsx|mjs|cjs|mts|cts|json|css|md|yaml|yml|html|vue|svelte)$"
```

### Combining remote + local

```toml
[[repos]]
repo = "https://github.com/oxc-project/mirrors-oxlint"
rev = "v1.46.0"
hooks = [{ id = "oxlint" }]

[[repos]]
repo = "local"
hooks = [
  { id = "oxfmt", name = "oxfmt", language = "system", entry = "npx oxfmt --write", files = "\\.(js|jsx|ts|tsx|json|css|md|yaml)$" },
]
```

### Builtin hooks (no external deps)

```toml
[[repos]]
repo = "builtin"
hooks = [
  { id = "trailing-whitespace" },
  { id = "end-of-file-fixer" },
  { id = "check-yaml" },
]
```

## Local hook fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable identifier |
| `name` | yes | Display name |
| `entry` | yes | Command to execute |
| `language` | yes | `system`, `node`, `python`, etc. |
| `files` | no | Regex or glob for file matching |
| `exclude` | no | Regex or glob to exclude |
| `args` | no | Extra arguments list |
| `pass_filenames` | no | Pass matched files to command (default: true) |
| `always_run` | no | Run even without matching files |
| `stages` | no | When to run (`pre-commit`, `pre-push`, etc.) |

### File filtering with globs (prek-only feature)

```toml
files = { glob = "src/**/*.ts" }
files = { glob = ["src/**/*.ts", "lib/**/*.ts"] }
exclude = { glob = ["dist/**", "node_modules/**"] }
```

## YAML format (also supported)

Prek reads `.pre-commit-config.yaml` for backwards compatibility:

```yaml
repos:
  - repo: https://github.com/oxc-project/mirrors-oxlint
    rev: v1.46.0
    hooks:
      - id: oxlint

  - repo: local
    hooks:
      - id: oxfmt
        name: oxfmt
        entry: npx oxfmt --write
        language: system
        files: \.(js|jsx|ts|tsx|json|css|md|yaml)$
```

## Useful commands

```bash
npx prek install          # Install git hooks
npx prek install -f       # Force reinstall
npx prek uninstall        # Remove git hooks
npx prek run              # Run on staged files
npx prek run --all-files  # Run on all files
npx prek run oxlint       # Run specific hook
npx prek list             # List all hooks
npx prek validate-config  # Validate config
npx prek auto-update      # Update hook versions
```

## GitHub Actions

```yaml
- uses: j178/prek-action@v2
```
