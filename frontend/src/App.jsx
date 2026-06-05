import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Header from './components/Header'
import Login from './pages/Login'
import DeviceList from './pages/DeviceList'
import DeviceDetail from './pages/DeviceDetail'

function ProtectedRoute({ children }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" replace />
}

function AppRoutes() {
  const { token, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50">
      {token && <Header onLogout={logout} />}
      <Routes>
        <Route path="/login" element={token ? <Navigate to="/devices" replace /> : <Login />} />
        <Route path="/devices" element={<ProtectedRoute><DeviceList /></ProtectedRoute>} />
        <Route path="/devices/:device_id" element={<ProtectedRoute><DeviceDetail /></ProtectedRoute>} />
        <Route path="/" element={<Navigate to="/devices" replace />} />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  )
}
