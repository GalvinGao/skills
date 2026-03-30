---
name: preheat
description: Explore the project and list setup steps needed to run it locally — dependencies, config, services, and manual actions.
---

# Preheat

Analyze the current project and produce a checklist of everything needed to get it running locally.

## Step 1 — Locate the project root

1. Run `git rev-parse --show-toplevel` to find the repo root. If not in a git repo, use the current working directory.
2. Read `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, and any `docs/setup*` or `docs/getting-started*` files if they exist — these often document setup steps.

## Step 2 — Detect the tech stack

Scan the repo root (and common subdirectories like `apps/`, `packages/`, `services/`) for project manifests and config files. Check for at least:

- **Node/Bun/Deno**: `package.json`, `bun.lockb`, `yarn.lock`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `deno.json`
- **Python**: `pyproject.toml`, `requirements.txt`, `Pipfile`, `setup.py`, `poetry.lock`, `uv.lock`
- **Ruby**: `Gemfile`
- **Rust**: `Cargo.toml`
- **Go**: `go.mod`
- **Java/Kotlin**: `build.gradle`, `pom.xml`
- **Swift/iOS**: `Package.swift`, `*.xcodeproj`, `Podfile`
- **PHP**: `composer.json`
- **Elixir**: `mix.exs`
- **Docker**: `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`, `.docker/`
- **Infra/services**: `Makefile`, `Procfile`, `Brewfile`, `.tool-versions`, `.mise.toml`, `.envrc`

Note whether this is a monorepo (workspaces, multiple manifests).

## Step 3 — Identify environment and secret requirements

1. Look for `.env.example`, `.env.template`, `.env.sample`, `.env.local.example`, or similar files.
2. Read them and list every variable, noting which ones look like secrets (API keys, tokens, database URLs) vs non-secret config.
3. Check for references to environment variables in config files, docker-compose, or entry-point scripts.

## Step 4 — Identify infrastructure dependencies

Check if the project requires external services to run locally:

- **Databases**: Look for connection strings, ORM config (`prisma/schema.prisma`, `knexfile`, `alembic.ini`, `database.yml`, etc.)
- **Docker services**: Parse `docker-compose.yml` for required services (postgres, redis, elasticsearch, etc.)
- **Message queues / caches**: Redis, RabbitMQ, Kafka references
- **Third-party APIs**: Stripe, AWS, Firebase, Supabase, etc. referenced in config or env vars

## Step 5 — Determine install and build commands

Based on detected stack, determine:

1. **Runtime/toolchain version requirements**: `.node-version`, `.nvmrc`, `.python-version`, `.tool-versions`, `.mise.toml`, `rust-toolchain.toml`, engines field in `package.json`, etc.
2. **Dependency install commands**: `npm install`, `bun install`, `pip install -e .`, `bundle install`, `cargo build`, etc.
3. **Code generation / build steps**: DB migrations, codegen, asset compilation, Prisma generate, protobuf compilation, etc.
4. **Seed / bootstrap commands**: Database seeding, fixture loading, initial data setup.

## Step 6 — Check for existing setup scripts

Look for automation that already exists:

- `Makefile` targets (especially `setup`, `init`, `bootstrap`, `dev`)
- `scripts/` directory with setup scripts
- `package.json` scripts (`prepare`, `postinstall`, `setup`, `dev`, `start`)
- `bin/setup`, `bin/bootstrap`
- `Taskfile.yml`, `Justfile`

If a comprehensive setup script already exists, prefer referencing it rather than duplicating its steps.

## Step 7 — Output the preheat checklist

Present two clearly separated sections:

### Section A: Automated Setup (commands to run)

List the commands in the order they should be executed. Group by category:

1. **Toolchain** — install required runtimes/versions
2. **Dependencies** — install packages
3. **Infrastructure** — start local services (Docker, databases)
4. **Build / Generate** — codegen, migrations, asset builds
5. **Seed / Bootstrap** — initial data

For each command, include a one-line explanation of what it does. If a setup script covers multiple steps, list it once and note what it handles.

### Section B: Manual Actions Required

List things the user must do themselves:

- Copy/create `.env` files and fill in secrets
- Sign up for third-party services and obtain API keys
- Install system-level tools (Homebrew packages, Docker Desktop, specific runtime versions)
- Configure local hostnames, SSL certs, or other OS-level setup
- Any accounts, permissions, or access that must be obtained

For each item, explain why it's needed and link to relevant docs if found in the repo.

## Rules

- Do NOT run any install or setup commands. Only analyze and report.
- Do NOT create or modify any files.
- If `$ARGUMENTS` is provided, treat it as additional context (e.g., a specific sub-project or platform to focus on).
- If the project has multiple apps/services (monorepo), cover all of them but organize by sub-project.
- Be specific — list actual commands with correct package managers, not generic placeholders.
- If something is ambiguous or you cannot determine a requirement, call it out as "Verify with team" rather than guessing.
