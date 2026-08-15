import { useQuery } from '@tanstack/react-query'
import { getDevelopers } from '../api/client'

export function useDevelopers(days?: number) {
  return useQuery({
    queryKey: ['developers', days],
    queryFn: () => getDevelopers(days),
  })
}
