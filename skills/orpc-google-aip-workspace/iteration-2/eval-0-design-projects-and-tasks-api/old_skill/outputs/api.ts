/**
 * Project management API surface.
 *
 * Design notes:
 * - Resources are modeled as nouns with hierarchical names (AIP-121, AIP-122).
 *   - Project's canonical parent is Workspace.
 *   - Task's canonical parent is Project (single parent — AIP-121).
 * - Resource names flow through the API as the `name` field on every resource
 *   and as the path in `.route({ path })` (AIP-122).
 * - Resource schemas are defined once and reused across methods; input
 *   variants are derived with `.omit` / `.partial` (AIP-121 schema
 *   consistency).
 * - Standard methods only — list / get / create / update / delete (AIP-130).
 * - Enums use UPPER_SNAKE_CASE with an `_UNSPECIFIED` sentinel; members are
 *   prefixed by enum name because both enums live in the same package and
 *   could otherwise collide (AIP-126).
 * - Resource types declared as constants for cross-service / generic tooling
 *   (AIP-123).
 */

import { os } from '@orpc/server'
import * as z from 'zod'

// ---------------------------------------------------------------------------
// Resource types (AIP-123)
// ---------------------------------------------------------------------------

export const ProjectType = 'pm.example.com/Project' as const
export const ProjectPattern = 'workspaces/{workspace}/projects/{project}' as const
export const ProjectSingular = 'project' as const
export const ProjectPlural = 'projects' as const

export const TaskType = 'pm.example.com/Task' as const
export const TaskPattern =
  'workspaces/{workspace}/projects/{project}/tasks/{task}' as const
export const TaskSingular = 'task' as const
export const TaskPlural = 'tasks' as const

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------

/**
 * Resource ID syntax for client-supplied IDs (AIP-122):
 * lowercase, hyphens, 1–63 chars, starts with a letter, ends with letter/digit.
 */
const ResourceIdSchema = z
  .string()
  .min(1)
  .max(63)
  .regex(/^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$/)

/** Cursor pagination input (AIP-130). */
const PageInput = z.object({
  pageSize: z.coerce.number().int().min(1).max(100).optional(),
  pageToken: z.string().optional(),
})

// ---------------------------------------------------------------------------
// Enums (AIP-126)
// ---------------------------------------------------------------------------

/**
 * Lifecycle status of a Task.
 *
 * Closed enum: the workflow is fixed for v1. Members are prefixed with the
 * enum name because both TaskStatus and TaskPriority are package-level enums
 * used inside the same Task schema (AIP-126).
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
    'Lifecycle status of a Task. Closed enum: clients should treat unknown values as TASK_STATUS_UNSPECIFIED.',
  )
export type TaskStatus = z.infer<typeof TaskStatus>

/**
 * Priority of a Task.
 *
 * Closed enum. Sentinel is TASK_PRIORITY_UNSPECIFIED so the server can
 * distinguish "client did not set" from "client set to a real value".
 */
export const TaskPriority = z
  .enum([
    'TASK_PRIORITY_UNSPECIFIED',
    'TASK_PRIORITY_LOW',
    'TASK_PRIORITY_MEDIUM',
    'TASK_PRIORITY_HIGH',
  ])
  .describe(
    'Priority of a Task. Closed enum: clients should treat unknown values as TASK_PRIORITY_UNSPECIFIED.',
  )
export type TaskPriority = z.infer<typeof TaskPriority>

// ---------------------------------------------------------------------------
// Project resource (AIP-121, AIP-122)
// ---------------------------------------------------------------------------

export const Project = z.object({
  /** Resource name: workspaces/{workspace}/projects/{project} */
  name: z
    .string()
    .describe(
      `Canonical resource name. Server-assigned on create. Type: ${ProjectType}. Pattern: ${ProjectPattern}.`,
    ),
  /** Human-readable display name. Distinct from the resource name. */
  displayName: z.string().min(1).max(200),
  description: z.string().max(4000).default(''),
  createTime: z
    .string()
    .datetime()
    .describe('Output only. RFC 3339 timestamp.'),
  updateTime: z
    .string()
    .datetime()
    .describe('Output only. RFC 3339 timestamp.'),
})
export type Project = z.infer<typeof Project>

// Inputs derived from the resource schema (AIP-121).

const ListProjectsInput = PageInput.extend({
  /** Parent collection: workspaces/{workspace} */
  parent: z.string(),
})

const ListProjectsOutput = z.object({
  projects: z.array(Project),
  nextPageToken: z.string().optional(),
})

const GetProjectInput = z.object({
  /** Path variables — the concatenation reconstructs the resource name. */
  workspace: z.string(),
  project: z.string(),
})

const CreateProjectInput = z.object({
  parent: z.string(),
  /** Optional client-supplied ID; server may generate when omitted. */
  projectId: ResourceIdSchema.optional(),
  project: Project.omit({
    name: true,
    createTime: true,
    updateTime: true,
  }),
})

