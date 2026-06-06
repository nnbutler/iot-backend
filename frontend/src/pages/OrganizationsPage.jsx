import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Building2, Plus, Pencil, Check, X, ExternalLink } from 'lucide-react'
import ErrorMessage from '../components/ErrorMessage'

const EMPTY_FORM = { name: '', logo_url: '', website: '' }

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newForm, setNewForm] = useState(EMPTY_FORM)
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(EMPTY_FORM)

  const load = async () => {
    try {
      const res = await client.get('/organizations')
      setOrgs(res.data.organizations)
    } catch {
      setError('Failed to load organizations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const create = async () => {
    if (!newForm.name.trim()) return
    setCreating(true)
    try {
      await client.post('/organizations', {
        name: newForm.name.trim(),
        logo_url: newForm.logo_url.trim() || null,
        website: newForm.website.trim() || null,
      })
      setNewForm(EMPTY_FORM)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create organization')
    } finally {
      setCreating(false)
    }
  }

  const startEdit = (org) => {
    setEditingId(org.id)
    setEditForm({ name: org.name, logo_url: org.logo_url || '', website: org.website || '' })
  }

  const saveEdit = async (id) => {
    try {
      await client.patch(`/organizations/${id}`, {
        name: editForm.name.trim(),
        logo_url: editForm.logo_url.trim() || null,
        website: editForm.website.trim() || null,
      })
      setEditingId(null)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update organization')
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Building2 className="h-6 w-6 text-muted-foreground" />
        <h1 className="text-2xl font-semibold tracking-tight">Organizations</h1>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Add Organization</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Input
              value={newForm.name}
              onChange={e => setNewForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Name *"
              onKeyDown={e => e.key === 'Enter' && create()}
            />
            <Input
              value={newForm.website}
              onChange={e => setNewForm(f => ({ ...f, website: e.target.value }))}
              placeholder="Website (e.g. https://acme.com)"
            />
            <Input
              value={newForm.logo_url}
              onChange={e => setNewForm(f => ({ ...f, logo_url: e.target.value }))}
              placeholder="Logo URL"
            />
          </div>
          <Button onClick={create} disabled={creating || !newForm.name.trim()}>
            <Plus className="h-4 w-4" />Add
          </Button>
        </CardContent>
      </Card>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10"></TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Website</TableHead>
              <TableHead>Logo URL</TableHead>
              <TableHead>Sites</TableHead>
              <TableHead className="w-20"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-8">Loading...</TableCell></TableRow>
            ) : orgs.length === 0 ? (
              <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-8">No organizations yet</TableCell></TableRow>
            ) : orgs.map(org => (
              <TableRow key={org.id}>
                <TableCell>
                  {org.logo_url
                    ? <img src={org.logo_url} alt="" className="h-7 w-7 rounded object-contain border border-border" onError={e => { e.target.style.display = 'none' }} />
                    : <div className="h-7 w-7 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground font-bold">{org.name[0]}</div>
                  }
                </TableCell>
                <TableCell className="font-medium">
                  {editingId === org.id
                    ? <Input value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} className="h-7 text-sm" autoFocus onKeyDown={e => { if (e.key === 'Enter') saveEdit(org.id); if (e.key === 'Escape') setEditingId(null) }} />
                    : org.name}
                </TableCell>
                <TableCell className="text-sm">
                  {editingId === org.id
                    ? <Input value={editForm.website} onChange={e => setEditForm(f => ({ ...f, website: e.target.value }))} className="h-7 text-sm" placeholder="https://…" />
                    : org.website
                      ? <a href={org.website} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline flex items-center gap-1">{org.website.replace(/^https?:\/\//, '')}<ExternalLink className="h-3 w-3" /></a>
                      : <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell className="text-sm max-w-xs truncate">
                  {editingId === org.id
                    ? <Input value={editForm.logo_url} onChange={e => setEditForm(f => ({ ...f, logo_url: e.target.value }))} className="h-7 text-sm" placeholder="https://…/logo.png" />
                    : org.logo_url
                      ? <span className="text-muted-foreground text-xs truncate">{org.logo_url}</span>
                      : <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell>
                  <Link to={`/sites?org=${org.id}`} className="text-sm text-primary hover:underline">View sites</Link>
                </TableCell>
                <TableCell>
                  {editingId === org.id ? (
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => saveEdit(org.id)}><Check className="h-3.5 w-3.5 text-green-600" /></Button>
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setEditingId(null)}><X className="h-3.5 w-3.5" /></Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => startEdit(org)}><Pencil className="h-3.5 w-3.5" /></Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
