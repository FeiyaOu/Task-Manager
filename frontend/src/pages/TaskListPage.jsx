import { useTasks } from '../hooks/useTasks'
import TaskTable from '../components/TaskTable.jsx'

export default function TaskListPage() {
  const { data: tasks, isLoading, isError } = useTasks()

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">All tasks</h1>
      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {isError && <p className="text-sm text-red-600">Failed to load tasks.</p>}
      {tasks && <TaskTable tasks={tasks} />}
    </div>
  )
}
