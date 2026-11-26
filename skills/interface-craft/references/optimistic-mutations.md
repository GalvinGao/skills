# Optimistic mutations

The UI shows the result at once and corrects itself if the server disagrees. Code uses TanStack Query; the rules apply to any cache.

## Recipe

```ts
useMutation({
  mutationFn,
  onMutate: async (vars) => {
    await queryClient.cancelQueries({ queryKey: treeKey });
    const snapshot = queryClient.getQueriesData({ queryKey: treeKey });
    queryClient.setQueriesData({ queryKey: treeKey }, (old) => old && applyEdit(old, vars));
    return { snapshot };
  },
  onError: (error, _vars, context) => {
    for (const [key, data] of context?.snapshot ?? []) queryClient.setQueryData(key, data);
    toast.error(error.message);
  },
  onSettled: () => {
    if (queryClient.isMutating({ mutationKey: treeKey }) === 1) {
      return queryClient.invalidateQueries({ queryKey: treeKey });
    }
  },
  mutationKey: treeKey,
});
```

- You MUST cancel the queries of the key before the patch. A refetch in flight otherwise
  overwrites the patch with old data.
- The snapshot MUST include each cached variant of the key (other filters, roots, depths, pages).
  `getQueriesData` with a partial key gives all of them. One variant left unpatched shows the old
  value elsewhere.
- Put the edit in a pure function with unit tests. The same function patches every variant.
- On error, restore the snapshot and show the real error message.
- On settle, invalidate. Another mutation can make the snapshot stale, and the server can change
  fields that the client derives (a path, a depth, an order).
- If edits can overlap, invalidate only when this is the last mutation of the key in flight
  (`isMutating(...) === 1`). Otherwise the refetch of the first edit overwrites the optimistic
  patch of the second.
- On success, merge the fields that only the server knows (ids, timestamps, normalized names).

## What to make optimistic

- Rename, move, delete, toggle, reorder, and cover changes SHOULD be optimistic.
- A create SHOULD stay pending unless the client can make a temporary id and replace it. Keep the
  pending state until the new item is in the cache: return the invalidation promise from
  `onSuccess`, so the temporary row and the real row never both show or both miss.
- Refuse a change before you send it if the server will reject it, for example a folder moved into
  its own child.
- A destructive optimistic change MAY offer Undo in its toast instead of a confirmation dialog.

## Traps

- An optimistic delete unmounts the component that called it. Callbacks passed to `mutate()` do
  not run after unmount. Put the error toast and analytics in the `useMutation` options.
- Two edits of one record can overlap. On a failure, restore the old value only if the current
  value is still the value that failed. Otherwise a late failure undoes a newer success.
- A batch operation can partly succeed. Refetch on settle, and report which items failed.
- An optimistic state is lost on reload. If a reload during the request can lose the user's work,
  warn before unload or persist the pending mutation.
- Check the pending, failure, retry, unmount, and reload states for each mutation.
