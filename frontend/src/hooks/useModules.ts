import { useQuery } from '@tanstack/react-query'
import { getModules } from '../api/client'

export function useModules() {
  return useQuery({ queryKey: ['modules'], queryFn: getModules })
}
