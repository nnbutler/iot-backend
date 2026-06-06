import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import client from '../api/client'
import { formatDate, formatUptime } from '../utils/formatting'
import ErrorMessage from '../components/ErrorMessage'
import SendCommandModal from '../components/SendCommandModal'
import RepairOutcomeModal from '../components/RepairOutcomeModal'
import AssignSiteModal from '../components/AssignSiteModal'
import DeviceLogs from '../components/DeviceLogs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Terminal, Wrench, MapPin } from 'lucide-react'

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
      { id: 1, step: 1, action: 'Check physical cable connection at sensor and PLC', description: 'Verify cable is plugged in at both ends and connector is seated properly', estimated_time: 5, success_rate: 0.88 },
      { id: 2, step: 2, action: 'Power cycle the sensor', description: 'Turn off sensor (power switch or unplug), wait 10 seconds, turn back on', estimated_time: 2, success_rate: 0.85 },
      { id: 3, step: 3, action: 'Power cycle entire unit', description: 'Perform full power cycle of the entire equipment', estimated_time: 3, success_rate: 0.92 },
    ],
  },
}

function InfoRow({ label, children }) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="mt-0.5">{children}</div>
    </div>
  )
}

export default function DeviceDetail() {
  const { device_id } = useParams()
  const [device, setDevice] = useState(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCommandModal, setShowCommandModal] = useState(false)
  const [showRepairModal, setShowRepairModal] = useState(false)
  const [showSiteModal, setShowSiteModal] = useState(false)

  useEffect(() => { fetchDevice() }, [device_id])

  const fetchDevice = async () => {
    try {
      setError(null)
      const response = await client.get(`/devices/${device_id}/status`)
      setDevice(response.data)
    } catch (err) {
      console.warn('Failed to fetch from API, using mock data:', err.message)
      setDevice(MOCK_DEVICE_STATUS)
    } finally {
      setInitialLoading(false)
    }
  }

  if (initialLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center text-muted-foreground">
        Loading device...
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
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/devices"><ArrowLeft className="h-4 w-4 mr-1" />Devices</Link>
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight font-mono">{device.device_id}</h1>
        {(() => {
          const since = device.online ? device.online_since : device.last_seen
          const duration = since ? ` · ${formatUptime(since)}` : ''
          return (
            <Badge variant={device.online ? 'success' : 'secondary'}>
              {device.online ? 'Online' : 'Offline'}{duration}
            </Badge>
          )
        })()}
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Device Info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Device Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <InfoRow label="Type">
              <span className="text-foreground">{device.device_type || '—'}</span>
            </InfoRow>
            <InfoRow label="Customer">
              <span className="text-foreground">{device.customer_name || '—'}</span>
            </InfoRow>
            <InfoRow label="Location">
              <span className="text-foreground">{device.location || '—'}</span>
            </InfoRow>
            <InfoRow label="Firmware">
              <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{device.firmware_version || '—'}</code>
            </InfoRow>
            <InfoRow label="Last Seen">
              <span className="text-foreground text-xs">{formatDate(device.last_seen)}</span>
            </InfoRow>
            <div className="border-t pt-3 space-y-3">
              <InfoRow label="Site">
                <div className="flex items-center gap-2">
                  {device.site_nickname
                    ? <Link to={`/sites/${device.site_id}`} className="text-primary hover:underline text-sm flex items-center gap-1"><MapPin className="h-3 w-3" />{device.site_nickname}</Link>
                    : <span className="text-muted-foreground text-sm">Not assigned</span>}
                  <Button size="sm" variant="ghost" className="h-6 text-xs px-2" onClick={() => setShowSiteModal(true)}>
                    {device.site_id ? 'Change' : 'Assign'}
                  </Button>
                </div>
              </InfoRow>
              {device.organization_name && (
                <InfoRow label="Organization">
                  <span className="text-foreground">{device.organization_name}</span>
                </InfoRow>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Last Error */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Last Error</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {device.last_error ? (
              <div className="space-y-3">
                <InfoRow label="Code">
                  <code className="text-xs bg-destructive/10 text-destructive px-1.5 py-0.5 rounded">
                    {device.last_error.code}
                  </code>
                </InfoRow>
                <InfoRow label="Message">
                  <span className="text-foreground">{device.last_error.message}</span>
                </InfoRow>
                <InfoRow label="Occurred">
                  <span className="text-foreground text-xs">{formatDate(device.last_error.occurred_at)}</span>
                </InfoRow>
              </div>
            ) : (
              <p className="text-muted-foreground">No recent errors</p>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button className="w-full" onClick={() => setShowCommandModal(true)}>
              <Terminal className="h-4 w-4" />Send Command
            </Button>
            <Button className="w-full" variant="secondary" onClick={() => setShowRepairModal(true)}>
              <Wrench className="h-4 w-4" />Record Repair
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Repair Steps */}
      {device.troubleshooting && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">
                Repair Steps — {device.troubleshooting.display_name}
              </CardTitle>
              <Badge variant="outline">
                {(device.troubleshooting.success_rate * 100).toFixed(0)}% success rate
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {device.troubleshooting.repair_actions?.map((action, idx) => (
              <div key={action.id} className="flex gap-4">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center mt-0.5">
                  {idx + 1}
                </div>
                <div>
                  <p className="font-medium text-sm">{action.action}</p>
                  <p className="text-muted-foreground text-sm mt-0.5">{action.description}</p>
                  <div className="flex gap-4 mt-1 text-xs text-muted-foreground">
                    <span>~{action.estimated_time} min</span>
                    <span>{(action.success_rate * 100).toFixed(0)}% success</span>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <DeviceLogs device_id={device.device_id} />

      {showCommandModal && (
        <SendCommandModal
          device_id={device.device_id}
          onClose={() => setShowCommandModal(false)}
          onSuccess={() => { setShowCommandModal(false); fetchDevice() }}
        />
      )}
      {showRepairModal && (
        <RepairOutcomeModal
          device_id={device.device_id}
          error_code={device.last_error?.code}
          onClose={() => setShowRepairModal(false)}
          onSuccess={() => { setShowRepairModal(false); fetchDevice() }}
        />
      )}
      {showSiteModal && (
        <AssignSiteModal
          device_id={device.device_id}
          current_site_id={device.site_id}
          onClose={() => setShowSiteModal(false)}
          onSuccess={() => { setShowSiteModal(false); fetchDevice() }}
        />
      )}
    </div>
  )
}
