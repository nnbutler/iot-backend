import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import client from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Save, MapPin, LocateFixed, Trash2, Send } from 'lucide-react'
import ErrorMessage from '../components/ErrorMessage'
import { formatDate } from '../utils/formatting'

export default function SiteDetail() {
  const { site_id } = useParams()
  const [site, setSite] = useState(null)
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [geocoding, setGeocoding] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState(null)

  const [comments, setComments] = useState([])
  const [commentsLoading, setCommentsLoading] = useState(true)
  const [newComment, setNewComment] = useState('')
  const [submittingComment, setSubmittingComment] = useState(false)
  const commentRef = useRef(null)

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
        latitude: siteRes.data.latitude ?? '',
        longitude: siteRes.data.longitude ?? '',
        timezone: siteRes.data.timezone || '',
      })
    } catch {
      setError('Failed to load site')
    } finally {
      setLoading(false)
    }
  }

  const loadComments = async () => {
    try {
      const res = await client.get(`/sites/${site_id}/comments`)
      setComments(res.data.comments)
    } catch {
      // non-fatal
    } finally {
      setCommentsLoading(false)
    }
  }

  useEffect(() => {
    load()
    loadComments()
  }, [site_id])

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await client.patch(`/sites/${site_id}`, {
        ...form,
        organization_id: Number(form.organization_id),
        latitude: form.latitude !== '' ? Number(form.latitude) : null,
        longitude: form.longitude !== '' ? Number(form.longitude) : null,
        timezone: form.timezone || null,
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

  const geocode = async () => {
    setGeocoding(true)
    setError(null)
    try {
      const res = await client.post(`/sites/${site_id}/geocode`)
      setForm(f => ({
        ...f,
        latitude: res.data.latitude,
        longitude: res.data.longitude,
        timezone: res.data.timezone,
      }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Geocoding failed')
    } finally {
      setGeocoding(false)
    }
  }

  const submitComment = async () => {
    if (!newComment.trim()) return
    setSubmittingComment(true)
    try {
      const res = await client.post(`/sites/${site_id}/comments`, { body: newComment.trim() })
      setComments(prev => [res.data, ...prev])
      setNewComment('')
    } catch {
      setError('Failed to post comment')
    } finally {
      setSubmittingComment(false)
    }
  }

  const deleteComment = async (commentId) => {
    try {
      await client.delete(`/sites/${site_id}/comments/${commentId}`)
      setComments(prev => prev.filter(c => c.id !== commentId))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete comment')
    }
  }

  const field = (key) => ({
    value: form?.[key] ?? '',
    onChange: e => setForm(f => ({ ...f, [key]: e.target.value })),
  })

  if (loading) return <div className="max-w-3xl mx-auto px-4 py-8 text-muted-foreground">Loading...</div>
  if (!site) return <div className="max-w-3xl mx-auto px-4 py-8"><ErrorMessage message="Site not found" /></div>

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

      {/* Site Details */}
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

          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Location</p>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5"
                onClick={geocode}
                disabled={geocoding || !form.address}
                title={!form.address ? 'Enter an address first' : 'Detect from address'}
              >
                <LocateFixed className="h-3.5 w-3.5" />
                {geocoding ? 'Detecting…' : 'Auto-detect from address'}
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Latitude</label>
                <Input {...field('latitude')} placeholder="33.4484" type="number" step="any" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Longitude</label>
                <Input {...field('longitude')} placeholder="-112.0740" type="number" step="any" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Timezone</label>
                <Input {...field('timezone')} placeholder="America/Phoenix" />
              </div>
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

      {/* Devices */}
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

      {/* Comments */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Notes & Comments</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              ref={commentRef}
              value={newComment}
              onChange={e => setNewComment(e.target.value)}
              placeholder="Add a note about this site…"
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && submitComment()}
            />
            <Button onClick={submitComment} disabled={submittingComment || !newComment.trim()} size="sm">
              <Send className="h-4 w-4" />
            </Button>
          </div>

          {commentsLoading ? (
            <p className="text-sm text-muted-foreground">Loading comments…</p>
          ) : comments.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No notes yet</p>
          ) : (
            <div className="space-y-3">
              {comments.map(c => (
                <div key={c.id} className="flex gap-3 group">
                  <div className="flex-shrink-0 h-7 w-7 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                    {c.username[0].toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-semibold">{c.username}</span>
                      <span className="text-xs text-muted-foreground">{formatDate(c.created_at)}</span>
                    </div>
                    <p className="text-sm mt-0.5 whitespace-pre-wrap break-words">{c.body}</p>
                  </div>
                  <button
                    onClick={() => deleteComment(c.id)}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity flex-shrink-0 mt-0.5"
                    title="Delete comment"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
