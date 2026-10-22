import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { HttpStatusError } from '../../api/http.ts'
import { createCatchLog, deleteCatchLog, updateCatchLog } from '../api/catchLogApi.ts'
import type { CatchLog, CatchLogInput } from '../api/catchLogTypes.ts'
import { useCatchLogDetail, useCatchLogs } from '../hooks/useCatchLogs.ts'
import { formatCaughtAt } from '../lib/catchLogPresentation.ts'
import { CatchLogDetails } from './CatchLogDetails.tsx'
import { CatchLogForm } from './CatchLogForm.tsx'

type View = { mode: 'list' } | { mode: 'create' } | { mode: 'detail'; id: string } | { mode: 'edit'; record: CatchLog }
const buttonClass = 'min-h-11 rounded-lg border border-white/20 px-3 text-sm disabled:cursor-not-allowed disabled:opacity-50'

// 協調真實紀錄列表、詳情、表單與刪除，不混用示意資料或首頁預報地點。
export function CatchLogsWorkspace(props: { apiBaseUrl: string; onUnauthorized: () => void }) {
  const { t, i18n } = useTranslation()
  const { page, offset, setOffset, refresh, pageSize } = useCatchLogs(props.apiBaseUrl, props.onUnauthorized)
  const [view, setView] = useState<View>({ mode: 'list' })
  const { detail, retry } = useCatchLogDetail(props.apiBaseUrl, view.mode === 'detail' ? view.id : null, props.onUnauthorized)
  const [busy, setBusy] = useState(false)
  const mutationLock = useRef(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const addButton = useRef<HTMLButtonElement>(null)
  const previousMode = useRef<View['mode']>('list')

  // 等 React 移除表單並重新啟用按鈕後才還原焦點，避免 focus 到 disabled 元素。
  useEffect(() => {
    if (busy) return
    if (view.mode === 'list' && previousMode.current !== 'list') addButton.current?.focus()
    previousMode.current = view.mode
  }, [view.mode, busy])

  // 切換視圖時清除上一筆的提示，避免訊息附著在錯誤紀錄上。
  function open(next: View): void {
    setActionError(null)
    setNotice(null)
    setView(next)
  }

  // 關閉操作後把焦點還給穩定存在的新增入口。
  function close(): void {
    open({ mode: 'list' })
  }

  // 將 API 錯誤轉成翻譯提示，不顯示原始資料庫或驗證 payload。
  function reportError(error: unknown): void {
    if (error instanceof HttpStatusError && error.status === 401) props.onUnauthorized()
    else setActionError(error instanceof HttpStatusError && error.status === 404 ? 'catchLogs.notFound'
      : error instanceof HttpStatusError && error.status === 422 ? 'catchLogs.invalidInput' : 'catchLogs.actionFailed')
  }

  // 防止重複提交；只有 API 成功才關閉表單並重新讀取儲存結果。
  async function save(input: CatchLogInput): Promise<void> {
    if (mutationLock.current) return
    mutationLock.current = true
    setBusy(true)
    setActionError(null)
    try {
      if (view.mode === 'edit') await updateCatchLog(props.apiBaseUrl, view.record.id, input)
      else await createCatchLog(props.apiBaseUrl, input)
      setView({ mode: 'list' })
      setNotice('catchLogs.saved')
      refresh()
    } catch (error) { reportError(error) }
    finally { mutationLock.current = false; setBusy(false) }
  }

  // 確認後才刪除目前詳情；失敗保留原紀錄，不先從畫面假裝移除。
  async function remove(): Promise<void> {
    if (view.mode !== 'detail' || mutationLock.current) return
    mutationLock.current = true
    setBusy(true)
    setActionError(null)
    try {
      await deleteCatchLog(props.apiBaseUrl, view.id)
      setView({ mode: 'list' })
      setNotice('catchLogs.deleted')
      refresh()
    } catch (error) { reportError(error) }
    finally { mutationLock.current = false; setBusy(false) }
  }

  return (
    <section id="logs" tabIndex={-1} aria-labelledby="logs-heading" className="dashboard-logs dashboard-anchor grid min-w-0 gap-4 rounded-[18px] border border-(--fs-line) bg-(--fs-panel) p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 id="logs-heading" className="text-base font-semibold">{t('catchLogs.title')}</h2><p className="mt-1 text-xs text-(--fs-muted)">{t('catchLogs.privateHint')}</p></div>
        <button ref={addButton} type="button" disabled={busy || view.mode === 'create' || view.mode === 'edit'} onClick={() => open({ mode: 'create' })} className={`${buttonClass} border-[rgba(61,255,138,.4)] text-(--fs-green-soft)`}>{t('catchLogs.add')}</button>
      </div>
      {notice ? <p role="status" className="text-sm text-(--fs-green-soft)">{t(notice)}</p> : null}
      {view.mode === 'create' || view.mode === 'edit' ? (
        <CatchLogForm key={view.mode === 'edit' ? view.record.id : 'new'} record={view.mode === 'edit' ? view.record : undefined} busy={busy} error={actionError ? t(actionError) : null} onSubmit={save} onCancel={close} />
      ) : null}
      {view.mode === 'detail' ? (
        detail.status === 'ready' && detail.data?.id === view.id ? <CatchLogDetails key={view.id} record={detail.data} busy={busy} error={actionError ? t(actionError) : null} onEdit={() => open({ mode: 'edit', record: detail.data! })} onDelete={remove} onClose={close} />
          : <div className="grid gap-3 rounded-xl border border-white/15 p-3"><p role="status" className="text-sm">{t(detail.status === 'error' ? detail.missing ? 'catchLogs.notFound' : 'catchLogs.loadFailed' : 'catchLogs.loading')}</p><div className="flex gap-2">{detail.status === 'error' && !detail.missing ? <button type="button" onClick={retry} className={buttonClass}>{t('catchLogs.retry')}</button> : null}<button type="button" onClick={close} className={buttonClass}>{t('catchLogs.close')}</button></div></div>
      ) : null}
      {page.status === 'loading' ? <p role="status" className="text-sm text-(--fs-muted)">{t('catchLogs.loading')}</p>
        : page.status === 'error' ? <div className="grid gap-3"><p role="alert" className="text-sm text-(--fs-muted)">{t('catchLogs.loadFailed')}</p><button type="button" onClick={refresh} className={`${buttonClass} w-fit`}>{t('catchLogs.retry')}</button></div>
          : page.data?.items.length === 0 ? <p className="rounded-xl bg-black/15 p-4 text-sm text-(--fs-muted)">{t('catchLogs.empty')}</p>
            : <ul className="grid min-w-0 gap-2">{page.data?.items.map((record) => (
              <li key={record.id}><button type="button" disabled={busy || view.mode === 'create' || view.mode === 'edit'} aria-label={t('catchLogs.viewRecord', { species: record.species_name, time: formatCaughtAt(record.caught_at, i18n.language) })} onClick={() => open({ mode: 'detail', id: record.id })} className="grid min-h-16 w-full min-w-0 gap-1 rounded-xl border border-white/10 bg-white/4 p-3 text-left hover:border-white/30 disabled:opacity-50">
                <span className="break-words font-semibold">{record.species_name}</span><time dateTime={record.caught_at} className="text-xs text-(--fs-muted)">{formatCaughtAt(record.caught_at, i18n.language)}</time>
                {record.fishing_method ? <span className="text-xs text-(--fs-green-soft)">{t(`catchLogs.methods.${record.fishing_method}`)}</span> : null}
              </button></li>
            ))}</ul>}
      <div className="flex flex-wrap items-center gap-2" aria-label={t('catchLogs.pagination')}>
        <button type="button" disabled={busy || view.mode !== 'list' || page.status !== 'ready' || offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))} className={buttonClass}>{t('catchLogs.previous')}</button>
        <span className="text-xs text-(--fs-muted)">{t('catchLogs.page', { page: Math.floor(offset / pageSize) + 1 })}</span>
        <button type="button" disabled={busy || view.mode !== 'list' || page.status !== 'ready' || !page.data?.has_more} onClick={() => setOffset(offset + pageSize)} className={buttonClass}>{t('catchLogs.next')}</button>
      </div>
    </section>
  )
}
