/**
 * Project management API surface for oRPC.
 *
 * Designed against Google AIPs:
 *   - AIP-121: resource-oriented design (nouns, hierarchy, standard methods,
 *     schema consistency, read-after-write).
 *   - AIP-122: resource names ("workspaces/{workspace}/projects/{project}",
 *     "name" field, parent fields, references as strings).
 *   - AIP-123: resource type identifiers ("pm.example.com/Project", etc.).
 *   - AIP-126: enums in UPPER_SNAKE_CASE with an _UNSPECIFIED zero value.
 *   - AIP-130: HTTP verb + path mapping for standard methods, PATCH for
 *     update with updateMask, pageSize/pageToken pagination.
 */

import { os } from '@orpc/server'
import * as z from 'zod'

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------

/**
 * Client-supplied resource ID grammar (AIP-122).
 * Lowercase, hyphenated, 1–63 chars, starts with a letter, ends alphanumeric.
 */
const ResourceIdSchema = z
  .string()
  .min(1)
  .max(63)
  .regex(/^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$/)
  .describe(
    'Client-supplied ID. Lowercase letters, digits, hyphens. Must start ' +
      'with a letter and end with a letter or digit. 1–63 characters. ' +
      'Optional on create — server generates one if omitted.',
  )

/**
 * Standard cursor-based pagination input (AIP-130).
 * pageSize is coerced because it arrives as a query-string in GETs.
 */
const PageInput = z.object({
  pageSize: z.coerce.number().int().min(1).max(100).optional()
    .describe('Maximum number of items to return. Server may return fewer. Default 50, max 100.'),
  pageToken: z.string().optional()
    .describe('Opaque cursor returned by a previous response\'s nextPageToken.'),
})

/**
 * AIP-122 + AIP-132: a list response also exposes the cursor for the next page
 * and a best-effort total. Total is optional because it can be expensive.
 */
function ListResponse<T extends z.ZodTypeAny>(itemKey: string, item: T) {
  return z.object({
    [itemKey]: z.array(item),
    nextPageToken: z.string().optional()
      .describe('Cursor to pass as pageToken on the next call. Absent when no more pages.'),
    totalSize: z.number().int().nonnegative().optional()
      .describe('Best-effort total count of items matching the filter. May be omitted for cost reasons.'),
  })
}

/** Stable ISO-8601 timestamp string. */
const Timestamp = z.string().datetime()

// ---------------------------------------------------------------------------
// Project resource (AIP-121, AIP-122, AIP-123)
// ---------------------------------------------------------------------------

export const ProjectType = 'pm.example.com/Project' as const
export const ProjectPattern = 'workspaces/{workspace}/projects/{project}' as const
export const ProjectSingular = 'project' as const
export const ProjectPlural = 'projects' as const

/**
 * Canonical Project schema. Reused verbatim in get/create/update/list
 * responses (AIP-121 schema consistency). All input shapes are derived
 * from this with .omit / .partial.
 */
export const Project = z.object({
  name: z.string()
    .describe(
      `Canonical resource name. Type: ${ProjectType}. ` +
        `Pattern: ${ProjectPattern}. Server-assigned on create.`,
    ),
  displayName: z.string().min(1).max(200)
    .describe('Human-readable name shown in UIs. Not unique.'),
  description: z.string().max(4096).optional()
    .describe('Optional long-form description.'),
  createTime: Timestamp
    .describe('Output-only. When the project was created.'),
  updateTime: Timestamp
    .describe('Output-only. When the project was last modified.'),
})
export type Project = z.infer<typeof Project>

// ---- Project inputs -------------------------------------------------------

const ListProjectsInput = PageInput.extend({
  parent: z.string()
    .describe('Resource name of the parent workspace, e.g. "workspaces/acme".'),
  filter: z.string().optional()
    .describe('Optional AIP-160-style filter expression (open string).'),
  orderBy: z.string().optional()
    .describe('Optional AIP-132 ordering, e.g. "displayName" or "createTime desc".'),
})

const GetProjectInput = z.object({
  // Path variables match {workspace}/{project} in the route. Together they
  // re-form the full resource name "workspaces/{workspace}/projects/{project}".
  workspace: z.string(),
  project: z.string(),
})

