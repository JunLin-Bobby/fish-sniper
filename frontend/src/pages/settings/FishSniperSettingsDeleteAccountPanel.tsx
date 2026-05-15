import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'

import { FishSniperDeleteAccountConfirmModal } from '../../components/settings/FishSniperDeleteAccountConfirmModal.tsx'
import { useFishSniperDeleteAccountMutation } from '../../hooks/useFishSniperDeleteAccountMutation.ts'
import type { FishSniperSignedInOutletContextValue } from '../../layout/fishSniperSignedInOutletContext.ts'

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
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-100">Delete Account</h2>
        <p className="mt-2 text-sm leading-relaxed text-gray-400">
          Permanently delete your FishSniper account and all associated fishing logs. This cannot
          be undone.
        </p>
      </div>

      <button
        type="button"
        className="rounded-md border border-red-500/50 bg-red-600 px-4 py-2 text-sm font-bold tracking-wide text-white shadow-sm shadow-red-900/30 hover:bg-red-500 transition-colors cursor-pointer"
        onClick={() => setIsDeleteModalOpen(true)}
      >
        DELETE
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
