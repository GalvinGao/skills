# Concentric corners

Two corner arcs are concentric when they share a center of curvature. Then the gap between the
two edges stays the same width around the corner.

## Formulas

- Child inside a parent: `inner = outer - inset`.
- Ring outside a shape (selection outline, halo, spotlight cut-out): `outer = inner + offset`.

## Rules

- The inset MUST count every layer between the two edges: padding, the parent's border width, and
  an inner ring. A 2px gap inside a 1px border is a 3px inset.
- If the result is below about 2px, you SHOULD use 0. A 1px radius reads as an anti-aliasing
  error, not as a corner.
- If the parent radius comes from a token, the child SHOULD be a `calc()` of the same token, for
  example `calc(var(--radius-md) - 3px)`. A hard-coded result MUST NOT be used where the parent
  radius can change (themes, density modes, a token update).
- If the child does not reach the corner zone (its inset is near or above the parent radius, or
  the padding is large, about 16px to 24px), the formula gives a near-square child that looks
  sharp. Treat the child as its own surface and use one radius step smaller than the parent.
- If the two sides that meet at a corner have different insets, the formula has no single answer.
  You SHOULD make the insets equal near the corner, or use the one-step-smaller rule.
- A ring that is its own element (an absolutely positioned outline) MUST get `inner + offset`. The
  same radius as the shape makes the ring pinch at each corner.
- A `box-shadow` spread ring (`0 0 0 2px`) MAY be used instead. The browser adds the spread to the
  border radius, so the ring stays concentric without a calculation.
- A tour spotlight or a cut-out around a target MUST use `target radius + padding`.
- A menu item in a padded menu MUST use `menu radius - menu padding`. Component libraries often
  give the item the same radius as the menu. Override it.
- Square children of a rounded parent (media, a scroll area, a table) MUST NOT show past the curve.
  Give each child the concentric radius, or clip the parent. Prefer `overflow: clip` to
  `overflow: hidden`: it does not create a scroll container, so `position: sticky` inside keeps
  working.

## Check

Zoom to 400% or take a 2x capture. Compare the gap at the middle of the curve with the gap on a
straight edge. They MUST be equal.

## See also

[product-tours](product-tours.md) for spotlights.
