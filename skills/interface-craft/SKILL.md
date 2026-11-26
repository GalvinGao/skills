---
name: interface-craft
description: A portable playbook for interface craft in React web apps. One workflow chains structure, surfaces, states, interaction, motion, and proof, with references for concentric corners, a neutral gray ramp, layout stability (no layout shift), fixed chrome insets, small viewports and overflow, loading indicators, empty states, product tours, anchored menu transitions, blur and opacity motion, a keyboard shortcut registry, inline rename, optimistic updates, tree drag and drop, and Storybook inspection across themes and locales. Use when building or reviewing a component, screen, panel, menu, list, tree, empty state, tour, shortcut, or rename field, or when UI jumps, clips, overflows, loads awkwardly, or looks wrong in dark mode, light mode, or another language.
---

# Interface craft

The key words MUST, SHOULD, and MAY follow RFC 2119. Each reference file stands alone. Read only the
files that the task needs.

## Workflow

For a new component or screen, go through the phases in order. For a narrow fix, use the
[symptom table](#route-by-symptom).

1. **Structure.** Decide where the component lives, what can cover it, and what it can push.
   [floating-chrome-insets](references/floating-chrome-insets.md),
   [small-viewport-overflow](references/small-viewport-overflow.md).
2. **Surface.** Pick tokens and corners. [neutral-gray-ramp](references/neutral-gray-ramp.md),
   [concentric-corners](references/concentric-corners.md).
3. **States.** List every state before you write code: loading, empty, error, one item, many items,
   long text, read-only, disabled. [loading-indicators](references/loading-indicators.md),
   [empty-states](references/empty-states.md). For first use, see
   [product-tours](references/product-tours.md).
4. **Interaction.** Use the pattern that users already know.
   [keyboard-shortcut-registry](references/keyboard-shortcut-registry.md),
   [inline-rename](references/inline-rename.md),
   [optimistic-mutations](references/optimistic-mutations.md),
   [tree-drag-and-drop](references/tree-drag-and-drop.md).
5. **Motion.** Only for a reveal or a state change. [motion](references/motion.md),
   [anchored-transitions](references/anchored-transitions.md).
6. **Proof.** A story for each state, a geometry assertion for each state change, both color
   schemes, and a pseudo-locale. [storybook-ui-inspection](references/storybook-ui-inspection.md),
   [layout-stability](references/layout-stability.md).

## Route by symptom

| Symptom                                                        | Read                                                                   |
| -------------------------------------------------------------- | ---------------------------------------------------------------------- |
| A component jumps, flickers, or reflows                        | [layout-stability](references/layout-stability.md)                     |
| Content, a hint, or a toast is under a panel                   | [floating-chrome-insets](references/floating-chrome-insets.md)         |
| Clips on a phone, a short window, or in German                 | [small-viewport-overflow](references/small-viewport-overflow.md)       |
| Hover is invisible, dark mode drifts, gray text fails contrast | [neutral-gray-ramp](references/neutral-gray-ramp.md)                   |
| Nested corners look off, a ring pinches                        | [concentric-corners](references/concentric-corners.md)                 |
| A page flashes, sticks on a skeleton, or loops on an error     | [loading-indicators](references/loading-indicators.md)                 |
| An empty state says only "nothing here"                        | [empty-states](references/empty-states.md)                             |
| A tour points at nothing or comes back after a skip            | [product-tours](references/product-tours.md)                           |
| A menu grows from the wrong corner                             | [anchored-transitions](references/anchored-transitions.md)             |
| A label swap or an entrance looks harsh                        | [motion](references/motion.md)                                         |
| Two shortcuts collide, or a key fires in a text field          | [keyboard-shortcut-registry](references/keyboard-shortcut-registry.md) |
| A rename loses text or opens on a drag                         | [inline-rename](references/inline-rename.md)                           |
| A rollback restores the wrong value                            | [optimistic-mutations](references/optimistic-mutations.md)             |
| A drop lands in the wrong place, or a click fires after a drag | [tree-drag-and-drop](references/tree-drag-and-drop.md)                 |
| It looks right in one theme or language only                   | [storybook-ui-inspection](references/storybook-ui-inspection.md)       |

## Rules across all topics

- A state change MUST NOT move or resize a neighbor, unless the user asked for that change.
- Components MUST use semantic tokens, not raw values.
- Each empty state and each error state MUST give a next step, or say who can act.
- Each command key MUST be in one shortcut catalog, and the user MUST be able to find it there.
- Each animation MUST fall back to an opacity change under reduced motion.
- An edit SHOULD show at once and roll back with the real error if the server refuses it.
- A rule is unverified until a real browser shows it, in both schemes and in a long locale. jsdom
  has no layout.

## Adapt to the project

- Project instructions take precedence over this skill.
- First find what the project already has: its tokens, its surface classes, its shortcut catalog,
  its rename component, its story setup. Use them. Do not add a second copy.
- Map roles, not names. "Accent" is a hover fill in shadcn/ui and the brand color in Mantine and
  Radix Themes.
- To use this skill elsewhere, copy the whole folder into the skills directory of the agent, for
  example `~/.claude/skills/`, `~/.agents/skills/`, or a project's `.claude/skills/`.
