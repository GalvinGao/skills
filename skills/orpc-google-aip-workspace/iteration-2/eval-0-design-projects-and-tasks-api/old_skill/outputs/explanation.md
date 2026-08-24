# Project / Task API design notes

The design follows Google AIPs 121, 122, 123, 126, and 130, translated to oRPC + Zod.

## Resource hierarchy (AIP-121, AIP-122)

Two resources, one canonical parent each — the resource graph is a DAG with no shared ownership:

```
workspaces/{workspace}                                         (given)
  workspaces/{workspace}/projects/{project}                    Project
    workspaces/{workspace}/projects/{project}/tasks/{task}     Task
```

Task's parent is **Project**, not Workspace. A task belongs to one project (AIP-121 "one canonical parent"). The `workspace` segment is carried along because resource names must encode the full hierarchical path (AIP-122).

The path string in `.route({ path })` is the resource name template — the same string returned in the `name` field of each resource (AIP-122).

## Resource types (AIP-123)

`ProjectType = 'pm.example.com/Project'` and `TaskType = 'pm.example.com/Task'` are declared as constants alongside their schemas. Singular/plural forms are also exported as constants in case a sibling service ever needs to agree on them (AIP-123 multi-service guidance). The `Pattern` constants mirror the route paths.

## Schema consistency (AIP-121)

Each resource (`Project`, `Task`) is defined **once**. All input/output variants are derived:

- `Create*Input` uses `Schema.omit({ name: true, createTime: true, updateTime: true })` — server assigns these.
- `Update*Input` uses `.omit(...).partial()` — partial patch, no patching of immutable/output-only fields.
- `Get*Input` / `Delete*Input` take only the path variables.

This prevents the "CreateBookBody vs BookResponse drifting apart" failure mode AIP-121 warns about.

## Standard methods only (AIP-130)

The user asked for list, get, create, update, delete — these are the five standard methods, so no custom `:verb` methods are needed (AIP-130 priority order: standard before custom).

| Method | HTTP   | Path                                                                  |
| ------ | ------ | --------------------------------------------------------------------- |
| list   | GET    | `/workspaces/{workspace}/projects` and `.../projects/{project}/tasks` |
| get    | GET    | `.../projects/{project}` and `.../tasks/{task}`                       |
| create | POST   | `/workspaces/{workspace}/projects` and `.../tasks` (parent collection) |
| update | PATCH  | `.../projects/{project}` and `.../tasks/{task}` (partial — AIP-130)   |
| delete | DELETE | `.../projects/{project}` and `.../tasks/{task}`                       |

Other AIP-130 details applied:

- **`PATCH`, not `PUT`** — update is partial.
- **`updateMask`** on update inputs to disambiguate "clear field" vs "leave alone".
- **`pageSize` + `pageToken`** (not `offset` + `limit`) for cursor pagination.
- **`projectId` / `taskId` optional on create** — server may generate; client may suggest a slug.
- **List output shape** is `{ projects: [...], nextPageToken? }` / `{ tasks: [...], nextPageToken? }`, following the convention that the array field is named after the plural resource.

Handlers are left as `throw new Error('not implemented')` stubs as requested.

## Enums (AIP-126)

Both `status` and `priority` fit the AIP-126 criteria for an enum: small (4 and 3 members), stable (the workflow is fixed for v1), no industry standard covers them, and they read more clearly than a free-form string.

Conventions applied:

- **UPPER_SNAKE_CASE** for every member.
- **`<TYPE>_UNSPECIFIED` zero value** — `TASK_STATUS_UNSPECIFIED`, `TASK_PRIORITY_UNSPECIFIED`. This is the sentinel so the server can detect "client did not set this field" vs "client set it to a real value", which matters for `updateMask` semantics.
- **Member-name prefixes** (`TASK_STATUS_TODO`, `TASK_PRIORITY_LOW`). Because both enums live in the same package and are used together on the `Task` schema, prefixing avoids collisions when this contract is ever rendered into languages that hoist enum members (Go, C++).
- Documented as **closed** enums in the `.describe(...)` text, with explicit guidance to clients on how to handle unknown values.

If the product team turned out to add new statuses every sprint, AIP-126 would push us to a documented `string` instead — but the four-state todo/in-progress/blocked/done workflow is the textbook stable case.

## What is intentionally not here

- **No custom methods** (`:archive`, `:complete`, etc.) — the user asked only for CRUD. If a status transition like "mark done" became a frequent single-shot operation, AIP-130 would justify a `POST .../tasks/{task}:complete` custom method, but a `PATCH` with `updateMask: ['status']` is fine for now.
- **No `parent` field on the resource bodies** — the parent is encoded in the `name`, so duplicating it would violate AIP-122's "name is the one identifier" rule.
- **No batch methods** — fine to add later (`:batchGet`, `:batchDelete`) per AIP-130 if N+1 round trips become a problem.
- **No `Operation` resource** — every CRUD here is fast and synchronous, so AIP-121's strong-consistency rule is met without long-running operations.
