# Review: oRPC `User` router vs. Google AIP conventions

The router gets the broad strokes right (one resource, contract-first Zod
schema, oRPC `.route()` describing the HTTP surface) but it deviates from
the Google AIPs in ways that will hurt as the API grows: verb-shaped
method names, ad-hoc paths, wrong HTTP verbs, schema drift between
`create`/`update`/`get`, an offset-based pager, an `id`-instead-of-`name`
identifier, an embedded parent resource, and an enum that is missing the
`_UNSPECIFIED` zero value. Below is each problem, the AIP that drives the
fix, and a corrected router at the end.

---

## 1. Method names are verb-shaped instead of resource-shaped

`getUser`, `listAllUsers`, `createNewUser`, `updateUserData` are
procedure-style names with redundant verbs (`All`, `New`, `Data`) baked
into them. The skill's rule #1 is "model nouns, not verbs," and AIP-130
says the standard vocabulary is exactly `list / get / create / update /
delete` — no embellishments.

In an oRPC router this is naturally expressed by grouping the procedures
under a `users` namespace and using the bare standard-method names:

```ts
export const router = {
  users: {
    list:   listUsers,
    get:    getUser,
    create: createUser,
    update: updateUser,
    // delete is missing — see §3
  },
}
```

**Why it matters:** standard names need zero documentation. `listAllUsers`
raises questions ("is there a `listSomeUsers`?") that `users.list` does
not. (AIP-121, AIP-130)

---

## 2. Paths are ad-hoc instead of resource-name-shaped

Current paths:

```
GET  /get-user
POST /list-users
PUT  /user/new
PUT  /user/update
```

AIP-122 says the path in `.route({ path })` *is* the resource name and
must alternate `plural-collection / id`. None of these do that:

| Current path     | Problem                                                                  |
| ---------------- | ------------------------------------------------------------------------ |
| `/get-user`      | Verb in the path; not a resource name; collides with method choice.      |
| `/list-users`    | Verb in the path; should be `GET /users` (or under a parent).            |
| `/user/new`      | Singular collection (`user`); `new` is a verb segment.                   |
| `/user/update`   | Same — singular, and `update` should be expressed by the HTTP verb.      |

The canonical paths (with the workspace parent — see §4) are:

```
GET    /workspaces/{workspace}/users
GET    /workspaces/{workspace}/users/{user}
POST   /workspaces/{workspace}/users
PATCH  /workspaces/{workspace}/users/{user}
DELETE /workspaces/{workspace}/users/{user}
```

Collection segments are **plural, camelCase, concise** (`users`,
`workspaces`) per AIP-122. The resource ID slot uses the singular
(`{user}`, `{workspace}`) per AIP-123.

---

## 3. Wrong HTTP verbs

| Procedure         | Current verb | Correct verb | AIP        |
| ----------------- | ------------ | ------------ | ---------- |
| `listAllUsers`    | `POST`       | `GET`        | AIP-130    |
| `createNewUser`   | `PUT`        | `POST`       | AIP-130    |
| `updateUserData`  | `PUT`        | `PATCH`      | AIP-130    |

Two specific points:

- **`list` must be `GET`.** `POST` for a read implies side-effects, breaks
  HTTP caching, and prevents intermediaries from treating it as
  idempotent. (AIP-130)
- **Update is `PATCH`, not `PUT`.** AIP-130 is explicit: "Update is
  partial. A full-replace `PUT` is almost never what callers want and
  forces them to read-modify-write." The current `updateUserData` takes
  the whole `User` schema, which is the classic `PUT` anti-pattern.
  Switching to `PATCH` + an `updateMask` (see §6) makes "leave this
  field alone" unambiguous.

Also, **`delete` is missing entirely.** AIP-121 says "every resource must
support `get`" and almost always `list`, `create`, `update`, and
`delete` — the omission should be deliberate, not accidental. Add a
`DELETE /workspaces/{workspace}/users/{user}` unless there is a real
reason users can't be removed.

---

## 4. The parent-child hierarchy is wrong way round

The `User` schema embeds the workspace as a property:

```ts
workspace: z.object({ id: z.number().int(), name: z.string() }),
```

And `getUser` takes both `userId` and `workspaceId` as flat fields. That
inverts the AIP-122 model in two ways:

**a) Embedding a referenced resource.** AIP-122 ("References between
resources") says you reference another resource **by name (a string)**,
not by embedding the whole object. Embedding creates dangling copies on
delete, bypasses per-resource permissions, and couples schemas. The
field should be:

```ts
workspace: z.string()   // "workspaces/{workspace}"
```

**b) Missing hierarchical path.** A user lives under exactly one workspace
(its "canonical parent" per AIP-121), so the resource name should
encode that:

