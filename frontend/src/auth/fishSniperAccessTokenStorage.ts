/** Browser persistence for the FishSniper JWT (P1). */

const FISH_SNIPER_ACCESS_TOKEN_LOCAL_STORAGE_KEY = 'fish_sniper_access_token_jwt_v1'

export function readFishSniperAccessTokenJwtFromBrowserStorage(): string | null {
  return window.localStorage.getItem(FISH_SNIPER_ACCESS_TOKEN_LOCAL_STORAGE_KEY)
}

export function writeFishSniperAccessTokenJwtToBrowserStorage(accessTokenJwt: string): void {
  window.localStorage.setItem(FISH_SNIPER_ACCESS_TOKEN_LOCAL_STORAGE_KEY, accessTokenJwt)
}

export function clearFishSniperAccessTokenJwtFromBrowserStorage(): void {
  window.localStorage.removeItem(FISH_SNIPER_ACCESS_TOKEN_LOCAL_STORAGE_KEY)
}
