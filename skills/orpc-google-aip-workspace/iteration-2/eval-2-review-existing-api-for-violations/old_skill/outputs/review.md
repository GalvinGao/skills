# Review: oRPC Router for `User` under `Workspace`

This router mostly works at the language level but it violates almost every Google AIP convention that oRPC inherits. Below is a per-procedure breakdown, then a corrected version of the router.

## Headline issues

1. **Procedure names are verbs, not resources.** `getUser`, `listAllUsers`, `createNewUser`, `updateUserData` are procedure-style names. The standard methods are `list / get / create / update / delete`, scoped under a resource collection. Each procedure should live on a resource group (e.g. `users.get`) and the name should be the bare standard verb. (AIP-121, AIP-130)
2. **Paths are RPC-style, not resource-oriented.** `/get-user`, `/list-users`, `/user/new`, `/user/update` all use verbs in the path. AIP-122 says the path *is* the resource name and must alternate `plural-collection / id`. The collection is `workspaces/{workspace}/users` (camelCase, plural).
3. **HTTP methods are wrong almost everywhere.** `GET` is fine for `get`, but `list` must be `GET` (not `POST`), `create` must be `POST` (not `PUT`), and `update` must be `PATCH` (not `PUT`). (AIP-130)
4. **The resource has an `id` (number) instead of a `name` (string path).** Per AIP-122, the canonical identifier is the resource name `workspaces/{workspace}/users/{user}` — a string. Numeric DB primary keys are an implementation detail. The schema should expose `name`, and optionally `uid` / a server-supplied opaque ID. The `workspaceId`/`userId` tuple anti-pattern is exactly what resource names exist to eliminate.
5. **Workspace is embedded inside User.** AIP-122 forbids embedding one resource inside another. Reference it by name: `parent: "workspaces/{workspace}"` (or just rely on the parent prefix of the user's name). Embedding breaks lifecycle, leaks permissions, and couples schemas.
6. **`create` and `update` share the same input schema (the full `User`).** Per AIP-121 you must derive input shapes from the canonical schema:
   - `create` input should omit server-assigned fields (`name`) and live under a `parent`.
   - `update` should be a *partial* (`PATCH`) with an `updateMask`, never a full replace.
7. **`list` uses `offset` + `limit`.** AIP-130 says use cursor pagination (`pageSize` + `pageToken`). Offsets break under concurrent insert/delete and force the server into expensive `OFFSET N` queries.
8. **`role` is an enum but missing the `_UNSPECIFIED` sentinel and isn't UPPER_SNAKE_CASE.** AIP-126: members are UPPER_SNAKE_CASE and the zero value is `<TYPE>_UNSPECIFIED`. Members should be `ROLE_UNSPECIFIED`, `ROLE_ADMIN`, `ROLE_USER`, `ROLE_GUEST` (or unprefixed if local to this schema only), and the open/closed nature documented.
9. **No `delete`.** Not strictly a bug, but AIP-121 expects every resource to support `get` (it does) and, in nearly all cases, the rest of the standard set. If `delete` is intentionally unsupported, leave a comment; otherwise add it.
10. **Procedure naming redundancy.** `listAllUsers`, `createNewUser`, `updateUserData` repeat the resource name and add filler words ("All", "New", "Data"). Once procedures are grouped under `users.*`, the bare standard verb is enough.

## Per-procedure breakdown

### `getUser`

```ts
os.route({ method: 'GET', path: '/get-user' })
  .input(z.object({ userId: z.number(), workspaceId: z.number() }))
```

- Path uses a verb (`/get-user`). Should be `/workspaces/{workspace}/users/{user}` — the path *is* the resource name. (AIP-122)
- Input addresses the resource as a `(workspaceId, userId)` numeric tuple. This is the exact anti-pattern AIP-122 calls out. Use path parameters (`workspace`, `user`) extracted from the resource name. (AIP-122)
- Numeric IDs leak DB structure. Resource IDs should be opaque strings matching `^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$` for client-supplied, or documented opaque tokens for server-supplied.

### `listAllUsers`

```ts
os.route({ method: 'POST', path: '/list-users' })
  .input(z.object({ workspaceId: z.number(), offset: z.number(), limit: z.number() }))
  .output(z.array(User))
```

- Method must be `GET`, not `POST`. (AIP-130)
- Path must be the collection: `/workspaces/{workspace}/users`. (AIP-122, AIP-130)
- Pagination must be `pageSize` (≤ a documented max, e.g. 100) and `pageToken`, not `offset`/`limit`. (AIP-130)
- Output should be an object `{ users, nextPageToken }`, not a bare array — clients need somewhere to receive the cursor, and wrapping the array also keeps room for adding sibling fields (`totalSize`, etc.) without a breaking change. (AIP-130)
- Parent collection is addressed via a `parent` string (`workspaces/{workspace}`) when there are multiple possible parents; for a single fixed parent, a path parameter `{workspace}` is fine.
- Procedure name should just be `list` once it lives under `users.*`. "All" is filler.

### `createNewUser`

```ts
os.route({ method: 'PUT', path: '/user/new' })
  .input(User)
  .output(User)
```

- Method must be `POST`, not `PUT`. (AIP-130)
- Path must be the *collection* (`/workspaces/{workspace}/users`), not `/user/new`. The verb is encoded by HTTP, not the path. (AIP-122, AIP-130)
- Input is the full `User`, including server-assigned `name`/`id` and an embedded `workspace`. Should be:
  - `parent: "workspaces/{workspace}"` (or a path param)
  - `userId?` — client may suggest one, server may override (AIP-122)
  - `user: User.omit({ name: true })` — derived from the canonical schema (AIP-121)
- Output (the created resource) is correct in principle, but it will now be `User` with a proper `name` field. (AIP-121, AIP-122)
- Procedure name should just be `create`.

### `updateUserData`

```ts
os.route({ method: 'PUT', path: '/user/update' })
  .input(User)
  .output(User)
```

- Method must be `PATCH`, not `PUT`. AIP-130 is explicit: full-replace `PUT` is almost never what callers want.
- Path must address the *resource*: `/workspaces/{workspace}/users/{user}`. (AIP-122, AIP-130)
- Input is the entire resource, which means a missing field is ambiguous ("clear it" vs "leave it alone"). Use `Schema.partial()` plus an `updateMask: string[]` that names the fields being changed. (AIP-130)
- Procedure name should just be `update` — `Data` is filler.

## Schema issues

```ts
const User = z.object({
  id: z.number().int(),
  email: z.string().email(),
  role: z.enum(['admin', 'user', 'guest']),
  workspace: z.object({ id: z.number().int(), name: z.string() }),
})
```

- **`id: number` → `name: string`.** The canonical identifier is `workspaces/{workspace}/users/{user}`, exposed as a `name` field. A numeric `id` may be additionally exposed as `uid` (read-only, opaque) if useful. (AIP-122)
- **`workspace` embedded resource → reference by name.** Replace with a string reference, or just rely on the parent prefix in `name`. If the workspace must be exposed inline for a particular endpoint, return a separate `workspace` reference field of type `z.string()` containing `"workspaces/{workspace}"`. (AIP-122)
- **`role` enum** needs UPPER_SNAKE_CASE members and a `_UNSPECIFIED` sentinel. Document whether it's open (server may add members) or closed. (AIP-126)
- The schema is missing a resource-type declaration. For a single-service app this is optional, but a `UserType = 'workspace.example.com/User'` constant alongside the schema costs nothing and pays off if the org ever grows past one service. (AIP-123)

## Corrected router

```ts
import { os } from '@orpc/server'
import * as z from 'zod'

// AIP-123: resource type + name pattern declared next to the schema.
export const UserType = 'workspace.example.com/User' as const
export const UserPattern = 'workspaces/{workspace}/users/{user}' as const

// AIP-126: UPPER_SNAKE_CASE, _UNSPECIFIED sentinel, documented openness.
export const Role = z
  .enum(['ROLE_UNSPECIFIED', 'ROLE_ADMIN', 'ROLE_USER', 'ROLE_GUEST'])
  .describe(
    'Role of a User within a Workspace. Closed enum; clients should treat ROLE_UNSPECIFIED as "server did not set this".',
  )

// AIP-121, AIP-122: canonical schema, addressed by `name`, references workspace by name.
export const User = z.object({
  name: z
    .string()
    .describe(`Canonical resource name. Type: ${UserType}. Pattern: ${UserPattern}.`),
  email: z.string().email(),
  role: Role,
})
export type User = z.infer<typeof User>

// AIP-130: cursor pagination.
const PageInput = z.object({
  pageSize: z.coerce.number().int().min(1).max(100).optional(),
  pageToken: z.string().optional(),
})

// AIP-122: client-supplied resource ID grammar.
const UserId = z
  .string()
  .min(1)
  .max(63)
  .regex(/^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$/)

// --- Standard methods ---------------------------------------------------

const listUsers = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/users' })
  .input(PageInput.extend({ workspace: z.string() }))
  .output(z.object({ users: z.array(User), nextPageToken: z.string().optional() }))
  .handler(async () => ({ users: [] }))

const getUser = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({ workspace: z.string(), user: z.string() }))
  .output(User)
  .handler(async () => ({}) as any)

const createUser = os
  .route({ method: 'POST', path: '/workspaces/{workspace}/users' })
  .input(
    z.object({
      workspace: z.string(),
      userId: UserId.optional(), // server may generate
      user: User.omit({ name: true }), // derived; server assigns the name
    }),
  )
  .output(User)
  .handler(async () => ({}) as any)

const updateUser = os
  .route({ method: 'PATCH', path: '/workspaces/{workspace}/users/{user}' })
  .input(
    z.object({
      workspace: z.string(),
      user: z.string(),
      patch: User.partial().omit({ name: true }),
      updateMask: z.array(z.string()).optional(),
    }),
  )
  .output(User)
  .handler(async () => ({}) as any)

const deleteUser = os
  .route({ method: 'DELETE', path: '/workspaces/{workspace}/users/{user}' })
  .input(z.object({ workspace: z.string(), user: z.string() }))
  .output(z.void())
  .handler(async () => undefined)

// AIP-121, AIP-130: standard methods grouped under the resource collection.
export const router = {
  users: {
    list: listUsers,
    get: getUser,
    create: createUser,
    update: updateUser,
    delete: deleteUser,
  },
}
```

## Summary of mapping

| Original                        | Corrected                                                       | Why                            |
| ------------------------------- | --------------------------------------------------------------- | ------------------------------ |
| `getUser`, `GET /get-user`      | `users.get`, `GET /workspaces/{workspace}/users/{user}`         | AIP-121, AIP-122, AIP-130      |
| `listAllUsers`, `POST /list-users`, offset/limit, bare array | `users.list`, `GET /workspaces/{workspace}/users`, pageSize/pageToken, `{ users, nextPageToken }` | AIP-130                        |
| `createNewUser`, `PUT /user/new`, input=`User`              | `users.create`, `POST /workspaces/{workspace}/users`, input derived via `User.omit({ name: true })`, optional `userId` | AIP-121, AIP-122, AIP-130      |
| `updateUserData`, `PUT /user/update`, input=`User`          | `users.update`, `PATCH /workspaces/{workspace}/users/{user}`, partial patch + `updateMask` | AIP-130                        |
| `User.id: number`               | `User.name: string` (`workspaces/{w}/users/{u}`)                | AIP-122                        |
| `User.workspace: { id, name }`  | Parent encoded in the name; cross-resource refs are strings     | AIP-122                        |
| `role: 'admin'\|'user'\|'guest'`| `Role` enum, `ROLE_UNSPECIFIED` sentinel, UPPER_SNAKE_CASE      | AIP-126                        |
| (none)                          | `users.delete`                                                  | AIP-121 (resources usually expose the full standard set) |

## Things I'm *not* flagging

- Numeric DB primary keys: fine to keep internally; just don't expose them as the canonical identifier. Surface them as a separate read-only `uid` if external systems already depend on them. (AIP-122)
- The decision to model `Workspace` as the parent of `User`: that's a domain call. The fix here is structural (reference by name, not by embedding), not "stop nesting".
- Resource type constants (`UserType`, `UserPattern`) are arguably overkill for a single-service app — AIP-123 itself says so. I included them because they cost nothing and pay off later.
