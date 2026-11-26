# Neutral gray ramp

Use this skill when gray carries hierarchy, emphasis, and state, and chromatic color is kept for
meaning (error, warning, success).

## Tokens

Define semantic tokens over the raw ramp. Components MUST use the semantic token, never a raw
step or a hex value. The names below follow shadcn/ui. In Mantine and Radix Themes, "accent" is
the brand color: map the roles, not the names, or you get the brand color as a hover fill.

| Role                | Token example                              |
| ------------------- | ------------------------------------------ |
| Surface ladder      | `background` < `card` < `popover`          |
| Quiet fill, hover   | `accent` (also `muted`)                    |
| Strong fill         | `accent-hover`: selected, open, pressed    |
| Lines               | `border-subtle` < `border` < `border-strong`, `ring` for focus |
| Text                | `foreground`, `muted-foreground`, `foreground-dimmed` |

## Step density

- Count steps from the surface under the element, not from the page background.
- A transient state (hover) SHOULD be one step. A state that stays (selected, open, pressed)
  SHOULD be two steps. A hover on a selected item SHOULD keep the selected fill. A third fill on
  top of it adds noise and makes the item flicker.
- Selected MUST stay distinct from hover. If both use the same step, the user cannot tell where
  the selection is while the pointer moves.
- A hover fill MUST be visible on each surface where the component appears. A fixed hover token
  that equals the panel fill disappears. Component libraries often have this defect in menus.
  Set the hover token for each surface, or use a translucent foreground overlay such as
  `foreground / 5%`, which works on any surface.
- To separate two groups on one level, use a hairline or spacing. You SHOULD NOT add a third fill.
  Many fills make a dense UI muddy.

## Light and dark

- Each scheme MUST have its own values. You MUST NOT derive one scheme by inversion or arithmetic.
- In dark mode, a raised surface is lighter. In light mode, surfaces near white cannot get much
  lighter, so `card` and `popover` MAY both be white and get their separation from a hairline and
  a shadow.
- Dark steps need a larger lightness change than light steps. Displays crush near-black values,
  and glare hides small dark differences. Tune each step on a real display, in both schemes.
- An inverted primary fill (near-white in dark mode) MUST NOT be used as a hover or selected fill.

## Text and contrast

- Use three text levels at most: primary, secondary, and dimmed.
- Secondary text MUST reach 4.5:1 on every surface where it appears, including frosted and
  translucent surfaces.
- Dimmed text MAY be below 4.5:1 only for disabled controls, which WCAG exempts.
- The placeholder of an enabled field MUST reach 4.5:1. Use the secondary token. The disabled
  exemption does not apply to it.
- Non-text parts that identify a control or a state (an input border without a fill, a focus ring,
  a selected outline, a meaningful icon) MUST reach 3:1 against what is next to them.
- A state MUST NOT depend on a gray step alone when the step is small. Add a second cue, for
  example a check, a weight change, or an outline.

## Translucent and frosted fills

- A fill with alpha mixes with the layer under it. Measure the painted color. Do not calculate it.
  A 1x1 canvas composites translucent colors. It cannot reproduce a backdrop blur: for a frosted
  surface, sample a pixel of a real screenshot.
- Test a frosted surface over its worst background, for example bright media under a dark menu.
- A submenu inside a frosted menu SHOULD be solid. An element with `backdrop-filter` is a backdrop
  root, so a nested backdrop filter sees only the parent menu, not the page behind it. A submenu in
  a portal is not nested and MAY be frosted.

## Libraries

If a component library has its own gray ramp, keep it aligned with the CSS tokens, and set its
hover and dimmed variables to your tokens.
