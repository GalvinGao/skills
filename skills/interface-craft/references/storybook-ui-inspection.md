# Storybook UI inspection

A story is a place to see a state and a place to assert it.

## Cover the states

- Each state SHOULD have its own story: empty, loading, error, one item, many items, long text,
  read-only, disabled, and each interaction state.
- To compare sizes by eye, you MAY put all states in fixed-size cells in one "playground" story.
  A difference in size then shows at once.
- A story MUST render the production component with fixtures. Sample data MUST stay in the story
  files, not in production modules.
- Render the component in its real container: the grid, the scroller, the panel width. A clip or an
  overflow shows only in context.
- Open menus, hover states, and focus states in a `play` function, so the story shows them and the
  test runner checks them.

## Themes

- A scheme toolbar global SHOULD switch light and dark.
- The decorator MUST set every switch that the UI reads: the class or attribute that the CSS
  tokens use, and the scheme of the component library. If it sets only one, half the UI renders in
  the wrong scheme.
- For an automated check, export one story for each scheme with the scheme fixed on the story.
  A toolbar setting does not reach the test runner.
- A test SHOULD prove that a scheme switch does not leak into the next story.

## Locales

- A locale toolbar global SHOULD switch the message locale.
- If the message functions read a module-level locale and do not subscribe to a context (for
  example Paraglide), the decorator MUST remount the tree (a `key` on the locale). A provider-based
  library (react-intl, i18next) re-renders without a remount.
- Add a pseudo-locale: accented characters, about 30% to 40% more length, and brackets around each
  string. It shows truncation, overflow, and strings that skip translation.
- A key locale (each string shows its message key) MAY be added to find the source of a string.
- Each story that shows text SHOULD have a fixture with long text, even without a locale switch.
- Queries in `play` functions MUST use roles or test IDs. A query by English text fails in every
  other locale.

## Contrast probes

You MAY check contrast in a story. Measure what the browser paints:

1. Read the computed foreground and the background of the surface behind the target.
2. Paint both on a 1x1 canvas, in order, so translucent layers composite as on the page. A canvas
   cannot reproduce a backdrop blur. For a frosted surface, sample a pixel of a real screenshot.
3. Compute the ratio, and compare it with a minimum: 4.5 for text, 3 for an icon or a boundary.
4. A probe whose target does not render MUST fail.
5. Run the probes in a story for each scheme.

If the probes check only a list of rows, a new row MUST be added to that list, or it cannot fail.

## Run as tests

- Run each story and its `play` function as a test in a real browser in CI, for example with the
  Storybook Vitest addon in browser mode.
- Screenshot diffs MAY be added. They SHOULD NOT be the only guard. They fail on any pixel change,
  and reviewers learn to approve them. An assertion names the invariant.
- A static capture does not verify motion. Watch it run.
- If a story layout makes `<body>` a flex container, a portaled overlay can render off the screen.
  Use a full-screen layout, and center the content in your own wrapper.

## See also

[layout-stability](layout-stability.md) for geometry assertions. [neutral-gray-ramp](neutral-gray-ramp.md) for contrast targets.
