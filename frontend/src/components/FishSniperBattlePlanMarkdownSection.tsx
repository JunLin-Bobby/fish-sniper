import ReactMarkdown from 'react-markdown'

export function FishSniperBattlePlanMarkdownSection(options: { battlePlanMarkdown: string }) {
  return (
    <div
      className={
        'rounded-md border border-gray-800 bg-gray-900/40 p-3 text-sm text-gray-300 ' +
        '[&_h1]:mt-3 [&_h1]:text-base [&_h1]:font-semibold [&_h1]:text-emerald-300 ' +
        '[&_h2]:mt-2 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:text-gray-200 ' +
        '[&_p]:my-2 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:my-0.5 ' +
        '[&_strong]:text-emerald-200'
      }
    >
      <ReactMarkdown>{options.battlePlanMarkdown}</ReactMarkdown>
    </div>
  )
}
