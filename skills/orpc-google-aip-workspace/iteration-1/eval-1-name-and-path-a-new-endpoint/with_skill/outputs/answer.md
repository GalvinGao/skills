# Suspending a `User`: name, verb, path, and shape

## Recommendation at a glance

| Decision           | Value                                                        | Why                                               |
| ------------------ | ------------------------------------------------------------ | ------------------------------------------------- |
| Endpoint name      | `suspend` (custom method on a `User`)                        | AIP-130, AIP-121                                  |
| HTTP method        | `POST`                                                       | AIP-130 (all custom methods are `POST`)           |
| Path               | `/organizations/{organization}/users/{user}:suspend`         | AIP-122 (hierarchical, plural, camelCase)         |
| Router placement   | `users.suspend` (sibling of `get`, `update`, `delete`)       | AIP-121, AIP-130                                  |
| Input              | `{ name, reason?, notify?, etag? }`                          | AIP-121 (resource-name-addressed), AIP-130        |
| Output             | The updated `User` resource                                  | AIP-121 (schema consistency + read-after-write)   |

## Why a custom `:suspend` method instead of `update`

Walking AIP-130's priority order:

1. **Standard methods first.** Could this be modelled as `users.update` with `state: 'SUSPENDED'`? Technically yes — but the operation isn't just a field flip. It also revokes sessions and emits a notification. Those side effects aren't visible from a `PATCH /users/{user}` with a partial body; a caller seeing the patch wouldn't know that touching `state` cascades. AIP-121 calls this out directly: a custom method is justified when the operation "genuinely doesn't map to CRUD" — `:archive`, `:publish`, `:rotateKey`, `:retry` are the canonical examples, and `:suspend` is the same shape (a one-shot state transition with security side effects).
2. **Batch / aggregate?** Not applicable — single resource.
3. **Custom method `:verb`?** Yes. This is the right tier.

So: a custom method on the `User` resource, named with an imperative verb (`suspend`), camelCase, scoped to one resource (AIP-130).

## Why this path

Per AIP-122:

- The resource name *is* the route path. A `User` lives under its `Org`, so the canonical name is `organizations/{organization}/users/{user}` — hierarchical, plural collection segments, camelCase, alternating `collection/id`.
- Custom methods append `:verb` to the resource path (AIP-130). Hence `/organizations/{organization}/users/{user}:suspend`.
- HTTP verb is `POST` — not a made-up verb, not `PATCH`. The `:suspend` suffix is the only signal that this is a custom method (AIP-130).

A couple of small calls worth flagging:

- I assumed your parent collection is `organizations` (the typical HR-app shape). If your existing routes already use `orgs/{org}` or a flat `users/{user}` namespace, follow the codebase — AIP-122 is a convention, and consistency with existing routes wins. The skill explicitly says: "When a rule and the user's existing codebase conflict, follow the codebase."
- `users/me` and similar aliases (AIP-122) should **not** be accepted by `:suspend`; the canonical name is required so audit logs and notifications are unambiguous.

## Why this input/output shape

**Input** is addressed by the canonical resource name plus operation-specific fields:

- `name: string` — the full resource name (`organizations/{organization}/users/{user}`). This is the AIP-122 convention: every operation addresses its resource by `name`, not by a `{ orgId, userId }` tuple. oRPC's path params bind to the same string.
- `reason?: string` — free-form audit context. Optional; defaults to none. Captured in the audit log alongside the actor.
- `notify?: boolean` — lets callers opt out of the user-facing email (e.g. when suspension is part of an offboarding workflow that sends its own notice). Defaults to `true` so the default behavior matches the verb's stated contract.
- `etag?: string` — optimistic concurrency. Prevents racing two suspensions, or suspending a user whose record was just edited. Standard AIP idiom; safe to omit if you don't use etags elsewhere.

**Output** is the updated `User` resource. Per AIP-121:

- **Schema consistency:** the `User` returned here has the same shape as `users.get` and `users.update` return. Use one `User` schema and derive the others — do not hand-write a `SuspendUserResponse`.
- **Read-after-write:** by the time the call returns OK, `users.get` must see `state: 'SUSPENDED'` and the sessions must already be revoked. If session revocation is genuinely async (e.g. a fan-out across regions), return an `Operation` resource the client can poll instead — but synchronous within the suspend handler is much simpler and almost always correct for an internal HR app.

For the `state` field itself: per AIP-126, model it as a small Zod literal union in UPPER_SNAKE_CASE with an `_UNSPECIFIED` zero value.

## The oRPC code

