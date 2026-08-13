import { useModules } from '../hooks/useModules'

interface Props {
  value: string[]
  onChange: (value: string[]) => void
}

export default function ModuleDropdown({ value, onChange }: Props) {
  const { data: modules, isLoading, isError } = useModules()

  function toggle(m: string) {
    onChange(value.includes(m) ? value.filter((x) => x !== m) : [...value, m])
  }

  return (
    <div className="block">
      <span className="mb-1 block text-sm font-medium">
        Affected modules{' '}
        <span className="font-normal text-slate-500">(select any that apply)</span>
      </span>
      {isLoading && <span className="text-xs text-slate-500">Loading modules…</span>}
      {isError && (
        <span className="text-xs text-red-600">
          Could not load modules — analyze a repo first.
        </span>
      )}
      {modules && modules.length > 0 && (
        <div className="max-h-40 space-y-1 overflow-y-auto rounded border border-slate-300 p-2">
          {modules.map((m) => (
            <label key={m} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={value.includes(m)}
                onChange={() => toggle(m)}
              />
              {m}
            </label>
          ))}
        </div>
      )}
      {value.length > 0 && (
        <p className="mt-1 text-xs text-slate-500">Selected: {value.join(', ')}</p>
      )}
    </div>
  )
}
