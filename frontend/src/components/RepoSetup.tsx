import { useState } from 'react'
import { useRepoStatus } from '../hooks/useRepoStatus'
import { useRefreshRepo } from '../hooks/useRefreshRepo'

export default function RepoSetup() {
  const { data: status, isLoading } = useRepoStatus()
  const refresh = useRefreshRepo()
  const [useWindow, setUseWindow] = useState(false) // false = all history
  const [days, setDays] = useState(30)

  const analyzed = (status?.module_count ?? 0) > 0

  function handleAnalyze() {
    // A window larger than the repo's history simply includes everything, so
    // this naturally falls back to "all" on the backend.
    refresh.mutate(useWindow ? days : undefined)
  }

  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Repository analysis</h2>
        {isLoading ? (
          <span className="text-xs text-slate-500">Checking…</span>
        ) : analyzed ? (
          <span className="text-xs text-green-700">
            ✓ {status?.developer_count} developers · {status?.module_count} modules
            {status?.last_analyzed_commit
              ? ` · @${status.last_analyzed_commit.slice(0, 7)}`
              : ''}
          </span>
        ) : (
          <span className="text-xs text-amber-700">Not analyzed yet</span>
        )}
      </div>

      {!analyzed && !isLoading && (
        <p className="mt-1 text-xs text-slate-500">
          Analyze the repository to build the expertise map before submitting bugs.
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            checked={!useWindow}
            onChange={() => setUseWindow(false)}
          />
          All history
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            checked={useWindow}
            onChange={() => setUseWindow(true)}
          />
          Last
          <input
            type="number"
            min={1}
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            disabled={!useWindow}
            className="w-20 rounded border border-slate-300 px-2 py-1 disabled:bg-slate-100"
          />
          days
        </label>
        <button
          onClick={handleAnalyze}
          disabled={refresh.isPending}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {refresh.isPending
            ? 'Analyzing…'
            : analyzed
              ? 'Re-analyze'
              : 'Analyze repository'}
        </button>
      </div>

      {refresh.isPending && (
        <p className="mt-2 text-xs text-slate-500">
          Reading git history and building the expertise map… large repos can take
          a while.
        </p>
      )}
      {refresh.isError && (
        <p className="mt-2 text-xs text-red-600">{refresh.error?.message}</p>
      )}
      {refresh.isSuccess && !refresh.isPending && (
        <p className="mt-2 text-xs text-green-700">
          Analyzed {refresh.data.new_commits} new commits · {refresh.data.modules}{' '}
          modules.
        </p>
      )}
    </div>
  )
}
