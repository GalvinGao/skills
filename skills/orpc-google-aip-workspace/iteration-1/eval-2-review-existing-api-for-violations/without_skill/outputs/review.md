# oRPC Router API Design Review

This router works, but it leaks several API design smells that will hurt
consumers, generated OpenAPI clients, and future maintainers. Below are the
issues grouped by theme, followed by a corrected version.

---

## 1. HTTP methods are wrong / inconsistent

| Procedure         | Current   | Should be | Why |
|-------------------|-----------|-----------|-----|
| `getUser`         | `GET`     | `GET`     | OK — but path is wrong (see §2) |
| `listAllUsers`    | `POST`    | `GET`     | Listing is a safe, idempotent, cacheable read. `POST` makes it un-cacheable, breaks browser/CDN semantics, and signals "side effect" to consumers. |
| `createNewUser`   | `PUT`     | `POST`    | `PUT` is for **idempotent upserts to a known URI**. Creating a new resource where the server assigns the `id` is the textbook `POST` case. |
| `updateUserData`  | `PUT`     | `PATCH` (partial) **or** `PUT` (full replace) | If the input is a partial update, this must be `PATCH`. If it's a full replacement, keep `PUT` — but then every field must be required, and currently the schema doesn't distinguish "update" from "create" at all (see §4). |

**Rule of thumb (REST + AIP-130/133/134):**
- `GET`   → read (safe, idempotent)
- `POST`  → create (server assigns id)
- `PUT`   → full replace at known URI (idempotent)
- `PATCH` → partial update (not necessarily idempotent in spec, but practically should be)
- `DELETE`→ remove

---

## 2. URL paths are unRESTful and inconsistent

Current paths:

```
GET  /get-user
POST /list-users
PUT  /user/new
PUT  /user/update
```

Problems:

1. **Verbs in paths.** `/get-user`, `/list-users`, `/user/new`, `/user/update`
   all embed the action in the URL. The HTTP method *is* the verb. Paths
   should be **nouns identifying resources**.
2. **Singular vs plural inconsistency.** `/list-users` (plural) vs
   `/user/new` (singular). Pick one — convention is **plural collection
   names** (`/users`).
3. **No resource identity in the path.** `getUser` takes `userId` in the
   *body/query* instead of `/users/{userId}`. Resource identity belongs in
   the URL so that caches, logs, access controls, and OpenAPI tooling can
   reason about it.
4. **Workspace scoping is implicit.** `workspaceId` is a body parameter, but
   semantically a user *belongs to* a workspace. That should be reflected
   hierarchically: `/workspaces/{workspaceId}/users/{userId}`. This is the
   Google AIP-122 "resource name" pattern and it makes authorization,
   routing, and multi-tenant isolation dramatically clearer.

**Corrected paths:**

```
GET    /workspaces/{workspaceId}/users          → list
GET    /workspaces/{workspaceId}/users/{userId} → get
POST   /workspaces/{workspaceId}/users          → create
PATCH  /workspaces/{workspaceId}/users/{userId} → update
DELETE /workspaces/{workspaceId}/users/{userId} → delete  (missing entirely!)
```

---

## 3. Procedure names embed redundant adjectives

- `getUser` ✅
- `listAllUsers` → should be `listUsers`. "All" is a lie anyway (it's
  paginated) and adds nothing.
- `createNewUser` → should be `createUser`. "New" is implied by "create".
- `updateUserData` → should be `updateUser`. "Data" is filler — *of course*
  it's data.

These read like junior code review smells, and once they're in a public
router they're hard to remove without a breaking change. Name procedures
`<verb><Resource>` (singular) per AIP-136 and the conventions oRPC's own
docs use.

---

## 4. Input schemas conflate create / update / read

`createNewUser` and `updateUserData` both take the full `User` schema as
input. That's wrong for at least three reasons:

1. **`id` shouldn't be in the create input.** The server assigns it.
   Accepting an `id` on create either silently ignores it (confusing) or
   lets clients pick ids (dangerous).
