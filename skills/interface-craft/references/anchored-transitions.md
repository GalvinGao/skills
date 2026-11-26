# Anchored transitions

A surface grows from the point where it attaches, so the user sees where it came from. For blur, easing, and reduced motion, see [motion](motion.md).

## Placement and origin

If the surface always opens at the same placement, set its origin to the corner that touches the
anchor:

| Placement      | Origin        |
| -------------- | ------------- |
| `bottom-start` | top left      |
| `bottom-end`   | top right     |
| `top-start`    | bottom left   |
| `top-end`      | bottom right  |
| `right-start`  | top left      |
| `left-start`   | top right     |
| `bottom`       | top center    |

- A surface that can flip MUST NOT have a fixed corner. After a flip, the surface grows away from
  its anchor.
- Read the origin from the positioning result: the final `placement` of Floating UI, the
  `--transform-origin` variable of Base UI, or the transform-origin variable of Radix. If you cannot
  read it, use a fade and a scale from the center.
- A component library preset (for example Mantine `pop-top-right`) is a fixed corner. Use it only
  where the placement cannot flip.

## Edges and sheets

- A drawer or sheet MUST enter from the edge it is attached to.
- A full-screen menu on a phone that opens from a top bar SHOULD enter from the top. A bottom sheet
  enters from the bottom.
- A submenu enters from the side of its parent item. When it flips to the other side, the direction
  MUST flip too.

## Movement

- Movement SHOULD be small: 4px to 8px, or a scale from 0.95 to 0.97. No overshoot.
- Exit SHOULD reverse the enter, and SHOULD be faster.
- A tooltip SHOULD only fade. A direction on a tooltip adds noise.
- Reduced motion MUST remove the movement and the scale. Keep a short fade.

## Nested surfaces

- A submenu nested inside a frosted (`backdrop-filter`) menu SHOULD be solid. The parent is a
  backdrop root, so the nested filter sees only the parent, not the page. A portaled submenu is
  not nested.
- An anchor inside a transformed canvas does not trigger a position update. Update the position
  when the viewport changes.
