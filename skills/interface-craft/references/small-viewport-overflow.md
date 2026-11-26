# Small viewports and overflow

Overflow is correct where the user expects it, and it MUST stay inside its own region.

## Where overflow belongs

- Overflow MAY occur in a list body, a canvas, a wide table, a code block, and a row of cards.
- Overflow MUST NOT hide a dialog footer, a navbar, or the primary action of a toolbar.
- Overflow MUST NOT push a neighbor out of place. Put the scroll region inside its own boundary.

## Height

- Cap the height of a popover, menu, or dialog body with `dvh`, not `vh`. On mobile, `vh` ignores
  the browser bars. Combine it with a fixed limit: `max-height: min(31rem, calc(100dvh - 14rem))`.
- Each flex or grid item between the height cap and the scroll region MUST have `min-height: 0`
  (`min-width: 0` in a row). Without it, a wrapper grows to its content and pushes the footer off
  the screen. The scroll container itself already has a minimum size of 0.
- Primary actions MUST stay outside the scroll region. Use a fixed footer in the dialog.
- Nested scroll regions SHOULD use `overscroll-behavior: contain`, so a scroll does not move the
  page or the canvas behind.

## Width

- A row of cards that scrolls sideways MUST show that more content exists: an edge fade, a partly
  visible card, or arrows. A hidden scrollbar without a cue hides content.
- A toolbar that does not fit SHOULD wrap to a second row. It SHOULD NOT scroll sideways. An
  overflow menu for the lowest-priority items MAY be used.
- A container query styles only the descendants of the container. Make a parent with a definite
  width the query container. `container-type: inline-size` on an element that sizes to its content
  (a floating toolbar) collapses it to zero width.
- A wide table on a phone goes in a horizontal scroller with an edge fade. A sticky first column
  MAY be added.
- A component SHOULD respond to its container (`@container`), not to the viewport. The same
  component lives in a narrow panel and on a full page.
- A long name in a row MUST have `min-width: 0` and truncate. Show the full text in a tooltip only
  when it is truncated. The only identifier of an item MUST NOT be truncated without a way to see
  it.
- A heading next to a link SHOULD wrap, and the link SHOULD NOT shrink.
- A button label MAY become icon-only below a breakpoint. Keep the label for screen readers and
  in a tooltip.

## Touch

- A control that shows only on hover MUST be visible on a touch screen:
  `@media (hover: none) { opacity: 1 }`.
- Each pointer target MUST be at least 24 by 24 CSS pixels, or have 24px of space around it
  (WCAG 2.5.8). A primary touch action SHOULD be 44px.

## Check

- Check 375px wide, a short window of about 600px high, and a desktop width with every side panel
  open.
- Use a pseudo-locale (accents and about 30% to 40% more length) to find tight fits. Then check the
  longest real locales, for example German, Ukrainian, French, and Spanish. Check CJK line breaks in
  each CJK language on its own.
