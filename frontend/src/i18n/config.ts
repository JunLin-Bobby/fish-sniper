import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import { en, zhTW } from './translations.ts'

export type AppLanguage = 'en' | 'zh-TW'

const languageStorageKey = 'fishsniper.language'

// 優先使用手動選擇的語言；首次造訪時依瀏覽器語言選擇，其他語言回退英文。
export function readInitialLanguage(): AppLanguage {
  try {
    const storedLanguage = window.localStorage.getItem(languageStorageKey)
    if (storedLanguage === 'en' || storedLanguage === 'zh-TW') {
      return storedLanguage
    }
  } catch {
    // 瀏覽器若封鎖 localStorage，仍可使用當次的語言切換。
  }

  return navigator.language.toLowerCase().startsWith('zh') ? 'zh-TW' : 'en'
}

// 切換目前語言、更新 HTML lang，並盡可能保存下次造訪的偏好。
export async function changeAppLanguage(language: AppLanguage): Promise<void> {
  await i18n.changeLanguage(language)
  document.documentElement.lang = language
  try {
    window.localStorage.setItem(languageStorageKey, language)
  } catch {
    // 偏好無法保存時，當前頁面仍維持已切換的語言。
  }
}

const initialLanguage = readInitialLanguage()
document.documentElement.lang = initialLanguage

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, 'zh-TW': { translation: zhTW } },
  lng: initialLanguage,
  fallbackLng: 'en',
  supportedLngs: ['en', 'zh-TW'],
  interpolation: { escapeValue: false },
  initAsync: false,
})

export default i18n
