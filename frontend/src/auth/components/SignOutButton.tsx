import { tacticalGhostButtonClassName } from '../../ui/tacticalUi.ts'

export function SignOutButton(options: { onSignOut: () => void }) {
  return (
    <button
      type="button"
      className={tacticalGhostButtonClassName}
      onClick={options.onSignOut}
    >
      Sign out
    </button>
  )
}