2. **`workspace` shouldn't be a nested object on create.** The workspace is
   determined by the URL path (`/workspaces/{workspaceId}/...`). Letting
   the body specify a different `workspace.id` creates a parameter-conflict
   class of bugs and authorization holes.
3. **Update should be partial.** Forcing clients to send every field on
   every update means a stale client can clobber fields it didn't intend
   to. Use `PATCH` with a partial schema (or an explicit `update_mask` per
   AIP-134 if you want to be rigorous).

You want three distinct schemas:
- `User` — the canonical resource (response shape)
- `UserCreate` — input for `POST`, no `id`, no nested workspace
- `UserUpdate` — input for `PATCH`, all fields optional, no `id`

---

## 5. Pagination is offset-based and unbounded

`listAllUsers` takes `offset` and `limit` with no constraints:

- `limit` has no max — a client can request `limit: 1_000_000` and DOS your
  database.
- `limit` has no default — clients have to guess.
- Offset pagination is **slow on large tables** (the DB still scans the
  skipped rows) and **inconsistent under writes** (rows shift between
  pages).
- There's no `nextPageToken` / total count / `hasMore` indicator in the
  response, so clients can't tell when they've reached the end without an
  extra empty request.

**Fix:** use AIP-158 cursor pagination — `pageSize` (with default + max) and
`pageToken`, and return `{ users, nextPageToken }`.

---

## 6. Zod schemas are under-constrained

- `z.number()` for ids accepts negatives, zero, floats, and `Infinity`. Use
  `z.number().int().positive()` — or, better, **make ids strings**
  (`z.string()`) so they survive JSON's 53-bit number limit. Most production
  APIs that started with numeric ids regret it.
- `z.string()` for `workspace.name` accepts the empty string and 10 MB of
  text. Use `.min(1).max(255)`.
