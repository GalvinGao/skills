# Product tours

A tour teaches a layout that the user cannot read alone. A small hint at the moment of need
teaches a single action better.

## When

- Use a tour for a new kind of surface: several panes, a new paradigm, a mode switch.
- For one action, you SHOULD use a contextual hint near its control, at the moment it matters.
- After the tour, contextual hints SHOULD teach the next steps.

## Steps

- A tour SHOULD have 3 to 6 steps. The first and the last step SHOULD be centered cards without a
  target.
- Each step MUST teach one idea, in one or two sentences.
- Select a target with a stable attribute (`data-tour`, a role attribute, a test ID). A class name
  or a DOM path breaks.
- Put the attribute on the element that moves. If the user can swap or resize panes, the tour then
  follows the layout.
- The spotlight radius MUST be `target radius + padding` (see [concentric-corners](concentric-corners.md)).
- A step whose target can be absent MUST be removed before the tour starts. A step that points at
  nothing confuses more than a missing step.
- A target outside the viewport MUST be scrolled into view, or the step MUST be skipped.

## Start

- Load the tour code lazily.
- Start the tour one time, after the layout settles (after entrance transitions and pane layout).
- You MUST NOT start it while a dialog is open, while a send or save is pending, or over another
  tour.
- Disable the page shortcuts while the tour is open.

## Progress

- Mark the tour as seen when it ends, whether the user completed it or skipped it. A skipped tour
  MUST NOT come back.
- Storage MAY be local or on the server. Reading and writing it MUST work when storage is not
  available.
- Put a replay item in the Help menu. Replay MUST start again at step 1.
- Record the step at which the tour ended, so you can find where users leave.

## Controls and positioning

- Give Next, Back (from step 2), Skip, and a step count. Escape MUST skip.
- On a step that explains, trap focus in the card. On a step that waits for the user to act, keep
  the target in the focus order, or a keyboard user cannot reach it.
- Return focus to the previous element when the tour ends.
- Position the card with collision handling (flip and shift) and update it on resize, scroll, and
  target size changes.
- The spotlight and the card MAY glide between steps. Reduced motion MUST stop the glide.
- A step that waits for the user to do the action MUST also offer Skip.
