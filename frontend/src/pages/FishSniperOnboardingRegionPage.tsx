import { useState } from 'react'

import { useFishSniperSaveRegionOnboardingMutation } from '../hooks/useFishSniperSaveRegionOnboardingMutation.ts'
import { FishSniperTacticalAuthShell } from '../ui/FishSniperTacticalAuthShell.tsx'
import {
  fishSniperTacticalAuthCardClassName,
  fishSniperTacticalErrorBannerClassName,
  fishSniperTacticalFieldLabelClassName,
  fishSniperTacticalInputClassName,
  fishSniperTacticalPrimaryButtonClassName,
} from '../ui/fishSniperTacticalUi.ts'

export function FishSniperOnboardingRegionPage(options: {
  apiBaseUrl: string
  accessTokenJwt: string
  onOnboardingCompleted: () => void
}) {
  const [profileRegionInput, setProfileRegionInput] = useState('')

  const saveRegionMutation = useFishSniperSaveRegionOnboardingMutation({
    apiBaseUrl: options.apiBaseUrl,
    accessTokenJwt: options.accessTokenJwt,
  })

  const handleStartSniping = async () => {
    const trimmedRegion = profileRegionInput.trim()
    if (trimmedRegion.length === 0) {
      return
    }
    const didSaveSucceed = await saveRegionMutation.saveUserProfileRegionForOnboarding(
      trimmedRegion,
    )
    if (didSaveSucceed) {
      options.onOnboardingCompleted()
    }
  }

  return (
    <FishSniperTacticalAuthShell
      title="FishSniper"
      subtitle="Set your home region for auto weather on Mission brief."
    >
      <div className={fishSniperTacticalAuthCardClassName}>
        <label className={fishSniperTacticalFieldLabelClassName}>
          Home region
          <input
            className={fishSniperTacticalInputClassName}
            placeholder="City name, e.g. Boston"
            value={profileRegionInput}
            autoFocus
            onChange={(event) => setProfileRegionInput(event.target.value)}
          />
        </label>

        {saveRegionMutation.saveRegionHardFailureMessage ? (
          <p className={fishSniperTacticalErrorBannerClassName}>
            {saveRegionMutation.saveRegionHardFailureMessage}
          </p>
        ) : null}

        <button
          type="button"
          className={fishSniperTacticalPrimaryButtonClassName}
          disabled={saveRegionMutation.isSavingRegion || profileRegionInput.trim().length === 0}
          onClick={() => void handleStartSniping()}
        >
          {saveRegionMutation.isSavingRegion ? 'Saving…' : 'Start sniping'}
        </button>
      </div>
    </FishSniperTacticalAuthShell>
  )
}
