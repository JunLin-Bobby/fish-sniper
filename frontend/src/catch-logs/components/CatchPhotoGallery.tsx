import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { HttpStatusError, NetworkRequestError, RequestTimeoutError } from '../../api/http.ts'
import { deleteCatchPhoto, updateCatchLog } from '../api/catchLogApi.ts'
import { useCatchPhotos } from '../hooks/useCatchPhotos.ts'
import { PhotoMetadataSuggestion } from './PhotoMetadataSuggestion.tsx'

// 私人相簿只使用後端簽署網址，不自行推算 bucket 路徑或信任前端 owner。
export function CatchPhotoGallery(props: { apiBaseUrl: string; logId: string; busy: boolean; onUnauthorized: () => void; onTimeChanged: () => void }) {
  const { t } = useTranslation()
  const { photos, status, refresh } = useCatchPhotos(props.apiBaseUrl, props.logId, props.onUnauthorized)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  // 每個操作都等待後端完成；失敗保留提示與重讀入口，不假裝刪除成功。
  async function act(operation: () => Promise<unknown>): Promise<void> {
    if (working || props.busy) return
    setWorking(true)
    setError(null)
    try { await operation(); setConfirm(null); refresh() }
    catch (failure) {
      if (failure instanceof HttpStatusError && failure.status === 401) props.onUnauthorized()
      setError(failure instanceof RequestTimeoutError ? 'catchLogs.actionTimeout'
        : failure instanceof NetworkRequestError ? 'catchLogs.actionNetwork' : 'catchLogs.photos.failed')
    } finally { setWorking(false) }
  }

  return <section aria-label={t('catchLogs.photos.label')} className="grid min-w-0 gap-3">
    <h4 className="font-semibold">{t('catchLogs.photos.label')}</h4>
    {status === 'loading' ? <p role="status">{t('catchLogs.photos.loading')}</p> : null}
    {status === 'error' || error ? <div role="alert"><p>{t(error ?? 'catchLogs.photos.failed')}</p><button type="button" onClick={() => { setError(null); refresh() }} className="min-h-11 rounded-lg border border-white/20 px-3">{t('catchLogs.retry')}</button></div> : null}
    {status === 'ready' && !photos.length ? <p className="text-sm text-(--fs-muted)">{t('catchLogs.photos.empty')}</p> : null}
    <div className="grid min-w-0 gap-4 sm:grid-cols-2">{photos.map((photo) => <div key={photo.id} className="grid min-w-0 content-start gap-3 rounded-lg border border-white/15 p-3">
      <button type="button" onClick={() => setExpanded(expanded === photo.id ? null : photo.id)} aria-expanded={expanded === photo.id} aria-label={t('catchLogs.photos.expand', { number: photo.photo_order })} className="min-h-11"><img src={photo.url} alt={t('catchLogs.photos.preview', { number: photo.photo_order })} className={`${expanded === photo.id ? 'max-h-none' : 'max-h-52'} w-full rounded object-contain`} /></button>
      <PhotoMetadataSuggestion metadata={photo.metadata} busy={working || props.busy} onApply={(caught_at) => void act(async () => { await updateCatchLog(props.apiBaseUrl, props.logId, { caught_at }); props.onTimeChanged() })} />
      {confirm === photo.id ? <><p>{t('catchLogs.photos.deleteConfirm')}</p><button type="button" disabled={working || props.busy} onClick={() => void act(() => deleteCatchPhoto(props.apiBaseUrl, props.logId, photo.id))} className="min-h-11 rounded-lg border border-red-300/40 px-3 text-red-300">{t('catchLogs.confirmDelete')}</button><button type="button" disabled={working} onClick={() => setConfirm(null)} className="min-h-11">{t('catchLogs.cancel')}</button></>
        : <button type="button" disabled={working || props.busy} onClick={() => setConfirm(photo.id)} className="min-h-11 rounded-lg border border-white/20 px-3">{t('catchLogs.photos.delete')}</button>}
    </div>)}</div>
  </section>
}
