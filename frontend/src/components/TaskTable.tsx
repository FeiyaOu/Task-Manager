import type { TaskRead } from '../api/types'

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
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t.task_id} className="border-t">
              <td className="px-4 py-2">{t.title}</td>
              <td className="px-4 py-2">{t.module || '—'}</td>
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