const UpdateProjectInput = z.object({
  workspace: z.string(),
  project: z.string(),
  /** Partial patch — `name`, `createTime`, `updateTime` are not patchable. */
  patch: Project.omit({
    name: true,
    createTime: true,
    updateTime: true,
  }).partial(),
  /** Field mask explicitly enumerating the fields being updated (AIP-130). */
  updateMask: z.array(z.string()).optional(),
})

const DeleteProjectInput = GetProjectInput

// ---------------------------------------------------------------------------
// Task resource (AIP-121, AIP-122)
// ---------------------------------------------------------------------------

export const Task = z.object({
  /** Resource name: workspaces/{workspace}/projects/{project}/tasks/{task} */
  name: z
    .string()
    .describe(
      `Canonical resource name. Server-assigned on create. Type: ${TaskType}. Pattern: ${TaskPattern}.`,
    ),
  title: z.string().min(1).max(200),
  description: z.string().max(8000).default(''),
  status: TaskStatus.default('TASK_STATUS_UNSPECIFIED'),
  priority: TaskPriority.default('TASK_PRIORITY_UNSPECIFIED'),
  createTime: z
    .string()
    .datetime()
    .describe('Output only. RFC 3339 timestamp.'),
  updateTime: z
    .string()
    .datetime()
    .describe('Output only. RFC 3339 timestamp.'),
})
export type Task = z.infer<typeof Task>

const ListTasksInput = PageInput.extend({
  /** Parent collection: workspaces/{workspace}/projects/{project} */
  parent: z.string(),
})

const ListTasksOutput = z.object({
  tasks: z.array(Task),
  nextPageToken: z.string().optional(),
})

const GetTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: z.string(),
})

const CreateTaskInput = z.object({
  parent: z.string(),
  taskId: ResourceIdSchema.optional(),
  task: Task.omit({
    name: true,
    createTime: true,
    updateTime: true,
  }),
})

const UpdateTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: z.string(),
  patch: Task.omit({
    name: true,
    createTime: true,
    updateTime: true,
  }).partial(),
  updateMask: z.array(z.string()).optional(),
})

const DeleteTaskInput = GetTaskInput

// ---------------------------------------------------------------------------
// Procedures — Project (AIP-130 standard methods)
//
// HTTP verb + path follow the AIP-130 table:
//   list   GET    /{collection}
//   get    GET    /{collection}/{id}
//   create POST   /{collection}
//   update PATCH  /{collection}/{id}
//   delete DELETE /{collection}/{id}
// ---------------------------------------------------------------------------

const listProjects = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/projects' })
  .input(ListProjectsInput.extend({ workspace: z.string() }))
  .output(ListProjectsOutput)
  .handler(async () => {
    throw new Error('not implemented')
  })

const getProject = os
  .route({
    method: 'GET',
    path: '/workspaces/{workspace}/projects/{project}',
  })
  .input(GetProjectInput)
  .output(Project)
  .handler(async () => {
    throw new Error('not implemented')
  })

const createProject = os
  .route({ method: 'POST', path: '/workspaces/{workspace}/projects' })
  .input(CreateProjectInput.extend({ workspace: z.string() }))
  .output(Project)
  .handler(async () => {
    throw new Error('not implemented')
  })

const updateProject = os
  .route({
    method: 'PATCH',
    path: '/workspaces/{workspace}/projects/{project}',
  })
  .input(UpdateProjectInput)
  .output(Project)
  .handler(async () => {
    throw new Error('not implemented')
  })

const deleteProject = os
  .route({
    method: 'DELETE',
    path: '/workspaces/{workspace}/projects/{project}',
  })
  .input(DeleteProjectInput)
  .output(z.void())
  .handler(async () => {
    throw new Error('not implemented')
  })

// ---------------------------------------------------------------------------
// Procedures — Task (AIP-130 standard methods)
// ---------------------------------------------------------------------------

const listTasks = os
  .route({
    method: 'GET',
    path: '/workspaces/{workspace}/projects/{project}/tasks',
  })
  .input(
    ListTasksInput.extend({
      workspace: z.string(),
      project: z.string(),
    }),
  )
  .output(ListTasksOutput)
  .handler(async () => {
    throw new Error('not implemented')
  })

const getTask = os
  .route({
    method: 'GET',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(GetTaskInput)
  .output(Task)
  .handler(async () => {
    throw new Error('not implemented')
  })

const createTask = os
  .route({
    method: 'POST',
    path: '/workspaces/{workspace}/projects/{project}/tasks',
  })
  .input(
    CreateTaskInput.extend({
      workspace: z.string(),
      project: z.string(),
    }),
  )
  .output(Task)
  .handler(async () => {
    throw new Error('not implemented')
  })

const updateTask = os
  .route({
    method: 'PATCH',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(UpdateTaskInput)
  .output(Task)
  .handler(async () => {
    throw new Error('not implemented')
  })

const deleteTask = os
  .route({
    method: 'DELETE',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(DeleteTaskInput)
  .output(z.void())
  .handler(async () => {
    throw new Error('not implemented')
  })

// ---------------------------------------------------------------------------
// Router
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
