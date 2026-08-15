import type {
  AssignmentResult,
  BugSubmit,
  RefreshResult,
  RepoStatus,
  TaskRead,
} from './types'

// One thin fetch wrapper per backend endpoint. Relative URLs are proxied to the
// FastAPI backend in dev (see vite.config.ts).
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail: string | undefined
    try {
      detail = (await res.json()).detail
    } catch {
      // response had no JSON body
    }
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return (await res.json()) as T
}

export const getModules = () => request<string[]>('/api/modules')
export const getTasks = () => request<TaskRead[]>('/api/tasks')
export const submitBug = (bug: BugSubmit) =>
  request<AssignmentResult>('/api/bugs', {
    method: 'POST',
    body: JSON.stringify(bug),
  })
export const getRepoStatus = () => request<RepoStatus>('/api/repo/status')
export const refreshRepo = (days?: number) =>
  request<RefreshResult>(
    `/api/repo/refresh${days ? `?days=${days}` : ''}`,
    { method: 'POST' },
  )
export const acceptTask = (taskId: number) =>
  request<TaskRead>(`/api/tasks/${taskId}/accept`, { method: 'POST' })
export const declineTask = (taskId: number) =>
  request<TaskRead>(`/api/tasks/${taskId}/decline`, { method: 'POST' })
export const getDevelopers = (days?: number) =>
  request<string[]>(`/api/developers${days ? `?days=${days}` : ''}`)