- `z.string().email()` — fine, but `email` is a [deprecated zod method as of
  zod v4](https://zod.dev/v4). Prefer `z.email()`.
- `User.id` and `User.workspace.id` should be branded types
  (`z.number().int().brand<'UserId'>()`) so a `WorkspaceId` can't be passed
  where a `UserId` is expected at the type level.

---

## 7. No errors are declared

oRPC supports `.errors({...})` to declare typed errors that appear in the
OpenAPI spec and client types. None of these procedures declare error
cases. At minimum:

- `getUser` / `updateUser` / `deleteUser` → `NOT_FOUND`
- `createUser` → `CONFLICT` (email already exists)
- All authenticated procedures → `UNAUTHORIZED`, `FORBIDDEN`
- `listUsers` → `INVALID_ARGUMENT` (bad page token)

Without these, clients have to guess error shapes and the generated
OpenAPI is silent on the failure modes.

---

## 8. No middleware / context / auth

Every procedure is built directly from `os` with no `.use(...)`
middleware. In a real app you almost always want:

- An auth middleware that injects `context.user`.
- A workspace-access middleware that verifies the caller can touch
  `workspaceId`.
- Logging / tracing.

Define a base procedure once and reuse it:

```ts
const authed = os.use(authMiddleware)
const inWorkspace = authed.use(workspaceAccessMiddleware)
```

…then build all workspace-scoped procedures off `inWorkspace`. As written,
every procedure would have to re-implement auth, which never stays
consistent.

---

## 9. `role` enum is fine, but consider future-proofing

`z.enum(['admin', 'user', 'guest'])` is a closed set. The moment you add
`'owner'`, every client that exhaustively switches on `role` breaks. This
is a judgment call, but for public APIs prefer documenting role as a
string with known values rather than a sealed enum — or version the enum
explicitly.

---

## 10. Missing operations

A resource CRUD surface for `User` should have all five:
`create`, `get`, `list`, `update`, `delete`. Delete is missing. If delete
is intentionally disallowed, document that — don't leave it ambiguous.

---

## Corrected router

```ts
import { os } from '@orpc/server'
import * as z from 'zod'

// --- Branded ids -----------------------------------------------------------

const UserId      = z.number().int().positive().brand<'UserId'>()
const WorkspaceId = z.number().int().positive().brand<'WorkspaceId'>()

// --- Schemas ---------------------------------------------------------------

const Role = z.enum(['admin', 'user', 'guest'])

const Workspace = z.object({
  id:   WorkspaceId,
  name: z.string().min(1).max(255),
})

// Canonical resource (response shape)
const User = z.object({
  id:        UserId,
  email:     z.email(),
  role:      Role,
  workspace: Workspace,
})

// Input shapes
const UserCreate = z.object({
  email: z.email(),
  role:  Role,
})

const UserUpdate = z.object({
  email: z.email().optional(),
  role:  Role.optional(),
})

// Pagination
const PageParams = z.object({
  pageSize:  z.number().int().min(1).max(100).default(20),
  pageToken: z.string().optional(),
})

const UserList = z.object({
  users:         z.array(User),
  nextPageToken: z.string().optional(),
})

// --- Common errors ---------------------------------------------------------

const baseErrors = {
  UNAUTHORIZED: { message: 'Authentication required.' },
  FORBIDDEN:    { message: 'Caller cannot access this workspace.' },
  NOT_FOUND:    { message: 'User not found in workspace.' },
}

// --- Procedures ------------------------------------------------------------
// In a real app, `os` here would be a base procedure built with
// `.use(authMiddleware).use(workspaceAccessMiddleware)`.

export const router = {
  listUsers: os
    .route({ method: 'GET', path: '/workspaces/{workspaceId}/users' })
    .errors(baseErrors)
    .input(z.object({ workspaceId: WorkspaceId }).extend(PageParams.shape))
    .output(UserList)
    .handler(async () => ({ users: [], nextPageToken: undefined })),

  getUser: os
    .route({ method: 'GET', path: '/workspaces/{workspaceId}/users/{userId}' })
    .errors(baseErrors)
    .input(z.object({ workspaceId: WorkspaceId, userId: UserId }))
    .output(User)
    .handler(async () => ({} as any)),

  createUser: os
    .route({ method: 'POST', path: '/workspaces/{workspaceId}/users' })
    .errors({ ...baseErrors, CONFLICT: { message: 'Email already in use.' } })
    .input(z.object({ workspaceId: WorkspaceId }).extend(UserCreate.shape))
    .output(User)
    .handler(async () => ({} as any)),

  updateUser: os
    .route({ method: 'PATCH', path: '/workspaces/{workspaceId}/users/{userId}' })
    .errors(baseErrors)
    .input(
      z.object({ workspaceId: WorkspaceId, userId: UserId }).extend(UserUpdate.shape),
    )
    .output(User)
    .handler(async () => ({} as any)),

  deleteUser: os
    .route({ method: 'DELETE', path: '/workspaces/{workspaceId}/users/{userId}' })
    .errors(baseErrors)
    .input(z.object({ workspaceId: WorkspaceId, userId: UserId }))
    .output(z.void())
    .handler(async () => {}),
}
```

---

## Summary of changes

| # | Issue                                       | Fix |
|---|---------------------------------------------|-----|
| 1 | Wrong HTTP methods (`POST` list, `PUT` create) | `GET` list, `POST` create, `PATCH` update |
| 2 | Verbs in paths, no resource ids in URL      | `/workspaces/{wid}/users/{uid}` hierarchy |
| 3 | Redundant procedure names                   | `listUsers`, `createUser`, `updateUser`   |
| 4 | One schema for create/update/read           | Separate `User`, `UserCreate`, `UserUpdate` |
| 5 | Unbounded offset pagination, no end signal  | Cursor pagination with capped `pageSize`  |
| 6 | Under-constrained zod types                 | `.int().positive()`, lengths, branded ids |
| 7 | No declared errors                          | `.errors({ NOT_FOUND, CONFLICT, ... })`   |
| 8 | No middleware / auth scaffolding            | Base procedure with auth + workspace mw   |
| 9 | Closed enum, no versioning plan             | Document evolution policy                 |
|10 | Missing `delete`                            | Added `deleteUser`                        |

The single highest-leverage fix is **§2 + §4 together**: putting resource
identity in the URL and splitting create/update/read schemas. That alone
eliminates most of the authorization bugs, OpenAPI ugliness, and client
ergonomics issues at once.
