import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'

import { FishSniperDeleteAccountConfirmModal } from '../../components/settings/FishSniperDeleteAccountConfirmModal.tsx'
import { useFishSniperDeleteAccountMutation } from '../../hooks/useFishSniperDeleteAccountMutation.ts'
import type { FishSniperSignedInOutletContextValue } from '../../layout/fishSniperSignedInOutletContext.ts'
import {
  fishSniperTacticalCardHeadingClassName,
  fishSniperTacticalCardClassName,
  fishSniperTacticalDangerButtonClassName,
  fishSniperTacticalMutedTextClassName,
} from '../../ui/fishSniperTacticalUi.ts'

export function FishSniperSettingsDeleteAccountPanel() {
  const navigate = useNavigate()
  const { fishSniperApiBaseUrl, fishSniperAccessTokenJwt, onSignOut } =
    useOutletContext<FishSniperSignedInOutletContextValue>()

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)

  const deleteAccountMutation = useFishSniperDeleteAccountMutation({
    apiBaseUrl: fishSniperApiBaseUrl,
    accessTokenJwt: fishSniperAccessTokenJwt,
    onUnauthorizedAccessToken: onSignOut,
  })

  const handleConfirmDelete = async () => {
    const didDeleteSucceed = await deleteAccountMutation.deleteFishSniperAccount()
    if (didDeleteSucceed) {
      setIsDeleteModalOpen(false)
      onSignOut()
      navigate('/', { replace: true })
    }
  }

  return (
    <section className={`${fishSniperTacticalCardClassName} space-y-5`}>
      <div>
        <h2 className={fishSniperTacticalCardHeadingClassName}>Delete Account</h2>
        <p className={`mt-2 ${fishSniperTacticalMutedTextClassName}`}>
          Permanently delete your FishSniper account and all associated fishing logs. This cannot
          be undone.
        </p>
      </div>

      <button
        type="button"
        className={fishSniperTacticalDangerButtonClassName}
        onClick={() => setIsDeleteModalOpen(true)}
      >
        Delete account
      </button>

      <FishSniperDeleteAccountConfirmModal
        isOpen={isDeleteModalOpen}
        isDeletingAccount={deleteAccountMutation.isDeletingAccount}
        deleteAccountHardFailureMessage={deleteAccountMutation.deleteAccountHardFailureMessage}
        onCancel={() => setIsDeleteModalOpen(false)}
        onConfirmDelete={() => void handleConfirmDelete()}
      />
    </section>
  )
}
