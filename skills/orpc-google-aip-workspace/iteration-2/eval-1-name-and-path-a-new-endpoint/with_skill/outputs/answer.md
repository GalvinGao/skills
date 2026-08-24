# Suspending a User — Endpoint Design

## Short answer

| Field        | Value                                                    |
| ------------ | -------------------------------------------------------- |
| Procedure    | `users.suspend`                                          |
| HTTP method  | `POST`                                                   |
| HTTP path    | `/orgs/{org}/users/{user}:suspend`                       |
| Input        | `{ org, user, reason?, notify? }`                        |
| Output       | The updated `User` resource                              |

This is a **custom method** rather than a standard one. The reasoning is below, followed by the oRPC code.

## Why not just `update`?

The first instinct under AIP-121 is to model nouns and reach for standard methods (`list`, `get`, `create`, `update`, `delete`) before inventing anything. So why not `PATCH /orgs/{org}/users/{user}` with `{ patch: { status: 'SUSPENDED' } }`?

Two reasons:

1. **The operation is more than a field write.** Suspending a user revokes active sessions and dispatches a notification. A `PATCH` on a `status` field looks like a pure state mutation; hiding the side effects there makes the API surface dishonest. Future readers (and code generators) have no way to know that flipping a string also kills sessions and sends mail.
2. **`PATCH` is partial-update by contract (AIP-130).** Any field can be patched independently. If `status` is patchable via `update`, then `{ status: 'ACTIVE' }` is also a valid request — i.e. you have implicitly defined `unsuspend` as a side-effect of a field write. That couples the two operations and removes your ability to give each one its own auth check, audit log, and notification policy.

State transitions with side effects are exactly what AIP-136 (custom methods) is for. The skill's rule 1 ("reach for standard methods first") is satisfied by considering and rejecting `update` for principled reasons, not skipped.

## Naming

- **Verb, not noun.** Custom methods are the one place in the API where a verb is appropriate, because they name an *operation* rather than a *resource*. `suspend` is the right English verb; don't dress it up as `setSuspended` or `changeStatus`.
- **Imperative, lowerCamelCase.** Matches the standard methods (`list`, `get`, `create`) so the router reads uniformly: `users.list`, `users.get`, `users.suspend`.
- **Pair with `unsuspend`** when you add the reverse operation. Don't reuse `update` for one direction and a custom method for the other.

## Path

The Google AIP convention is `POST /resource/{name}:customVerb` — the colon visually separates the resource name from the action performed on it, and `POST` is the safe default verb for anything non-idempotent that isn't a pure read.

For this app:

```
POST /orgs/{org}/users/{user}:suspend
```

A few decisions baked in:

- **`POST`, not `PATCH`.** `PATCH` is reserved for partial updates of the resource representation (AIP-130). Custom methods use `POST` because they aren't idempotent in general (re-suspending may re-send the notification or extend a suspension window — that's an operation-specific decision, but `POST` keeps the door open).
- **`{user}` is the user's id segment, not their full resource name.** The handler reconstructs `orgs/{org}/users/{user}` for use as the canonical `name` field on the resource (AIP-121).
- **`User` lives under `Org`.** Your description mentions both resources; per AIP-121, every resource has one canonical parent, and a User in an HR app belongs to an Org. If your existing routes already put `User` at the top level (`/users/{user}`), follow the codebase — the skill's guidance is to defer to established conventions and surface AIP as a suggestion, not a correction.
- **Colon, not slash, before `suspend`.** `/users/{user}/suspend` reads like a sub-resource and would imply `GET /users/{user}/suspend` returns a suspension object. The colon syntax makes it unambiguous that `suspend` is a verb, not a noun.

## Input

```ts
{
  org: string,           // path param — the parent Org's id
  user: string,          // path param — the User's id
  reason?: string,       // optional free-form reason, stored on the audit log
  notify?: boolean,      // default true — send the notification email
}
```

Notes:

- **Keep it minimal.** Custom methods take only the fields the operation needs; they are not a place to sneak in `patch`-style updates of unrelated fields.
- **`reason` is a documented `string`, not an enum** (AIP-126). Reasons for suspension are open-ended HR concerns and will churn over time; enumerating them would force a schema change every time HR invents a new category.
- **`notify` defaults to `true`.** The common case — a real suspension — should notify the user. The flag exists to let admin tools suspend silently during bulk operations.

## Output

Return the **updated `User` resource**. AIP-121 rule 3 (strong consistency after mutations) requires that a subsequent `get` reflect the new state — returning the resource directly lets the client skip that round-trip and guarantees its local cache matches the server.

