# Floating chrome insets

Chrome that floats over a surface covers part of it. Each element that it can cover must know
where the free area is.

## Decide first

- Docked chrome takes its own space, and the layout reflows. Floating chrome covers the surface,
  and everything else MUST yield to it.
- Use floating chrome over a canvas, a map, or media, where a reflow would move the view. Use
  docked chrome for documents and forms.

## Publish the insets

- Each inset MUST have one source: a constant with the state that it depends on (sidebar width and
  collapsed state), or a measured size.
- A measured size SHOULD come from a `ResizeObserver` and go into a CSS variable on a common
  ancestor. Portaled elements (toasts) need the variable on `document.documentElement`.
- The owner MUST remove the variable or reset the inset when it unmounts.
- Consumers MUST read the published inset. They MUST NOT measure the chrome again. Two measurements
  drift apart.

## Consumers

- Centered hints, empty states, docks, and banners MUST stay in the free area.
- The yield MUST use the same duration and easing as the chrome, so both move as one.
- Fit-to-content, zoom-to-selection, and programmatic camera moves MUST pad by the insets. Content
  then never lands under the chrome.
- Toasts SHOULD sit above the bottom chrome. Popovers near an edge SHOULD use the insets as their
  collision padding.
- An overlay layer over an interactive surface MUST use `pointer-events: none` on its wrapper and
  enable pointer events only on its controls.

## Narrow widths

- Define which panel gives way when two panels and a usable main area do not fit. Close one panel
  at a width threshold.
- Panels MUST NOT overlap each other.
- A control that a narrow window can push off the screen MUST have a second path, for example a
  collapse button inside the panel.
- On mobile, fixed bars SHOULD add `env(safe-area-inset-*)`.

## Traps

- `position: fixed` inside an element with `transform`, `translate`, `rotate`, `scale`,
  `perspective`, `filter`, `backdrop-filter`, `contain: layout` or `paint`,
  `content-visibility: auto`, or `will-change` of one of these is positioned against that element,
  not the viewport. Tailwind v4 emits `translate`, `rotate`, and `scale`. Portal the fixed element
  to `body`. `container-type` does not trap it.
- A floating library does not see an anchor that a CSS transform moves (a zoomed or panned canvas).
  Update the position when the viewport changes.
- Under a fixed header, in-page anchors SHOULD use `scroll-padding-top`.
