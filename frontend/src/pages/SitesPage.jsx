import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import client from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { MapPin, Plus } from 'lucide-react'
import ErrorMessage from '../components/ErrorMessage'

export default function SitesPage() {
  const [searchParams] = useSearchParams()
  const orgFilter = searchParams.get('org')

  const [sites, setSites] = useState([])
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    organization_id: orgFilter ? Number(orgFilter) : '',
    nickname: '',
    address: '',
    contact_name: '',
    contact_phone: '',
    contact_email: '',
    operating_hours: '',
  })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    try {
      const [sitesRes, orgsRes] = await Promise.all([
        client.get('/sites'),
        client.get('/organizations'),
      ])
      setSites(sitesRes.data.sites)
      setOrgs(orgsRes.data.organizations)
    } catch {
      setError('Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = orgFilter
    ? sites.filter(s => String(s.organization_id) === orgFilter)
    : sites

  const create = async () => {
    if (!form.organization_id || !form.nickname.trim()) return
    setSaving(true)
    try {
      const res = await client.post('/sites', {
        ...form,
        organization_id: Number(form.organization_id),
      })
      setShowCreate(false)
      setForm({ organization_id: orgFilter ? Number(orgFilter) : '', nickname: '', address: '', contact_name: '', contact_phone: '', contact_email: '', operating_hours: '' })
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create site')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MapPin className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold tracking-tight">Sites</h1>
          {orgFilter && orgs.length > 0 && (
            <span className="text-muted-foreground text-sm">
              — {orgs.find(o => String(o.id) === orgFilter)?.name}
            </span>
          )}
        </div>
        <Button onClick={() => setShowCreate(v => !v)}>
          <Plus className="h-4 w-4" />New Site
        </Button>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      {showCreate && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">New Site</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Organization *</label>
                <Select
                  value={String(form.organization_id)}
                  onValueChange={v => setForm(f => ({ ...f, organization_id: Number(v) }))}
                >
                  <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                  <SelectContent>
                    {orgs.map(o => <SelectItem key={o.id} value={String(o.id)}>{o.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Nickname *</label>
                <Input value={form.nickname} onChange={e => setForm(f => ({ ...f, nickname: e.target.value }))} placeholder="e.g. Phoenix Plant" />
              </div>
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-medium text-muted-foreground">Address</label>
                <Input value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))} placeholder="123 Main St, Phoenix AZ 85001" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Contact Name</label>
                <Input value={form.contact_name} onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))} placeholder="Jane Smith" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Contact Phone</label>
                <Input value={form.contact_phone} onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))} placeholder="+1 555 000 0000" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Contact Email</label>
                <Input value={form.contact_email} onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))} placeholder="jane@example.com" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Operating Hours</label>
                <Input value={form.operating_hours} onChange={e => setForm(f => ({ ...f, operating_hours: e.target.value }))} placeholder="Mon–Fri 6am–10pm" />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <Button onClick={create} disabled={saving || !form.organization_id || !form.nickname.trim()}>
                {saving ? 'Creating…' : 'Create Site'}
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nickname</TableHead>
              <TableHead>Organization</TableHead>
              <TableHead>Address</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead className="w-16"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">Loading...</TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">No sites yet</TableCell>
              </TableRow>
            ) : filtered.map(site => (
              <TableRow key={site.id}>
                <TableCell className="font-medium">{site.nickname}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{site.organization_name}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{site.address || '—'}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{site.contact_name || '—'}</TableCell>
                <TableCell>
                  <Button variant="ghost" size="sm" asChild>
                    <Link to={`/sites/${site.id}`}>Edit</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
