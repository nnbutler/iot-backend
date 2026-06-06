import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Building2, Plus, Pencil, Check, X } from 'lucide-react'
import ErrorMessage from '../components/ErrorMessage'

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')

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
    if (!newName.trim()) return
    setCreating(true)
    try {
      await client.post('/organizations', { name: newName.trim() })
      setNewName('')
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create organization')
    } finally {
      setCreating(false)
    }
  }

  const startEdit = (org) => {
    setEditingId(org.id)
    setEditName(org.name)
  }

  const saveEdit = async (id) => {
    try {
      await client.patch(`/organizations/${id}`, { name: editName.trim() })
      setEditingId(null)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update organization')
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Building2 className="h-6 w-6 text-muted-foreground" />
        <h1 className="text-2xl font-semibold tracking-tight">Organizations</h1>
      </div>

      {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Add Organization</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="Organization name"
              onKeyDown={e => e.key === 'Enter' && create()}
              className="max-w-sm"
            />
            <Button onClick={create} disabled={creating || !newName.trim()}>
              <Plus className="h-4 w-4" />Add
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Sites</TableHead>
              <TableHead className="w-24"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground py-8">Loading...</TableCell>
              </TableRow>
            ) : orgs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground py-8">No organizations yet</TableCell>
              </TableRow>
            ) : orgs.map(org => (
              <TableRow key={org.id}>
                <TableCell className="font-medium">
                  {editingId === org.id ? (
                    <Input
                      value={editName}
                      onChange={e => setEditName(e.target.value)}
                      className="h-7 text-sm max-w-xs"
                      onKeyDown={e => { if (e.key === 'Enter') saveEdit(org.id); if (e.key === 'Escape') setEditingId(null) }}
                      autoFocus
                    />
                  ) : org.name}
                </TableCell>
                <TableCell>
                  <Link to={`/sites?org=${org.id}`} className="text-sm text-primary hover:underline">
                    View sites
                  </Link>
                </TableCell>
                <TableCell>
                  {editingId === org.id ? (
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => saveEdit(org.id)}>
                        <Check className="h-3.5 w-3.5 text-green-600" />
                      </Button>
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setEditingId(null)}>
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => startEdit(org)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
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
