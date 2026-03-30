---
name: setup-superset
description: Create .superset/config.json with setup and teardown scripts for Superset workspaces.
---

# Setup Superset

Create a `.superset/config.json` file in the current repository root so Superset automatically runs commands when workspaces are created or deleted.

## Step 1 — Locate the repository root

1. Run `git rev-parse --show-toplevel` to find the repo root.
2. If not inside a git repo, use the current working directory and warn the user.

## Step 2 — Check for existing config

1. Check if `.superset/config.json` already exists at the repo root.
2. If it does, read the file, show its contents, and ask the user whether to overwrite or update it.

## Step 3 — Determine project stack

1. Inspect the repo root for indicators of the project's tech stack (e.g. `package.json`, `Cargo.toml`, `docker-compose.yml`, `Gemfile`, `pyproject.toml`, `go.mod`, `.env`, etc.).
2. Based on what you find, suggest sensible defaults for `setup` and `teardown` arrays.

### Copying gitignored environment files

Workspaces are created from a git worktree, so gitignored files like `.env`, `.env.local`, `.env.development.local`, etc. will NOT be present. These files are often **critical** for the developer to actually run and test the project. The setup script **must** copy them from the root repo into the workspace.

1. Check which `.env*` files exist at the repo root (e.g. `.env`, `.env.local`, `.env.development.local`).
2. For every gitignored env file found, add a `cp` command to the setup array.
3. Also check for other gitignored-but-critical files the project might need (e.g. `credentials.json`, `serviceAccountKey.json`, `.dev.vars`, `wrangler.toml` with secrets, local database files, etc.).

Common patterns:

- **Node/Bun:** install deps, copy env files, start services
  ```json
  {
    "setup": [
      "cp \"$SUPERSET_ROOT_PATH/.env\" .env",
      "cp \"$SUPERSET_ROOT_PATH/.env.local\" .env.local",
      "bun install"
    ],
    "teardown": []
  }
  ```
- **Docker:** copy env files, start services on create, stop on delete
  ```json
  {
    "setup": [
      "cp \"$SUPERSET_ROOT_PATH/.env\" .env",
      "docker-compose up -d",
      "bun install"
    ],
    "teardown": ["docker-compose down -v"]
  }
  ```
- **Python:** copy env files, create venv, install deps
  ```json
  {
    "setup": [
      "cp \"$SUPERSET_ROOT_PATH/.env\" .env",
      "python -m venv .venv",
      "source .venv/bin/activate && pip install -e ."
    ],
    "teardown": []
  }
  ```

If the stack is unclear, ask the user what commands they need.

## Step 4 — Present the config and confirm

1. Show the proposed `.superset/config.json` to the user.
2. Explain:
   - `setup` runs sequentially in the workspace directory when a workspace is created.
   - `teardown` runs when a workspace is deleted. If teardown fails, Superset offers a force-delete option.
   - Two environment variables are available in scripts: `$SUPERSET_ROOT_PATH` (path to the root repo) and `$SUPERSET_WORKSPACE_NAME` (current workspace name).
3. Ask the user to confirm or adjust before writing.

## Step 5 — Write the file

1. Create the `.superset/` directory if it doesn't exist.
2. Write `config.json` with the confirmed content.
3. Tell the user they can commit `.superset/` to share the config with their team.

## Notes

- **Completeness over speed.** The setup script must produce a workspace that is fully ready for the developer to work in — do NOT skip steps like copying `.env` files, running `docker-compose up`, or installing dependencies just to keep setup fast. A workspace that boots in 2 seconds but can't run the project is useless. These steps run once per workspace creation, not on every command.
- For complex logic, suggest extracting to a shell script (e.g. `.superset/setup.sh`) and referencing it from the config.
- Users can override project config per-machine at `~/.superset/projects/<project-id>/config.json` without touching the repo.
- If `$ARGUMENTS` is provided, use it as guidance for what the setup/teardown scripts should do.
