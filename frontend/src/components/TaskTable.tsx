import type { TaskRead } from '../api/types'
import { useTaskResponse } from '../hooks/useTaskResponse'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-blue-100 text-blue-800',
  accepted: 'bg-green-100 text-green-800',
  declined: 'bg-red-100 text-red-800',
  unassigned: 'bg-amber-100 text-amber-800',
}

interface Props {
  tasks: TaskRead[]
}

export default function TaskTable({ tasks }: Props) {
  const { accept, decline } = useTaskResponse()

  if (!tasks.length) {
    return (
      <p className="text-sm text-slate-500">
        No tasks yet. Submit a bug to get started.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-100 text-left">
          <tr>
            <th className="px-4 py-2">Bug</th>
            <th className="px-4 py-2">Module</th>
            <th className="px-4 py-2">Assignee</th>
            <th className="px-4 py-2">Score</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => {
            const busy =
              (accept.isPending && accept.variables === t.task_id) ||
              (decline.isPending && decline.variables === t.task_id)
            return (
              <tr key={t.task_id} className="border-t">
                <td className="px-4 py-2">{t.title}</td>
                <td className="px-4 py-2">{t.modules.join(', ') || '—'}</td>
                <td className="px-4 py-2">{t.assigned_email || '—'}</td>
                <td className="px-4 py-2">
                  {t.score != null ? t.score.toFixed(2) : '—'}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs ${STATUS_STYLES[t.status] ?? ''}`}
                  >
                    {t.status}
                  </span>
                </td>
                <td className="px-4 py-2">
                  {t.status === 'pending' ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => accept.mutate(t.task_id)}
                        disabled={busy}
                        className="rounded bg-green-600 px-2 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        onClick={() => decline.mutate(t.task_id)}
                        disabled={busy}
                        className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                      >
                        Decline
                      </button>
                    </div>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

