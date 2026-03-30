---
name: sync-simplelocalize
description: Sync i18n translation changes from the current PR/branch to SimpleLocalize via MCP, then revert local i18n file diffs. Use when the user wants to push translation keys or values to SimpleLocalize, sync i18n changes, upload translations to SimpleLocalize, or mentions "sync simplelocalize", "push translations", "sync translations", "sync i18n", or "upload i18n". Also trigger when the user is done adding translation keys and wants to clean up i18n diffs before merging a PR.
---

# Sync SimpleLocalize

Pushes new i18n translation keys and their values from the current git branch to SimpleLocalize via MCP, then reverts the local i18n file changes so the PR stays clean (SimpleLocalize syncs translations back via its GitHub App integration).

## Step 0: Preflight — verify SimpleLocalize MCP is available

Call `mcp__simplelocalize__get_languages` with no parameters. If the call fails or the tool is not available, **stop immediately** and tell the user:

> "SimpleLocalize MCP server is not available. Please check your MCP configuration and try again."

Save the returned language list — you'll need it in Step 3.

## Step 1: Detect base branch and i18n file changes

Detect the base branch of the current PR:

```bash
gh pr view --json baseRefName --jq '.baseRefName'
```

If that fails (e.g., no PR exists yet), fall back to `main`.

Then find which i18n files changed compared to the base branch:

```bash
git diff <base-branch> --name-only -- 'packages/pixai-app/src/i18n/'
```

If no files changed, tell the user "No i18n changes found on this branch" and stop.

Parse each changed file path to extract:
- **Language**: directory name (e.g., `src/i18n/en/common.json` → `en`)
- **Namespace**: filename without extension (e.g., `common.json` → `common`)

## Step 2: Compute the key-level diff

For each changed **English** (`en`) file, compare the base branch version against the current version to find **newly added** keys.

Get the base branch version:
```bash
git show <base-branch>:packages/pixai-app/src/i18n/en/<namespace>.json
```
If the file doesn't exist on the base branch (new namespace), treat all keys as added.

Read the current version with the Read tool.

**Flatten nested JSON** into dot-notation keys. For example:
```json
{ "auth": { "login": { "title": "Log In" } } }
```
becomes `auth.login.title = "Log In"`.

A key is **added** if it exists in the current branch but not in the base branch. Only collect added keys — ignore keys that merely changed their English value.

Then collect **all translations** for the added keys from every language. Read `packages/pixai-app/src/i18n/{lang}/{namespace}.json` for each language and extract the values for the added keys.

## Step 3: Language code mapping

Map local directory names to SimpleLocalize language codes:

| Local dir | SimpleLocalize code |
|-----------|-------------------|
| `en` | `en` |
| `de` | `de` |
| `es` | `es` |
| `fr` | `fr` |
| `it` | `it` |
| `ja` | `ja` |
| `kr` | `kr` |
| `pt` | `pt` |
| `zh` | `zh_tw` |

Cross-reference with the language list from Step 0. If a local language doesn't exist in SimpleLocalize, skip it and warn the user.

## Step 4: Create translation keys on SimpleLocalize

For all added keys, call `mcp__simplelocalize__create_translation_key_bulk`:

```json
{
  "translationKeys": [
    { "key": "auth.login.title", "namespace": "common" },
    { "key": "auth.login.subtitle", "namespace": "common" }
  ]
}
```

The API won't error on duplicates, so it's safe to include keys that might already exist remotely.

**Batch in groups of 100** — the API limit is 100 keys per call. Make multiple calls if needed.

## Step 5: Upload translations

For every added key, upload translations for all languages that have a non-empty value. Call `mcp__simplelocalize__update_translations_bulk`:

```json
{
  "translations": [
    { "key": "auth.login.title", "language": "en", "namespace": "common", "text": "Log In" },
    { "key": "auth.login.title", "language": "ja", "namespace": "common", "text": "ログイン" }
  ]
}
```

**Skip empty strings** — only send translations that have actual content.

**Batch in groups of 100** — the API limit is 100 translations per call.

## Step 6: Revert i18n file changes

Only after **all** MCP operations in Steps 4 and 5 succeed, revert the i18n files to match the base branch:

```bash
git checkout <base-branch> -- packages/pixai-app/src/i18n/
```

This removes the i18n diff from the working tree. The translations now live in SimpleLocalize and will be synced back to the repo via the SimpleLocalize GitHub App.

If any MCP call failed in Steps 4 or 5, **do not revert**. Tell the user which calls failed so they can investigate before losing local changes.

## Step 7: Report

Summarize what happened:
- Number of new keys created
- Number of translations uploaded (broken down by language if helpful)
- Which namespaces were affected
- Whether i18n files were reverted successfully
- Any warnings (skipped languages, failed batches, etc.)
