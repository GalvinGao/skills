# Empty states

An empty state is the first lesson for a new user and a dead end for everyone else if it only
says "nothing here".

## Tell the kinds apart

Each kind needs its own message and action. You MUST NOT use one generic message for all of them.

| Kind                         | Message                               | Action                                     |
| ---------------------------- | ------------------------------------- | ------------------------------------------ |
| First use                    | What this place is for                | Create, upload, start from a template or preset |
| Cleared by the user          | Short confirmation                    | The same create action                     |
| Filter or search result      | That the filter causes it, with the query | Clear the filter                       |
| No permission to add         | Who can add items                     | None that fails. A request path if one exists |
| Error                        | What failed, in plain words           | Retry                                      |

## Rules

- An empty state MUST give one or more next actions that work from this place: a button, a preset,
  a template, an example, or a gesture hint with a key cap such as "Double-click" or "Drag".
- A user who cannot do the action MUST NOT see a button that fails. Tell them who can, and give a
  request path if one exists. This is the only empty state without an action.
- The copy SHOULD be one line that names the purpose of the place, in plain words, without jargon.
- If the action lives in another place (a toolbar, a context menu, a node menu), the empty state
  SHOULD show a small mockup of that control, so the user knows what to look for.
- An empty state MUST stay clear of floating chrome. Read the same insets as the rest of the
  layout (see [floating-chrome-insets](floating-chrome-insets.md)).
- An empty state over a canvas or a drop zone MUST let input through: `pointer-events: none` on
  the wrapper, and pointer events only on its controls. A hint over a drop zone MUST NOT take the
  drop.
- While the options of the empty state load, it MUST keep its layout. Show a skeleton in place of
  each option, and keep an unavailable option disabled in place.
- A loading skeleton for a place that can be empty MUST NOT draw fake items.

## Mockup of a remote control

- Build the mockup from the real components, rendered inside an `inert` and `aria-hidden` frame.
  The picture then matches the product, follows the theme and the locale, and cannot take focus.
- You MUST NOT use a screenshot. It goes out of date and ignores the theme and the locale.
- Mute the mockup (lower opacity and saturation) so it does not read as a working control. It MAY
  become brighter when the pointer is over its panel.
- Add a fake pointer or a highlight on the control to use, and a caption that names the action.

## See also

[loading-indicators](loading-indicators.md) for the state before the result. [product-tours](product-tours.md) for guided first use.
