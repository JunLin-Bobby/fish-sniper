import { tacticalGoogleButtonClassName } from '../../ui/tacticalUi.ts'

export function GoogleSignInButton(options: {
  onContinueWithGoogle: () => void | Promise<void>
}) {
  return (
    <button
      type="button"
      className={tacticalGoogleButtonClassName}
      onClick={() => void options.onContinueWithGoogle()}
    >
      Continue with Google
    </button>
  )
}