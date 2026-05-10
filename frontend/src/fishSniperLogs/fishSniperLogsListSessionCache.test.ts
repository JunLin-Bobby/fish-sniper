import { describe, expect, it, beforeEach } from 'vitest'

import {
  FISH_SNIPER_LOGS_LIST_SESSION_STORAGE_KEY,
  invalidateFishSniperLogsListCacheInSessionStorage,
  readFishSniperLogsListCacheFromSessionStorage,
  writeFishSniperLogsListCacheToSessionStorage,
} from './fishSniperLogsListSessionCache.ts'

describe('fishSniperLogsListSessionCache', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('returns null when cache is empty', () => {
    expect(readFishSniperLogsListCacheFromSessionStorage()).toBeNull()
  })

  it('persists etag and serialized logs for conditional GET', () => {
    writeFishSniperLogsListCacheToSessionStorage({
      etag: 'W/"abc"',
      logsJson: '[{"log_id":"x"}]',
    })
    expect(readFishSniperLogsListCacheFromSessionStorage()).toEqual({
      etag: 'W/"abc"',
      logsJson: '[{"log_id":"x"}]',
    })
    expect(sessionStorage.getItem(FISH_SNIPER_LOGS_LIST_SESSION_STORAGE_KEY)).toBeTruthy()
  })

  it('invalidate removes cache so the next load performs a full GET', () => {
    writeFishSniperLogsListCacheToSessionStorage({
      etag: 'W/"old"',
      logsJson: '[]',
    })
    invalidateFishSniperLogsListCacheInSessionStorage()
    expect(readFishSniperLogsListCacheFromSessionStorage()).toBeNull()
  })

  it('returns null for corrupt JSON in sessionStorage', () => {
    sessionStorage.setItem(FISH_SNIPER_LOGS_LIST_SESSION_STORAGE_KEY, 'not-json')
    expect(readFishSniperLogsListCacheFromSessionStorage()).toBeNull()
  })
})
