import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'

import { readEmailFromFishSniperAccessTokenJwt } from '../../auth/readEmailFromFishSniperAccessTokenJwt.ts'
import { useFishSniperSaveRegionOnboardingMutation } from '../../hooks/useFishSniperSaveRegionOnboardingMutation.ts'
import type { FishSniperSignedInOutletContextValue } from '../../layout/fishSniperSignedInOutletContext.ts'

export function FishSniperSettingsProfilePanel() {
  const {
    fishSniperApiBaseUrl,
    fishSniperAccessTokenJwt,
    userPreferences,
    reloadUserPreferences,
  } = useOutletContext<FishSniperSignedInOutletContextValue>()

  const [profileRegionInput, setProfileRegionInput] = useState(userPreferences?.region ?? '')
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null)

  const saveRegionMutation = useFishSniperSaveRegionOnboardingMutation({
    apiBaseUrl: fishSniperApiBaseUrl,
    accessTokenJwt: fishSniperAccessTokenJwt,
  })

  useEffect(() => {
    setProfileRegionInput(userPreferences?.region ?? '')
  }, [userPreferences?.region])

  const displayEmail =
    readEmailFromFishSniperAccessTokenJwt(fishSniperAccessTokenJwt) ?? 'Unknown'

  const handleSaveRegion = async () => {
    const trimmedRegion = profileRegionInput.trim()
    if (trimmedRegion.length === 0) {
      return
    }
    setSaveSuccessMessage(null)
    const didSaveSucceed = await saveRegionMutation.saveUserProfileRegionForOnboarding(
      trimmedRegion,
    )
    if (didSaveSucceed) {
      await reloadUserPreferences()
      setSaveSuccessMessage('Default region saved.')
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-100">Profile</h2>
        <p className="mt-1 text-sm leading-relaxed text-gray-400">
          Your default region is used for weather on the strategy screen when you do not override
          it per trip.
        </p>
      </div>

      <div className="space-y-2">
        <span className="block text-xs font-medium uppercase tracking-wide text-gray-500">
          Email
        </span>
        <p className="text-sm text-gray-300">{displayEmail}</p>
      </div>

      <div className="space-y-2">
        <label
          htmlFor="settings-default-region"
          className="block text-xs font-medium uppercase tracking-wide text-gray-400"
        >
          Default region
        </label>
        <input
          id="settings-default-region"
          className="w-full max-w-md rounded-md bg-gray-900 border border-gray-800 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          placeholder="City name, e.g. Boston"
          value={profileRegionInput}
          onChange={(event) => setProfileRegionInput(event.target.value)}
        />
      </div>

      {saveRegionMutation.saveRegionHardFailureMessage ? (
        <p className="text-sm text-red-400">{saveRegionMutation.saveRegionHardFailureMessage}</p>
      ) : null}
      {saveSuccessMessage ? (
        <p className="text-sm text-emerald-400">{saveSuccessMessage}</p>
      ) : null}

      <button
        type="button"
        className="rounded-md bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-semibold px-4 py-2 text-sm disabled:opacity-50"
        disabled={
          saveRegionMutation.isSavingRegion || profileRegionInput.trim().length === 0
        }
        onClick={() => void handleSaveRegion()}
      >
        {saveRegionMutation.isSavingRegion ? 'Saving…' : 'Save region'}
      </button>
    </section>
  )
}
