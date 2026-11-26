# Layout stability

A state change MUST NOT move or resize a neighbor, unless the change is what the user asked for
(for example, expanding a section).

## Build it so that it cannot jump

- **Swaps in one cell.** Put each state of a slot in the same grid cell
  (`display: grid` with each child at `grid-area: 1 / 1`). The cell takes the size of the largest
  state. The hidden layer MUST be `inert`, or `visibility: hidden` when it does not fade, so it
  takes no focus, no pointer input, and no screen reader attention. `aria-hidden` alone leaves its
  buttons in the tab order.
- **Reserved space.** Media MUST get its size or `aspect-ratio` before it loads. A changing number
  SHOULD use `tabular-nums` and a minimum width for its expected digits.
- **Skeletons.** A skeleton MUST have the box of the loaded component. Share the class or constant
  with the real component when you can. Put a thin bar in a row with the line height of the real
  text, so the bar thickness and the row height are independent.
- **Hover actions.** Actions that show on hover MUST be an overlay or use space that is always
  reserved. They MUST NOT enter the flow.
- **Unavailable items.** Keep an item that becomes unavailable in place and disabled. Do not
  remove it, unless the removal is the result that the user asked for.
- **Edit fields.** A rename input MUST have the font, padding, line height, and border width of its
  label. Give the label a transparent border if the input has a visible one. Use
  `field-sizing: content` or a measured width.
- **Scrollbars.** A container whose overflow can change SHOULD use `scrollbar-gutter: stable`.
- **Fonts.** A late web font MUST NOT move text. A preload alone does not stop a swap after the
  first paint. Preload with `font-display: optional`, or declare a `local()` fallback face with
  `size-adjust` that matches the web font. Safari ignores `ascent-override` and
  `descent-override`.
- **Images.** A partly downloaded image MUST NOT paint over the previous content. Keep the old
  layer until `image.decode()` resolves, then swap.
- **Measurement.** A measurement that changes layout SHOULD run before paint
  (`useLayoutEffect`), so the user never sees the first frame.
- **Hydration.** The first client render MUST match the server layout. A client-only layout (for
  example masonry that needs a width) MUST keep the server layout until it can measure.
- **Motion.** A short effect SHOULD animate `transform` and `opacity`, not layout properties. If a
  width must animate, tween a measured width (see [motion](motion.md)).

## Prove it

Geometry tests MUST run in a real browser. jsdom returns zero for each rect. Use a Storybook
`play` function in the browser runner, or Playwright. Select elements by role or test ID, not by
translated text.

### End-state geometry

```ts
const before = { item: item.getBoundingClientRect(), next: next.getBoundingClientRect() };
await userEvent.click(trigger);
await waitFor(() => expect(endStateFact()).toBe(true));
await expect(item.getBoundingClientRect().height).toBe(before.item.height);
await expect(next.getBoundingClientRect().top).toBe(before.next.top);
```

- Measure a neighbor too. A component can keep its size and still push the next element.
- A rect includes CSS transforms. Measure after `waitFor` confirms the end state, not during a
  transition.

### Every frame

An end-state check does not see a size that changes and then returns. Watch the box during the
interaction:

```ts
const nextFrame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

async function watchBox(element: Element) {
  const sizes = new Set<string>();
  const observer = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const [box] = entry.borderBoxSize;
      if (box !== undefined) sizes.add(`${box.inlineSize}x${box.blockSize}`);
    }
  });
  observer.observe(element, { box: "border-box" });
  await nextFrame();
  await nextFrame();
  return async () => {
    await nextFrame();
    await nextFrame();
    observer.disconnect();
    return [...sizes];
  };
}

const stop = await watchBox(button);
await userEvent.click(button);
await waitFor(() => expect(button).toHaveAttribute("data-state", "done"));
await expect(await stop()).toHaveLength(1);
```

- Observe the border box. The default content box does not change when only the padding or the
  border changes, so a label-to-input jump passes the test.
- Wait two frames before the interaction, so the observer records the first size.
- `ResizeObserver` sees a size that lasts one frame or more. It does not see a move. Use the
  end-state check for position.
- Observe the component and its container. A container that changes size moves its neighbors.
- In Chromium you MAY also collect `PerformanceObserver` entries of type `layout-shift`. Read every
  entry: the CLS score drops shifts that follow user input, and a test always uses input.

### Which transitions to guard

Skeleton to content, label to rename input, a label swap, hover that shows actions, a long title
or locale, server render to client render, and a late web font (hold the font request in
Playwright, then compare text rects).
