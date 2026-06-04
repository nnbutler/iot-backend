import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Header from './components/Header'
import DeviceList from './pages/DeviceList'
import DeviceDetail from './pages/DeviceDetail'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <Routes>
          <Route path="/devices" element={<DeviceList />} />
          <Route path="/devices/:device_id" element={<DeviceDetail />} />
          <Route path="/" element={<Navigate to="/devices" replace />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
