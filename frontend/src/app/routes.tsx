import { Route, Routes } from 'react-router-dom'

import { DashboardPage } from '../dashboard/pages/DashboardPage.tsx'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="*" element={<DashboardPage />} />
    </Routes>
  )
}
