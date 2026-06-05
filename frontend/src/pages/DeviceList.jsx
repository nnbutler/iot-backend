import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'
import { formatUptime } from '../utils/formatting'
import ErrorMessage from '../components/ErrorMessage'
import MqttDebug from '../components/MqttDebug'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

function StatusBadge({ online, since }) {
  const duration = since ? ` · ${formatUptime(since)}` : ''
  return online
    ? <Badge variant="success">Online{duration}</Badge>
    : <Badge variant="secondary">Offline{duration}</Badge>
}

export default function DeviceList() {
  const [tab, setTab] = useState('devices')
  const [devices, setDevices] = useState([])
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [errorFilter, setErrorFilter] = useState('all')
  const [sortBy, setSortBy] = useState('device_id')
  const [sortOrder, setSortOrder] = useState('asc')

  useEffect(() => {
    fetchDevices()
  }, [search, statusFilter, errorFilter, sortBy, sortOrder])

  const fetchDevices = async () => {
    try {
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
      setInitialLoading(false)
    }
  }

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  const SortIcon = ({ field }) => {
    if (sortBy !== field) return <ArrowUpDown className="ml-1 h-3.5 w-3.5 text-muted-foreground/50 inline" />
    return sortOrder === 'asc'
      ? <ArrowUp className="ml-1 h-3.5 w-3.5 text-primary inline" />
      : <ArrowDown className="ml-1 h-3.5 w-3.5 text-primary inline" />
  }

  if (initialLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center text-muted-foreground">Loading devices...</div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Devices</h1>
        <div className="flex gap-1 bg-muted rounded-lg p-1">
          {['devices', 'debug'].map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                tab === t
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t === 'debug' ? 'MQTT Debug' : 'Devices'}
            </button>
          ))}
        </div>
      </div>

      {tab === 'debug' && <MqttDebug />}

      {tab === 'devices' && (
        <>
          {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

          <Card>
            <CardContent className="pt-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-foreground">Search</label>
                  <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Device ID, customer, location…"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-foreground">Status</label>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="online">Online</SelectItem>
                      <SelectItem value="offline">Offline</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-foreground">Errors</label>
                  <Select value={errorFilter} onValueChange={setErrorFilter}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="error">With Error</SelectItem>
                      <SelectItem value="healthy">Healthy</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-foreground">Results</label>
                  <div className="flex h-9 items-center px-3 rounded-md border border-input bg-muted/50 text-sm text-muted-foreground">
                    {devices.length} device{devices.length !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  {[
                    { label: 'Device ID', field: 'device_id' },
                    { label: 'Customer', field: 'customer_name' },
                    { label: 'Location', field: 'location' },
                    { label: 'Status', field: 'online' },
                    { label: 'Last Error', field: 'last_error' },
                  ].map(({ label, field }) => (
                    <TableHead key={field}>
                      <button
                        onClick={() => handleSort(field)}
                        className="flex items-center font-medium text-foreground hover:text-primary transition-colors"
                      >
                        {label}<SortIcon field={field} />
                      </button>
                    </TableHead>
                  ))}
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                      No devices found
                    </TableCell>
                  </TableRow>
                ) : (
                  devices.map((device) => (
                    <TableRow key={device.device_id}>
                      <TableCell className="font-mono text-sm">{device.device_id}</TableCell>
                      <TableCell className="text-sm">{device.customer_name || '—'}</TableCell>
                      <TableCell className="text-sm">{device.location || '—'}</TableCell>
                      <TableCell>
                        <StatusBadge
                          online={device.online}
                          since={device.online ? device.online_since : device.last_seen}
                        />
                      </TableCell>
                      <TableCell className="text-sm">
                        {device.last_error
                          ? <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{device.last_error}</code>
                          : <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" asChild>
                          <Link to={`/devices/${device.device_id}`}>View</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </>
      )}
    </div>
  )
}
