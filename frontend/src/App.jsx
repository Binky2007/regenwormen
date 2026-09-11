// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { SocketProvider } from './context/SocketContext'
import { GameProvider } from './context/GameContext'
import Header from './components/Header'
import Lobby from './pages/Lobby'
import Table from './pages/Table'
import Rules from './pages/Rules'
import Leaderboard from './pages/Leaderboard'
import Profile from './pages/Profile'
import SignedOut from './pages/SignedOut'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? children : <Navigate to="/signed-out" replace />
}

function Shell() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', fontFamily: "'Archivo', system-ui, sans-serif", color: '#1c1a14', background: '#e9e3d5' }}>
      <Header />
      <main style={{ flex: '1 1 auto', display: 'flex', flexDirection: 'column' }}>
        <Routes>
          <Route path="/" element={<Lobby />} />
          <Route path="/table" element={<RequireAuth><Table /></RequireAuth>} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />
          <Route path="/signed-out" element={<SignedOut />} />
        </Routes>
      </main>
      <footer style={{ padding: '22px 20px 30px', textAlign: 'center', font: "400 12px 'Archivo', sans-serif", color: '#77736a', borderTop: '1px solid #c9c2b1' }}>
        Fan-made table for Regenwormen. Prototype.
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SocketProvider>
          <GameProvider>
            <Shell />
          </GameProvider>
        </SocketProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
