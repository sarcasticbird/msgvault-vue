// API response types — match msgvault /api/v1 JSON shapes

export interface TotalStats {
  message_count: number
  total_size: number
  attachment_count: number
  attachment_size: number
  label_count: number
  account_count: number
}

export interface AccountInfo {
  id: number
  email: string
  display_name?: string
  last_sync_at?: string
  last_sync_with_data_at?: string
  next_sync_at?: string
  schedule?: string
  enabled: boolean
}

export interface MessageSummary {
  id: number
  conversation_id?: number
  subject: string
  from: string
  to: string[]
  cc?: string[]
  bcc?: string[]
  sent_at: string
  deleted_at?: string
  snippet: string
  labels: string[]
  has_attachments: boolean
  size_bytes: number
}

export interface MessageDetail extends MessageSummary {
  body: string
  body_html?: string
  attachments: AttachmentInfo[]
}

export interface AttachmentInfo {
  filename: string
  mime_type: string
  size_bytes: number
}

export interface AggregateRow {
  key: string
  count: number
  total_size: number
  attachment_size: number
  attachment_count: number
  total_unique: number
}

export interface AggregateResponse {
  view_type: string
  rows: AggregateRow[]
}

export interface FilteredMessagesResponse {
  count: number
  has_more: boolean
  offset: number
  limit: number
  messages: MessageSummary[]
}

export interface SearchFastResponse {
  query: string
  messages: MessageSummary[]
  total_count: number
  stats?: TotalStats
}

export interface SearchDeepResponse {
  query: string
  messages: MessageSummary[]
  count: number
  has_more: boolean
  offset: number
  limit: number
}

export interface SchedulerStatus {
  running: boolean
  accounts: SchedulerAccountStatus[]
}

export interface SchedulerAccountStatus {
  email: string
  running: boolean
  last_run: string
  next_run: string
  last_error?: string
  schedule: string
}

export interface ApiClient {
  getStats(): Promise<TotalStats>
  getAccounts(): Promise<{ accounts: AccountInfo[] }>
  triggerSync(account: string): Promise<{ status: string; message: string }>
  getSchedulerStatus(): Promise<SchedulerStatus>
  getAggregates(params: Record<string, string>): Promise<AggregateResponse>
  getSubAggregates(params: Record<string, string>): Promise<AggregateResponse>
  getFilteredMessages(params: Record<string, string>): Promise<FilteredMessagesResponse>
  getMessage(id: number): Promise<MessageDetail>
  searchFast(params: Record<string, string>): Promise<SearchFastResponse>
  searchDeep(params: Record<string, string>): Promise<SearchDeepResponse>
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function createApiClient(baseUrl: string, apiKey?: string): ApiClient {
  async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...(apiKey ? { 'X-API-Key': apiKey } : {}),
    }
    const res = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers: { ...headers, ...((options?.headers as Record<string, string>) ?? {}) },
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({ error: 'unknown' }))
      throw new ApiError(res.status, body.message || body.error || `HTTP ${res.status}`)
    }
    return res.json()
  }

  function qs(params: Record<string, string>): string {
    const entries = Object.entries(params).filter(([, v]) => v != null && v !== '')
    if (entries.length === 0) return ''
    return '?' + new URLSearchParams(entries).toString()
  }

  return {
    getStats: () => request('/stats/total'),
    getAccounts: () => request('/accounts'),
    triggerSync: (account) =>
      request(`/sync/${encodeURIComponent(account)}`, { method: 'POST' }),
    getSchedulerStatus: () => request('/scheduler/status'),
    getAggregates: (params) => request(`/aggregates${qs(params)}`),
    getSubAggregates: (params) => request(`/aggregates/sub${qs(params)}`),
    getFilteredMessages: (params) => request(`/messages/filter${qs(params)}`),
    getMessage: (id) => request(`/messages/${id}`),
    searchFast: (params) => request(`/search/fast${qs(params)}`),
    searchDeep: (params) => request(`/search/deep${qs(params)}`),
  }
}

export const api = createApiClient(
  import.meta.env.VITE_API_URL || '/api/v1',
  import.meta.env.VITE_API_KEY || undefined,
)
