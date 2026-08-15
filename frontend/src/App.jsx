import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { VoltBuddyProvider } from './context/VoltBuddyContext'
import AppLayout from './layout/AppLayout'
import DashboardPage from './pages/DashboardPage'
import FindAppliancesPage from './pages/FindAppliancesPage'
import HistoryPage from './pages/HistoryPage'
import HomeSetupPage from './pages/HomeSetupPage'
import InsightsPage from './pages/InsightsPage'
import RatesPage from './pages/RatesPage'
import RecommendationsPage from './pages/RecommendationsPage'
import ResultsPage from './pages/ResultsPage'
import SchedulePage from './pages/SchedulePage'
import SimulatePage from './pages/SimulatePage'
import './App.css'

function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/home" element={<HomeSetupPage />} />
        <Route path="/appliances" element={<FindAppliancesPage />} />
        <Route path="/simulate" element={<SimulatePage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/schedule" element={<SchedulePage />} />
        <Route path="/rates" element={<RatesPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <VoltBuddyProvider>
        <AppRoutes />
      </VoltBuddyProvider>
    </BrowserRouter>
  )
}

export default App
