# Motion: blur, opacity, and state changes

Motion shows what changed and where it went. It is not decoration. For the direction of a menu or
a sheet, see [anchored-transitions](anchored-transitions.md).

## Values

- Use one ease-out curve for a whole surface, with no overshoot: `[0.16, 1, 0.3, 1]`.
- A small change SHOULD take 120 ms to 220 ms. An entrance SHOULD take about 300 ms. An exit SHOULD
  be faster than its entrance.
- Chrome MUST NOT bounce, spring, loop while idle, or move to get attention.
- Blur SHOULD be 3px to 4px for a row or a short label, and at most 8px for a crossfade in a chip.

## Blur with opacity

Animate `opacity` and `filter: blur()` together when content changes in one place: a label swap
("Copy" to "Copied"), a value that becomes an action, a row that enters a list. The outgoing
content softens as it leaves, so two sharp texts never overlap.

For a swap in place:

1. Put both layers in one grid cell (`grid-area: 1 / 1`). The cell takes the size of the larger
   layer, so the control keeps its width.
2. Start with `initial={false}`, so the first render does not animate.
3. The hidden layer MUST be `inert` or `aria-hidden` with no focusable content inside.

```tsx
<motion.span
  aria-hidden={!shown}
  style={{ gridArea: "1 / 1" }}
  initial={false}
  animate={
    reducedMotion
      ? { opacity: shown ? 1 : 0 }
      : { opacity: shown ? 1 : 0, filter: shown ? "blur(0px)" : "blur(4px)" }
  }
  transition={reducedMotion ? { duration: 0 } : { duration: 0.2, ease: EASE }}
/>
```

For an entrance, add a small move in the direction of travel: `y: -4` for a row that drops from a
trigger, `y: 12` for dialog content that rises into place. Stagger rows by 30 ms to 50 ms. On exit,
the container and its rows SHOULD fade together, so an empty box does not linger.

You SHOULD NOT animate `filter` on a large surface, on many items at once, or in a loop. It is
expensive to paint.

## Reduced motion

- Every animation MUST read `prefers-reduced-motion`.
- The reduced path MUST remove movement, scale, and blur. It SHOULD keep a short opacity change, so
  feedback does not disappear.
- In CSS, use `@media (prefers-reduced-motion: reduce)` or the `motion-reduce:` variant.

## Width that follows content

CSS cannot transition to `width: auto`, and a layout animation scales the text and distorts it.

1. Render both contents, stacked, in a slot with `overflow: hidden`.
2. Measure each with `getBoundingClientRect().width`, round up, and add 1px. Measure before paint,
   and again after `document.fonts.ready`.
3. Tween the numeric width with the same duration and easing as the content crossfade. If the width
   lags behind, the incoming text shows clipped and then pops.

## Traps

- Tailwind v4 `scale-*`, `translate-*`, and `rotate-*` set the individual CSS properties, not
  `transform`. `transition-transform` does not animate them. Name the properties, for example
  `transition-[scale,translate]`.
- A static screenshot does not verify motion. Watch the enter, the settle, and the exit. In a
  headless browser, a synthetic hover can miss React pointer handlers: dispatch `pointerenter` and
  `pointerover` events on the element.
