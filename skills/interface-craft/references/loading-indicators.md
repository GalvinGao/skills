# Loading indicators

Choose the indicator from the result of the wait, not from the component that waits.

## Choose

| Wait                                                  | Indicator                                                    |
| ----------------------------------------------------- | ------------------------------------------------------------ |
| Under about 300 ms                                    | Nothing                                                      |
| Content block with a known shape                      | Skeleton with the same geometry, first load only             |
| Result that can be empty or fail in unknown ways      | Container loader, then a real empty or error state           |
| Known box that content fills (media, a count, a preview) | Reserve the box, then fade the content in                 |
| A user action (save, send, pick)                      | Spinner in the trigger                                       |
| Work with a known duration                            | Progress with an estimate                                    |
| Next page of a list                                   | Small loader below the loaded items                          |
| Refetch of shown data                                 | Keep the data. Mark the region `aria-busy`                   |

## Rules

- An indicator SHOULD appear only after a delay of about 300 ms. Once it shows, it SHOULD stay for
  about 500 ms. A shorter flash reads as a glitch.
- A skeleton MUST NOT draw fake items when the result can be empty. It promises content that may
  not arrive.
- A skeleton MUST NOT come back during a refetch or a page load. Keep the loaded content on the
  screen.
- A fade SHOULD take 150 ms to 250 ms on opacity. It MAY add a small blur. The box MUST be
  reserved first, or the fade hides a jump.
- New media MUST NOT paint before it decodes. Keep the previous content until it is ready.
- An action spinner MUST stay inside the trigger and MUST keep the trigger width. It MUST NOT
  replace a section or a page.
- A control that opens a surface (a menu, a picker, a dialog) MUST stay enabled while its data
  loads or after the load fails. Show the loading or the error state, with a retry, in the surface
  that it opens. Disable a control only for
  a persistent restriction, such as a missing permission. A disabled control looks like a missing
  feature.
- Reduced motion MUST stop a shimmer. The fade MAY stay.
- A loader MUST have an accessible label. A long operation SHOULD announce its end in a live
  region.

## TanStack Query traps

- A query that waits for authentication is disabled while identity resolves. A disabled query
  has `isLoading === false`. Include the auth pending state in the loading condition, or the page
  shows a blank gap first.
- You MUST NOT use `isPending` of a query that can stay disabled as the skeleton condition. An
  anonymous visitor then sees a skeleton forever.
- An error screen MUST NOT call the hook of the query that failed. A new observer refetches an
  errored query, the status goes back to pending, and the gate shows the loader and the error in a
  loop. Pass the error from a parent that stays mounted.
- Return the invalidation promise from a mutation callback when the UI must stay pending until
  the new data is in the cache.

## See also

[layout-stability](layout-stability.md) for skeleton geometry tests. [empty-states](empty-states.md) for the state after the load.
