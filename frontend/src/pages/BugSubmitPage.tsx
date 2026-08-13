import { useSubmitBug } from '../hooks/useSubmitBug'
import BugForm from '../components/BugForm'
import SuccessCard from '../components/SuccessCard'

export default function BugSubmitPage() {
  const mutation = useSubmitBug()

  if (mutation.isSuccess) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Bug submitted</h1>
        <SuccessCard result={mutation.data} onReset={mutation.reset} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Submit a bug</h1>
      {mutation.isError && (
        <p className="rounded bg-red-50 px-4 py-2 text-sm text-red-700">
          {mutation.error.message}
        </p>
      )}
      <BugForm onSubmit={mutation.mutate} isSubmitting={mutation.isPending} />
    </div>
  )
}