The schema must be the same `User` shape used everywhere else (AIP-121 schema consistency). Do not invent a `SuspendUserResponse` with a subset of fields.

If session revocation or the notification dispatch could realistically take more than a couple of hundred milliseconds, do *not* return the user before that work completes — either do it synchronously, or return an `Operation` resource the client can poll (AIP-121). Returning success while sessions are still alive would violate read-after-write.

## Status as an enum

`User.status` is a small, stable, closed set, which is exactly the AIP-126 case for an enum:

```ts
export const UserStatus = z.enum([
  'USER_STATUS_UNSPECIFIED',  // sentinel; never a real state
  'ACTIVE',
  'SUSPENDED',
  'DEACTIVATED',
])
```

The `USER_STATUS_UNSPECIFIED` zero value is required by AIP-126 so clients can distinguish "the server didn't set this" from "the server explicitly set it to a real value".

## oRPC code

```ts
import { os } from '@orpc/server'
import * as z from 'zod'

// ---------- Resource schema (defined once, reused everywhere) ----------

export const UserStatus = z.enum([
  'USER_STATUS_UNSPECIFIED',
  'ACTIVE',
  'SUSPENDED',
  'DEACTIVATED',
])

export const User = z.object({
  name: z.string(),                           // "orgs/{org}/users/{user}"
  email: z.string().email(),
  displayName: z.string(),
  status: UserStatus,
  suspendedAt: z.string().datetime().nullable(),
  suspensionReason: z.string().nullable(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
})
export type User = z.infer<typeof User>

// ---------- suspend ----------

const SuspendUserInput = z.object({
  org: z.string(),
  user: z.string(),
  reason: z.string().max(500).optional()
    .describe('Optional free-form reason, stored on the audit log. No enumeration.'),
  notify: z.boolean().default(true)
    .describe('Send the user a notification email about the suspension. Default true.'),
})

export const suspendUser = os
  .route({
    method: 'POST',
    path: '/orgs/{org}/users/{user}:suspend',
    summary: 'Suspend a user account.',
    description:
      'Sets status to SUSPENDED, revokes all active sessions, and (by default) ' +
      'sends a notification email. Idempotent: suspending an already-suspended ' +
      'user is a no-op and does not re-send the notification.',
  })
  .input(SuspendUserInput)
  .output(User)
  .handler(async ({ input, context }) => {
    const name = `orgs/${input.org}/users/${input.user}`

    // 1. Flip status. Do this first so any concurrent session validation
    //    sees the user as suspended before we revoke.
    const user = await context.db.users.update({
      where: { name },
      data: {
        status: 'SUSPENDED',
        suspendedAt: new Date().toISOString(),
        suspensionReason: input.reason ?? null,
      },
    })

    // 2. Revoke active sessions synchronously — read-after-write requires
    //    that the user be unable to act by the time we return success.
    await context.sessions.revokeAllForUser(name)

    // 3. Notification. If this is slow or external, queue it; do not let
    //    a flaky email provider fail a suspension.
    if (input.notify) {
      await context.notifications.enqueue({
        kind: 'USER_SUSPENDED',
        userName: name,
        reason: input.reason ?? null,
      })
    }

    return user
  })

// ---------- Router placement ----------

export const router = {
  users: {
    list:    listUsers,
    get:     getUser,
    create:  createUser,
    update:  updateUser,
    delete:  deleteUser,
    suspend: suspendUser,   // custom method sits alongside the standard ones
    // unsuspend: ...        // add when you need the reverse
  },
}
```

## Cited rules

- **AIP-121** — model nouns, derive request shapes from the resource schema, guarantee read-after-write, every resource has one canonical parent.
- **AIP-126** — `UserStatus` is a closed enum with a `_UNSPECIFIED` zero value; `reason` is a documented `string` because it would churn.
- **AIP-130** — `PATCH` is reserved for partial update of the resource itself; custom (non-standard) methods use `POST` and the `:verb` path suffix.

## Caveats

- If your existing API already exposes `User` at `/users/{user}` rather than under an `Org` parent, **follow the codebase** — the skill explicitly says to defer to established conventions and surface AIP as a suggestion, not a correction.
- If `suspendedAt` / `suspensionReason` aren't currently fields on your `User` schema, decide whether to add them (so `get` reflects the suspension state without an extra call) or store them on a separate `Suspension` audit resource. The schema-consistency rule then applies to whichever choice you make.
