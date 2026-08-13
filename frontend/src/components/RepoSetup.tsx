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
        <div className="flex items-center gap-1.5">
          <h2 className="text-sm font-semibold">Repository analysis</h2>
          <span className="group relative inline-flex">
            <button
              type="button"
              aria-label="What does repository analysis do?"
              className="flex h-4 w-4 items-center justify-center rounded-full border border-slate-400 text-[10px] font-bold leading-none text-slate-500 hover:bg-slate-100"
            >
              i
            </button>
            <div className="pointer-events-none absolute left-1/2 top-6 z-10 hidden w-72 -translate-x-1/2 rounded-lg border bg-white p-3 text-xs font-normal text-slate-600 shadow-lg group-hover:block">
              <p className="mb-2">
                Reads the target repository's git history and builds the expertise
                map — who has worked on which modules. Submitting bugs is enabled
                once this is built.
              </p>
              <p className="mb-1">
                <span className="font-semibold text-slate-800">All history:</span>{' '}
                analyzes every commit since the last analysis (incremental — never
                misses commits).
              </p>
              <p>
                <span className="font-semibold text-slate-800">Last N days:</span>{' '}
                analyzes only commits from the last N days (a bounded window — can
                skip older commits that were never analyzed).
              </p>
            </div>
          </span>
        </div>
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

      {analyzed && status?.is_stale && (
        <p className="mt-2 rounded bg-amber-50 px-3 py-2 text-xs text-amber-800">
          The repository has new commits since the last analysis. Re-analyze to keep
          assignments current.
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
