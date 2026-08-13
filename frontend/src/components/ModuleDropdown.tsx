import { useModules } from '../hooks/useModules'

interface Props {
  value: string
  onChange: (value: string) => void
}

export default function ModuleDropdown({ value, onChange }: Props) {
  const { data: modules, isLoading, isError } = useModules()

  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium">Affected module</span>
      <select
        className="w-full rounded border border-slate-300 px-3 py-2"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select a module…</option>
        {(modules ?? []).map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      {isLoading && <span className="text-xs text-slate-500">Loading modules…</span>}
      {isError && (
        <span className="text-xs text-red-600">
          Could not load modules — analyze a repo first (POST /api/repo/refresh).
        </span>
      )}
    </label>
  )
}
