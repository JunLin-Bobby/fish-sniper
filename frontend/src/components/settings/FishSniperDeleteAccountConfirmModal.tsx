import { useEffect, useState, type ReactNode } from 'react'

import {
  fishSniperTacticalDangerButtonClassName,
  fishSniperTacticalErrorBannerClassName,
  fishSniperTacticalGhostButtonClassName,
  fishSniperTacticalInputClassName,
  fishSniperTacticalModalPanelClassName,
  fishSniperTacticalMutedTextClassName,
} from '../../ui/fishSniperTacticalUi.ts'

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
          <h2 className="text-lg font-semibold text-slate-100">Delete your account?</h2>
          <ul className={`list-disc space-y-1 pl-5 ${fishSniperTacticalMutedTextClassName}`}>
            <li>Your fishing logs and preferences will be permanently removed.</li>
            <li>You will be signed out immediately.</li>
            <li>This action cannot be undone.</li>
          </ul>
          <div className="flex justify-end gap-2">
            <button type="button" className={fishSniperTacticalGhostButtonClassName} onClick={resetAndClose}>
              Cancel
            </button>
            <button
              type="button"
              className={fishSniperTacticalDangerButtonClassName}
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
          <h2 className="text-lg font-semibold text-slate-100">Confirm account deletion</h2>
          <p className={fishSniperTacticalMutedTextClassName}>
            Type <span className="font-mono font-semibold text-slate-100">Delete</span> to confirm.
          </p>
          <input
            className={`${fishSniperTacticalInputClassName} font-mono focus:border-rose-500/60 focus:ring-rose-500/20`}
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
            <p className={fishSniperTacticalErrorBannerClassName}>
              {options.deleteAccountHardFailureMessage}
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className={fishSniperTacticalGhostButtonClassName}
              disabled={options.isDeletingAccount}
              onClick={resetAndClose}
            >
              Cancel
            </button>
            <button
              type="button"
              className={`${fishSniperTacticalDangerButtonClassName} disabled:opacity-50`}
              disabled={typedConfirmation !== 'Delete' || options.isDeletingAccount}
              onClick={() => options.onConfirmDelete()}
            >
              {options.isDeletingAccount ? 'Deleting…' : 'Delete'}
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
        className={`${fishSniperTacticalModalPanelClassName} space-y-4`}
        onClick={(event) => event.stopPropagation()}
      >
        {options.children}
      </div>
    </div>
  )
}
