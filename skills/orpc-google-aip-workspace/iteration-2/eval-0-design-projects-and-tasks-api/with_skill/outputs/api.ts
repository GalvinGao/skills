/**
 * Project-management API surface for oRPC.
 *
 * Design follows Google AIP-121 (resource-oriented design),
 * AIP-126 (enumerations), and AIP-130 (standard methods) as translated
 * to oRPC + Zod by the `orpc-google-aip` skill.
 *
 * Resource hierarchy (single canonical parent per resource, DAG):
 *
 *   workspaces/{workspace}
 *     projects/{project}                 (parent: workspaces/{workspace})
 *       tasks/{task}                     (parent: …/projects/{project})
 *
 * Handlers are intentionally stubbed out.
 */

import { os } from '@orpc/server'
import * as z from 'zod'

// ---------------------------------------------------------------------------
// Shared building blocks
// ---------------------------------------------------------------------------

/**
 * Cursor pagination shared across every `list` method.
 * `limit` is hard-capped at 100 so clients can't accidentally pull the world.
 * (AIP-130 — pagination uses `limit` + `cursor`, not `offset`.)
 */
const PageInput = z.object({
  limit: z.coerce.number().int().min(1).max(100).optional(),
  cursor: z.string().optional(),
})

// ---------------------------------------------------------------------------
// Enums (AIP-126)
// ---------------------------------------------------------------------------

/**
 * Task lifecycle status. Small, stable, no external standard — enum is the
 * right tool. `TASK_STATUS_UNSPECIFIED` is the zero-value sentinel so a
 * client can distinguish "server didn't set this" from a real state.
 */
export const TaskStatus = z
  .enum([
    'TASK_STATUS_UNSPECIFIED',
    'TODO',
    'IN_PROGRESS',
    'BLOCKED',
    'DONE',
  ])
  .describe(
    'Lifecycle state of a Task. Closed enum; new members would be a breaking change.',
  )
export type TaskStatus = z.infer<typeof TaskStatus>

/**
 * Task priority. Same reasoning as TaskStatus — small, stable, closed set.
 */
export const TaskPriority = z
  .enum([
    'TASK_PRIORITY_UNSPECIFIED',
    'LOW',
    'MEDIUM',
    'HIGH',
  ])
  .describe(
    'Priority bucket for a Task. Closed enum; new members would be a breaking change.',
  )
export type TaskPriority = z.infer<typeof TaskPriority>

// ---------------------------------------------------------------------------
// Resource: Project
// ---------------------------------------------------------------------------

/**
 * Canonical `Project` resource schema. Defined ONCE; every input shape below
 * is derived from this with `.omit` / `.partial` so the shapes can't drift
 * (AIP-121 — schema consistency).
 *
 * `name` is the full hierarchical resource name and is the stable identifier:
 *   workspaces/{workspace}/projects/{project}
 */
export const Project = z.object({
  name: z
    .string()
    .describe('Resource name: workspaces/{workspace}/projects/{project}'),
  displayName: z.string().min(1).max(200),
  description: z.string().max(10_000).default(''),
  createTime: z.string().datetime(),
  updateTime: z.string().datetime(),
})
export type Project = z.infer<typeof Project>

/** Server-assigned / server-managed fields the client may not write. */
const ProjectWritable = Project.omit({
  name: true,
  createTime: true,
  updateTime: true,
})

// ----- Inputs / Outputs -----------------------------------------------------

const ListProjectsInput = PageInput.extend({
  workspace: z.string().describe('Parent workspace id (path segment).'),
})

const ListProjectsOutput = z.object({
  projects: z.array(Project),
  nextCursor: z.string().optional(),
})

const GetProjectInput = z.object({
  workspace: z.string(),
  project: z.string(),
})

const CreateProjectInput = z.object({
  workspace: z.string(),
  // Server assigns `name`, `createTime`, `updateTime`.
  project: ProjectWritable,
})

const UpdateProjectInput = z.object({
  workspace: z.string(),
  project: z.string(),
  // PATCH semantics: every mutable field is optional. Omitted fields are
  // untouched. (AIP-130)
  patch: ProjectWritable.partial(),
})

const DeleteProjectInput = z.object({
  workspace: z.string(),
  project: z.string(),
})

// ----- Procedures -----------------------------------------------------------

