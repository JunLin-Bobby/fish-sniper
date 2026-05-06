/** Passed from `FishSniperSignedInAppShell` to child routes via React Router `<Outlet />`. */

export interface FishSniperSignedInOutletContextValue {
  fishSniperApiBaseUrl: string
  fishSniperAccessTokenJwt: string
}
