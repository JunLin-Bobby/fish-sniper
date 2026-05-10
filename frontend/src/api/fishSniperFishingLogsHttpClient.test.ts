import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import { getFishSniperFishingLogsListWithEtag } from './fishSniperFishingLogsHttpClient.ts'

describe('getFishSniperFishingLogsListWithEtag', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { ETag: 'W/"full"' },
        }),
      ),
    )
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.unstubAllGlobals()
  })

  it('returns full list and etag on 200', async () => {
    const result = await getFishSniperFishingLogsListWithEtag({
      apiBaseUrl: 'http://api.test',
      accessTokenJwt: 'jwt',
      ifNoneMatch: null,
    })
    expect(result.outcome).toBe('full')
    if (result.outcome === 'full') {
      expect(result.etag).toBe('W/"full"')
      expect(result.logs).toEqual([])
    }
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://api.test/logs',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt',
        }),
      }),
    )
  })

  it('sends If-None-Match when provided', async () => {
    await getFishSniperFishingLogsListWithEtag({
      apiBaseUrl: 'http://api.test',
      accessTokenJwt: 'jwt',
      ifNoneMatch: 'W/"cached"',
    })
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://api.test/logs',
      expect.objectContaining({
        headers: expect.objectContaining({
          'If-None-Match': 'W/"cached"',
        }),
      }),
    )
  })

  it('returns not_modified on 304 without parsing body', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(null, {
          status: 304,
          headers: { ETag: 'W/"same"' },
        }),
      ),
    )
    const result = await getFishSniperFishingLogsListWithEtag({
      apiBaseUrl: 'http://api.test',
      accessTokenJwt: 'jwt',
      ifNoneMatch: 'W/"same"',
    })
    expect(result.outcome).toBe('not_modified')
    if (result.outcome === 'not_modified') {
      expect(result.etag).toBe('W/"same"')
    }
  })
})
