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
    <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-emerald-400 tracking-tight">FishSniper</h1>
          {activeSignInStep === 'email' ? (
            <>
              <h2 className="text-xl font-semibold">Sign in to FishSniper</h2>
              <p className="text-sm text-gray-500">
                Enter your email to receive a verification code
              </p>
            </>
          ) : (
            <>
              <h2 className="text-xl font-semibold">Check your email</h2>
              <p className="text-sm text-gray-500">
                We sent a 6-digit code to {emailAddressInput.trim()}
              </p>
            </>
          )}
        </div>

        {activeSignInStep === 'email' ? (
          <div className="space-y-3">
            <input
              className="w-full rounded-md bg-gray-900 border border-gray-800 px-3 py-2 text-sm outline-none focus:border-emerald-500"
              type="email"
              placeholder="you@example.com"
              value={emailAddressInput}
              autoFocus
              onChange={(event) => setEmailAddressInput(event.target.value)}
            />
            {sendOtpHardFailureMessage ? (
              <p className="text-sm text-red-400">{sendOtpHardFailureMessage}</p>
            ) : null}
            <button
              type="button"
              className="w-full rounded-md bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-semibold py-2 text-sm disabled:opacity-50"
              disabled={isSendingEmailOtp}
              onClick={() => void handleSendEmailOtp()}
            >
              {isSendingEmailOtp ? 'Sending…' : 'Send code'}
            </button>
          </div>
        ) : (
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
                  className="w-full text-center rounded-md bg-gray-900 border border-gray-800 py-2 text-lg outline-none focus:border-emerald-500"
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
              <p className="text-sm text-red-400">{verifyOtpHardFailureMessage}</p>
            ) : null}

            <button
              type="button"
              className="w-full rounded-md bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-semibold py-2 text-sm disabled:opacity-50"
              disabled={isVerifyingEmailOtp}
              onClick={() => void handleVerifyEmailOtp()}
            >
              {isVerifyingEmailOtp ? 'Verifying…' : 'Verify'}
            </button>

            <div className="text-center text-sm">
              <button
                type="button"
                className="text-emerald-400 disabled:text-gray-600 disabled:cursor-not-allowed"
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
              className="w-full text-sm text-gray-500 hover:text-gray-300"
              onClick={() => {
                setActiveSignInStep('email')
                setVerifyOtpHardFailureMessage(null)
                setOtpDigitCharList(['', '', '', '', '', ''])
              }}
            >
              Use a different email
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