const CreateProjectInput = z.object({
  parent: z.string()
    .describe('Resource name of the parent workspace, e.g. "workspaces/acme".'),
  projectId: ResourceIdSchema.optional(),
  // Server assigns `name`, `createTime`, `updateTime` — strip from the body.
  project: Project.omit({ name: true, createTime: true, updateTime: true }),
})

const UpdateProjectInput = z.object({
  workspace: z.string(),
  project: z.string(),
  // PATCH semantics: send only the fields you intend to change. `name` is
  // immutable; `createTime`/`updateTime` are output-only.
  patch: Project.omit({ name: true, createTime: true, updateTime: true }).partial(),
  updateMask: z.array(z.string()).optional()
    .describe(
      'Explicit list of field paths to update (AIP-134). When omitted, ' +
        'the server updates exactly the fields present in `patch`.',
    ),
})

const DeleteProjectInput = z.object({
  workspace: z.string(),
  project: z.string(),
})

// ---------------------------------------------------------------------------
// Task resource
// ---------------------------------------------------------------------------

export const TaskType = 'pm.example.com/Task' as const
export const TaskPattern =
  'workspaces/{workspace}/projects/{project}/tasks/{task}' as const
export const TaskSingular = 'task' as const
export const TaskPlural = 'tasks' as const

/**
 * Task status (AIP-126).
 *
 * Closed enum: the lifecycle states of a task are stable. UPPER_SNAKE_CASE
 * members, with TASK_STATUS_UNSPECIFIED as the zero-value sentinel. Members
 * are prefixed with the enum name because TaskStatus and TaskPriority both
 * live in this package and `DONE`/`HIGH` would collide in languages that
 * hoist enum members.
 */
export const TaskStatus = z
  .enum([
    'TASK_STATUS_UNSPECIFIED',
    'TASK_STATUS_TODO',
    'TASK_STATUS_IN_PROGRESS',
    'TASK_STATUS_BLOCKED',
    'TASK_STATUS_DONE',
  ])
  .describe(
    'Lifecycle state of a task. Closed enum — new members are not expected. ' +
      'Clients should still tolerate unknown values defensively.',
  )
export type TaskStatus = z.infer<typeof TaskStatus>

/**
 * Task priority (AIP-126). Also a closed, prefixed enum.
 */
export const TaskPriority = z
  .enum([
    'TASK_PRIORITY_UNSPECIFIED',
    'TASK_PRIORITY_LOW',
    'TASK_PRIORITY_MEDIUM',
    'TASK_PRIORITY_HIGH',
  ])
  .describe('Priority of a task. Closed enum.')
export type TaskPriority = z.infer<typeof TaskPriority>

/**
 * Canonical Task schema. Same shape in every method (AIP-121).
 */
export const Task = z.object({
  name: z.string()
    .describe(
      `Canonical resource name. Type: ${TaskType}. Pattern: ${TaskPattern}. ` +
        'Server-assigned on create.',
    ),
  displayName: z.string().min(1).max(200)
    .describe('Short human-readable title for the task.'),
  description: z.string().max(16_384).optional()
    .describe('Optional long-form description / body.'),
  status: TaskStatus
    .describe('Current lifecycle state. Defaults to TASK_STATUS_TODO on create.'),
  priority: TaskPriority
    .describe('Priority. Defaults to TASK_PRIORITY_MEDIUM on create.'),
  // Reference to another resource by **name** (AIP-122) — never embed the
  // full User object here; that couples lifecycles and bypasses permissions.
  assignee: z.string().optional()
    .describe('Optional resource name of the assigned user, e.g. "users/alice". Reference, not embedded.'),
  dueTime: Timestamp.nullable().optional()
    .describe('Optional due date/time. Null clears it.'),
  createTime: Timestamp
    .describe('Output-only. When the task was created.'),
  updateTime: Timestamp
    .describe('Output-only. When the task was last modified.'),
})
export type Task = z.infer<typeof Task>

// ---- Task inputs ----------------------------------------------------------

const ListTasksInput = PageInput.extend({
  parent: z.string()
    .describe('Resource name of the parent project, e.g. "workspaces/acme/projects/website".'),
  filter: z.string().optional()
    .describe('Optional AIP-160-style filter, e.g. "status=TASK_STATUS_TODO AND priority=TASK_PRIORITY_HIGH".'),
  orderBy: z.string().optional()
    .describe('Optional AIP-132 ordering, e.g. "dueTime" or "priority desc".'),
})

const GetTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: z.string(),
})

const CreateTaskInput = z.object({
  parent: z.string()
    .describe('Resource name of the parent project, e.g. "workspaces/acme/projects/website".'),
  taskId: ResourceIdSchema.optional(),
  task: Task.omit({ name: true, createTime: true, updateTime: true }),
})

const UpdateTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: z.string(),
  patch: Task.omit({ name: true, createTime: true, updateTime: true }).partial(),
  updateMask: z.array(z.string()).optional()
    .describe('Explicit list of field paths to update (AIP-134).'),
})

const DeleteTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: z.string(),
})

// ---------------------------------------------------------------------------
// Procedures — Projects
//
// Standard-method matrix (AIP-130):
//   list   GET     /workspaces/{workspace}/projects
//   get    GET     /workspaces/{workspace}/projects/{project}
//   create POST    /workspaces/{workspace}/projects
//   update PATCH   /workspaces/{workspace}/projects/{project}
//   delete DELETE  /workspaces/{workspace}/projects/{project}
// ---------------------------------------------------------------------------

const listProjects = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/projects' })
  // The path variable {workspace} arrives as a string and is merged with the
  // body-derived ListProjectsInput; we accept it as `parent` for AIP-122
  // consistency in handlers, but expose it on the wire as the path segment.
  .input(ListProjectsInput.extend({ workspace: z.string() }))
  .output(ListResponse('projects', Project))
  .handler(async ({ input: _input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

const getProject = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/projects/{project}' })
  .input(GetProjectInput)
  .output(Project)
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

const createProject = os
  .route({ method: 'POST', path: '/workspaces/{workspace}/projects' })
  .input(CreateProjectInput.extend({ workspace: z.string() }))
  .output(Project)
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

const updateProject = os
  .route({ method: 'PATCH', path: '/workspaces/{workspace}/projects/{project}' })
  .input(UpdateProjectInput)
  .output(Project)
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

const deleteProject = os
  .route({ method: 'DELETE', path: '/workspaces/{workspace}/projects/{project}' })
  .input(DeleteProjectInput)
  .output(z.void())
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

// ---------------------------------------------------------------------------
// Procedures — Tasks
//
//   list   GET     /workspaces/{workspace}/projects/{project}/tasks
//   get    GET     /workspaces/{workspace}/projects/{project}/tasks/{task}
//   create POST    /workspaces/{workspace}/projects/{project}/tasks
//   update PATCH   /workspaces/{workspace}/projects/{project}/tasks/{task}
//   delete DELETE  /workspaces/{workspace}/projects/{project}/tasks/{task}
// ---------------------------------------------------------------------------

const listTasks = os
  .route({
    method: 'GET',
    path: '/workspaces/{workspace}/projects/{project}/tasks',
  })
  .input(ListTasksInput.extend({ workspace: z.string(), project: z.string() }))
  .output(ListResponse('tasks', Task))
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

const getTask = os
  .route({
    method: 'GET',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(GetTaskInput)
  .output(Task)
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

const createTask = os
  .route({
    method: 'POST',
    path: '/workspaces/{workspace}/projects/{project}/tasks',
  })
  .input(CreateTaskInput.extend({ workspace: z.string(), project: z.string() }))
  .output(Task)
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

const updateTask = os
  .route({
    method: 'PATCH',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(UpdateTaskInput)
  .output(Task)
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

const deleteTask = os
  .route({
    method: 'DELETE',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(DeleteTaskInput)
  .output(z.void())
  .handler(async ({ input: _input }) => {
    throw new Error('not implemented')
  })

// ---------------------------------------------------------------------------
// Router
//
// Grouped by collection. The router shape mirrors the resource hierarchy so
// client code reads as `client.projects.list(...)`, `client.tasks.create(...)`.
// ---------------------------------------------------------------------------

export const router = {
  projects: {
    list: listProjects,
    get: getProject,
    create: createProject,
    update: updateProject,
    delete: deleteProject,
  },
  tasks: {
    list: listTasks,
    get: getTask,
    create: createTask,
    update: updateTask,
    delete: deleteTask,
  },
}

export type Router = typeof router
