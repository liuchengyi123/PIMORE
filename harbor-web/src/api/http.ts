import { apiRoot } from './config'
import { catalogLangHeaders } from './catalogLang'

export interface HarborRequestOptions {
  method?: 'GET' | 'POST'
  data?: Record<string, unknown>
  headers?: Record<string, string>
  json?: boolean
  form?: boolean
  signal?: AbortSignal
}

export interface HarborResponse<T = unknown> {
  statusCode: number
  data: T
  header: Record<string, string>
}

export async function harborRequest<T = unknown>(
  path: string,
  opts: HarborRequestOptions = {},
): Promise<HarborResponse<T>> {
  const method = opts.method || 'GET'
  const root = apiRoot().replace(/\/$/, '')
  const url = root + (path.startsWith('/') ? path : '/' + path)

  const headers: Record<string, string> = { ...catalogLangHeaders(), ...(opts.headers || {}) }
  if (opts.json) {
    headers.Accept = headers.Accept || 'application/json'
    headers['X-Harbor-Ajax'] = '1'
  }

  let body: string | undefined
  if (method === 'POST') {
    const data = opts.data || {}
    if (opts.form) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded'
      body = Object.entries(data)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
    } else {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json'
      body = JSON.stringify(data)
    }
  }

  const res = await fetch(url, {
    method,
    headers,
    body,
    credentials: 'include',
    signal: opts.signal,
  })

  const ct = res.headers.get('content-type') || ''
  let data: any
  if (ct.includes('application/json')) data = await res.json()
  else {
    const text = await res.text()
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  const header: Record<string, string> = {}
  res.headers.forEach((v, k) => {
    header[k] = v
  })

  return { statusCode: res.status, data: data as T, header }
}
