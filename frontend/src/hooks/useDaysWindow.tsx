// Shared "last N days" window, set once (in RepoSetup) and reused by the All
// Tasks developer filter, so both features stay in sync without duplicating UI.
import { createContext, useContext, useState, type ReactNode } from 'react'

interface DaysWindowValue {
  useWindow: boolean
  setUseWindow: (value: boolean) => void
  days: number
  setDays: (value: number) => void
}

const DaysWindowContext = createContext<DaysWindowValue | null>(null)

export function DaysWindowProvider({ children }: { children: ReactNode }) {
  const [useWindow, setUseWindow] = useState(false) // false = all history
  const [days, setDays] = useState(30)

  return (
    <DaysWindowContext.Provider value={{ useWindow, setUseWindow, days, setDays }}>
      {children}
    </DaysWindowContext.Provider>
  )
}

export function useDaysWindow() {
  const ctx = useContext(DaysWindowContext)
  if (!ctx) throw new Error('useDaysWindow must be used within DaysWindowProvider')
  return ctx
}
