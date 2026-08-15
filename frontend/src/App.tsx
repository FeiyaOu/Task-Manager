import { Link, Route, Routes } from 'react-router-dom'
import BugSubmitPage from './pages/BugSubmitPage'
import TaskListPage from './pages/TaskListPage'
import { DaysWindowProvider } from './hooks/useDaysWindow'

export default function App() {
  return (
    <DaysWindowProvider>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b bg-white">
          <nav className="mx-auto flex max-w-4xl items-center gap-6 px-4 py-4">
            <span className="text-lg font-semibold">Task Manager</span>
            <Link to="/" className="text-sm text-slate-600 hover:text-slate-900">
              Submit bug
            </Link>
            <Link to="/tasks" className="text-sm text-slate-600 hover:text-slate-900">
              All tasks
            </Link>
          </nav>
        </header>
        <main className="mx-auto max-w-4xl px-4 py-8">
          <Routes>
            <Route path="/" element={<BugSubmitPage />} />
            <Route path="/tasks" element={<TaskListPage />} />
          </Routes>
        </main>
      </div>
    </DaysWindowProvider>
  )
}
