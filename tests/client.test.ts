import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createApiClient, type ApiClient } from '../src/api/client'

describe('ApiClient', () => {
  let client: ApiClient

  beforeEach(() => {
    client = createApiClient('/api/v1', 'test-key')
  })

  it('adds auth header to requests', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await client.getStats()

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/stats/total',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-API-Key': 'test-key',
        }),
      }),
    )

    vi.unstubAllGlobals()
  })

  it('throws on non-ok response', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ error: 'unauthorized' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await expect(client.getStats()).rejects.toThrow()

    vi.unstubAllGlobals()
  })
})
