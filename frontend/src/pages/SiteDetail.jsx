import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import client from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Save } from 'lucide-react'
import ErrorMessage from '../components/ErrorMessage'

export default function SiteDetail() {
  const { site_id } = useParams()
  const [site, setSite] = useState(null)
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState(null)

  const load = async () => {
    try {
      const [siteRes, orgsRes] = await Promise.all([
        client.get(`/sites/${site_id}`),
        client.get('/organizations'),
      ])
      setSite(siteRes.data)
      setOrgs(orgsRes.data.organizations)
      setForm({
        organization_id: siteRes.data.organization_id,
        nickname: siteRes.data.nickname || '',
        address: siteRes.data.address || '',
        contact_name: siteRes.data.contact_name || '',
        contact_phone: siteRes.data.contact_phone || '',
        contact_email: siteRes.data.contact_email || '',
        operating_hours: siteRes.data.operating_hours || '',
      })
    } catch {
      setError('Failed to load site')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [site_id])

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await client.patch(`/sites/${site_id}`, {
        ...form,
        organization_id: Number(form.organization_id),
      })
      setSite(res.data)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const field = (key) => ({
    value: form?.[key] ?? '',
    onChange: e => setForm(f => ({ ...f, [key]: e.target.value })),
  })

  if (loading) {
    return <div className="max-w-3xl mx-auto px-4 py-8 text-muted-foreground">Loading...</div>
  }

  if (!site) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <ErrorMessage message="Site not found" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/sites"><ArrowLeft className="h-4 w-4 mr-1" />Sites</Link>
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight">{site.nickname}</h1>
        <span className="text-muted-foreground text-sm">{site.organization_name}</span>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Site Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Organization</label>
              <Select
                value={String(form.organization_id)}
                onValueChange={v => setForm(f => ({ ...f, organization_id: Number(v) }))}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {orgs.map(o => <SelectItem key={o.id} value={String(o.id)}>{o.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Nickname</label>
              <Input {...field('nickname')} placeholder="e.g. Phoenix Plant" />
            </div>
            <div className="space-y-1.5 md:col-span-2">
              <label className="text-xs font-medium text-muted-foreground">Address</label>
              <Input {...field('address')} placeholder="123 Main St, Phoenix AZ 85001" />
            </div>
          </div>

          <div className="border-t pt-4">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Point of Contact</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Name</label>
                <Input {...field('contact_name')} placeholder="Jane Smith" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Phone</label>
                <Input {...field('contact_phone')} placeholder="+1 555 000 0000" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Email</label>
                <Input {...field('contact_email')} placeholder="jane@example.com" />
              </div>
            </div>
          </div>

          <div className="border-t pt-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Operating Hours</label>
              <Input {...field('operating_hours')} placeholder="Mon–Fri 6am–10pm, Sat 8am–6pm" />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <Button onClick={save} disabled={saving}>
              <Save className="h-4 w-4" />{saving ? 'Saving…' : 'Save Changes'}
            </Button>
            {saved && <span className="text-sm text-green-600">Saved</span>}
          </div>
        </CardContent>
      </Card>

      {site.devices && site.devices.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Devices at this Site</CardTitle>
          </CardHeader>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Device ID</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Error</TableHead>
                <TableHead className="w-16"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {site.devices.map(d => (
                <TableRow key={d.device_id}>
                  <TableCell className="font-mono text-sm">{d.device_id}</TableCell>
                  <TableCell>
                    <Badge variant={d.online ? 'success' : 'secondary'}>{d.online ? 'Online' : 'Offline'}</Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    {d.last_error
                      ? <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{d.last_error}</code>
                      : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" asChild>
                      <Link to={`/devices/${d.device_id}`}>View</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}
