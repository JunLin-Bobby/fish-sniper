import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { CatchLog } from '../api/catchLogTypes.ts'
import { formatCaughtAt } from '../lib/catchLogPresentation.ts'
import { CatchPhotoGallery } from './CatchPhotoGallery.tsx'

// 呈現私人紀錄並在刪除前二次確認，失敗後保留原資料與重試入口。
export function CatchLogDetails(props: {
  record: CatchLog
  apiBaseUrl: string
  onUnauthorized: () => void
  onTimeChanged: () => void
  busy: boolean
  error: string | null
  onEdit: () => void
  onDelete: () => Promise<void>
  onClose: () => void
}) {
  const { t, i18n } = useTranslation()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const rows = [
    [t('catchLogs.caughtAt'), formatCaughtAt(props.record.caught_at, i18n.language)],
    [t('catchLogs.length'), props.record.length_cm === null ? t('catchLogs.unspecified') : `${props.record.length_cm} cm`],
    [t('catchLogs.weight'), props.record.weight_g === null ? t('catchLogs.unspecified') : `${props.record.weight_g} g`],
    [t('catchLogs.method'), props.record.fishing_method ? t(`catchLogs.methods.${props.record.fishing_method}`) : t('catchLogs.unspecified')],
  ]

  return (
    <article aria-label={t('catchLogs.details')} className="grid gap-4 rounded-xl border border-white/15 bg-black/15 p-3 sm:p-4">
      <h3 className="break-words text-lg font-semibold">{props.record.species_name}</h3>
      <dl className="grid gap-3 sm:grid-cols-2">
        {rows.map(([label, value]) => <div key={label} className="min-w-0"><dt className="text-xs text-(--fs-muted)">{label}</dt><dd className="mt-1 break-words text-sm">{value}</dd></div>)}
      </dl>
      <div><h4 className="text-xs text-(--fs-muted)">{t('catchLogs.notes')}</h4><p className="mt-1 whitespace-pre-wrap break-words text-sm">{props.record.notes || t('catchLogs.unspecified')}</p></div>
      <CatchPhotoGallery apiBaseUrl={props.apiBaseUrl} logId={props.record.id} busy={props.busy} onUnauthorized={props.onUnauthorized} onTimeChanged={props.onTimeChanged} />
      {props.error ? <p role="alert" className="text-sm text-red-300">{props.error}</p> : null}
      {confirmDelete ? (
        <div className="grid gap-3 rounded-lg border border-red-300/30 p-3">
          <p className="text-sm">{t('catchLogs.deleteConfirm')}</p>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={props.busy} onClick={() => void props.onDelete()} className="min-h-11 rounded-lg bg-red-300 px-4 text-sm font-bold text-[#031007] disabled:opacity-60">{t(props.busy ? 'catchLogs.deleting' : 'catchLogs.confirmDelete')}</button>
            <button type="button" disabled={props.busy} onClick={() => setConfirmDelete(false)} className="min-h-11 rounded-lg border border-white/20 px-4 text-sm">{t('catchLogs.cancel')}</button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={props.busy} onClick={props.onEdit} className="min-h-11 rounded-lg border border-white/20 px-4 text-sm">{t('catchLogs.edit')}</button>
          <button type="button" disabled={props.busy} onClick={() => setConfirmDelete(true)} className="min-h-11 rounded-lg border border-red-300/40 px-4 text-sm text-red-300">{t('catchLogs.delete')}</button>
          <button type="button" disabled={props.busy} onClick={props.onClose} className="min-h-11 rounded-lg border border-white/20 px-4 text-sm">{t('catchLogs.close')}</button>
        </div>
      )}
    </article>
  )
}
