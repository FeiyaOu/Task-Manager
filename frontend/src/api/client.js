// One thin fetch wrapper per backend endpoint. Relative URLs are proxied to the
// FastAPI backend in dev (see vite.config.js).
async function request(path, options) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      // response had no JSON body
    }
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return res.json()
}

export const getModules = () => request('/api/modules')
export const getTasks = () => request('/api/tasks')
export const submitBug = (bug) =>
  request('/api/bugs', { method: 'POST', body: JSON.stringify(bug) })
export const getRepoStatus = () => request('/api/repo/status')
export const refreshRepo = (days) =>
  request(`/api/repo/refresh${days ? `?days=${days}` : ''}`, { method: 'POST' })
