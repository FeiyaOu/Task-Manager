// Shared types mirroring the backend API schemas.
export type TaskStatus = 'pending' | 'accepted' | 'declined' | 'unassigned'

export interface BugSubmit {
  title: string
  description: string
  module: string | null
  severity: string | null
}

export interface Candidate {
  developer_email: string
  score: number
  matched_modules: string[]
}

export interface AssignmentResult {
  bug_id: number
  task_id: number
  assigned_email: string | null
  score: number | null
  matched_modules: string[]
  status: TaskStatus
  match_tier: string | null
  candidates: Candidate[]
}

export interface TaskRead {
  task_id: number
  bug_id: number
  title: string
  module: string | null
  assigned_email: string | null
  score: number | null
  matched_modules: string[]
  status: TaskStatus
  match_tier: string | null
}
