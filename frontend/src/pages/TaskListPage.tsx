import { useState } from 'react'
import { useTasks } from '../hooks/useTasks'
import { useDevelopers } from '../hooks/useDevelopers'
import { useDaysWindow } from '../hooks/useDaysWindow'
import TaskTable from '../components/TaskTable'

export default function TaskListPage() {
  const { data: tasks, isLoading, isError } = useTasks()
  const { useWindow, days } = useDaysWindow()
  const { data: developers } = useDevelopers(useWindow ? days : undefined)
  const [selectedDeveloper, setSelectedDeveloper] = useState('')

  const visibleTasks = selectedDeveloper
    ? tasks?.filter((t) => t.assigned_email === selectedDeveloper)
    : tasks

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">All tasks</h1>
        <select
          value={selectedDeveloper}
          onChange={(e) => setSelectedDeveloper(e.target.value)}
          className="rounded border border-slate-300 px-2 py-1 text-sm"
        >
          <option value="">All developers</option>
          {developers?.map((email) => (
            <option key={email} value={email}>
              {email}
            </option>
          ))}
        </select>
      </div>
      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {isError && <p className="text-sm text-red-600">Failed to load tasks.</p>}
      {visibleTasks && <TaskTable tasks={visibleTasks} />}
    </div>
  )
}
