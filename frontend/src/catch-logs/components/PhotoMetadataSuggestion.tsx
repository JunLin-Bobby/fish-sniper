import { useTranslation } from 'react-i18next'
import type { PhotoMetadata } from '../api/catchLogTypes.ts'

// 拍攝資訊只是候選值；缺少時區不可自動套用，GPS 不建立已確認釣點。
export function PhotoMetadataSuggestion(props: { metadata: PhotoMetadata; busy: boolean; onApply: (value: string) => void }) {
  const { t, i18n } = useTranslation()
  const metadata = props.metadata
  return <div className="grid gap-2 text-sm text-(--fs-muted)">
    {metadata.captured_at ? <><p>{t('catchLogs.photos.capturedAt', { time: new Date(metadata.captured_at).toLocaleString(i18n.language) })}</p><button type="button" disabled={props.busy} onClick={() => props.onApply(metadata.captured_at!)} className="min-h-11 rounded-lg border border-white/20 px-3 text-(--fs-ink) disabled:opacity-60">{t('catchLogs.photos.applyTime')}</button></>
      : metadata.local_captured_at ? <p>{t('catchLogs.photos.unknownTimeZone', { time: metadata.local_captured_at })}</p> : <p>{t('catchLogs.photos.noTime')}</p>}
    <p>{t(metadata.latitude !== null && metadata.longitude !== null ? 'catchLogs.photos.hasGps' : 'catchLogs.photos.noGps')}</p>
  </div>
}
