# Tree drag and drop Examples name dnd-kit; the rules apply to any
drag library.

## Start

- A drag MUST start only after a movement threshold (about 8px, `activationConstraint.distance`).
  A click then stays a click.
- On touch, a drag SHOULD start after a press delay, so the user can still scroll the list.
- Keyboard dragging SHOULD start from a drag handle, and MUST announce the pick-up, each move, and
  the drop to screen readers.
- Show the grabbing cursor for the whole drag.

## Preview

- The preview MUST render in a portal on `body`. dnd-kit `DragOverlay` does not portal by default:
  wrap it in `createPortal(..., document.body)`. Otherwise a transformed ancestor or an
  `overflow: hidden` parent can move or clip it. It MUST have `pointer-events: none`.
- For a multiple selection, the preview MUST show all selected items, or the first one with a
  count.
- The source item SHOULD stay in place and dim (about 40% opacity). Removing it moves the list.

## Targets

- A valid target MUST show a clear highlight while the pointer is over it, for example an inset
  ring on a folder.
- In an ordered list, show an insertion line at the drop index. In a tree with order, split each
  row into zones: the top quarter drops before it, the middle drops into it, and the bottom quarter
  drops after it.
- A collapsed folder SHOULD open after about 700 ms of hover. Cancel the timer when the pointer
  leaves.
- The scroll container MUST auto-scroll when the pointer is near its edge.
- An invalid target (a folder into itself or its child, a read-only place) MUST show no highlight,
  or a no-drop cursor. The drop MUST be refused before the request.
- Measure the targets again when the layout changes during the drag, for example when a folder
  opens. Use a `ResizeObserver` or the library's measuring option.

## Drop

- The preview MAY shrink into the target in about 200 ms. Reduced motion MUST skip this animation.
- Escape MUST cancel the drag and put everything back.
- The click that the pointer release makes MUST NOT open or select the item.
- Apply the move as an optimistic update with a rollback (see [optimistic-mutations](optimistic-mutations.md)).
- A drop outside the list onto another surface (a canvas, an editor) MUST use a clear data
  contract, and the list MUST NOT also handle it as a move.
- A file drag from the operating system is a different drag. Detect `Files` in
  `dataTransfer.types`, show a drop overlay, and do not mix it with an internal drag.

## Alternative

Each drag action MUST have a path without a drag, for example a "Move to" dialog. Some users cannot
drag, and a long move is easier in a dialog.
