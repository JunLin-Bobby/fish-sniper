/**
 * Session cache for GET /logs ETag + JSON body (P3 Task 4).
 * Survives in-tab navigation; invalidated after mutations.
 */

export const FISH_SNIPER_LOGS_LIST_SESSION_STORAGE_KEY = 'fishSniper.logsList.v1'

export type FishSniperLogsListCachedSnapshot = {
  etag: string | null
  logsJson: string
}

type FishSniperLogsListCacheEnvelopeV1 = {
  v: 1
  etag: string | null
  logsJson: string
}

export function readFishSniperLogsListCacheFromSessionStorage(): FishSniperLogsListCachedSnapshot | null {
  try {
    const raw = sessionStorage.getItem(FISH_SNIPER_LOGS_LIST_SESSION_STORAGE_KEY)
    if (!raw) {
      return null
    }
    const parsedUnknown: unknown = JSON.parse(raw)
    if (
      typeof parsedUnknown !== 'object' ||
      parsedUnknown === null ||
      !('v' in parsedUnknown) ||
      (parsedUnknown as FishSniperLogsListCacheEnvelopeV1).v !== 1
    ) {
      return null
    }
    const envelope = parsedUnknown as FishSniperLogsListCacheEnvelopeV1
    if (typeof envelope.logsJson !== 'string') {
      return null
    }
    return { etag: envelope.etag, logsJson: envelope.logsJson }
  } catch {
    return null
  }
}

export function writeFishSniperLogsListCacheToSessionStorage(
  snapshot: FishSniperLogsListCachedSnapshot,
): void {
  const envelope: FishSniperLogsListCacheEnvelopeV1 = {
    v: 1,
    etag: snapshot.etag,
    logsJson: snapshot.logsJson,
  }
  sessionStorage.setItem(FISH_SNIPER_LOGS_LIST_SESSION_STORAGE_KEY, JSON.stringify(envelope))
}

export function invalidateFishSniperLogsListCacheInSessionStorage(): void {
  sessionStorage.removeItem(FISH_SNIPER_LOGS_LIST_SESSION_STORAGE_KEY)
}
