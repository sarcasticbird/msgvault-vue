import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createApiClient, ApiError, type ApiClient } from '../src/api/client'

describe('ApiClient', () => {
  let client: ApiClient
  let mockFetch: ReturnType<typeof vi.fn>

  function mockOk(data: unknown) {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(data),
    })
  }

  function mockError(status: number, body: Record<string, string>) {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status,
      json: () => Promise.resolve(body),
    })
  }

  beforeEach(() => {
    mockFetch = vi.fn()
    vi.stubGlobal('fetch', mockFetch)
    client = createApiClient('/api/v1', 'test-key')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('adds X-API-Key header when key provided', async () => {
    mockOk({ message_count: 0 })
    await client.getStats()

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/stats/total',
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-API-Key': 'test-key' }),
      }),
    )
  })

  it('omits auth header when no key', async () => {
    const noKeyClient = createApiClient('/api/v1')
    mockOk({})
    await noKeyClient.getStats()

    const headers = mockFetch.mock.calls[0][1].headers
    expect(headers).not.toHaveProperty('X-API-Key')
  })

  it('throws ApiError on non-ok response', async () => {
    mockError(401, { error: 'unauthorized' })

    try {
      await client.getStats()
      expect.fail('should have thrown')
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError)
      expect((e as ApiError).status).toBe(401)
    }
  })

  it('handles non-JSON error body gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('not json')),
    })

    await expect(client.getStats()).rejects.toThrow('unknown')
  })

  it('getAccounts calls correct path', async () => {
    mockOk({ accounts: [] })
    await client.getAccounts()
    expect(mockFetch.mock.calls[0][0]).toBe('/api/v1/accounts')
  })

  it('triggerSync sends POST with encoded email', async () => {
    mockOk({ status: 'accepted' })
    await client.triggerSync('user@example.com')

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/v1/sync/user%40example.com')
    expect(opts.method).toBe('POST')
  })

  it('getMessage calls correct path', async () => {
    mockOk({ id: 42, subject: 'test' })
    await client.getMessage(42)
    expect(mockFetch.mock.calls[0][0]).toBe('/api/v1/messages/42')
  })

  it('getAggregates builds query string', async () => {
    mockOk({ view_type: 'senders', rows: [] })
    await client.getAggregates({ view: 'senders', sort: 'count' })
    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/aggregates?')
    expect(mockFetch.mock.calls[0][0]).toContain('view=senders')
    expect(mockFetch.mock.calls[0][0]).toContain('sort=count')
  })

  it('getAggregates omits empty params', async () => {
    mockOk({ view_type: 'senders', rows: [] })
    await client.getAggregates({ view: 'senders', filter: '' })
    const url = mockFetch.mock.calls[0][0] as string
    expect(url).not.toContain('filter')
  })

  it('searchFast calls correct path', async () => {
    mockOk({ query: 'test', messages: [], total_count: 0 })
    await client.searchFast({ q: 'test' })
    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/search/fast?q=test')
  })

  it('searchDeep calls correct path', async () => {
    mockOk({ query: 'test', messages: [], count: 0, has_more: false, offset: 0, limit: 50 })
    await client.searchDeep({ q: 'test', offset: '0', limit: '50' })
    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/search/deep?')
  })

  it('getSchedulerStatus calls correct path', async () => {
    mockOk({ running: true, accounts: [] })
    await client.getSchedulerStatus()
    expect(mockFetch.mock.calls[0][0]).toBe('/api/v1/scheduler/status')
  })

  it('getFilteredMessages calls correct path', async () => {
    mockOk({ messages: [], count: 0, has_more: false, offset: 0, limit: 50 })
    await client.getFilteredMessages({ sender: 'test@example.com' })
    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/messages/filter?')
  })
})
