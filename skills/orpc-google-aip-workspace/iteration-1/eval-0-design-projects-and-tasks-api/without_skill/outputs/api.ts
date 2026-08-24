/**
 * Project Management API — oRPC + Zod design
 *
 * Resources:
 *   - Project (belongs to a Workspace)
 *   - Task    (belongs to a Project)
 *
 * Each procedure declares an HTTP route so the same router can be served as
 * either RPC or a REST/OpenAPI surface via `@orpc/openapi`.
 *
 * Handlers are intentionally left as stubs.
 */

import { os } from '@orpc/server'
import * as z from 'zod'

/* -------------------------------------------------------------------------- */
/*                             Shared primitives                              */
/* -------------------------------------------------------------------------- */

/** ID shape used across all resources. Stable, opaque, string-typed. */
const Id = z.string().min(1)

/** ISO-8601 timestamp, produced by the server. */
const Timestamp = z.string().datetime()

/** Cursor-based pagination input, reusable across list endpoints. */
const PaginationInput = z.object({
  limit: z.number().int().min(1).max(100).default(20),
  cursor: z.string().optional(),
})

/** Cursor-based pagination envelope, reusable across list endpoints. */
function paginated<T extends z.ZodTypeAny>(item: T) {
  return z.object({
    items: z.array(item),
    nextCursor: z.string().nullable(),
  })
}

/* -------------------------------------------------------------------------- */
/*                                  Project                                   */
/* -------------------------------------------------------------------------- */

export const ProjectSchema = z.object({
  id: Id,
  workspaceId: Id,
  name: z.string().min(1).max(120),
  description: z.string().max(2_000).nullable(),
  createdAt: Timestamp,
  updatedAt: Timestamp,
})
export type Project = z.infer<typeof ProjectSchema>

export const CreateProjectInput = z.object({
  workspaceId: Id,
  name: ProjectSchema.shape.name,
  description: ProjectSchema.shape.description.optional(),
})

export const UpdateProjectInput = z.object({
  id: Id,
  // PATCH-style: every mutable field is optional.
  name: ProjectSchema.shape.name.optional(),
  description: ProjectSchema.shape.description.optional(),
})

export const ListProjectsInput = PaginationInput.extend({
  workspaceId: Id,
})

/* ---------------------------- Project procedures -------------------------- */

export const listProjects = os
  .route({ method: 'GET', path: '/workspaces/{workspaceId}/projects' })
  .input(ListProjectsInput)
  .output(paginated(ProjectSchema))
  .handler(async ({ input }) => {
    // TODO: implement
    return { items: [], nextCursor: null }
  })

export const getProject = os
  .route({ method: 'GET', path: '/projects/{id}' })
  .input(z.object({ id: Id }))
  .output(ProjectSchema)
  .handler(async ({ input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

export const createProject = os
  .route({ method: 'POST', path: '/workspaces/{workspaceId}/projects' })
  .input(CreateProjectInput)
  .output(ProjectSchema)
  .handler(async ({ input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

export const updateProject = os
  .route({ method: 'PATCH', path: '/projects/{id}' })
  .input(UpdateProjectInput)
  .output(ProjectSchema)
  .handler(async ({ input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

export const deleteProject = os
  .route({ method: 'DELETE', path: '/projects/{id}' })
  .input(z.object({ id: Id }))
  .output(z.object({ id: Id, deleted: z.literal(true) }))
  .handler(async ({ input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

/* -------------------------------------------------------------------------- */
/*                                    Task                                    */
/* -------------------------------------------------------------------------- */

export const TaskStatus = z.enum(['todo', 'in_progress', 'blocked', 'done'])
export type TaskStatus = z.infer<typeof TaskStatus>

export const TaskPriority = z.enum(['low', 'medium', 'high'])
export type TaskPriority = z.infer<typeof TaskPriority>

export const TaskSchema = z.object({
  id: Id,
  projectId: Id,
  title: z.string().min(1).max(200),
  description: z.string().max(10_000).nullable(),
  status: TaskStatus,
  priority: TaskPriority,
  dueAt: Timestamp.nullable(),
  createdAt: Timestamp,
  updatedAt: Timestamp,
})
export type Task = z.infer<typeof TaskSchema>

export const CreateTaskInput = z.object({
  projectId: Id,
  title: TaskSchema.shape.title,
  description: TaskSchema.shape.description.optional(),
  // Sensible server-side defaults when omitted.
  status: TaskStatus.default('todo'),
  priority: TaskPriority.default('medium'),
  dueAt: TaskSchema.shape.dueAt.optional(),
})

export const UpdateTaskInput = z.object({
  id: Id,
  title: TaskSchema.shape.title.optional(),
  description: TaskSchema.shape.description.optional(),
  status: TaskStatus.optional(),
  priority: TaskPriority.optional(),
  dueAt: TaskSchema.shape.dueAt.optional(),
})

export const ListTasksInput = PaginationInput.extend({
  projectId: Id,
  // Optional filters — cheap to add, very common in real UIs.
  status: TaskStatus.optional(),
  priority: TaskPriority.optional(),
})

/* ------------------------------ Task procedures --------------------------- */

export const listTasks = os
  .route({ method: 'GET', path: '/projects/{projectId}/tasks' })
  .input(ListTasksInput)
  .output(paginated(TaskSchema))
  .handler(async ({ input }) => {
    // TODO: implement
    return { items: [], nextCursor: null }
  })

export const getTask = os
  .route({ method: 'GET', path: '/tasks/{id}' })
  .input(z.object({ id: Id }))
  .output(TaskSchema)
  .handler(async ({ input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

export const createTask = os
  .route({ method: 'POST', path: '/projects/{projectId}/tasks' })
  .input(CreateTaskInput)
  .output(TaskSchema)
  .handler(async ({ input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

export const updateTask = os
  .route({ method: 'PATCH', path: '/tasks/{id}' })
  .input(UpdateTaskInput)
  .output(TaskSchema)
  .handler(async ({ input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

export const deleteTask = os
  .route({ method: 'DELETE', path: '/tasks/{id}' })
  .input(z.object({ id: Id }))
  .output(z.object({ id: Id, deleted: z.literal(true) }))
  .handler(async ({ input }) => {
    // TODO: implement
    throw new Error('not implemented')
  })

/* -------------------------------------------------------------------------- */
/*                                   Router                                   */
/* -------------------------------------------------------------------------- */

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

export type AppRouter = typeof router