```
workspaces/{workspace}/users/{user}
```

This eliminates the awkward `(userId, workspaceId)` tuple in
`getUser`'s input — AIP-122 explicitly calls that tuple an
"anti-pattern resource names exist to prevent." The path parameters
*are* the parent and ID.

If users genuinely belong to multiple workspaces (membership) then the
resource isn't `User` at all — it's `WorkspaceMember`, with `users` as
a top-level collection and `WorkspaceMember` linking the two by name.
That's a bigger refactor; flag it with the product team.

---

## 5. Identifier is `id: number` instead of `name: string`

AIP-122 is emphatic: the canonical identifier is `name`, a string
containing the full hierarchical path:

```ts
name: z.string()  // "workspaces/{workspace}/users/{user}"
```

Reasons not to use a bare `id: number`:

- A 64-bit integer can't encode the parent, so callers have to assemble
  paths client-side — the exact thing resource names prevent.
- `id` is industry shorthand for "local primary key", which clients then
  treat as the canonical identifier.
- Cross-service references (AIP-122 "Full resource names") need a string
  anyway.

If the database really does use a numeric PK, expose it as an optional
`uid` (read-only, documented) per AIP-122 — but the `name` field is the
contract.

---

## 6. `update` accepts the full resource

`updateUserData` takes the entire `User` and returns the entire `User`.
Two problems:

- It implies `PUT` semantics (full replace) — see §3.
- There is no `updateMask`, so a missing field is ambiguous between
  "clear it" and "leave it alone." AIP-130 calls this out specifically.

The corrected input derives from `User` (rule #3 — "schema consistency,"
AIP-121) instead of being re-declared:

```ts
input: z.object({
  workspace: z.string(),
  user: z.string(),
  patch: User.partial().omit({ name: true, workspace: true }),
  updateMask: z.array(z.string()).optional(),
})
```

`name` and `workspace` are omitted because they're identifier fields,
not mutable state.

---

## 7. `create` accepts the full resource (including server-assigned fields)

`createNewUser` takes the whole `User` including `id`/`name`. AIP-121's
example is explicit: the client sends the resource **without** the
server-assigned name, and may optionally suggest an ID:

```ts
input: z.object({
  workspace: z.string(),                      // parent
  userId: ResourceIdSchema.optional(),        // client may suggest; server may override
  user: User.omit({ name: true }),
})
```

`ResourceIdSchema` is the AIP-122 pattern
(`^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$`). If your server always generates
IDs, drop the `userId` field entirely (AIP-130).

---

## 8. Pagination uses `offset` + `limit` instead of `pageSize` + `pageToken`

`listAllUsers` takes `{ offset, limit }`. AIP-130 specifically calls
this out: "`pageSize` + `pageToken` for pagination (not `offset` +
`limit`). Cursors survive insertions and deletions cleanly; offsets do
not." With offset paging, a user created between page 1 and page 2 will
either be skipped or duplicated.

```ts
input: z.object({
  workspace: z.string(),                                   // parent
  pageSize: z.coerce.number().int().min(1).max(100).optional(),
  pageToken: z.string().optional(),
})
output: z.object({
  users: z.array(User),
  nextPageToken: z.string().optional(),
})
```

The output is also wrapped (`{ users, nextPageToken }`) — a bare
`z.array(User)` has no place for the cursor. (AIP-130)

---

## 9. The `role` enum is missing `ROLE_UNSPECIFIED`

```ts
role: z.enum(['admin', 'user', 'guest'])
```

Two AIP-126 violations:

- Members must be **UPPER_SNAKE_CASE**: `ADMIN`, `USER`, `GUEST`.
- The first member must be the `_UNSPECIFIED` sentinel so clients can
  distinguish "server didn't set this" from "server said GUEST".

Also note `USER` collides with the resource name. Prefixing every
member with the enum name is the AIP-126 fix for package-level enums:

```ts
role: z.enum([
  'USER_ROLE_UNSPECIFIED',
  'USER_ROLE_ADMIN',
  'USER_ROLE_MEMBER',     // 'USER' is too generic; rename to MEMBER
  'USER_ROLE_GUEST',
])
.describe('Role of the user within the workspace. Closed enum.')
```

Mark it as a **closed** or **open** enum in the description so clients
know whether to tolerate unknown values.

---

## 10. `email` should be documented, not validated as RFC-5322

Minor, but worth noting: `z.string().email()` rejects valid addresses
(plus-aliases in some encodings, IDN, quoted locals) and accepts
invalid ones. Best practice per AIP-126's "fall back to string" advice:
constrain loosely and document the canonical form:

```ts
email: z.string().min(3).max(254)
  .describe('Email address (RFC 5321 mailbox). Server normalizes to lowercase.')
```

