# Suspending a User Account in oRPC

Below is a recommendation for naming, HTTP shape, and the oRPC implementation of a "suspend user" operation in an internal HR app.

## TL;DR

- **Operation name**: `users.suspend`
- **HTTP method + path**: `POST /v1/users/{userId}:suspend`
- **Why**: This is a *state-changing custom action* on a single resource. It is not a CRUD update (it has side effects: revoking sessions and notifying the user), so a custom verb is the right call. The `resource:verb` pattern (popularized by Google AIP-136) is the idiomatic way to model custom actions on REST-style resources, and it composes cleanly with oRPC's OpenAPI generator.

---

## Naming rationale

A few options were considered:

| Option | Verdict |
|---|---|
| `PATCH /v1/users/{userId}` with `{ status: "SUSPENDED" }` | Rejected. Suspension has side effects (revoke sessions, send email). Hiding those in a generic update makes the API surprising and harder to authorize/audit. |
| `POST /v1/users/{userId}/suspend` | Acceptable, but conflates a sub-resource with an action. `:suspend` makes "this is a verb, not a resource" obvious. |
| `POST /v1/users/{userId}:suspend` | **Chosen.** Clearly a custom action; pairs naturally with `:unsuspend`, `:resetPassword`, etc. |
| `DELETE /v1/users/{userId}` | Wrong semantics — suspension is reversible; deletion implies removal. |

The oRPC procedure is named `users.suspend` (dot-namespaced under the `users` router), which gives clients a typed `client.users.suspend({...})` call.

---

## Input / Output shape

### Input

- `userId` (path param) — the user being suspended.
- `reason` (required) — short enum/string for audit (`POLICY_VIOLATION`, `OFFBOARDING`, `SECURITY`, `OTHER`).
- `note` (optional) — free-form admin note, stored on the audit record.
- `notifyUser` (optional, default `true`) — whether to send the notification email. Useful to skip for offboarding flows where HR sends a separate message.
- `effectiveAt` (optional) — ISO timestamp; defaults to "now". Allows scheduled suspension.

### Output

Return the updated `User` plus a small operation summary so the UI can confirm what happened without a follow-up read:

- `user` — the full updated `User` resource (status now `SUSPENDED`).
- `revokedSessionCount` — how many active sessions were killed.
- `notificationSent` — boolean.
- `suspendedAt` — server timestamp.

Returning the full resource follows the "actions return the mutated resource" convention and keeps clients cache-friendly.

---

## oRPC code

```ts
// contracts/users.ts
import { oc } from '@orpc/contract'
import { z } from 'zod'

// ---------- Shared schemas ----------

export const UserStatusSchema = z.enum([
  'ACTIVE',
  'SUSPENDED',
  'INVITED',
  'DEACTIVATED',
])

export const UserSchema = z.object({
  id: z.string(),
  orgId: z.string(),
  email: z.string().email(),
  displayName: z.string(),
  status: UserStatusSchema,
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
  suspendedAt: z.string().datetime().nullable(),
})

export const SuspendUserInputSchema = z.object({
  userId: z.string().min(1),
  reason: z.enum([
    'POLICY_VIOLATION',
    'OFFBOARDING',
    'SECURITY',
    'OTHER',
  ]),
  note: z.string().max(2_000).optional(),
  notifyUser: z.boolean().default(true),
  effectiveAt: z.string().datetime().optional(),
})

export const SuspendUserOutputSchema = z.object({
  user: UserSchema,
  revokedSessionCount: z.number().int().nonnegative(),
  notificationSent: z.boolean(),
  suspendedAt: z.string().datetime(),
})

// ---------- Contract ----------

export const usersContract = oc.router({
  suspend: oc
    .route({
      method: 'POST',
      path: '/v1/users/{userId}:suspend',
      summary: 'Suspend a user account',
      description:
        'Sets the user status to SUSPENDED, revokes all active sessions, ' +
        'and (unless notifyUser=false) sends a notification email. ' +
        'Idempotent: suspending an already-suspended user is a no-op that ' +
        'still returns the current state.',
      tags: ['Users'],
    })
    .input(SuspendUserInputSchema)
    .output(SuspendUserOutputSchema)
    .errors({
      NOT_FOUND: {
        message: 'User not found',
        data: z.object({ userId: z.string() }),
      },
      FORBIDDEN: {
        message: 'Caller may not suspend users in this org',
      },
      CONFLICT: {
        message: 'User is in a state that cannot be suspended',
        data: z.object({ currentStatus: UserStatusSchema }),
      },
    }),
})
```

