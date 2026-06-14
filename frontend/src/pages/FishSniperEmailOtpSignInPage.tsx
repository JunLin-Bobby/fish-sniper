/**
 * [暫時棄用 — Email OTP / Resend]
 * 尚未有付費 email 服務與已驗證寄件網域，無法寄 OTP；登入改 Google OAuth。
 * UI 保留，待開通 Resend 與網域後可恢復。顯示與否由 readFishSniperShouldShowEmailOtpLoginFromEnv 控制。
 */
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import type {
  SendEmailOtpResponsePayload,
  VerifyEmailOtpResponsePayload,
} from '../api/fishSniperApiTypes.ts'
import {
  FishSniperHttpStatusError,
  FishSniperHttpTimeoutError,
  postJsonWithFishSniperApi,
} from '../api/fishSniperJsonHttpClient.ts'
import { beginGoogleOAuthAuthorizationFlowFromBrowser } from '../auth/fishSniperGoogleOAuthPkce.ts'
import {
  readFishSniperGoogleOAuthPublicConfigFromEnvOrNull,
  readFishSniperShouldShowEmailOtpLoginFromEnv,
} from '../config/readFishSniperPublicEnv.ts'
import { FishSniperTacticalAuthShell } from '../ui/FishSniperTacticalAuthShell.tsx'
import {
  fishSniperTacticalAuthCardClassName,
  fishSniperTacticalErrorBannerClassName,
  fishSniperTacticalGoogleButtonClassName,
  fishSniperTacticalInputClassName,
  fishSniperTacticalMutedTextClassName,
  fishSniperTacticalOtpInputClassName,
  fishSniperTacticalPrimaryButtonClassName,
} from '../ui/fishSniperTacticalUi.ts'

function isLikelyValidEmailAddress(rawEmailAddress: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(rawEmailAddress.trim())
}

function sanitizeSingleOtpDigitChar(rawInputValue: string): string {
  if (rawInputValue.length === 0) {
    return ''
  }
  const lastChar = rawInputValue.slice(-1)
  return /\d/.test(lastChar) ? lastChar : ''
}

