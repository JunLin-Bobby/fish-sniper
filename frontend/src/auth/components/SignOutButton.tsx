export function SignOutButton(props: { onSignOut: () => void }) {
  return (
    <button
      type="button"
      className="min-h-[42px] cursor-pointer rounded-xl border border-white/15 bg-white/[0.05] px-4 text-sm font-bold text-slate-100 transition-colors duration-200 hover:border-white/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--fs-green)]"
      onClick={props.onSignOut}
    >
      Sign out
    </button>
  )
}