---

## 11. Missing: resource type declaration (AIP-123)

Once the API spans more than one service (or feeds an audit logger /
webhook router / permission checker), AIP-123 wants:

```ts
export const UserType    = 'auth.example.com/User'    as const
export const UserPattern = 'workspaces/{workspace}/users/{user}' as const
```

For a single-service app this is optional — but declaring `Type` and
`Pattern` is cheap and keeps the door open.

---

## Corrected router

```ts
import { os } from '@orpc/server'
import * as z from 'zod'

// ── Shared schemas ───────────────────────────────────────────────────────

const ResourceIdSchema = z
  .string()
  .min(1)
  .max(63)
  .regex(/^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$/)
  .describe('Resource ID. Lowercase, hyphens, 1–63 chars (AIP-122).')

const PageInput = z.object({
  pageSize: z.coerce.number().int().min(1).max(100).optional(),
  pageToken: z.string().optional(),
})

// ── User resource (AIP-121, AIP-122, AIP-123) ───────────────────────────

export const UserType    = 'auth.example.com/User' as const
export const UserPattern = 'workspaces/{workspace}/users/{user}' as const

export const UserRole = z
  .enum([
    'USER_ROLE_UNSPECIFIED',
    'USER_ROLE_ADMIN',
    'USER_ROLE_MEMBER',
    'USER_ROLE_GUEST',
  ])
  .describe('Role of the user within the workspace. Closed enum (AIP-126).')

export const User = z.object({
  name: z.string()
    .describe(`Resource name. Type: ${UserType}. Pattern: ${UserPattern}. Server-assigned on create.`),
  workspace: z.string()
    .describe('Parent workspace resource name, e.g. "workspaces/acme" (AIP-122).'),
  email: z.string().min(3).max(254)
    .describe('Email address (RFC 5321 mailbox). Server normalizes to lowercase.'),
  role: UserRole,
})
export type User = z.infer<typeof User>

// ── Procedures (AIP-130) ────────────────────────────────────────────────

const listUsers = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/users' })
  .input(PageInput.extend({ workspace: z.string() }))
  .output(z.object({
    users: z.array(User),
    nextPageToken: z.string().optional(),
  }))
  .handler(async () => ({ users: [], nextPageToken: undefined }))

const getUser = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({ workspace: z.string(), user: z.string() }))
  .output(User)
  .handler(async () => ({} as User))

const createUser = os
  .route({ method: 'POST', path: '/workspaces/{workspace}/users' })
  .input(z.object({
    workspace: z.string(),                          // parent
    userId: ResourceIdSchema.optional(),            // client may suggest
    user: User.omit({ name: true, workspace: true }),
  }))
  .output(User)
  .handler(async () => ({} as User))

const updateUser = os
  .route({ method: 'PATCH', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({
    workspace: z.string(),
    user: z.string(),
    patch: User.partial().omit({ name: true, workspace: true }),
    updateMask: z.array(z.string()).optional()
      .describe('Field paths to update. Omitted = full patch (AIP-130).'),
  }))
  .output(User)
  .handler(async () => ({} as User))

const deleteUser = os
  .route({ method: 'DELETE', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({ workspace: z.string(), user: z.string() }))
  .output(z.void())
  .handler(async () => {})

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

## Summary of changes

| # | Change                                                             | AIP             |
| - | ------------------------------------------------------------------ | --------------- |
| 1 | Rename to standard methods: `list/get/create/update/delete`        | AIP-121, AIP-130|
| 2 | Replace ad-hoc paths with hierarchical resource paths              | AIP-122         |
| 3 | Fix HTTP verbs: `list`→`GET`, `create`→`POST`, `update`→`PATCH`    | AIP-130         |
| 4 | Add the missing `delete` standard method                           | AIP-121         |
| 5 | Reference `workspace` by name (string), don't embed it             | AIP-122         |
| 6 | Replace `id: number` with `name: string` resource-name             | AIP-122         |
| 7 | Derive `create`/`update` inputs from `User` via `omit/partial`     | AIP-121         |
| 8 | Add `updateMask` to `update`                                       | AIP-130         |
| 9 | Replace `offset`/`limit` with `pageSize`/`pageToken` + cursor      | AIP-130         |
| 10| Wrap list output: `{ users, nextPageToken }`                       | AIP-130         |
| 11| Rename enum members to `UPPER_SNAKE_CASE`, add `_UNSPECIFIED`      | AIP-126         |
| 12| Prefix enum members (`USER_ROLE_…`); rename `USER` → `MEMBER`      | AIP-126         |
| 13| Loosen `email` validation, document the canonical form             | AIP-126         |
| 14| Declare `UserType` and `UserPattern` constants                     | AIP-123         |
