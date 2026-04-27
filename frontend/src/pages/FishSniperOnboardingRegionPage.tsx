import { useState } from 'react'

import { useFishSniperSaveRegionOnboardingMutation } from '../hooks/useFishSniperSaveRegionOnboardingMutation.ts'

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
    <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-4">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-semibold">Set up your fishing profile</h1>
          <p className="text-sm text-gray-500">
            We use your home region for weather on the strategy screen (coming next).
          </p>
        </div>

        <input
          className="w-full rounded-md bg-gray-900 border border-gray-800 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          placeholder="City name, e.g. Boston"
          value={profileRegionInput}
          autoFocus
          onChange={(event) => setProfileRegionInput(event.target.value)}
        />

        {saveRegionMutation.saveRegionHardFailureMessage ? (
          <p className="text-sm text-red-400">{saveRegionMutation.saveRegionHardFailureMessage}</p>
        ) : null}

        <button
          type="button"
          className="w-full rounded-md bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-semibold py-2 text-sm disabled:opacity-50"
          disabled={saveRegionMutation.isSavingRegion || profileRegionInput.trim().length === 0}
          onClick={() => void handleStartSniping()}
        >
          {saveRegionMutation.isSavingRegion ? 'Saving…' : 'Start sniping'}
        </button>
      </div>
    </div>
  )
}
