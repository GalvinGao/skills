---
name: pr-visual-evidence
description: "Open a pull request for a frontend/visual change with a screenshot as the very first thing in its description, uploaded with the `gh attach` CLI extension. Use when creating, opening, or editing a PR that changes what a user sees — components, markup, CSS, layout, spacing, color, motion, on-screen copy, new screens or states — and when the user asks to add a screenshot, image, or before/after to a PR. Trigger on: create a PR, open a PR, ship this, gh pr create, attach a screenshot to the PR. Skip entirely when the diff renders identically (backend, config, CI, tests, docs, tooling) — a PR with no visual change gets no image."
---

# PR visual evidence

A PR that changes what someone sees opens with a picture of it. A PR that doesn't, doesn't — never
manufacture an image to satisfy the rule.

## 1. Does this PR need an image?

**Yes** — components, markup, CSS/Tailwind, layout, spacing, color, theming, motion, icons, on-screen
copy, new screens or empty/error/loading states.

**No** — server/backend, build/config/CI, tests only, docs, or a refactor that renders identically.

Unsure? Check the diff for UI files (`.tsx`/`.vue`/`.svelte`/`.css`). None → skip, and say you skipped
it because nothing renders differently.

## 2. Capture

See [CAPTURE.md](CAPTURE.md) for the Storybook / dev-server / composite recipes and the traps
(cross-origin iframes, Playwright's allowed roots, hover cards left open by `play` functions).

Non-negotiables: shoot the **real component**, crop tight, caption each panel, and use the app's
default color scheme (add the other only if the change is scheme-sensitive). Before/after belongs in
one image, labeled, when the point is a delta.

## 3. Create the PR, then attach

`gh attach --url-only` needs an existing PR number, so the PR comes first.

```bash
gh pr create --base main --title "..." --body-file /tmp/pr-body.md
# path is relative to this skill's directory; add --node <ver> where node is pinned per-project
scripts/pr-attach-image.sh --pr 123 --image ~/shots/pr-shot.png --alt "New x on the frame tiles"
```

The script uploads, then rewrites the body so the image is line one — re-running it with a new
screenshot **replaces** the existing image instead of stacking a second one, and re-uploading the
same filename overwrites the release asset rather than erroring.

Doing it by hand is three steps: `gh attach --issue N --image F --release --url-only` → prepend
`<img width="900" alt="..." src="URL" />` plus a blank line to the body → `gh pr edit N --body-file`.
Use the `<img>` tag, not `![]()`, so the width is controlled.

## `gh attach` modes

- **Default (browser/direct)** needs `playwright-cli` on PATH and a browser login. Without it the
  command fails immediately with an install hint — don't retry, switch to `--release`.
- **`--release`** is the CLI-auth-only path: uploads as an asset on a `gh-attach-assets` release.
  Run `gh release list` first. If that release already exists, you're adding to an established
  bucket — proceed. If it doesn't and the repo is shared, tell the user you're about to create a
  release before doing it.
- **`--url-only`** prints the URL and skips commenting, but still requires `--issue`.
- If the extension is a JS one and the machine pins Node per-project, invoke through the version
  manager (e.g. `fnm exec --using=<ver> -- gh attach ...`).

## Verifying the link

On a **private or internal** repo, `releases/download/...` returns **404 to anonymous and
token-header fetches** — it resolves only for a signed-in member's browser session. That 404 is not
a broken upload and is not worth "fixing". Confirm the bytes instead:

```bash
ID=$(gh api repos/OWNER/REPO/releases/tags/gh-attach-assets --jq '.assets[]|select(.name=="shot.png").id')
gh api -H "Accept: application/octet-stream" repos/OWNER/REPO/releases/assets/$ID > /tmp/check.png
```

Then compare size/dimensions with the local file.

## Before handing back

- [ ] The image is the **first line** of the description, above all prose
- [ ] It shows the change (not a stale or unrelated frame)
- [ ] The worktree is clean — no stray `.png`, no `.playwright-mcp/`, no temp page left in `public/`
- [ ] Local dev servers started for the capture are stopped
