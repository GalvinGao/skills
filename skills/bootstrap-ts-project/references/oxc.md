# OXC Toolchain Reference (oxlint + oxfmt)

## Installation

```bash
pnpm add -D oxlint oxfmt
```

## oxlint

High-performance JavaScript/TypeScript linter, 50-100x faster than ESLint. 695+ rules covering ESLint core, TypeScript, React, Jest, Vitest, Import, Unicorn, jsx-a11y.

### package.json scripts

```json
{
  "scripts": {
    "lint": "oxlint",
    "lint:fix": "oxlint --fix"
  }
}
```

### Supported file types

`.js`, `.mjs`, `.cjs`, `.ts`, `.mts`, `.cts`, `.jsx`, `.tsx`, `.vue`, `.svelte`, `.astro`

### Configuration: `.oxlintrc.json`

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "categories": {
    "correctness": "error",
    "suspicious": "warn"
  },
  "rules": {
    "eslint/no-unused-vars": "error"
  }
}
```

#### Categories

| Category | Description |
|----------|-------------|
| `correctness` | Code that is definitely wrong or useless |
| `suspicious` | Code that is likely wrong or useless |
| `pedantic` | Extra strict rules, may have false positives |
| `perf` | Runtime performance improvements |
| `style` | Idiomatic and consistent style |
| `restriction` | Rules banning specific patterns |
| `nursery` | Rules under development |

#### Rule severity

- `"off"` or `"allow"` — disable
- `"warn"` — warning
- `"error"` or `"deny"` — error

#### Plugins

```json
{
  "plugins": ["unicorn", "typescript", "oxc"]
}
```

Setting `plugins` overwrites defaults — include everything needed.

---

## oxfmt

High-performance formatter, ~30x faster than Prettier, 2x faster than Biome. 100% Prettier JS/TS conformance.

### Supported languages

JavaScript, JSX, TypeScript, TSX, JSON, JSONC, JSON5, YAML, TOML, HTML, Angular, Vue, CSS, SCSS, Less, Markdown, MDX, GraphQL, Ember, Handlebars.

### package.json scripts

```json
{
  "scripts": {
    "fmt": "oxfmt",
    "fmt:check": "oxfmt --check"
  }
}
```

### Generate config

```bash
npx oxfmt --init
```

### Configuration: `.oxfmtrc.json`

```json
{
  "$schema": "./node_modules/oxfmt/configuration_schema.json",
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all"
}
```

#### All options

| Option | Default | Description |
|--------|---------|-------------|
| `printWidth` | 100 | Line width limit |
| `tabWidth` | 2 | Spaces per indent level |
| `useTabs` | false | Tabs instead of spaces |
| `semi` | true | Add semicolons |
| `singleQuote` | false | Use single quotes |
| `trailingComma` | `"all"` | Trailing commas in multi-line |
| `ignorePatterns` | — | Glob patterns to exclude |
| `sortImports` | disabled | Import sorting |
| `sortTailwindcss` | disabled | Tailwind class sorting |
| `sortPackageJson` | enabled | package.json field sorting |
| `insertFinalNewline` | true | Final newline in files |

#### Overrides

```json
{
  "printWidth": 100,
  "overrides": [
    {
      "files": ["*.test.ts"],
      "options": { "printWidth": 120 }
    }
  ]
}
```

Reads `.editorconfig` as fallback for unset fields.
