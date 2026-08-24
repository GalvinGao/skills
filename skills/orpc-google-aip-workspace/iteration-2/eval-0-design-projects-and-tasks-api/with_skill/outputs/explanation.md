# Design notes

This API surface follows Google AIP-121, AIP-126, and AIP-130, translated to
oRPC + Zod by the `orpc-google-aip` skill. Each non-obvious choice below cites
the rule that drove it.

## Resource hierarchy

```
workspaces/{workspace}
  projects/{project}                     ← parent: workspace
    tasks/{task}                          ← parent: project
```

A `Project` has exactly one canonical parent (`Workspace`) and a `Task` has
exactly one canonical parent (`Project`). The reference graph is a DAG with no
cycles — **AIP-121** ("Each resource has one canonical parent").

The full hierarchical name is the stable identifier and is the resource's
`name` field — e.g. `workspaces/acme/projects/launch/tasks/42`. Path params in
the oRPC routes (`{workspace}`, `{project}`, `{task}`) are just the segments
of that name. This is straight out of **AIP-121** (resources are addressed by
a name that encodes the hierarchy) and aligns with **AIP-130**'s path matrix.

## Standard methods only

Both resources expose `list`, `get`, `create`, `update`, `delete` and nothing
else (**AIP-121** — reach for the standard vocabulary before inventing
anything; **AIP-130** — the canonical five). HTTP verbs follow AIP-130's
matrix:

| Method | Verb     | Path                                                                 |
| ------ | -------- | -------------------------------------------------------------------- |
| list   | `GET`    | `/workspaces/{w}/projects` · `/workspaces/{w}/projects/{p}/tasks`    |
| get    | `GET`    | `/workspaces/{w}/projects/{p}` · `…/tasks/{t}`                       |
| create | `POST`   | `/workspaces/{w}/projects` · `/workspaces/{w}/projects/{p}/tasks`    |
| update | `PATCH`  | `/workspaces/{w}/projects/{p}` · `…/tasks/{t}`                       |
| delete | `DELETE` | `/workspaces/{w}/projects/{p}` · `…/tasks/{t}`                       |

Two specific calls worth flagging:

- **`update` is `PATCH`, not `PUT`** (**AIP-130**). The input contains a
  `patch` field that is `Resource.partial()` — omitted fields are left alone.
  This avoids forcing callers into read-modify-write and avoids racing
  writers clobbering each other.
- **`list` is `GET`** (**AIP-130**). Using `POST` for a read breaks HTTP
  caching and signals "side effects".

## Schema consistency via derivation

Each resource (`Project`, `Task`) is defined exactly once as the canonical
schema. Every input shape is derived from it:

- `…Writable = Resource.omit({ name, createTime, updateTime })` — strips
  server-owned fields.
- `CreateInput` uses `…Writable` directly.
- `UpdateInput` uses `…Writable.partial()` for `PATCH` semantics.

This is the **AIP-121** schema-consistency rule: a resource has the same
shape wherever it appears in the surface (response of `get`, items in `list`,
response of `create`, response of `update`). Hand-writing parallel
`CreateProjectBody` / `ProjectResponse` schemas is exactly the drift this
avoids.

## Enums for `status` and `priority`

Both `TaskStatus` (`TODO` / `IN_PROGRESS` / `BLOCKED` / `DONE`) and
`TaskPriority` (`LOW` / `MEDIUM` / `HIGH`) satisfy **AIP-126**'s checklist:

- Discrete, finite set.
- Stable — these don't churn.
- No external standard covers them.
- Reads more clearly than a free-form string at the call site.

Therefore both are encoded as `z.enum([...])` with UPPER_SNAKE_CASE members.
Each enum's first member is the `<TYPE>_UNSPECIFIED` zero-value sentinel —
**AIP-126** — so a client can distinguish "server didn't set this" from a
real state. They are documented as closed enums (adding members would be a
breaking change).

## Pagination: `limit` + `cursor`

`list` methods take an optional `limit` (clamped at `[1, 100]` so a client
can't ask for ten thousand) and an opaque `cursor`. The response includes
`nextCursor` only when there are more pages. This is **AIP-130**'s
cursor-pagination convention. Offset paging is rejected on the usual grounds
(slow scans on large tables, skip/duplicate under concurrent writes).

## Strong consistency after mutations

The contract assumes **AIP-121**'s read-after-write guarantee: a `get` after a
successful `create` / `update` returns the new state, and a `get` after
`delete` returns NOT_FOUND. None of these operations are modeled as
long-running — if any becomes async in the future, the right move is to
return an `Operation` resource the client can poll, not silent eventual
consistency.

## What is intentionally *not* here

- **No `archive`, `restore`, `assign`, `markDone` custom verbs.** Status
  transitions are modeled as `update` with `patch: { status: 'DONE' }`.
  Reassigning is `update` with `patch: { assignee: '…' }`. Custom methods
  exist in AIP for cases the standard five can't express (**AIP-121**'s
  deviation clause); none of these qualify.
- **No `PUT`.** See above.
- **No nested writes** (creating a `Project` does not accept inline `tasks`).
  Each resource has its own create call — the surface stays orthogonal and
  the strong-consistency guarantee stays simple.
