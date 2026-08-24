# API design review: `users` router

Reviewed against Google AIP-121 (resource-oriented design), AIP-126 (enumerations), and AIP-130 (methods). The router has correct intent — five operations on a `User` resource — but it violates almost every standard-method convention. Most of the fixes are mechanical.

---

## 1. Verb-shaped procedure names instead of resource-oriented method names

**Violation:** AIP-121 — *model nouns, not verbs.* Standard methods are `list`, `get`, `create`, `update`, `delete`, hung off a resource collection.

The current names — `getUser`, `listAllUsers`, `createNewUser`, `updateUserData` — bake the noun into each procedure name and use redundant qualifiers (`All`, `New`, `Data`). AIP-130's canonical router groups the standard methods under the resource:

```ts
router = { users: { list, get, create, update, delete } }
```

That structure reads identically to every other resource in the API, generates clean OpenAPI operation IDs (`users.list`, `users.get`), and removes the noise words. Also: `listAllUsers` is misleading — it doesn't actually return all users, it pages them (`offset` + `limit`). The name promises something the implementation can't deliver.

**Change:** rename and regroup as `users.list`, `users.get`, `users.create`, `users.update` (plus a missing `users.delete` — see §5).

---

## 2. HTTP verbs and paths violate the standard-method matrix

**Violation:** AIP-130 — *the standard-method matrix.*

| Procedure       | Current                  | Should be (AIP-130)         |
| --------------- | ------------------------ | --------------------------- |
| `getUser`       | `GET /get-user`          | `GET /users/{user}`         |
| `listAllUsers`  | `POST /list-users`       | `GET /users`                |
| `createNewUser` | `PUT /user/new`          | `POST /users`               |
| `updateUserData`| `PUT /user/update`       | `PATCH /users/{user}`       |

Specific problems:

- **`list` is `POST`.** AIP-130 explicitly calls this out: "Using `POST` for a read breaks HTTP caching, breaks intermediary idempotency assumptions, and signals 'this has side effects' to anyone reading the route." Must be `GET`.
- **`create` is `PUT`.** `POST` to the collection is the convention; the server assigns identity. `PUT` implies the client knows the target URL.
- **`update` is `PUT`, not `PATCH`.** AIP-130 again: "A full-replace `PUT` is almost never what callers want — it forces them to read the current resource, merge their change, and write the whole thing back, and racing writers clobber each other's fields." This is a real correctness problem, not just style. With `PUT`-replace semantics, two concurrent updates to different fields will silently overwrite each other.
- **Verb-in-path (`/get-user`, `/list-users`, `/user/new`, `/user/update`).** The path should be a resource name. The HTTP method is the verb.
- **Singular vs plural inconsistency.** `/list-users` (plural) but `/user/new` and `/user/update` (singular). AIP-130 paths use the collection name (plural) consistently.

---

## 3. Resource hierarchy is missing

**Violation:** AIP-121 — *one canonical parent.*

`User.workspace` is a writable nested object. Every input also carries `workspaceId`. This is a strong signal that `User` lives under `Workspace` and the API should reflect that hierarchy:

```
/workspaces/{workspace}/users
/workspaces/{workspace}/users/{user}
```

The parent moves out of the body and into the path, which:

- removes the ability to send a `workspaceId` that disagrees with the user's actual workspace (currently possible),
- makes the URL stable and bookmarkable per AIP-121's "stateless interactions" principle,
- gives you a place to scope authz cleanly (`canRead(workspace)` before the handler runs).

`User.workspace` then becomes either a) gone from the resource (the parent is implicit in `name`), or b) an output-only computed `workspaceName: string` reference. Keeping a writable nested `Workspace` object inside `User` would also break AIP-121's DAG rule the moment `Workspace` needs to reference its `User`s.

---

## 4. Schema drift between read and write

**Violation:** AIP-121 — *schema consistency across methods.*

`create` and `update` both take the full `User` schema as input, including `id`:

- For `create`, the client should not supply `id` — the server assigns it. `User` should expose a `name: string` (e.g. `workspaces/42/users/7`) and `create` should accept `User.omit({ name: true })`.
- For `update`, every mutable field should be optional so the client sends only what changes. AIP-130's PATCH example uses `User.partial().omit({ name: true })`. Currently a partial update is impossible — the schema forces the client to send the entire user.
- `role` is writable on `create`, which is almost certainly wrong from a security standpoint (anyone can create themselves as `admin`). Either remove from `create` input or make it an explicit, separately-authorized field.

Hand-writing `User` once and reusing it for both create-input, update-input, and get-output is exactly the drift AIP-121 warns about. Derive with `.omit` / `.partial` from a single source of truth.

---

## 5. Missing `delete`

**Violation:** AIP-121/130 — *every resource should support the standard methods unless there's a reason not to.*

There's no `users.delete`. If users genuinely can't be deleted, document that as a deliberate decision. Otherwise add it:

```ts
delete: os
  .route({ method: 'DELETE', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({ workspace: z.string(), user: z.string() }))
  .output(z.void())
```

---

## 6. Pagination uses `offset`/`limit` instead of `limit`/`cursor`

**Violation:** AIP-130 — *cursor pagination.*

`offset`/`limit` is slow on large tables (the database still scans the skipped rows) and inconsistent under concurrent writes (a row inserted between page 1 and page 2 is either skipped or duplicated). Cursors survive both.

Also: `limit` has no upper bound. A client can ask for `limit: 100000` today. Per AIP-130, "`limit` should have a hard upper bound enforced by the schema (e.g. `.max(100)`); otherwise clients will ask for ten thousand and your database will hate you."

