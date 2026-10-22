import { useId, useRef, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { fishingMethods, type CatchLog, type CatchLogInput, type FishingMethod } from '../api/catchLogTypes.ts'
import { toLocalDateTimeInput } from '../lib/catchLogPresentation.ts'

const inputClass = 'min-h-11 w-full rounded-lg border border-white/20 bg-[#07101f] px-3 py-2 text-base text-(--fs-ink) focus-visible:outline focus-visible:outline-2 focus-visible:outline-(--fs-green)'

// 新增與修改共用的純文字表單，不提供照片或經緯度輸入框。
export function CatchLogForm(props: {
  record?: CatchLog
  busy: boolean
  error: string | null
  onSubmit: (input: CatchLogInput) => Promise<void>
  onCancel: () => void
}) {
  const { t } = useTranslation()
  const id = useId()
  const speciesRef = useRef<HTMLInputElement>(null)
  const [species, setSpecies] = useState(props.record?.species_name ?? '')
  const [initialTime] = useState(() => toLocalDateTimeInput(props.record?.caught_at ?? new Date()))
  const [caughtDate, setCaughtDate] = useState(initialTime.slice(0, 10))
  const [caughtTime, setCaughtTime] = useState(initialTime.slice(11))
  const [length, setLength] = useState(props.record?.length_cm?.toString() ?? '')
  const [weight, setWeight] = useState(props.record?.weight_g?.toString() ?? '')
  const [method, setMethod] = useState<FishingMethod | ''>(props.record?.fishing_method ?? '')
  const [notes, setNotes] = useState(props.record?.notes ?? '')
  const [validationError, setValidationError] = useState(false)
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone

  // 開啟表單後移動鍵盤焦點到魚種，讓手機與鍵盤使用者可直接輸入。
  useEffect(() => { speciesRef.current?.focus() }, [])

  // 驗證必要與數值欄位，將裝置本地時間轉成明確時間點後交給 API。
  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (props.busy) return
    const caught = new Date(`${caughtDate}T${caughtTime}`)
    const lengthValue = length === '' ? null : Number(length)
    const weightValue = weight === '' ? null : Number(weight)
    if (!species.trim() || !caughtDate || !caughtTime || Number.isNaN(caught.getTime()) ||
      [lengthValue, weightValue].some((value) => value !== null && (!Number.isFinite(value) || value <= 0))) {
      setValidationError(true)
      return
    }
    setValidationError(false)
    await props.onSubmit({
      species_name: species.trim(), caught_at: caught.toISOString(),
      length_cm: lengthValue, weight_g: weightValue,
      fishing_method: method || null, notes: notes.trim() || null,
    })
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="grid gap-4 rounded-xl border border-white/15 bg-black/15 p-3 sm:p-4" aria-label={t(props.record ? 'catchLogs.edit' : 'catchLogs.add')}>
      <h3 className="font-semibold">{t(props.record ? 'catchLogs.edit' : 'catchLogs.add')}</h3>
      <p className="text-sm text-(--fs-muted)">{t('catchLogs.formHint')}</p>
      <fieldset disabled={props.busy} className="grid min-w-0 gap-4 disabled:opacity-70 sm:grid-cols-2">
        <div className="grid min-w-0 gap-2 text-sm">
          <label htmlFor={`${id}-species`}>{t('catchLogs.species')}</label>
          <input ref={speciesRef} id={`${id}-species`} required maxLength={100} value={species} onChange={(event) => setSpecies(event.target.value)} className={inputClass} />
        </div>
        <div className="grid min-w-0 gap-2 text-sm">
          <label htmlFor={`${id}-date`}>{t('catchLogs.caughtDate')}</label>
          <input id={`${id}-date`} type="date" required value={caughtDate} onChange={(event) => setCaughtDate(event.target.value)} className={`${inputClass} min-w-0`} />
        </div>
        <div className="grid min-w-0 gap-2 text-sm">
          <label htmlFor={`${id}-time`}>{t('catchLogs.caughtAt')}</label>
          <input id={`${id}-time`} type="time" required step="1" value={caughtTime} onChange={(event) => setCaughtTime(event.target.value)} className={`${inputClass} min-w-0`} />
        </div>
        <p className="break-words text-xs text-(--fs-muted) sm:col-span-2">{t('catchLogs.timeZone', { timeZone })}</p>
        <div className="grid min-w-0 gap-2 text-sm">
          <label htmlFor={`${id}-length`}>{t('catchLogs.length')}</label>
          <input id={`${id}-length`} type="number" inputMode="decimal" min="0" step="any" value={length} onChange={(event) => setLength(event.target.value)} className={inputClass} />
        </div>
        <div className="grid min-w-0 gap-2 text-sm">
          <label htmlFor={`${id}-weight`}>{t('catchLogs.weight')}</label>
          <input id={`${id}-weight`} type="number" inputMode="decimal" min="0" step="any" value={weight} onChange={(event) => setWeight(event.target.value)} className={inputClass} />
        </div>
        <div className="grid min-w-0 gap-2 text-sm sm:col-span-2">
          <label htmlFor={`${id}-method`}>{t('catchLogs.method')}</label>
          <select id={`${id}-method`} value={method} onChange={(event) => setMethod(event.target.value as FishingMethod | '')} className={inputClass}>
            <option value="">{t('catchLogs.unspecified')}</option>
            {fishingMethods.map((value) => <option key={value} value={value}>{t(`catchLogs.methods.${value}`)}</option>)}
          </select>
        </div>
        <div className="grid min-w-0 gap-2 text-sm sm:col-span-2">
          <label htmlFor={`${id}-notes`}>{t('catchLogs.notes')}</label>
          <textarea id={`${id}-notes`} rows={3} maxLength={2000} value={notes} onChange={(event) => setNotes(event.target.value)} className={`${inputClass} resize-y`} />
        </div>
      </fieldset>
      {validationError || props.error ? <p role="alert" className="text-sm text-red-300">{validationError ? t('catchLogs.invalidInput') : props.error}</p> : null}
      <div className="flex flex-wrap gap-2">
        <button type="submit" disabled={props.busy} className="min-h-11 rounded-lg bg-(--fs-green) px-4 text-sm font-bold text-[#031007] disabled:cursor-wait disabled:opacity-60">{t(props.busy ? 'catchLogs.saving' : 'catchLogs.save')}</button>
        <button type="button" disabled={props.busy} onClick={props.onCancel} className="min-h-11 rounded-lg border border-white/20 px-4 text-sm disabled:opacity-60">{t('catchLogs.cancel')}</button>
      </div>
    </form>
  )
}