export function FishSniperEmailOtpSignInPage(options: {
  apiBaseUrl: string
  onAuthenticatedWithAccessToken: (accessTokenJwt: string) => void
}) {
  const [emailAddressInput, setEmailAddressInput] = useState('')
  const [activeSignInStep, setActiveSignInStep] = useState<'email' | 'otp'>('email')

  const [otpDigitCharList, setOtpDigitCharList] = useState<string[]>(() => {
    return ['', '', '', '', '', '']
  })

  const otpInputElementRefList = useRef<Array<HTMLInputElement | null>>([
    null,
    null,
    null,
    null,
    null,
    null,
  ])

  const [sendOtpHardFailureMessage, setSendOtpHardFailureMessage] = useState<string | null>(null)
  const [verifyOtpHardFailureMessage, setVerifyOtpHardFailureMessage] = useState<string | null>(null)
  const [isSendingEmailOtp, setIsSendingEmailOtp] = useState(false)
  const [isVerifyingEmailOtp, setIsVerifyingEmailOtp] = useState(false)

  const [resendCooldownSecondsRemaining, setResendCooldownSecondsRemaining] = useState(0)
  const [googleSignInHardFailureMessage, setGoogleSignInHardFailureMessage] = useState<
    string | null
  >(null)
  const googleOAuthPublicConfig = useMemo(
    () => readFishSniperGoogleOAuthPublicConfigFromEnvOrNull(),
    [],
  )
  const shouldShowEmailOtpLoginBlock = useMemo(
    () => readFishSniperShouldShowEmailOtpLoginFromEnv(),
    [],
  )

  const handleClickContinueWithGoogle = async (): Promise<void> => {
    setGoogleSignInHardFailureMessage(null)
    if (!googleOAuthPublicConfig) {
      setGoogleSignInHardFailureMessage('Google sign-in is not configured for this environment.')
      return
    }
    try {
      await beginGoogleOAuthAuthorizationFlowFromBrowser({
        clientId: googleOAuthPublicConfig.clientId,
        redirectUri: googleOAuthPublicConfig.redirectUri,
      })
    } catch {
      setGoogleSignInHardFailureMessage('Could not start the Google sign-in flow. Please try again.')
    }
  }

  const mergedOtpSixDigits = useMemo(() => {
    return otpDigitCharList.join('')
  }, [otpDigitCharList])

  useEffect(() => {
    if (resendCooldownSecondsRemaining <= 0) {
      return undefined
    }
    const intervalId = window.setInterval(() => {
      setResendCooldownSecondsRemaining((previousSeconds) => Math.max(0, previousSeconds - 1))
    }, 1000)
    return () => window.clearInterval(intervalId)
  }, [resendCooldownSecondsRemaining === 0])

  const focusOtpDigitInputAtIndex = (digitIndex: number) => {
    const targetInput = otpInputElementRefList.current[digitIndex]
    targetInput?.focus()
    targetInput?.select()
  }

  const handleSendEmailOtp = async () => {
    setSendOtpHardFailureMessage(null)
    if (!isLikelyValidEmailAddress(emailAddressInput)) {
      setSendOtpHardFailureMessage('Please enter a valid email address')
      return
    }

    setIsSendingEmailOtp(true)
    try {
      await postJsonWithFishSniperApi<SendEmailOtpResponsePayload>({
        apiBaseUrl: options.apiBaseUrl,
        path: '/auth/send-otp',
        requestBody: { email: emailAddressInput.trim() },
      })
    } catch (unknownError) {
      if (unknownError instanceof FishSniperHttpStatusError) {
        setSendOtpHardFailureMessage(unknownError.responseBodyText)
      } else if (unknownError instanceof FishSniperHttpTimeoutError) {
        setSendOtpHardFailureMessage(unknownError.message)
      } else {
        setSendOtpHardFailureMessage('Could not send the verification code. Please try again.')
      }
      setIsSendingEmailOtp(false)
      return
    }

    setIsSendingEmailOtp(false)
    setActiveSignInStep('otp')
    setOtpDigitCharList(['', '', '', '', '', ''])
    setResendCooldownSecondsRemaining(60)
    window.setTimeout(() => focusOtpDigitInputAtIndex(0), 0)
  }

  const handleVerifyEmailOtp = async () => {
    setVerifyOtpHardFailureMessage(null)
    if (mergedOtpSixDigits.length !== 6) {
      setVerifyOtpHardFailureMessage('Please enter the full 6-digit code.')
      return
    }

    setIsVerifyingEmailOtp(true)
    try {
      const verifyResponse = await postJsonWithFishSniperApi<VerifyEmailOtpResponsePayload>({
        apiBaseUrl: options.apiBaseUrl,
        path: '/auth/verify-otp',
        requestBody: {
          email: emailAddressInput.trim(),
          otp: mergedOtpSixDigits,
        },
      })
      options.onAuthenticatedWithAccessToken(verifyResponse.access_token)
    } catch (unknownError) {
      if (unknownError instanceof FishSniperHttpStatusError) {
        setVerifyOtpHardFailureMessage('Invalid or expired code. Please try again.')
      } else if (unknownError instanceof FishSniperHttpTimeoutError) {
        setVerifyOtpHardFailureMessage(unknownError.message)
      } else {
        setVerifyOtpHardFailureMessage('Could not verify the code. Please try again.')
      }
    } finally {
      setIsVerifyingEmailOtp(false)
    }
  }

  const handleOtpDigitChangedAtIndex = (digitIndex: number, rawInputValue: string) => {
    const nextDigitChar = sanitizeSingleOtpDigitChar(rawInputValue)
    setOtpDigitCharList((previousDigitList) => {
      const nextDigitList = [...previousDigitList]
      nextDigitList[digitIndex] = nextDigitChar
      return nextDigitList
    })
    if (nextDigitChar.length === 1 && digitIndex < 5) {
      focusOtpDigitInputAtIndex(digitIndex + 1)
    }
  }

  const handleOtpDigitKeyDownAtIndex = (
    digitIndex: number,
    keyboardEvent: KeyboardEvent<HTMLInputElement>,
  ) => {
    if (keyboardEvent.key === 'Backspace') {
      if (otpDigitCharList[digitIndex] === '' && digitIndex > 0) {
        focusOtpDigitInputAtIndex(digitIndex - 1)
      }
    }
  }

  return (
    <FishSniperTacticalAuthShell
      title="FishSniper"
      subtitle={
        activeSignInStep === 'email'
          ? shouldShowEmailOtpLoginBlock
            ? 'Continue with Google, or use email to receive a verification code.'
            : 'Continue with your Google account.'
          : `We sent a 6-digit code to ${emailAddressInput.trim()}`
      }
    >
      <div className={fishSniperTacticalAuthCardClassName}>
        {activeSignInStep === 'email' && googleOAuthPublicConfig ? (
          <div className="space-y-3">
            <button
              type="button"
              className={fishSniperTacticalGoogleButtonClassName}
              onClick={() => void handleClickContinueWithGoogle()}
            >
              Continue with Google
            </button>
            {googleSignInHardFailureMessage ? (
              <p className={fishSniperTacticalErrorBannerClassName}>{googleSignInHardFailureMessage}</p>
            ) : null}
            {shouldShowEmailOtpLoginBlock ? (
              <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-500">
                <span className="h-px flex-1 bg-white/10" />
                or use email
                <span className="h-px flex-1 bg-white/10" />
              </div>
            ) : null}
          </div>
        ) : null}

        {shouldShowEmailOtpLoginBlock && activeSignInStep === 'email' ? (
          <div className="space-y-3">
            <input
              className={fishSniperTacticalInputClassName}
              type="email"
              placeholder="you@example.com"
              value={emailAddressInput}
              autoFocus
              onChange={(event) => setEmailAddressInput(event.target.value)}
            />
            {sendOtpHardFailureMessage ? (
              <p className={fishSniperTacticalErrorBannerClassName}>{sendOtpHardFailureMessage}</p>
            ) : null}
            <button
              type="button"
              className={fishSniperTacticalPrimaryButtonClassName}
              disabled={isSendingEmailOtp}
              onClick={() => void handleSendEmailOtp()}
            >
              {isSendingEmailOtp ? 'Sending…' : 'Send code'}
            </button>
          </div>
        ) : null}

        {activeSignInStep === 'otp' ? (
          <div className="space-y-4">
            <div className="grid grid-cols-6 gap-2">
              {otpDigitCharList.map((digitChar, digitIndex) => (
                <input
                  key={`fish-sniper-otp-slot-${digitIndex}`}
                  ref={(element) => {
                    otpInputElementRefList.current[digitIndex] = element
                  }}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  className={fishSniperTacticalOtpInputClassName}
                  value={digitChar}
                  maxLength={1}
                  onChange={(event) =>
                    handleOtpDigitChangedAtIndex(digitIndex, event.target.value)
                  }
                  onKeyDown={(event) => handleOtpDigitKeyDownAtIndex(digitIndex, event)}
                />
              ))}
            </div>

            {verifyOtpHardFailureMessage ? (
              <p className={fishSniperTacticalErrorBannerClassName}>{verifyOtpHardFailureMessage}</p>
            ) : null}

            <button
              type="button"
              className={fishSniperTacticalPrimaryButtonClassName}
              disabled={isVerifyingEmailOtp}
              onClick={() => void handleVerifyEmailOtp()}
            >
              {isVerifyingEmailOtp ? 'Verifying…' : 'Verify'}
            </button>

            <div className="text-center text-sm">
              <button
                type="button"
                className="cursor-pointer text-[#5dff9a] transition-colors duration-200 hover:text-[#3dff8a] disabled:cursor-not-allowed disabled:text-slate-600"
                disabled={resendCooldownSecondsRemaining > 0 || isSendingEmailOtp}
                onClick={() => void handleSendEmailOtp()}
              >
                {resendCooldownSecondsRemaining > 0
                  ? `Resend code (${resendCooldownSecondsRemaining}s)`
                  : 'Resend code'}
              </button>
            </div>

            <button
              type="button"
              className={`w-full ${fishSniperTacticalMutedTextClassName} transition-colors duration-200 hover:text-slate-200`}
              onClick={() => {
                setActiveSignInStep('email')
                setVerifyOtpHardFailureMessage(null)
                setOtpDigitCharList(['', '', '', '', '', ''])
              }}
            >
              Use a different email
            </button>
          </div>
        ) : null}
      </div>
    </FishSniperTacticalAuthShell>
  )
}
