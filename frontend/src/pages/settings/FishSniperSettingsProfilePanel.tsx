import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'

import { readEmailFromFishSniperAccessTokenJwt } from '../../auth/readEmailFromFishSniperAccessTokenJwt.ts'
import { useFishSniperSaveRegionOnboardingMutation } from '../../hooks/useFishSniperSaveRegionOnboardingMutation.ts'
import type { FishSniperSignedInOutletContextValue } from '../../layout/fishSniperSignedInOutletContext.ts'
import {
  fishSniperTacticalCardHeadingClassName,
  fishSniperTacticalCardClassName,
  fishSniperTacticalErrorBannerClassName,
  fishSniperTacticalFieldLabelClassName,
  fishSniperTacticalInputClassName,
  fishSniperTacticalMutedTextClassName,
  fishSniperTacticalPrimaryButtonClassName,
  fishSniperTacticalSuccessTextClassName,
} from '../../ui/fishSniperTacticalUi.ts'

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
    <section className={`${fishSniperTacticalCardClassName} space-y-6`}>
      <div>
        <h2 className={fishSniperTacticalCardHeadingClassName}>Profile</h2>
        <p className={`mt-2 ${fishSniperTacticalMutedTextClassName}`}>
          Your default region is used for weather on the strategy screen when you do not override
          it per trip.
        </p>
      </div>

      <div className="space-y-2">
        <span className={fishSniperTacticalFieldLabelClassName}>Email</span>
        <p className="text-sm text-slate-200">{displayEmail}</p>
      </div>

      <label htmlFor="settings-default-region" className={fishSniperTacticalFieldLabelClassName}>
        Default region
        <input
          id="settings-default-region"
          className={fishSniperTacticalInputClassName}
          placeholder="City name, e.g. Boston"
          value={profileRegionInput}
          onChange={(event) => setProfileRegionInput(event.target.value)}
        />
      </label>

      {saveRegionMutation.saveRegionHardFailureMessage ? (
        <p className={fishSniperTacticalErrorBannerClassName}>
          {saveRegionMutation.saveRegionHardFailureMessage}
        </p>
      ) : null}
      {saveSuccessMessage ? (
        <p className={fishSniperTacticalSuccessTextClassName}>{saveSuccessMessage}</p>
      ) : null}

      <button
        type="button"
        className={`${fishSniperTacticalPrimaryButtonClassName} max-w-xs`}
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
