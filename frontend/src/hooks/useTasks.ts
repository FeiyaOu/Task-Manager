import { useQuery } from '@tanstack/react-query'
import { getTasks } from '../api/client'

export function useTasks() {
  return useQuery({ queryKey: ['tasks'], queryFn: getTasks })
}
