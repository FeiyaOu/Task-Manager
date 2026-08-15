import { useMutation, useQueryClient } from '@tanstack/react-query'
import { acceptTask, declineTask } from '../api/client'

export function useTaskResponse() {
  const queryClient = useQueryClient()
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['tasks'] })

  const accept = useMutation({ mutationFn: acceptTask, onSuccess: invalidate })
  const decline = useMutation({ mutationFn: declineTask, onSuccess: invalidate })
  return { accept, decline }
}
