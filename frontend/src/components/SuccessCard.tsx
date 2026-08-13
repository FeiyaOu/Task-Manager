import { Link } from 'react-router-dom'
import type { AssignmentResult } from '../api/types'

interface Props {
  result: AssignmentResult
  onReset: () => void
}

export default function SuccessCard({ result, onReset }: Props) {
  const assigned = result.status !== 'unassigned' && result.assigned_email

  return (
    <div className="rounded-lg border bg-white p-6">
      {assigned ? (
        <>
          <h2 className="text-lg font-semibold text-green-700">
            Assigned to {result.assigned_email}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Score {result.score?.toFixed(2)} · matched{' '}
            {result.matched_modules.join(', ') || '—'}
            {result.match_tier ? ` · via ${result.match_tier} match` : ''}
          </p>
        </>
      ) : (
        <>
          <h2 className="text-lg font-semibold text-amber-700">
            No confident match — left unassigned
          </h2>
          <p className="mt-1 text-sm text-slate-600">Needs manual triage.</p>
        </>
      )}

      {result.candidates.length > 1 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-slate-700">Other candidates</h3>
          <ul className="mt-1 space-y-1 text-sm text-slate-600">
            {result.candidates.slice(1, 4).map((c) => (
              <li key={c.developer_email}>
                {c.developer_email} — {c.score.toFixed(2)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 flex gap-3">
        <button
          onClick={onReset}
          className="rounded border px-4 py-2 text-sm hover:bg-slate-50"
        >
          Submit another
        </button>
        <Link
          to="/tasks"
          className="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700"
        >
          View tasks
        </Link>
      </div>
    </div>
  )
}
