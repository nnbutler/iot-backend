import { useState, useEffect } from 'react'
import client from '../api/client'
import { Button } from '@/components/ui/button'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { X } from 'lucide-react'

export default function AssignSiteModal({ device_id, current_site_id, onClose, onSuccess }) {
  const [sites, setSites] = useState([])
  const [selectedSite, setSelectedSite] = useState(current_site_id ? String(current_site_id) : '')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    client.get('/sites')
      .then(res => setSites(res.data.sites))
      .catch(() => setError('Failed to load sites'))
      .finally(() => setLoading(false))
  }, [])

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      if (selectedSite) {
        await client.patch(`/sites/${selectedSite}/devices/${device_id}`)
      } else if (current_site_id) {
        await client.delete(`/sites/${current_site_id}/devices/${device_id}`)
      }
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to assign site')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-background rounded-xl shadow-xl w-full max-w-sm mx-4 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Assign to Site</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">Site</label>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading sites…</p>
          ) : (
            <Select value={selectedSite} onValueChange={setSelectedSite}>
              <SelectTrigger><SelectValue placeholder="None (unassigned)" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">None (unassigned)</SelectItem>
                {sites.map(s => (
                  <SelectItem key={s.id} value={String(s.id)}>
                    {s.nickname} — {s.organization_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        <div className="flex gap-2 pt-2">
          <Button onClick={save} disabled={saving || loading}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
        </div>
      </div>
    </div>
  )
}
