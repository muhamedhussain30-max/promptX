import { Routes, Route, Navigate } from 'react-router-dom'
import HomePage from '@/pages/HomePage'
import HostLoginPage from '@/pages/HostLoginPage'
import CreateGamePage from '@/pages/CreateGamePage'
import JoinPage from '@/pages/JoinPage'
import LobbyPage from '@/pages/LobbyPage'
import GamePage from '@/pages/GamePage'
import HostDashboardPage from '@/pages/HostDashboardPage'
import ResultsPage from '@/pages/ResultsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/host/login" element={<HostLoginPage />} />
      <Route path="/host/create" element={<CreateGamePage />} />
      <Route path="/host/dashboard/:roomCode" element={<HostDashboardPage />} />
      <Route path="/join" element={<JoinPage />} />
      <Route path="/lobby/:roomCode" element={<LobbyPage />} />
      <Route path="/game/:roomCode" element={<GamePage />} />
      <Route path="/results/:roomCode" element={<ResultsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
