import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import client from '../api/client'
import { formatDate, formatStatus, formatSeverity } from '../utils/formatting'
import ErrorMessage from '../components/ErrorMessage'
import SendCommandModal from '../components/SendCommandModal'
import RepairOutcomeModal from '../components/RepairOutcomeModal'
import DeviceLogs from '../components/DeviceLogs'

const MOCK_DEVICE_STATUS = {
  device_id: 'plc-001',
  online: true,
  last_seen: new Date().toISOString(),
  state: 'idle',
  firmware_version: '1.2.3',
  location: 'Phoenix, AZ',
  customer_name: 'Acme Inc',
  device_type: 'plc',
  last_error: {
    code: 'sensor_disconnected',
    message: 'Sensor X not responding',
    occurred_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  },
  troubleshooting: {
    display_name: 'Sensor Disconnected',
    success_rate: 0.88,
    repair_actions: [
      {
        id: 1,
        step: 1,
        action: 'Check physical cable connection at sensor and PLC',
        description: 'Verify cable is plugged in at both ends and connector is seated properly',
        estimated_time: 5,
        success_rate: 0.88,
      },
      {
        id: 2,
        step: 2,
        action: 'Power cycle the sensor',
        description: 'Turn off sensor (power switch or unplug), wait 10 seconds, turn back on',
        estimated_time: 2,
        success_rate: 0.85,
      },
      {
        id: 3,
        step: 3,
        action: 'Power cycle entire unit',
        description: 'Perform full power cycle of the entire equipment',
        estimated_time: 3,
        success_rate: 0.92,
      },
    ],
  },
}

export default function DeviceDetail() {
  const { device_id } = useParams()
  const [device, setDevice] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCommandModal, setShowCommandModal] = useState(false)
  const [showRepairModal, setShowRepairModal] = useState(false)

  useEffect(() => {
    fetchDevice()
  }, [device_id])

  const fetchDevice = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await client.get(`/devices/${device_id}/status`)
      setDevice(response.data)
    } catch (err) {
      console.warn('Failed to fetch from API, using mock data:', err.message)
      setDevice(MOCK_DEVICE_STATUS)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center text-gray-600">Loading device...</div>
      </div>
    )
  }

  if (!device) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <ErrorMessage message="Device not found" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link to="/devices" className="text-blue-600 hover:text-blue-800 mb-6 inline-block">
        ← Back to Devices
      </Link>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Device Info Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Device Info</h2>
          <div className="space-y-3 text-sm">
            <div>
              <span className="font-medium text-gray-600">ID:</span>
              <p className="font-mono text-gray-900">{device.device_id}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Status:</span>
              <p className="mt-1">{formatStatus(device.online)}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Type:</span>
              <p className="text-gray-900">{device.device_type || 'N/A'}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Customer:</span>
              <p className="text-gray-900">{device.customer_name || 'N/A'}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Location:</span>
              <p className="text-gray-900">{device.location || 'N/A'}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Firmware:</span>
              <p className="text-gray-900">{device.firmware_version || 'N/A'}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Last Seen:</span>
              <p className="text-gray-900 text-xs">{formatDate(device.last_seen)}</p>
            </div>
          </div>
        </div>

        {/* Last Error Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Last Error</h2>
          {device.last_error ? (
            <div className="space-y-3">
              <div>
                <span className="font-medium text-gray-600 text-sm">Code:</span>
                <p className="font-mono text-sm text-red-700 bg-red-50 px-2 py-1 rounded mt-1">
                  {device.last_error.code}
                </p>
              </div>
              <div>
                <span className="font-medium text-gray-600 text-sm">Message:</span>
                <p className="text-gray-900 text-sm mt-1">{device.last_error.message}</p>
              </div>
              <div>
                <span className="font-medium text-gray-600 text-sm">Occurred:</span>
                <p className="text-gray-900 text-xs mt-1">{formatDate(device.last_error.occurred_at)}</p>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">No recent errors</p>
          )}
        </div>

        {/* Actions Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Actions</h2>
          <div className="space-y-3">
            <button
              onClick={() => setShowCommandModal(true)}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm"
            >
              Send Command
            </button>
            <button
              onClick={() => setShowRepairModal(true)}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium text-sm"
            >
              Record Repair
            </button>
          </div>
        </div>
      </div>

      {/* Repair Suggestions */}
      {device.troubleshooting && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">
            Repair Steps for: {device.troubleshooting.display_name}
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Success rate: {(device.troubleshooting.success_rate * 100).toFixed(1)}%
          </p>
          <div className="space-y-4">
            {device.troubleshooting.repair_actions?.map((action, idx) => (
              <div key={action.id} className="border-l-4 border-blue-500 pl-4 py-2">
                <h3 className="font-semibold text-gray-900 text-sm">
                  Step {idx + 1}: {action.action}
                </h3>
                <p className="text-gray-600 text-sm mt-1">{action.description}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                  <span>Estimated: {action.estimated_time} min</span>
                  <span>Success rate: {(action.success_rate * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-6">
        <DeviceLogs device_id={device.device_id} />
      </div>

      {/* Modals */}
      {showCommandModal && (
        <SendCommandModal
          device_id={device.device_id}
          onClose={() => setShowCommandModal(false)}
          onSuccess={() => {
            setShowCommandModal(false)
            fetchDevice()
          }}
        />
      )}

      {showRepairModal && (
        <RepairOutcomeModal
          device_id={device.device_id}
          error_code={device.last_error?.code}
          onClose={() => setShowRepairModal(false)}
          onSuccess={() => {
            setShowRepairModal(false)
            fetchDevice()
          }}
        />
      )}
    </div>
  )
}
