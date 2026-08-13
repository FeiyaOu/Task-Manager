import { useMutation, useQueryClient } from '@tanstack/react-query'
import { submitBug } from '../api/client'

export function useSubmitBug() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: submitBug,
    onSuccess: () => {
      // Refresh the task list so the new assignment shows up.
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}
