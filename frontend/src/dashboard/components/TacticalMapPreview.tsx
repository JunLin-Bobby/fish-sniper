export function TacticalMapPreview() {
  return (
    <section className="min-h-96 border border-cyan-400/20 bg-cyan-950/20 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-cyan-200">Primary display</p>
          <h2 className="mt-1 text-lg font-medium text-zinc-50">Water intelligence map</h2>
        </div>
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-500">Placeholder</p>
      </div>
      <div className="mt-4 grid h-72 place-items-center border border-cyan-300/20 bg-zinc-900/80">
        <div className="text-center">
          <p className="text-sm text-zinc-300">Tactical map preview</p>
          <p className="mt-2 text-xs text-zinc-500">Waters, terrain, catches, and strategy layers.</p>
        </div>
      </div>
    </section>
  )
}
