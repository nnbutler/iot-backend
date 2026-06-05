import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'
import { formatDate, formatStatus } from '../utils/formatting'
import ErrorMessage from '../components/ErrorMessage'

export default function DeviceList() {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filter state
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [errorFilter, setErrorFilter] = useState('all')

  // Sort state
  const [sortBy, setSortBy] = useState('device_id')
  const [sortOrder, setSortOrder] = useState('asc')

  useEffect(() => {
    fetchDevices()
  }, [search, statusFilter, errorFilter, sortBy, sortOrder])

  const fetchDevices = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (search) params.append('search', search)
      if (statusFilter !== 'all') params.append('online', statusFilter === 'online')
      if (errorFilter !== 'all') params.append('has_error', errorFilter === 'error')
      params.append('sort_by', sortBy)
      params.append('sort_order', sortOrder)

      const response = await client.get(`/devices?${params.toString()}`)
      setDevices(response.data.devices || response.data)
    } catch (err) {
      console.warn('Failed to fetch devices:', err.message)
      setError('Failed to load devices')
      setDevices([])
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (field) => {
    if (sortBy === field) {
      // Toggle order if same field clicked
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      // New field, start with asc
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  const SortIcon = ({ field }) => {
    if (sortBy !== field) return <span className="text-gray-300">⇅</span>
    return sortOrder === 'asc' ? <span className="text-blue-600">↑</span> : <span className="text-blue-600">↓</span>
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center text-gray-600">Loading devices...</div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-4">Devices</h1>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Device ID, customer, location..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All</option>
                <option value="online">Online</option>
                <option value="offline">Offline</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Errors</label>
              <select
                value={errorFilter}
                onChange={(e) => setErrorFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All</option>
                <option value="error">With Error</option>
                <option value="healthy">Healthy</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Results</label>
              <div className="py-2 px-3 bg-gray-100 rounded-lg text-sm text-gray-700">
                {devices.length} device{devices.length !== 1 ? 's' : ''}
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <div className="overflow-x-auto bg-white rounded-lg shadow">
        <table className="w-full">
          <thead className="bg-gray-100 border-b border-gray-200">
            <tr>
              <th className="text-left px-6 py-3 font-semibold text-gray-700 cursor-pointer hover:bg-gray-200" onClick={() => handleSort('device_id')}>
                Device ID <SortIcon field="device_id" />
              </th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700 cursor-pointer hover:bg-gray-200" onClick={() => handleSort('customer_name')}>
                Customer <SortIcon field="customer_name" />
              </th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700 cursor-pointer hover:bg-gray-200" onClick={() => handleSort('location')}>
                Location <SortIcon field="location" />
              </th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700 cursor-pointer hover:bg-gray-200" onClick={() => handleSort('online')}>
                Status <SortIcon field="online" />
              </th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700 cursor-pointer hover:bg-gray-200" onClick={() => handleSort('last_error')}>
                Last Error <SortIcon field="last_error" />
              </th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700 cursor-pointer hover:bg-gray-200" onClick={() => handleSort('last_seen')}>
                Last Seen <SortIcon field="last_seen" />
              </th>
              <th className="text-left px-6 py-3 font-semibold text-gray-700 cursor-pointer hover:bg-gray-200" onClick={() => handleSort('uptime_percent')}>
                Uptime <SortIcon field="uptime_percent" />
              </th>
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