```ts
import { os } from '@orpc/server'
import * as z from 'zod'

// --- Canonical User resource schema (lives wherever you keep User today) ----

export const UserState = z.enum([
  'USER_STATE_UNSPECIFIED', // AIP-126: zero-value sentinel
  'ACTIVE',
  'SUSPENDED',
  'DEACTIVATED',
])

export const User = z.object({
  // AIP-122: full hierarchical resource name. "organizations/{org}/users/{user}".
  name: z.string().describe('Canonical resource name. Server-assigned on create.'),
  displayName: z.string(),
  email: z.string().email(),
  state: UserState,
  suspendedAt: z.string().datetime().nullable(),
  suspensionReason: z.string().nullable(),
  etag: z.string().optional(),
  // ...other fields
})
export type User = z.infer<typeof User>

// --- Suspend input/output --------------------------------------------------

const SuspendUserInput = z.object({
  // AIP-122: resource name, not a (orgId, userId) tuple.
  // Bound to the path params {organization} and {user}; oRPC will compose
  // the full name from the route, but we also accept it explicitly so
  // batch / server-to-server callers can use the canonical form.
  organization: z.string(),
  user: z.string(),

  // AIP-130: custom-method-specific fields live alongside the resource name.
  reason: z.string().max(500).optional(),
  notify: z.boolean().default(true),
  etag: z.string().optional(),
})

// AIP-121: output is the same User schema returned by get/update.
const SuspendUserOutput = User

// --- The procedure ---------------------------------------------------------

export const suspendUser = os
  .route({
    // AIP-130: custom methods are POST + ":verb" suffix on the resource path.
    method: 'POST',
    path: '/organizations/{organization}/users/{user}:suspend',
    summary: 'Suspend a user account',
    description:
      'Sets the user state to SUSPENDED, revokes all active sessions, and ' +
      '(unless notify=false) emails the user. After this returns OK, a ' +
      'subsequent users.get is guaranteed to observe state=SUSPENDED and ' +
      'no valid sessions (AIP-121 read-after-write).',
  })
  .input(SuspendUserInput)
  .output(SuspendUserOutput)
  .handler(async ({ input, context }) => {
    const name = `organizations/${input.organization}/users/${input.user}`

    // All three side-effects happen inside one transactional unit so that
    // read-after-write holds (AIP-121). If any step fails, the whole
    // operation fails and state is unchanged.
    const updated = await context.db.transaction(async (tx) => {
      const user = await tx.users.findByNameForUpdate(name)
      if (!user) throw new ORPCError('NOT_FOUND', { message: `${name} not found` })
      if (input.etag && user.etag !== input.etag) {
        throw new ORPCError('ABORTED', { message: 'etag mismatch' })
      }
      if (user.state === 'SUSPENDED') return user // idempotent

      const next = await tx.users.update(name, {
        state: 'SUSPENDED',
        suspendedAt: new Date().toISOString(),
        suspensionReason: input.reason ?? null,
      })
      await tx.sessions.revokeAllFor(name, { reason: 'user_suspended' })
      await tx.auditLog.record({
        action: 'users.suspend',
        target: name,
        actor: context.actor.name,
        reason: input.reason,
      })
      return next
    })

    if (input.notify) {
      // Outside the txn so a transient mailer failure doesn't roll back the
      // suspension. Notifier is itself idempotent + retried.
      await context.notifier.userSuspended(updated, { reason: input.reason })
    }

    return updated
  })

// --- Router placement ------------------------------------------------------

export const usersRouter = {
  list:    listUsers,
  get:     getUser,
  create:  createUser,
  update:  updateUser,
  delete:  deleteUser,
  suspend: suspendUser, // AIP-130: custom method sits next to standard ones.
  // If you later add the inverse: reinstate / unsuspend (AIP-136 pairs verbs).
}
```

## Things to consider next

- **Inverse operation.** If a suspended user can come back, add `users.reinstate` (or `unsuspend`) as a paired custom method (`POST /…/users/{user}:reinstate`). Keeping the pair symmetrical is an AIP-136 instinct.
- **State enum vs boolean.** A `suspended: boolean` would be simpler, but per AIP-126 a small, stable, semantically-rich set (`ACTIVE` / `SUSPENDED` / `DEACTIVATED`) is the better long-term shape — you'll likely want a third state eventually and won't want to add a second boolean.
- **Bulk suspension.** If admins ever need to suspend many users at once (offboarding a whole team), the AIP-130 progression says: don't add `?ids=` to the single-resource endpoint; add a batch custom method `POST /organizations/{organization}/users:batchSuspend` instead.
- **Long-running variant.** If session revocation fans out across regions and might take > a few seconds, return an `Operation` resource (AIP-130's long-running pattern) rather than blocking the request.
