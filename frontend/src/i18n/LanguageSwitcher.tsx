import { useTranslation } from 'react-i18next'

import { changeAppLanguage, type AppLanguage } from './config.ts'

const languageOptions: { code: AppLanguage; label: string }[] = [
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'en', label: 'English' },
]

// 共用語言切換鈕；首頁可使用短標籤與較大的觸控範圍，登入頁維持原版樣式。
export function LanguageSwitcher(props: { compact?: boolean } = {}) {
  const { t, i18n } = useTranslation()

  return (
    <div className="inline-flex rounded-lg border border-white/15 bg-black/20 p-1" role="group" aria-label={t('common.language')}>
      {languageOptions.map(({ code, label }) => (
        <button
          key={code}
          type="button"
          aria-label={label}
          aria-pressed={i18n.resolvedLanguage === code}
          className={`${props.compact ? 'min-h-11' : 'min-h-8'} cursor-pointer rounded-md px-2.5 text-xs font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-(--fs-green) ${
            i18n.resolvedLanguage === code
              ? 'bg-[rgba(61,255,138,0.18)] text-(--fs-green-soft)'
              : 'text-(--fs-muted) hover:text-slate-100'
          }`}
          onClick={() => void changeAppLanguage(code)}
        >
          {props.compact ? code === 'zh-TW' ? '中' : 'EN' : label}
        </button>
      ))}
    </div>
  )
}
