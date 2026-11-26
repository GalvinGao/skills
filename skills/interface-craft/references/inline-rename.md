# Inline rename

Users already know this pattern from file managers and design tools. Build it completely, with one
shared component.

## Affordance

- An editable label SHOULD show a hover fill and a text cursor, so the user sees that it is
  editable. The edit field SHOULD use the same fill. Then entering edit mode adds only a caret.
- A standalone label (a page title) MUST have a tab stop, a role (`button`) or an equivalent, and
  a visible focus ring.
- A label inside a focusable row (a tree item, a list row, a grid cell) MUST NOT add a second tab
  stop. The row keeps focus: F2 renames, and Enter keeps the open action of the row.
- A read-only user MUST NOT see the hover fill or the text cursor.

## Activation

- A label that has no other click action (a page or document title) MAY open on a single click.
- An item that opens on click (a row, a card, a file) MUST rename on double-click, F2, and a Rename
  menu item. The first click of the double-click MUST NOT open the item. Exclude the name area
  from the row's open action, or delay the open and cancel it when a click with
  `event.detail === 2` arrives. The first click has `detail === 1`, the same as a single click.
- From the keyboard, F2 MUST open the field. On a standalone label, Enter MAY open it too.
- A drag that starts on the label MUST NOT open the field. Use a movement threshold.
- A menu item MUST be able to open the field through a ref or a command, not only through a click
  on the label.

## Editing

- On open, select all of a short name, because the user usually replaces it. For long text, place
  the caret where the user double-clicked.
- Enter and blur MUST commit. Escape MUST cancel. Do not ask for confirmation.
- Trim the value. An empty value MUST restore the previous name. An unchanged value MUST NOT send a
  request.
- If the new name is rejected (validation, a duplicate, a server error), the field MUST stay open
  with the user's text and a message. It MUST NOT drop what the user typed.
- Enter during IME composition MUST NOT commit.
- After Enter or Escape, focus MUST return to the label.
- Enforce the maximum length in the input itself.
- Inside a canvas or another surface with pointer and key handlers, the field MUST stop pointer and
  key events from reaching them. A key typed in the name MUST NOT delete a node.

## Geometry

The label and the input MUST have the same font, padding, line height, border width, and maximum
width. Use `field-sizing: content` or a measured width. Test it: the text MUST NOT move when the
field opens (see [layout-stability](layout-stability.md)).

## Saving

Send the rename as an optimistic update, so the new name shows at once. Roll it back with a
message if it fails (see [optimistic-mutations](optimistic-mutations.md)).
