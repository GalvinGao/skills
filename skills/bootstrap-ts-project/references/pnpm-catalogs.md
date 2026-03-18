# pnpm Catalogs Reference

Catalogs let you define dependency version ranges as reusable constants in `pnpm-workspace.yaml`, shared across all packages in a monorepo.

## When to use

Use catalogs whenever you have a pnpm workspace (monorepo). They:
- Ensure consistent dependency versions across packages
- Simplify upgrades (change once in pnpm-workspace.yaml)
- Reduce merge conflicts (no package.json edits for version bumps)

## The `catalog:` protocol

In any package.json within the workspace:

```json
{
  "dependencies": {
    "react": "catalog:",
    "react-dom": "catalog:"
  },
  "devDependencies": {
    "typescript": "catalog:",
    "oxlint": "catalog:",
    "oxfmt": "catalog:"
  }
}
```

## Defining catalogs in pnpm-workspace.yaml

### Default catalog

```yaml
packages:
  - "packages/*"

catalog:
  react: ^19.0.0
  react-dom: ^19.0.0
  typescript: ^5.8.0
  oxlint: ^1.0.0
  oxfmt: ^0.10.0
  "@j178/prek": ^0.3.0
```

Referenced via `catalog:` or `catalog:default`.

### Named catalogs

```yaml
packages:
  - "packages/*"

catalogs:
  react18:
    react: ^18.2.0
    react-dom: ^18.2.0
  react19:
    react: ^19.0.0
    react-dom: ^19.0.0
  tooling:
    typescript: ^5.8.0
    oxlint: ^1.0.0
    oxfmt: ^0.10.0
```

Referenced via `catalog:react18`, `catalog:tooling`, etc.

## Supported fields

The `catalog:` protocol works in:
- `dependencies`
- `devDependencies`
- `peerDependencies`
- `optionalDependencies`
- `pnpm.overrides` (in pnpm-workspace.yaml)

## Publishing

`catalog:` references are automatically replaced with actual version ranges during `pnpm publish` or `pnpm pack`.

## Example monorepo setup

### pnpm-workspace.yaml

```yaml
packages:
  - "packages/*"
  - "apps/*"

catalog:
  typescript: ^5.8.0
  oxlint: ^1.0.0
  oxfmt: ^0.10.0
  "@j178/prek": ^0.3.0
```

### packages/lib-a/package.json

```json
{
  "name": "@myorg/lib-a",
  "devDependencies": {
    "typescript": "catalog:",
    "oxlint": "catalog:"
  }
}
```

### apps/web/package.json

```json
{
  "name": "@myorg/web",
  "devDependencies": {
    "typescript": "catalog:",
    "oxlint": "catalog:",
    "oxfmt": "catalog:"
  }
}
```
