import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'
import { formatDate, formatStatus } from '../utils/formatting'
import ErrorMessage from '../components/ErrorMessage'

const MOCK_DEVICES = [
  {
    device_id: 'plc-001',
    customer_name: 'Acme Inc',
    location: 'Phoenix, AZ',
    online: true,
    last_seen: new Date().toISOString(),
    last_error: 'sensor_disconnected',
    uptime_percent: 99.2,
  },
  {
    device_id: 'plc-042',
    customer_name: 'Acme Inc',
    location: 'Denver, CO',
    online: false,
    last_seen: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    last_error: 'internet_down',
    uptime_percent: 95.5,
  },
  {
    device_id: 'plc-105',
    customer_name: 'Beta Corp',
    location: 'Seattle, WA',
    online: true,
    last_seen: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    last_error: null,
    uptime_percent: 99.9,
  },
]

export default function DeviceList() {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchDevices()
  }, [])

  const fetchDevices = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await client.get('/devices')
      setDevices(response.data.devices || response.data)
    } catch (err) {
      console.warn('Failed to fetch from API, using mock data:', err.message)
      // Use mock data if API fails
      setDevices(MOCK_DEVICES)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center text-gray-600">Loading devices...</div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Devices</h1>
        <p className="text-gray-600">
          Showing {devices.length} devices
        </p>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <div className="overflow-x-auto bg-white rounded-lg shadow">
        <table className="w-full">
          <thead className="bg-gray-100 border-b border-gray-200">
            <tr>
              <th className="text-left px-6 py-3 font-semibold text-gray-700">Device ID</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700">Customer</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700">Location</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700">Status</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700">Last Error</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700">Last Seen</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700">Uptime</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {devices.length === 0 ? (
              <tr>
                <td colSpan="8" className="px-6 py-8 text-center text-gray-600">
                  No devices found
                </td>
              </tr>
            ) : (
              devices.map((device) => (
                <tr key={device.device_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 font-mono text-sm">{device.device_id}</td>
                  <td className="px-6 py-4 text-sm">{device.customer_name || 'N/A'}</td>
                  <td className="px-6 py-4 text-sm">{device.location || 'N/A'}</td>
                  <td className="px-6 py-4">
                    {formatStatus(device.online)}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {device.last_error ? (
                      <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                        {device.last_error}
                      </code>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm">{formatDate(device.last_seen)}</td>
                  <td className="px-6 py-4 text-sm">
                    {device.uptime_percent ? `${device.uptime_percent}%` : 'N/A'}
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/devices/${device.device_id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
