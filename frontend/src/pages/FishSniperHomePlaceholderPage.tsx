export function FishSniperHomePlaceholderPage(options: { onSignOut: () => void }) {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-lg text-center space-y-4">
        <h1 className="text-4xl font-bold text-emerald-400 tracking-tight">FishSniper</h1>
        <p className="text-gray-500 text-sm">
          You’re signed in. The strategy screen ships in P2 — for now this is your home base.
        </p>
        <button
          type="button"
          className="text-sm text-gray-500 hover:text-gray-300 underline"
          onClick={() => options.onSignOut()}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
