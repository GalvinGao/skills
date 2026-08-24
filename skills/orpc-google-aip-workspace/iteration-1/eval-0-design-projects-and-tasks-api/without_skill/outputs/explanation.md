# Project & Task API — Design Notes

## Shape of the API

Two resources, each with the standard five operations:

| Resource | Operation | RPC name              | HTTP                                            |
| -------- | --------- | --------------------- | ----------------------------------------------- |
| Project  | list      | `projects.list`       | `GET /workspaces/{workspaceId}/projects`        |
| Project  | get       | `projects.get`        | `GET /projects/{id}`                            |
| Project  | create    | `projects.create`     | `POST /workspaces/{workspaceId}/projects`       |
| Project  | update    | `projects.update`     | `PATCH /projects/{id}`                          |
| Project  | delete    | `projects.delete`     | `DELETE /projects/{id}`                         |
| Task     | list      | `tasks.list`          | `GET /projects/{projectId}/tasks`               |
| Task     | get       | `tasks.get`           | `GET /tasks/{id}`                               |
| Task     | create    | `tasks.create`        | `POST /projects/{projectId}/tasks`              |
| Task     | update    | `tasks.update`        | `PATCH /tasks/{id}`                             |
| Task     | delete    | `tasks.delete`        | `DELETE /tasks/{id}`                            |

## Key design choices

- **One router, two transports.** Every procedure uses `.route(...)` so the
  same router can be served as RPC and as a REST/OpenAPI API via
  `@orpc/openapi` — no duplicate definitions.
- **Nested parents on collection routes, flat IDs on item routes.** Listing
  and creating are scoped under their parent (`/workspaces/.../projects`,
  `/projects/.../tasks`) because the parent is required and meaningful.
  Get/update/delete take a globally-unique ID at the top level (`/projects/{id}`,
  `/tasks/{id}`), which keeps URLs short and matches how clients usually hold
  on to a single identifier.
- **String IDs.** Opaque strings instead of numbers — works for UUIDs, ULIDs,
  or any future ID scheme without an API break.
- **Enums for `status` and `priority`.** `z.enum(...)` gives both runtime
  validation and a literal union type, and produces a clean OpenAPI enum.
  Statuses use `in_progress` (snake_case, stable wire format) rather than
  `in-progress` so it's a valid identifier in generated clients.
- **PATCH-style updates.** `Update*Input` makes every mutable field optional
  and excludes server-managed fields (`id`, `workspaceId`/`projectId`,
  `createdAt`, `updatedAt`). Partial updates are what UIs almost always want.
- **Server-owned fields are output-only.** `id`, `createdAt`, `updatedAt`,
  and the parent FK on creation are not in the create/update inputs — they're
  derived by the server.
- **Cursor pagination, not offset.** A reusable `PaginationInput` +
  `paginated(item)` envelope (`{ items, nextCursor }`) avoids the classic
  offset-pagination duplication/skip bugs and scales to large projects.
- **Cheap, common filters on list.** `tasks.list` accepts optional `status`
  and `priority` because filtering by these is almost universal in task UIs;
  adding them up front avoids a near-immediate breaking change.
- **Sensible create-time defaults.** New tasks default to
  `status: "todo"` and `priority: "medium"` so the minimum viable create
  payload is `{ projectId, title }`.
- **Nullable vs optional, used deliberately.** `description` and `dueAt`
  are `.nullable()` on the resource (the server always returns the field,
  possibly as `null`) and `.optional()` on inputs (the client can omit
  them). This keeps response shapes predictable for typed clients.
- **Delete returns a small confirmation object** (`{ id, deleted: true }`)
  rather than `void`, so the OpenAPI response is well-typed and clients
  can react without a separate refetch.

## What was intentionally left out

- Auth/permissions middleware — the brief said "leave handlers as stubs",
  so no `.use(...)` middleware is wired up. In a real codebase this is where
  a `workspaceMember` / `projectMember` check would live.
- Bulk operations, soft-delete, archival, comments, attachments, assignees,
  labels — all reasonable extensions, none required by the spec.
- Realtime/subscriptions — orthogonal to the CRUD surface.
