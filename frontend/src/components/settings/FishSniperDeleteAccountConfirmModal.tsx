import { useEffect, useState, type ReactNode } from 'react'

type FishSniperDeleteAccountModalStep = 'confirm_intent' | 'type_delete'

export function FishSniperDeleteAccountConfirmModal(options: {
  isOpen: boolean
  isDeletingAccount: boolean
  deleteAccountHardFailureMessage: string | null
  onCancel: () => void
  onConfirmDelete: () => void
}) {
  const [modalStep, setModalStep] =
    useState<FishSniperDeleteAccountModalStep>('confirm_intent')
  const [typedConfirmation, setTypedConfirmation] = useState('')

  useEffect(() => {
    if (!options.isOpen) {
      setModalStep('confirm_intent')
      setTypedConfirmation('')
    }
  }, [options.isOpen])

  if (!options.isOpen) {
    return null
  }

  const resetAndClose = () => {
    setModalStep('confirm_intent')
    setTypedConfirmation('')
    options.onCancel()
  }

  return (
    <FishSniperModalBackdrop onBackdropClick={resetAndClose}>
      {modalStep === 'confirm_intent' ? (
        <>
          <h2 className="text-lg font-semibold text-gray-100">Delete your account?</h2>
          <ul className="list-disc pl-5 text-sm text-gray-300 space-y-1">
            <li>Your fishing logs and preferences will be permanently removed.</li>
            <li>You will be signed out immediately.</li>
            <li>This action cannot be undone.</li>
          </ul>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-200 hover:bg-gray-800"
              onClick={resetAndClose}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded-md bg-red-600 hover:bg-red-500 text-white font-semibold px-3 py-2 text-sm"
              onClick={() => {
                setModalStep('type_delete')
                setTypedConfirmation('')
              }}
            >
              Continue
            </button>
          </div>
        </>
      ) : (
        <>
          <h2 className="text-lg font-semibold text-gray-100">Confirm account deletion</h2>
          <p className="text-sm text-gray-300">
            Type <span className="font-mono font-semibold text-gray-100">Delete</span> to confirm.
          </p>
          <input
            className="w-full rounded-md bg-gray-950 border border-gray-700 px-3 py-2 text-sm outline-none focus:border-red-500 font-mono"
            value={typedConfirmation}
            autoComplete="off"
            spellCheck={false}
            autoFocus
            onChange={(event) => setTypedConfirmation(event.target.value)}
            onPaste={(event) => event.preventDefault()}
            onDrop={(event) => event.preventDefault()}
            onContextMenu={(event) => event.preventDefault()}
          />
          {options.deleteAccountHardFailureMessage ? (
            <p className="text-sm text-red-400">{options.deleteAccountHardFailureMessage}</p>
          ) : null}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-200 hover:bg-gray-800"
              disabled={options.isDeletingAccount}
              onClick={resetAndClose}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded-md bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-semibold px-3 py-2 text-sm"
              disabled={typedConfirmation !== 'Delete' || options.isDeletingAccount}
              onClick={() => options.onConfirmDelete()}
            >
              {options.isDeletingAccount ? 'Deleting…' : 'DELETE'}
            </button>
          </div>
        </>
      )}
    </FishSniperModalBackdrop>
  )
}

function FishSniperModalBackdrop(options: {
  children: ReactNode
  onBackdropClick: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      role="presentation"
      onClick={options.onBackdropClick}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-md rounded-lg border border-gray-800 bg-gray-900 p-5 shadow-xl space-y-4"
        onClick={(event) => event.stopPropagation()}
      >
        {options.children}
      </div>
    </div>
  )
}

