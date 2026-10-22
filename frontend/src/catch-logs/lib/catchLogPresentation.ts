// 將時間點轉為瀏覽器當地時間，供 datetime-local 編輯，不寫死台灣時區。
export function toLocalDateTimeInput(value: string | Date): string {
  const date = typeof value === 'string' ? new Date(value) : value
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return shifted.toISOString().slice(0, 19)
}

// 使用介面語言與裝置時區顯示釣獲時間，附上時區避免旅行時混淆。
export function formatCaughtAt(value: string, language: string): string {
  return new Intl.DateTimeFormat(language, {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(value))
}
