import { QueryClient } from '@tanstack/vue-query'

const base = '/api/v1'
type Portal = 'guest' | 'staff' | 'admin'
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

export async function api<T>(
  path: string,
  data?: unknown,
  portal: Portal = 'guest',
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
): Promise<T> {
  const isFormData = typeof FormData !== 'undefined' && data instanceof FormData
  const hasData = data !== undefined
  const resolvedMethod = method || (hasData ? 'POST' : 'GET')
  const isWrite = resolvedMethod !== 'GET'
  const headers: Record<string, string> = { 'X-Portal': portal }
  if (isWrite) {
    // Django rotates its CSRF token on staff login. Never cache it across sessions.
    const csrfResponse = await fetch(`${base}/auth/csrf`, { credentials: 'include', headers: { 'X-Portal': portal } })
    if (!csrfResponse.ok) throw new Error('Unable to initialize your session. Refresh and retry.')
    const { csrfToken } = await csrfResponse.json() as { csrfToken: string }
    if (!isFormData) {
      headers['Content-Type'] = 'application/json'
    }
    headers['X-CSRFToken'] = csrfToken
  }
  let body: BodyInit | undefined = undefined
  if (hasData) {
    body = isFormData ? (data as FormData) : JSON.stringify(data)
  }
  const response = await fetch(`${base}${path}`, {
    credentials: 'include', method: resolvedMethod, headers, body,
  })
  const value: unknown = response.headers.get('content-type')?.includes('json') ? await response.json() : null
  if (!response.ok) throw new Error(errorMessage(value) ?? `Request failed (${response.status}). Refresh and retry.`)
  if (value === null) throw new Error('The server returned an unexpected response. Refresh and retry.')
  if (isWrite && (path.startsWith('/housekeeping/tasks/') || path.endsWith('/check-in') || path.endsWith('/check-out'))) {
    await queryClient.invalidateQueries({ queryKey: ['rooms'] })
  }
  return value as T
}

export const staffApi = <T>(path: string, data?: unknown, method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE') =>
  api<T>(path, data, 'staff', method)
export const adminApi = <T>(path: string, data?: unknown, method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE') =>
  api<T>(path, data, 'admin', method)

