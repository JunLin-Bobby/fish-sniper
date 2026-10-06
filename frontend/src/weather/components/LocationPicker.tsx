import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { HttpStatusError } from '../../api/http.ts'
import { searchWeatherLocations } from '../api/weatherApi.ts'
import type { LocationSuggestion, SelectedLocation } from '../api/weatherTypes.ts'
import type { LocationStatus } from '../hooks/useSelectedLocation.ts'

// 讓使用者在瀏覽器定位與手動地名搜尋之間切換。
export function LocationPicker(props: {
  apiBaseUrl: string
  location: SelectedLocation | null
  status: LocationStatus
  onUseCurrentLocation: () => void
  onSelectLocation: (location: SelectedLocation) => void
  onUnauthorized: () => void
}) {
  const { t, i18n } = useTranslation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<LocationSuggestion[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchFailed, setSearchFailed] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // 只在使用者送出地名後呼叫後端搜尋，避免每輸入一字就消耗額度。
  async function handleSearch(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const trimmed = query.trim()
    if (trimmed.length < 2) return
    setIsSearching(true)
    setSearchFailed(false)
    setHasSearched(false)
    setResults([])
    try {
      const suggestions = await searchWeatherLocations(
        props.apiBaseUrl,
        trimmed,
        i18n.language.startsWith('zh') ? 'zh' : 'en',
      )
      setResults(suggestions)
      setHasSearched(true)
    } catch (error) {
      if (error instanceof HttpStatusError && error.status === 401) props.onUnauthorized()
      else setSearchFailed(true)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="grid gap-3 rounded-[14px] border border-white/10 bg-black/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">
            {t('liveWeather.locationLabel')}
          </p>
          <p className="mt-1 text-sm font-semibold">
            {props.location?.name || (props.location
              ? `${props.location.latitude.toFixed(3)}, ${props.location.longitude.toFixed(3)}`
              : props.status === 'requesting'
                ? t('liveWeather.locating')
                : t('liveWeather.selectLocation'))}
          </p>
        </div>
        <button
          type="button"
          onClick={props.onUseCurrentLocation}
          className="min-h-9 cursor-pointer rounded-lg border border-white/15 px-3 text-xs font-semibold hover:border-white/30"
        >
          {t('liveWeather.useCurrentLocation')}
        </button>
      </div>
      {props.status === 'needs_selection' || props.status === 'unsupported' ? (
        <p className="text-xs text-(--fs-muted)">{t('liveWeather.locationUnavailable')}</p>
      ) : null}
      <form onSubmit={(event) => void handleSearch(event)} className="flex gap-2">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t('liveWeather.searchPlaceholder')}
          aria-label={t('liveWeather.searchPlaceholder')}
          className="min-w-0 flex-1 rounded-lg border border-white/15 bg-black/25 px-3 py-2 text-sm text-white outline-none focus:border-(--fs-green)"
        />
        <button
          type="submit"
          disabled={isSearching || query.trim().length < 2}
          className="min-h-10 rounded-lg bg-(--fs-green) px-4 text-sm font-bold text-[#031007] disabled:opacity-50"
        >
          {isSearching ? t('liveWeather.searching') : t('liveWeather.search')}
        </button>
      </form>
      {searchFailed ? <p className="text-xs text-(--fs-muted)">{t('liveWeather.tryAgain')}</p> : null}
      {hasSearched && results.length === 0 ? (
        <p className="text-xs text-(--fs-muted)">{t('liveWeather.noSearchResults')}</p>
      ) : null}
      {results.length > 0 ? (
        <ul className="grid max-h-44 gap-1 overflow-y-auto" aria-label={t('liveWeather.searchResults')}>
          {results.map((result) => (
            <li key={`${result.name}:${result.latitude}:${result.longitude}`}>
              <button
                type="button"
                onClick={() => {
                  props.onSelectLocation(result)
                  setResults([])
                  setHasSearched(false)
                  setQuery('')
                }}
                className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-white/10"
              >
                {result.name}{result.region ? ` · ${result.region}` : ''}
                {result.country ? ` · ${result.country}` : ''}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
