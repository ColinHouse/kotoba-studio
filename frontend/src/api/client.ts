export class ApiError extends Error {
  code: string
  status: number
  constructor(code: string, message: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

async function request<T>(method: string, path: string, body?: unknown, raw = false): Promise<T> {
  const init: RequestInit = { method, headers: {} }
  if (body instanceof FormData) {
    init.body = body
  } else if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(body)
  }
  let res: Response
  try {
    res = await fetch(BASE + path, init)
  } catch (err) {
    throw new ApiError('network', `无法连接服务器（${(err as Error).message}）`, 0)
  }
  if (raw) return res as unknown as T
  if (res.status === 204) return undefined as T
  const text = await res.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = null
  }
  if (!res.ok) {
    const env = (data as { error?: { code: string; message: string } } | null)?.error
    throw new ApiError(env?.code ?? 'http_error', env?.message ?? `HTTP ${res.status}`, res.status)
  }
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
  raw: (path: string, body?: unknown) => request<Response>('POST', path, body, true),
}

export function mediaUrl(path: string | null | undefined): string | undefined {
  return path ? `${BASE}/media/${path}` : undefined
}

export function wsUrl(path: string): string {
  const base = BASE || window.location.origin
  return base.replace(/^http/, 'ws') + path
}
