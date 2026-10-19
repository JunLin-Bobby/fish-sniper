import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { SignOutButton } from '../../auth/components/SignOutButton.tsx'
import { useCurrentUser } from '../../users/hooks/useCurrentUser.ts'
import { forecastDate, ForecastDatePicker } from '../../weather/components/ForecastDatePicker.tsx'
import { LocationPicker } from '../../weather/components/LocationPicker.tsx'
import { WeatherDashboard } from '../../weather/components/WeatherDashboard.tsx'
import { WeatherSummary } from '../../weather/components/WeatherSummary.tsx'
import { useDailyConditions } from '../../weather/hooks/useDailyConditions.ts'
import { useSelectedLocation } from '../../weather/hooks/useSelectedLocation.ts'
import { CatchLogPanel } from '../components/CatchLogPanel.tsx'
import { StrategySummaryPanel } from '../components/StrategySummaryPanel.tsx'
import { TacticalMapPreview } from '../components/TacticalMapPreview.tsx'
import { TacticalShell } from '../components/TacticalShell.tsx'

// 統一管理首頁釣點、日期與一份預報，以響應式版面組合環境、策略、地圖及紀錄。
export function DashboardPage(props: { apiBaseUrl: string; onSignOut: () => void }) {
  const { t } = useTranslation()
  const currentUser = useCurrentUser(props.apiBaseUrl, props.onSignOut)
  const [daysAhead, setDaysAhead] = useState(0)
  const date = forecastDate(daysAhead)
  const { location, status, requestBrowserLocation, selectLocation } = useSelectedLocation()
  const { weather, retry } = useDailyConditions(props.apiBaseUrl, location, date, props.onSignOut)
  const sessionLabel = currentUser.isLoading
    ? t('dashboard.validatingSession')
    : currentUser.user ? t('dashboard.signedInAs', { email: currentUser.user.email })
      : currentUser.hasError ? t('dashboard.userUnavailable') : t('dashboard.sessionUnavailable')

  return (
    <TacticalShell actions={<SignOutButton onSignOut={props.onSignOut} />} sessionLabel={sessionLabel}>
      <section id="overview" tabIndex={-1} aria-labelledby="overview-heading" className="dashboard-anchor mb-5 grid min-w-0 gap-4">
        <div>
          <h1 id="overview-heading" className="text-2xl font-bold">{t('dashboardLayout.overviewTitle')}</h1>
          <p className="mt-1 text-sm text-(--fs-muted)">{t('dashboardLayout.overviewDescription')}</p>
        </div>
        <LocationPicker apiBaseUrl={props.apiBaseUrl} location={location} status={status}
          onUseCurrentLocation={requestBrowserLocation} onSelectLocation={selectLocation} onUnauthorized={props.onSignOut} />
        <ForecastDatePicker daysAhead={daysAhead} onChange={setDaysAhead} />
      </section>
      <div className="dashboard-layout" data-has-summary={weather.status === 'ready' && weather.data !== null}>
        {weather.status === 'ready' && weather.data ? (
          <div className="dashboard-summary"><WeatherSummary weather={weather.data} /></div>
        ) : null}
        <StrategySummaryPanel location={location} date={date} />
        <div className="dashboard-weather"><WeatherDashboard weather={weather} hasLocation={location !== null} onRetry={retry} /></div>
        <TacticalMapPreview location={location} />
        <CatchLogPanel />
      </div>
    </TacticalShell>
  )
}
