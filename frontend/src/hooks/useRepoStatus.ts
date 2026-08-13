import { useQuery } from '@tanstack/react-query'
import { getRepoStatus } from '../api/client'

export function useRepoStatus() {
  return useQuery({ queryKey: ['repoStatus'], queryFn: getRepoStatus })
}
