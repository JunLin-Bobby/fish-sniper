export function formatStrategyReportTimestamp(isoTimestamp: string): string {
  const parsed = Date.parse(isoTimestamp)
  if (Number.isNaN(parsed)) {
    return isoTimestamp
  }
  return new Date(parsed).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}
