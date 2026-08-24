# Suspending a `User` — endpoint design

## Short answer

| Decision | Value | Why |
| --- | --- | --- |
| Method name (in the router) | `suspend` | Imperative, camelCase, unambiguous in the HR domain (AIP-130). |
| HTTP verb | `POST` | All custom methods are `POST`; the `:verb` suffix is what marks it as custom (AIP-130). |
| Path | `/orgs/{org}/users/{user}:suspend` | Custom method scoped to a single `User` resource; path is the resource name + `:suspend` suffix (AIP-121, AIP-122, AIP-130). |
| Input | `{ name, reason?, notify?, etag? }` | `name` is the canonical resource name (AIP-122). The rest are operation parameters, not resource fields. |
| Output | The updated `User` resource | Read-after-write: a subsequent `get` must reflect the new status (AIP-121). |

## Why a custom method, not `update`?

The skill's priority order (AIP-130) is: standard → batch → custom → streaming. Walking down it:

1. **Standard `update`?** Technically you could `PATCH /orgs/{org}/users/{user}` with `{ status: 'SUSPENDED' }`. But the operation isn't really "patch this field" — it has *side effects* (revoke sessions, send notification) that a partial update implies nothing about. AIP-121 and AIP-130 both call out one-shot state transitions with side effects (`:archive`, `:publish`, `:rotateKey`, `:revoke`, `:cancel`) as the canonical case for a custom method. Suspension is exactly that shape.
2. **Batch variant?** Not yet — you're suspending one user. If you later need bulk suspension, add `:batchSuspend` on the collection rather than overloading this one.
3. **Custom method.** Yes — `:suspend`, scoped to a single `User`.

So we land on a custom method, and the AIP-130 shape is fixed: `POST`, path is the resource name plus a `:verb` suffix.

## Resource name and path

Assuming your existing hierarchy is `Org` → `User` (the HR app's natural parent → child), the resource name pattern is:

```
orgs/{org}/users/{user}
```

That gives:

- Plural, camelCase collection identifiers (`orgs`, `users`) — AIP-122.
- One canonical parent for `User` — AIP-121.
- The same string used in `.route({ path })` *and* in the `name` field on the `User` schema — AIP-122.

The custom method's path is just that name with `:suspend` appended:

```
POST /orgs/{org}/users/{user}:suspend
```

If your existing API uses a flat `/users/{user}` (no `Org` parent in the URL), match the codebase — AIP-122 says the path and the `name` field are the same string, so deviating just for this one endpoint would be worse than staying consistent. Cite the codebase, not the AIP, when you do.

## Input shape

```ts
import { os } from '@orpc/server'
import * as z from 'zod'

// Per AIP-126: small, stable, no existing standard — enum is appropriate.
// _UNSPECIFIED sentinel as the zero value.
export const UserStatus = z.enum([
  'USER_STATUS_UNSPECIFIED',
  'ACTIVE',
  'SUSPENDED',
  'DEACTIVATED',
]).describe(
  'Lifecycle state of a User. Closed enum; new members would be a breaking change.',
)

export const User = z.object({
  name: z.string().describe(
    'Canonical resource name: "orgs/{org}/users/{user}". Server-assigned on create.',
  ),
  email: z.string().email(),
  displayName: z.string(),
  status: UserStatus,
  suspendedAt: z.string().datetime().nullable(),
  suspensionReason: z.string().nullable(),
  // …other HR fields
})

export const SuspendUserInput = z.object({
  // The canonical resource name — AIP-122. Not `userId` + `orgId`.
  name: z.string(),

  // Optional human-readable reason; stored on the resource and shown in audit
  // logs. Free-form string per AIP-126 (high-churn, no closed set).
  reason: z.string().max(500).optional(),

  // Whether to send the notification email. Defaults to true; expose the
  // switch so internal tools can suspend silently when needed.
  notify: z.boolean().optional(),

  // Optional optimistic-concurrency token. Returned by `get`; if the caller
  // supplies it and the resource has changed since, the server rejects with
  // ABORTED. Cheap to add now; expensive to retrofit later.
  etag: z.string().optional(),
})
```

A few things to call out:

- **`name`, not `{ orgId, userId }`.** AIP-122: the canonical identifier is the full resource name, one string. Splitting it into a tuple is exactly the anti-pattern resource names exist to prevent.
- **`reason` is a `string`, not an enum.** AIP-126: reasons churn (HR will keep adding new categories), and there's no existing standard. Document the *recommended* values in the field description instead of locking them in a closed set.
- **`notify` is a boolean.** Two values, no plausible third — a real boolean is the right call (AIP-126).
- **`etag` is optional but recommended.** Suspension is destructive-ish; a stale-write guard is cheap insurance.

## Output shape

Return the updated `User`. Read-after-write (AIP-121) demands that a subsequent `GET /orgs/{org}/users/{user}` reflect `status: 'SUSPENDED'` immediately, and returning the resource directly saves the caller a round-trip:

```ts
const suspendUser = os
  .route({
    method: 'POST',
    path: '/orgs/{org}/users/{user}:suspend',
    summary: 'Suspend a user account.',
    description: [
      'Sets status to SUSPENDED, revokes all active sessions, and (by default)',
      'sends a notification email. Idempotent: suspending an already-suspended',
      'user is a no-op that returns the current resource.',
    ].join(' '),
  })
  .input(SuspendUserInput)
  .output(User)
  .handler(async ({ input, context }) => {
    // 1. Load + authorize.
    const user = await context.users.getByName(input.name)
    if (input.etag && user.etag !== input.etag) {
      throw new ORPCError('ABORTED', { message: 'User has changed since read.' })
    }

    // 2. Idempotent short-circuit.
    if (user.status === 'SUSPENDED') return user

    // 3. Do the work atomically — AIP-121 strong consistency.
    const updated = await context.users.transact(async (tx) => {
      const next = await tx.users.update(input.name, {
        status: 'SUSPENDED',
        suspendedAt: new Date().toISOString(),
        suspensionReason: input.reason ?? null,
      })
      await tx.sessions.revokeAllFor(input.name)
      return next
    })

    // 4. Side effects that don't need to be in the transaction.
    if (input.notify ?? true) {
      await context.notifications.sendSuspensionEmail(updated)
    }

    return updated
  })
```

If revoking sessions or sending mail is slow enough that you don't want the client holding the connection, AIP-130 says to return an `Operation` resource the caller can poll instead. For an HR app suspending one user, synchronous is almost certainly fine — but it's worth knowing the escape hatch exists.

## Adding it to the router

Drop it next to the standard methods on `users`:

```ts
export const router = {
  orgs: {
    // …
    users: {
      list:    listUsers,
      get:     getUser,
      create:  createUser,
      update:  updateUser,
      delete:  deleteUser,
      suspend: suspendUser,   // ← here
      // future: unsuspend, resetPassword, rotateKey, …
    },
  },
}
```

Keep the symmetric `:unsuspend` (or `:reactivate`) in mind — pairs of state-transition custom methods are common, and you'll want consistent naming when the second one shows up.

## Summary of the rules cited

- **AIP-121** — Suspension is a one-shot state transition with side effects; that's a custom method, not `update`. Output the resource so read-after-write holds.
- **AIP-122** — One `name` string, not `{ orgId, userId }`. The path in `.route` *is* the resource name.
- **AIP-126** — `UserStatus` is a closed enum with a `_UNSPECIFIED` sentinel; `reason` stays a `string`; `notify` is a real boolean.
- **AIP-130** — Custom methods are `POST` with a `:verb` suffix, scoped to a resource. `suspend` is the verb.
