import { useState, type FormEvent } from 'react'
import ModuleDropdown from './ModuleDropdown'
import type { BugSubmit } from '../api/types'

interface Props {
  onSubmit: (bug: BugSubmit) => void
  isSubmitting: boolean
  ready: boolean
}

const SEVERITIES = ['low', 'medium', 'high', 'critical']

export default function BugForm({ onSubmit, isSubmitting, ready }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [module, setModule] = useState('')
  const [severity, setSeverity] = useState('medium')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit({ title, description, module: module || null, severity })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border bg-white p-6">
      <label className="block">
        <span className="mb-1 block text-sm font-medium">Title</span>
        <input
          className="w-full rounded border border-slate-300 px-3 py-2"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium">Description</span>
        <textarea
          className="w-full rounded border border-slate-300 px-3 py-2"
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
      </label>

      <ModuleDropdown value={module} onChange={setModule} />

      <label className="block">
        <span className="mb-1 block text-sm font-medium">Severity</span>
        <select
          className="w-full rounded border border-slate-300 px-3 py-2"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
        >
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>

      <button
        type="submit"
        disabled={isSubmitting || !ready}
        className="rounded bg-slate-900 px-4 py-2 text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Assigning…' : 'Submit bug'}
      </button>
      {!ready && (
        <p className="text-xs text-amber-700">
          Analyze the repository above to enable submission.
        </p>
      )}
    </form>
  )
}