### Server implementation

```ts
// server/users.ts
import { os } from '@orpc/server'
import { ORPCError } from '@orpc/client'
import { usersContract } from '../contracts/users'
import { authed } from './middleware/auth' // your auth middleware
import { db } from './db'
import { revokeAllSessions } from './sessions'
import { sendSuspensionEmail } from './notifications'

export const usersRouter = os
  .contract(usersContract)
  .router({
    suspend: authed
      .handler(async ({ input, context }) => {
        const { userId, reason, note, notifyUser, effectiveAt } = input

        // 1. Authorization: only org admins can suspend.
        if (!context.actor.permissions.includes('users:suspend')) {
          throw new ORPCError('FORBIDDEN')
        }

        // 2. Load + scope check.
        const user = await db.user.findUnique({ where: { id: userId } })
        if (!user || user.orgId !== context.actor.orgId) {
          throw new ORPCError('NOT_FOUND', { data: { userId } })
        }

        // 3. Idempotency: already suspended? Return current state.
        if (user.status === 'SUSPENDED') {
          return {
            user,
            revokedSessionCount: 0,
            notificationSent: false,
            suspendedAt: user.suspendedAt ?? new Date().toISOString(),
          }
        }

        if (user.status === 'DEACTIVATED') {
          throw new ORPCError('CONFLICT', {
            data: { currentStatus: user.status },
          })
        }

        const suspendedAt = effectiveAt ?? new Date().toISOString()

        // 4. Atomic mutation + audit log.
        const updated = await db.$transaction(async (tx) => {
          const u = await tx.user.update({
            where: { id: userId },
            data: { status: 'SUSPENDED', suspendedAt },
          })
          await tx.auditLog.create({
            data: {
              orgId: u.orgId,
              actorId: context.actor.id,
              action: 'user.suspend',
              targetId: u.id,
              metadata: { reason, note },
            },
          })
          return u
        })

        // 5. Side effects (best-effort, logged on failure).
        const revokedSessionCount = await revokeAllSessions(userId)
        let notificationSent = false
        if (notifyUser) {
          notificationSent = await sendSuspensionEmail(updated, { reason })
        }

        return {
          user: updated,
          revokedSessionCount,
          notificationSent,
          suspendedAt,
        }
      }),
  })
```

### Client usage

```ts
const result = await client.users.suspend({
  userId: 'usr_123',
  reason: 'POLICY_VIOLATION',
  note: 'Repeated violations of acceptable use policy.',
})

console.log(result.user.status) // 'SUSPENDED'
console.log(result.revokedSessionCount) // e.g. 3
```

---

## Design notes worth keeping

1. **Pair it with `users.unsuspend`** at `POST /v1/users/{userId}:unsuspend`. Same shape, no `notifyUser` default change.
2. **Idempotent** — re-suspending returns the existing state rather than 409. This makes retries safe.
3. **Audit log is part of the transaction**, not a side effect. Side effects (sessions, email) are intentionally outside the DB transaction so a flaky email provider can't roll back the suspension.
4. **Authorization lives in the handler**, but consider a dedicated `requirePermission('users:suspend')` middleware once you have more than two or three such verbs.
5. **No bulk variant yet** — if HR needs to suspend many users at once (e.g., offboarding a contractor agency), add `POST /v1/users:batchSuspend` with `{ userIds: string[], reason, ... }` returning per-user results. Don't overload the single-user endpoint.
