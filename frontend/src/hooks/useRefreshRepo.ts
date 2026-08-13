import { useMutation, useQueryClient } from '@tanstack/react-query'
import { refreshRepo } from '../api/client'

export function useRefreshRepo() {
  const queryClient = useQueryClient()
  return useMutation({
    // undefined days = analyze all history.
    mutationFn: (days?: number) => refreshRepo(days),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repoStatus'] })
      queryClient.invalidateQueries({ queryKey: ['modules'] })
    },
  })
}
