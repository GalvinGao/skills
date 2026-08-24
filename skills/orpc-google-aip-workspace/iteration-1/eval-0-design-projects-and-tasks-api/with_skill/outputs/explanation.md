# Project / Task API — design notes

This is a resource-oriented oRPC API for `Project` (child of `Workspace`)
and `Task` (child of `Project`). The shape follows Google's AIPs, adapted
to oRPC + Zod + OpenAPI. Each numbered choice cites the rule that drove it.

## Resource hierarchy and names

Two resources, one parent chain:

```
workspaces/{workspace}/projects/{project}
workspaces/{workspace}/projects/{project}/tasks/{task}
```

- **Hierarchical names (AIP-122).** The path in `.route({ path })` is
  literally the resource name. The same string flows through as the `name`
  field on the resource schema. No parallel `{ workspaceId, projectId }`
  tuples; one canonical identifier.
- **One canonical parent (AIP-121).** A `Task` belongs to one `Project`,
  which belongs to one `Workspace`. The graph is a DAG.
- **Plural, camelCase collection segments (AIP-122).** `workspaces`,
  `projects`, `tasks` — never `Project` or `task`.
- **Client-supplied IDs validated (AIP-122).** `ResourceIdSchema` enforces
  `^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$`. `projectId`/`taskId` are optional on
  create so the server can generate one when the client doesn't care.
- **References by name, not embedding (AIP-122).** `Task.assignee` is a
  string `users/alice`, not an embedded `User` object. Embedding would
  couple lifecycles and bypass per-resource auth.

## Resource types (AIP-123)

Declared as constants alongside each schema:

```ts
ProjectType = 'pm.example.com/Project'
TaskType    = 'pm.example.com/Task'
```

Plus `*Pattern`, `*Singular`, `*Plural` constants. For a single-service app
this is mild overhead, but it keeps audit logs, webhooks, and cross-service
references self-describing if the system grows.

## Standard methods only (AIP-121, AIP-130)

The task is pure CRUD, so every operation maps to a standard method. No
custom `:archive` / `:complete` / `:assign` verbs — those would be
premature. If the product later needs them, they slot in as
`POST /...projects/{project}/tasks/{task}:complete` etc. (AIP-130 custom
method shape) without disturbing the existing surface.

| Method | HTTP   | Path                                                              |
| ------ | ------ | ----------------------------------------------------------------- |
| list   | GET    | `/workspaces/{workspace}/projects`                                |
| get    | GET    | `/workspaces/{workspace}/projects/{project}`                      |
| create | POST   | `/workspaces/{workspace}/projects`                                |
| update | PATCH  | `/workspaces/{workspace}/projects/{project}`                      |
| delete | DELETE | `/workspaces/{workspace}/projects/{project}`                      |
| list   | GET    | `/workspaces/{workspace}/projects/{project}/tasks`                |
| get    | GET    | `/workspaces/{workspace}/projects/{project}/tasks/{task}`         |
| create | POST   | `/workspaces/{workspace}/projects/{project}/tasks`                |
| update | PATCH  | `/workspaces/{workspace}/projects/{project}/tasks/{task}`         |
| delete | DELETE | `/workspaces/{workspace}/projects/{project}/tasks/{task}`         |

A few specific calls:

- **`PATCH`, not `PUT` (AIP-130).** Update is partial; `updateMask` makes
  the intent explicit so a missing field is never ambiguous between "clear
  it" and "leave it alone".
- **Cursor pagination, not offset (AIP-130).** `pageSize` + `pageToken` on
  every `list`, and `ListResponse(...)` wraps the item array plus an
  optional `nextPageToken` and `totalSize`.
- **`pageSize` is `z.coerce.number()`** because list inputs arrive as
  query-string in `GET`s — strings until coerced.
- **Delete returns `z.void()` (AIP-130).** No tombstone needed for an
  in-memory project tool; if soft-delete is added later, return the
  resource with an output-only `deleteTime` instead.

## Schema consistency (AIP-121)

`Project` and `Task` are each defined once. All input shapes are derived:

- `Project.omit({ name: true, createTime: true, updateTime: true })` for
  create bodies (server assigns these three).
- `Project.omit(...).partial()` for update patches.
- The same `Project` is the response shape of get/create/update and the
  item type in list responses.

This is the single biggest defense against drift. If a new field is added
to `Project`, every method picks it up automatically.

## Enums (AIP-126)

Two closed enums on `Task`:

- `TaskStatus`: `TASK_STATUS_UNSPECIFIED | TASK_STATUS_TODO | TASK_STATUS_IN_PROGRESS | TASK_STATUS_BLOCKED | TASK_STATUS_DONE`
- `TaskPriority`: `TASK_PRIORITY_UNSPECIFIED | TASK_PRIORITY_LOW | TASK_PRIORITY_MEDIUM | TASK_PRIORITY_HIGH`

Rules applied:

- **UPPER_SNAKE_CASE members** with an **`_UNSPECIFIED` zero value** as the
  sentinel for "client didn't set this".
- **Member-name prefixes.** `TASK_STATUS_DONE` rather than bare `DONE`,
  because `DONE` would otherwise collide with potential members of other
  enums in this package (and in client languages that hoist enum members
  to the top level, like Go or C++).
- **Closed-enum disclaimer** in the description. Statuses and priorities
  are stable; new members are not expected. Clients should still tolerate
  unknown values defensively (an open-by-default posture is cheap).
- Both fields are non-optional on `Task` with documented defaults
  (`TASK_STATUS_TODO`, `TASK_PRIORITY_MEDIUM`) — the server fills these
  in on create if the client omits them. The `_UNSPECIFIED` member exists
  so a client *can* explicitly send "I have no opinion".

## What is deliberately not here

- **No `Workspace` resource.** The task scoped only `Project` and `Task`.
  `workspaces/{workspace}` is referenced as a parent name only — the
  surface for managing workspaces themselves is out of scope.
- **No custom methods** like `:archive`, `:complete`, `:assign`. These are
  the typical follow-ups but AIP-130 says reach for them only after a
  standard method can't carry the meaning. Status changes here ride on
  `update` with an `updateMask: ["status"]`.
- **No batch endpoints** (`batchGet`, `batchUpdate`). AIP-130 puts these
  between standard methods and custom methods on the priority ladder; add
  them when round-trip cost becomes a real complaint, not before.
- **Implementation.** Handlers are stubs (`throw new Error('not
  implemented')`) so the contract is the deliverable.

## Read-after-write (AIP-121)

The contract assumes the standard strong-consistency guarantee: once
`create` / `update` / `delete` returns success, a subsequent `get` reflects
it. This is a property of the *handlers* (not yet written), but the schema
contract — output-only `createTime`/`updateTime`, server-assigned `name`,
synchronous return of the full resource — is what makes the guarantee
expressible.
