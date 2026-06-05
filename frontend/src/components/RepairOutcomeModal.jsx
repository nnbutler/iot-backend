import { useState, useEffect } from 'react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

export default function RepairOutcomeModal({ device_id, error_code, onClose, onSuccess }) {
  const { username } = useAuth()
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [fetchError, setFetchError] = useState(null)
  const [submitError, setSubmitError] = useState(null)

  const [selectedActionId, setSelectedActionId] = useState(null)
  const [worked, setWorked] = useState(null)
  const [notes, setNotes] = useState('')
  const [timeSpent, setTimeSpent] = useState('')

  useEffect(() => {
    if (!error_code) { setLoading(false); return }
    client.get(`/errors/${error_code}`)
      .then(r => setActions(r.data.repair_actions ?? []))
      .catch(() => setFetchError('Could not load repair actions.'))
      .finally(() => setLoading(false))
  }, [error_code])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (worked === null) { setSubmitError('Select whether the repair worked.'); return }
    setSubmitting(true)
    setSubmitError(null)
    try {
      await client.post(`/errors/${error_code}/outcomes`, {
        device_id,
        repair_action_id: selectedActionId ?? null,
        worked,
        notes: notes.trim() || null,
        time_spent_minutes: timeSpent ? parseInt(timeSpent, 10) : null,
      })
      onSuccess()
    } catch (err) {
      setSubmitError(err.response?.data?.detail ?? 'Failed to record outcome.')
      setSubmitting(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent data-testid="repair-outcome-modal" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Record Repair Outcome</DialogTitle>
          <DialogDescription className="space-x-2">
            <code className="text-xs text-foreground">{device_id}</code>
            {error_code && <><span>—</span><code className="text-xs text-foreground">{error_code}</code></>}
            {username && <><span>—</span><span>by <strong>{username}</strong></span></>}
          </DialogDescription>
        </DialogHeader>

        <DialogBody>
          {loading && <p className="text-sm text-muted-foreground">Loading repair actions…</p>}
          {fetchError && <p className="text-sm text-destructive">{fetchError}</p>}

          {!loading && (
            <form id="repair-form" onSubmit={handleSubmit} className="space-y-5">
              {actions.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Which repair action did you try?</p>
                  {actions.map((a) => (
                    <label
                      key={a.id}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                        selectedActionId === a.id ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50'
                      )}
                    >
                      <input
                        type="radio"
                        name="action"
                        className="mt-0.5 shrink-0"
                        checked={selectedActionId === a.id}
                        onChange={() => setSelectedActionId(a.id)}
                      />
                      <span className="text-sm">
                        <span className="font-medium">Step {a.step}:</span> {a.action}
                        {a.estimated_time && <span className="text-muted-foreground"> (~{a.estimated_time} min)</span>}
                      </span>
                    </label>
                  ))}
                  <label
                    className={cn(
                      'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                      selectedActionId === null ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50'
                    )}
                  >
                    <input
                      type="radio"
                      name="action"
                      className="mt-0.5 shrink-0"
                      checked={selectedActionId === null}
                      onChange={() => setSelectedActionId(null)}
                    />
                    <span className="text-sm text-muted-foreground">Other / not listed</span>
                  </label>
                </div>
              )}

              <div className="space-y-2">
                <p className="text-sm font-medium">Did it work? <span className="text-destructive">*</span></p>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    className="flex-1"
                    variant={worked === true ? 'default' : 'outline'}
                    onClick={() => setWorked(true)}
                  >
                    Yes, it worked
                  </Button>
                  <Button
                    type="button"
                    className="flex-1"
                    variant={worked === false ? 'destructive' : 'outline'}
                    onClick={() => setWorked(false)}
                  >
                    No, it didn't
                  </Button>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Time spent (minutes)</label>
                <Input
                  type="number"
                  min="1"
                  max="999"
                  value={timeSpent}
                  onChange={(e) => setTimeSpent(e.target.value)}
                  placeholder="Optional"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Notes</label>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="What did you observe? What exactly fixed it?"
                  rows={3}
                />
              </div>

              {submitError && (
                <p className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">{submitError}</p>
              )}
            </form>
          )}
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" form="repair-form" disabled={submitting || worked === null}>
            {submitting ? 'Saving…' : 'Record Outcome'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
