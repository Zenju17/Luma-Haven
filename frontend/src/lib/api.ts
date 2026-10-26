export const apiBase = '/api/v1'

export function apiError(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(apiError).filter(Boolean).join(' ') || null
  if (value && typeof value === 'object') {
    const fields = value as Record<string, unknown>
    if ('detail' in fields) return apiError(fields.detail)
    return (
      Object.entries(fields)
        .map(([key, item]) => `${key}: ${apiError(item) ?? 'Invalid value'}`)
        .join('; ') || null
    )
  }
  return null
}

export async function api<T>(path: string, data?: unknown): Promise<T> {
  const isWrite = data !== undefined
  let headers: Record<string, string> = {}
  if (isWrite) {
    // Django rotates the CSRF token on staff login. Obtain a fresh token for
    // each write rather than reusing one from the previous session.
    const csrfResponse = await fetch(`${apiBase}/auth/csrf`, { credentials: 'include' })
    if (!csrfResponse.ok) throw new Error('Unable to initialize your session. Refresh and retry.')
    const { csrfToken } = (await csrfResponse.json()) as { csrfToken: string }
    headers = { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken }
  }
  const response = await fetch(`${apiBase}${path}`, {
    credentials: 'include',
    method: isWrite ? 'POST' : 'GET',
    headers,
    body: isWrite ? JSON.stringify(data) : undefined,
  })
  const json: unknown = response.headers.get('content-type')?.includes('json')
    ? await response.json()
    : null
  if (!response.ok) {
    throw new Error(apiError(json) ?? `Request failed (${response.status}). Refresh and retry.`)
  }
  if (json === null) throw new Error('The server returned an unexpected response. Refresh and retry.')
  return json as T
}

export function money(value: number): string {
  return `$${(value / 100).toFixed(2)}`
}
