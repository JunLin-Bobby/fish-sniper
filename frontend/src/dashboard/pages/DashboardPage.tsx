import { TacticalMapPreview } from '../components/TacticalMapPreview.tsx'
import { TacticalShell } from '../components/TacticalShell.tsx'

const upcomingModules = [
  { title: 'Waters', description: 'Personal fishing water boundaries and terrain markers.' },
  { title: 'Logs', description: 'Catch history tied to a selected water.' },
  { title: 'Strategy', description: 'AI-assisted recommendations from water context and logs.' },
]

export function DashboardPage() {
  return (
    <TacticalShell>
      <section className="grid flex-1 gap-4 py-8 md:grid-cols-[1.4fr_0.8fr]">
        <TacticalMapPreview />
        <aside className="space-y-4">
          {upcomingModules.map((module) => (
            <div key={module.title} className="border border-white/10 bg-white/[0.03] p-4">
              <p className="text-sm text-zinc-400">Coming soon</p>
              <h2 className="mt-1 text-lg font-medium">{module.title}</h2>
              <p className="mt-2 text-sm text-zinc-500">{module.description}</p>
            </div>
          ))}
        </aside>
      </section>
    </TacticalShell>
  )
}
