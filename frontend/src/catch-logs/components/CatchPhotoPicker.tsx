import { useEffect, useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { validatePhotoSelection } from '../lib/photoSelection.ts'

// 管理本機預覽 URL 並在卸載時釋放；HEIC 沒有預覽也能正常選取與提交。
function SelectedPhoto(props: { file: File; index: number; onRemove: () => void }) {
  const { t } = useTranslation()
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    const value = URL.createObjectURL(props.file)
    setUrl(value)
    return () => URL.revokeObjectURL(value)
  }, [props.file])
  return <li className="grid min-w-0 gap-2 rounded-lg border border-white/15 p-3">
    {url && !failed ? <img src={url} onError={() => setFailed(true)} alt={t('catchLogs.photos.preview', { number: props.index + 1 })} className="h-32 w-full rounded object-contain" /> : <p className="text-sm text-(--fs-muted)">{t('catchLogs.photos.noPreview')}</p>}
    <p className="break-all text-sm">{props.file.name}</p>
    <button type="button" onClick={props.onRemove} className="min-h-11 rounded-lg border border-white/20 px-3 text-sm">{t('catchLogs.photos.removeSelection')}</button>
  </li>
}

// 這是魚獲表單的子元件，不自行發送上傳請求，照片與文字一起按儲存送出。
export function CatchPhotoPicker(props: { files: File[]; onChange: (files: File[]) => void }) {
  const { t } = useTranslation()
  const id = useId()
  const [error, setError] = useState(false)
  return <div className="grid min-w-0 gap-3 sm:col-span-2">
    <label htmlFor={id}>{t('catchLogs.photos.label')}</label>
    <p className="text-xs text-(--fs-muted)">{t('catchLogs.photos.hint')}</p>
    <input id={id} type="file" accept=".jpg,.jpeg,.png,.heic,.heif,image/jpeg,image/png,image/heic,image/heif" multiple disabled={props.files.length >= 2} className="min-h-11 w-full min-w-0 text-sm" onChange={(event) => {
      const next = [...props.files, ...Array.from(event.target.files ?? [])]
      event.target.value = ''
      if (!validatePhotoSelection(next)) { setError(true); return }
      setError(false)
      props.onChange(next)
    }} />
    {error ? <p role="alert" className="text-sm text-red-300">{t('catchLogs.photos.invalid')}</p> : null}
    <ul className="grid min-w-0 gap-3 sm:grid-cols-2">{props.files.map((file, index) => <SelectedPhoto key={`${file.name}-${file.lastModified}-${index}`} file={file} index={index} onRemove={() => { props.onChange(props.files.filter((_, position) => position !== index)); setError(false) }} />)}</ul>
  </div>
}
