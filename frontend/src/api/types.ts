// Shared types mirroring the backend API schemas.
export type TaskStatus = 'pending' | 'accepted' | 'declined' | 'unassigned'

export interface BugSubmit {
  title: string
  description: string
  modules: string[]
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
  modules: string[]
  assigned_email: string | null
  score: number | null
  matched_modules: string[]
  status: TaskStatus
  match_tier: string | null
  reassign_count: number
  declined_emails: string[]
}

export interface RepoStatus {
  repo_path: string
  last_analyzed_commit: string | null
  head_commit: string | null
  is_stale: boolean
  developer_count: number
  module_count: number
}

export interface RefreshResult {
  new_commits: number
  modules: number
}
