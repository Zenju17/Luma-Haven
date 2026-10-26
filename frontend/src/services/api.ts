import { QueryClient } from '@tanstack/vue-query'

const base = '/api/v1'
export const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

function errorMessage(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(errorMessage).filter(Boolean).join(' ') || null
  if (value && typeof value === 'object') {
    const fields = value as Record<string, unknown>
    if ('detail' in fields) return errorMessage(fields.detail)
    return Object.entries(fields).map(([key, detail]) => `${key}: ${errorMessage(detail) ?? 'Invalid value'}`).join('; ') || null
  }
  return null
}

export async function api<T>(path: string, data?: unknown): Promise<T> {
  const isWrite = data !== undefined
  const headers: Record<string, string> = {}
  if (isWrite) {
    // Django rotates its CSRF token on staff login. Never cache it across sessions.
    const csrfResponse = await fetch(`${base}/auth/csrf`, { credentials: 'include' })
    if (!csrfResponse.ok) throw new Error('Unable to initialize your session. Refresh and retry.')
    const { csrfToken } = await csrfResponse.json() as { csrfToken: string }
    headers['Content-Type'] = 'application/json'
    headers['X-CSRFToken'] = csrfToken
  }
  const response = await fetch(`${base}${path}`, {
    credentials: 'include', method: isWrite ? 'POST' : 'GET', headers,
    body: isWrite ? JSON.stringify(data) : undefined,
  })
  const value: unknown = response.headers.get('content-type')?.includes('json') ? await response.json() : null
  if (!response.ok) throw new Error(errorMessage(value) ?? `Request failed (${response.status}). Refresh and retry.`)
  if (value === null) throw new Error('The server returned an unexpected response. Refresh and retry.')
  if (isWrite && (path.startsWith('/housekeeping/tasks/') || path.endsWith('/check-in') || path.endsWith('/check-out'))) {
    await queryClient.invalidateQueries({ queryKey: ['rooms'] })
  }
  return value as T
}
