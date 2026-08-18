import type { ReactNode } from 'react'

export function TacticalShell(props: { children: ReactNode }) {
  return (
    <main className="min-h-dvh bg-zinc-950 px-6 py-8 text-zinc-100">
      <div className="mx-auto flex min-h-[calc(100dvh-4rem)] max-w-6xl flex-col">
        <header className="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-300">FishSniper</p>
            <h1 className="mt-2 text-2xl font-semibold">Tactical rebuild shell</h1>
          </div>
          <span className="border border-emerald-400/40 px-3 py-1 text-sm text-emerald-200">
            Online
          </span>
        </header>
        {props.children}
      </div>
    </main>
  )
}