const listProjects = os
  .route({ method: 'GET', path: '/workspaces/{workspace}/projects' })
  .input(ListProjectsInput)
  .output(ListProjectsOutput)
  .handler(async ({ input: _input }) => {
    throw new Error('stub: list projects')
  })

const getProject = os
  .route({
    method: 'GET',
    path: '/workspaces/{workspace}/projects/{project}',
  })
  .input(GetProjectInput)
  .output(Project)
  .handler(async ({ input: _input }) => {
    throw new Error('stub: get project')
  })

const createProject = os
  .route({ method: 'POST', path: '/workspaces/{workspace}/projects' })
  .input(CreateProjectInput)
  .output(Project)
  .handler(async ({ input: _input }) => {
    throw new Error('stub: create project')
  })

const updateProject = os
  .route({
    method: 'PATCH',
    path: '/workspaces/{workspace}/projects/{project}',
  })
  .input(UpdateProjectInput)
  .output(Project)
  .handler(async ({ input: _input }) => {
    throw new Error('stub: update project')
  })

const deleteProject = os
  .route({
    method: 'DELETE',
    path: '/workspaces/{workspace}/projects/{project}',
  })
  .input(DeleteProjectInput)
  .output(z.void())
  .handler(async ({ input: _input }) => {
    throw new Error('stub: delete project')
  })

// ---------------------------------------------------------------------------
// Resource: Task
// ---------------------------------------------------------------------------

/**
 * Canonical `Task` resource schema. Same conventions as `Project`.
 *
 * `name` is the full hierarchical resource name:
 *   workspaces/{workspace}/projects/{project}/tasks/{task}
 */
export const Task = z.object({
  name: z
    .string()
    .describe(
      'Resource name: workspaces/{workspace}/projects/{project}/tasks/{task}',
    ),
  title: z.string().min(1).max(500),
  description: z.string().max(10_000).default(''),
  status: TaskStatus.default('TASK_STATUS_UNSPECIFIED'),
  priority: TaskPriority.default('TASK_PRIORITY_UNSPECIFIED'),
  assignee: z
    .string()
    .nullable()
    .default(null)
    .describe('Resource name of the assigned user, or null if unassigned.'),
  dueTime: z.string().datetime().nullable().default(null),
  createTime: z.string().datetime(),
  updateTime: z.string().datetime(),
})
export type Task = z.infer<typeof Task>

const TaskWritable = Task.omit({
  name: true,
  createTime: true,
  updateTime: true,
})

// ----- Inputs / Outputs -----------------------------------------------------

const ListTasksInput = PageInput.extend({
  workspace: z.string(),
  project: z.string(),
})

const ListTasksOutput = z.object({
  tasks: z.array(Task),
  nextCursor: z.string().optional(),
})

const GetTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: z.string(),
})

const CreateTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: TaskWritable,
})

const UpdateTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: z.string(),
  patch: TaskWritable.partial(),
})

const DeleteTaskInput = z.object({
  workspace: z.string(),
  project: z.string(),
  task: z.string(),
})

// ----- Procedures -----------------------------------------------------------

const listTasks = os
  .route({
    method: 'GET',
    path: '/workspaces/{workspace}/projects/{project}/tasks',
  })
  .input(ListTasksInput)
  .output(ListTasksOutput)
  .handler(async ({ input: _input }) => {
    throw new Error('stub: list tasks')
  })

const getTask = os
  .route({
    method: 'GET',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(GetTaskInput)
  .output(Task)
  .handler(async ({ input: _input }) => {
    throw new Error('stub: get task')
  })

const createTask = os
  .route({
    method: 'POST',
    path: '/workspaces/{workspace}/projects/{project}/tasks',
  })
  .input(CreateTaskInput)
  .output(Task)
  .handler(async ({ input: _input }) => {
    throw new Error('stub: create task')
  })

const updateTask = os
  .route({
    method: 'PATCH',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(UpdateTaskInput)
  .output(Task)
  .handler(async ({ input: _input }) => {
    throw new Error('stub: update task')
  })

const deleteTask = os
  .route({
    method: 'DELETE',
    path: '/workspaces/{workspace}/projects/{project}/tasks/{task}',
  })
  .input(DeleteTaskInput)
  .output(z.void())
  .handler(async ({ input: _input }) => {
    throw new Error('stub: delete task')
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

export type Router = typeof router
