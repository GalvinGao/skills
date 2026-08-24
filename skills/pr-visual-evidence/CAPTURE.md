# Capturing the screenshot

Ordered by how much setup they cost. Stop at the first one that shows the change honestly.

## Storybook (best for a component change)

A story already renders the real component with fixtures, needs no auth, and boots in ~30s. Start it
on a free port — the default one is usually held by another worktree:

```bash
pnpm storybook --port 6017 --no-open --ci   # then: curl -sf localhost:6017/index.json
```

Story ids come from `curl -s localhost:6017/index.json`; render one bare at
`/iframe.html?id=<id>&viewMode=story`, and force a scheme with `&globals=colorScheme%3Alight`
(url-encode the colon — a raw `:` can be rejected by the navigation tool).

**A story's `play` function runs on load.** One that hovers something leaves a hover card open in
your shot. Pick a story without an interactive `play`, or close the card before capturing.

Small components look lost at 1× in a PR. Scale the subject rather than shrinking the viewport:

```js
document.querySelector('[data-testid="…"]').style.transform = "scale(2)";
```

## Dev server

For anything Storybook can't reach (a full route, real data, auth-gated UI). Run a plain `vite` on a
dedicated port — a portless HTTPS proxy is usually not drivable by the browser tooling.

## Composite of two panels

To show two states in one image, build a page of `<iframe>`s and screenshot the wrapper.

**Serve it from the same origin as the stories.** A page on a different port loads the iframe, but
Vite blocks the cross-origin module requests inside it and every story renders
"Failed to fetch dynamically imported module". Dropping the page into the app's `public/` dir gets it
served by the same dev server — delete it immediately after.

```html
<div class="wrap">
  <figure>
    <figcaption>What this panel shows</figcaption>
    <div class="shot"><iframe src="/iframe.html?id=…&viewMode=story"></iframe></div>
  </figure>
</div>
<style>
  body { margin: 0; background: #242424; font: 13px/1.4 ui-sans-serif, system-ui; color: #a1a1a1; }
  .wrap { width: 900px; display: flex; flex-direction: column; gap: 26px; padding: 28px 0 12px; }
  figure { margin: 0; display: flex; flex-direction: column; gap: 10px; align-items: center; }
  .shot { width: 880px; height: 200px; overflow: hidden; }
  iframe { width: 440px; height: 100px; border: 0; display: block;
           transform: scale(2); transform-origin: top left; }
</style>
```

Match the page background to the iframe's or you get visible banding between panels. Sample both and
set the page to whatever the iframe reports:

```bash
magick shot.png -format "page:%[pixel:p{450,10}] iframe:%[pixel:p{450,290}]\n" info:
```

Size each `.shot` so the centered content nearly fills it — dead space reads as sloppiness.

## Taking the shot

Playwright MCP writes **only inside the repo root**, so pass a bare relative filename, then move the
file out and remove the artifacts:

```
browser_navigate  → browser_resize → browser_take_screenshot { filename: "pr-shot.png",
                                                               target: ".wrap", scale: "device" }
mv pr-shot.png ~/shots/ && rm -rf .playwright-mcp
```

`target` (an element screenshot) beats `fullPage` — it crops to the subject with no scrollbars or
page chrome. `scale: "device"` gives a retina-sharp image; these stay small (a 900×523 UI shot is
~20 KB).

## The other browser pane

If you're using the in-editor browser pane instead: its screenshot pixels are **not** CSS pixels, so
clicking coordinates read off a screenshot silently misses, and `read_page` can report a 0×0 viewport.
Drive it with `document.querySelector('[data-testid=…]').click()` and read the resulting DOM in a
**second** call — React batches state, so the same eval still sees the old tree.