The `list` response is also a bare `z.array(User)` with no envelope, so there's no place to return `nextCursor`. The envelope is required for pagination to work at all.

---

## 7. `role` enum is missing the `_UNSPECIFIED` sentinel and isn't in `UPPER_SNAKE_CASE`

**Violation:** AIP-126 — *enum naming and the zero-value convention.*

```ts
role: z.enum(['admin', 'user', 'guest'])
```

Two issues:

- **Lowercase.** AIP-126 mandates `UPPER_SNAKE_CASE` for every member.
- **No zero-value sentinel.** The first member should be `ROLE_UNSPECIFIED` so clients can distinguish "the server didn't set this" from a real role. Without it, a default-initialized field can't be detected as unset.
- **`user` is a bad member name** because the enum lives on a resource also called `User`. Rename to `MEMBER` or `STANDARD` to avoid the collision.
- **Documentation.** Note whether the enum is closed (we don't expect new roles) or open (clients must tolerate unknown values).

```ts
role: z
  .enum(['ROLE_UNSPECIFIED', 'ADMIN', 'MEMBER', 'GUEST'])
  .describe('Open enum. Clients must tolerate unknown values and treat them as ROLE_UNSPECIFIED.')
```

If roles change more than ~once a year (common in early-stage products), drop the enum entirely and use a documented `string` per AIP-126's churn rule.

---

## 8. Resource identity uses an opaque integer instead of a hierarchical name

**Violation:** AIP-121 — *resources have a name.*

`User.id: number` works at the database layer but isn't what AIP-121 expects on the wire. The canonical identifier is a `name: string` carrying the full hierarchical path: `workspaces/{workspace}/users/{user}`. Benefits:

- one field uniquely identifies the resource across the whole API,
- it's URL-safe and copy-pasteable into a path,
- it tells the reader where the resource lives (under which workspace),
- it lets you change the underlying primary key (e.g. `int` → `uuid`) without breaking the contract.

Keep the integer `id` server-side if you want; the wire format should be `name`.

---

## Corrected router

```ts
import { os } from '@orpc/server'
import * as z from 'zod'

// ---------- Resource ----------

const Role = z
  .enum(['ROLE_UNSPECIFIED', 'ADMIN', 'MEMBER', 'GUEST'])
  .describe('Open enum (AIP-126). Clients must tolerate unknown values and treat them as ROLE_UNSPECIFIED.')

// Canonical User resource. Used as the response shape everywhere it appears
// (AIP-121: schema consistency).
const User = z.object({
  // Resource name: "workspaces/{workspace}/users/{user}"
  name: z.string(),
  email: z.string().email(),
  role: Role,
})

// ---------- Pagination (AIP-130) ----------

const PageInput = z.object({
  limit: z.coerce.number().int().min(1).max(100).optional(),
  cursor: z.string().optional(),
})

// ---------- Procedures ----------

const listUsers = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/users' })
  .input(PageInput.extend({ workspace: z.string() }))
  .output(z.object({
    users: z.array(User),
    nextCursor: z.string().optional(),
  }))
  .handler(async () => ({ users: [], nextCursor: undefined }))

const getUser = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({ workspace: z.string(), user: z.string() }))
  .output(User)
  .handler(async () => ({} as any))

const createUser = os
  .route({ method: 'POST', path: '/workspaces/{workspace}/users' })
  .input(z.object({
    workspace: z.string(),
    // Server assigns `name`; `role` is privileged and typically excluded here.
    user: User.omit({ name: true, role: true }),
  }))
  .output(User)
  .handler(async () => ({} as any))

const updateUser = os
  .route({ method: 'PATCH', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({
    workspace: z.string(),
    user: z.string(),
    // PATCH semantics (AIP-130): every mutable field is optional. Omitted
    // fields are left untouched.
    patch: User.partial().omit({ name: true }),
  }))
  .output(User)
  .handler(async () => ({} as any))

const deleteUser = os
  .route({ method: 'DELETE', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({ workspace: z.string(), user: z.string() }))
  .output(z.void())
  .handler(async () => undefined)

// ---------- Router ----------

export const router = {
  users: {
    list:   listUsers,
    get:    getUser,
    create: createUser,
    update: updateUser,
    delete: deleteUser,
  },
}
```

---

## Summary of changes (and the AIP behind each)

| # | Change                                                             | AIP             |
| - | ------------------------------------------------------------------ | --------------- |
| 1 | Rename to standard methods grouped under `users.*`                 | AIP-121, AIP-130|
| 2 | Fix HTTP verbs: `list`=GET, `create`=POST, `update`=PATCH          | AIP-130         |
| 3 | Move `workspaceId` from body to path; nest under `/workspaces/{}`  | AIP-121         |
| 4 | Derive create/update inputs via `.omit` and `.partial`             | AIP-121         |
| 5 | Add `users.delete`                                                 | AIP-121, AIP-130|
| 6 | Replace `offset`/`limit` with `limit`/`cursor`; add response envelope; cap `limit` | AIP-130 |
| 7 | Reshape `role` enum: `UPPER_SNAKE_CASE` + `ROLE_UNSPECIFIED` sentinel + describe openness | AIP-126 |
| 8 | Replace integer `id` with hierarchical `name: string`              | AIP-121         |

The cumulative effect: a router that reads identically to every other resource in the system, generates clean OpenAPI, and won't have its update semantics silently clobber concurrent writes.
