import { useTranslation } from 'react-i18next'

import { changeAppLanguage, type AppLanguage } from './config.ts'

const languageOptions: { code: AppLanguage; label: string }[] = [
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'en', label: 'English' },
]

// 共用語言切換鈕，登入頁與儀表板會同步顯示目前選擇。
export function LanguageSwitcher() {
  const { t, i18n } = useTranslation()

  return (
    <div className="inline-flex rounded-lg border border-white/15 bg-black/20 p-1" role="group" aria-label={t('common.language')}>
      {languageOptions.map(({ code, label }) => (
        <button
          key={code}
          type="button"
          aria-pressed={i18n.resolvedLanguage === code}
          className={`min-h-8 cursor-pointer rounded-md px-2.5 text-xs font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-(--fs-green) ${
            i18n.resolvedLanguage === code
              ? 'bg-[rgba(61,255,138,0.18)] text-(--fs-green-soft)'
              : 'text-(--fs-muted) hover:text-slate-100'
          }`}
          onClick={() => void changeAppLanguage(code)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
