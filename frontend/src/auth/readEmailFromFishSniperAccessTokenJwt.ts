/**
 * Read display-only email from a FishSniper JWT payload (no signature verification).
 */

export function readEmailFromFishSniperAccessTokenJwt(
  accessTokenJwt: string,
): string | null {
  const tokenParts = accessTokenJwt.split('.')
  if (tokenParts.length < 2) {
    return null
  }
  try {
    const payloadBase64Url = tokenParts[1]
    const payloadBase64 = payloadBase64Url.replace(/-/g, '+').replace(/_/g, '/')
    const paddedPayloadBase64 =
      payloadBase64 + '='.repeat((4 - (payloadBase64.length % 4)) % 4)
    const payloadJson = atob(paddedPayloadBase64)
    const payloadUnknown: unknown = JSON.parse(payloadJson)
    if (
      typeof payloadUnknown === 'object' &&
      payloadUnknown !== null &&
      'email' in payloadUnknown &&
      typeof (payloadUnknown as { email: unknown }).email === 'string'
    ) {
      return (payloadUnknown as { email: string }).email
    }
  } catch {
    return null
  }
  return null
}
