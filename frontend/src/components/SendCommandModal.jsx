import { useState } from 'react'
import client from '../api/client'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CheckCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

const COMMANDS = [
  { command_type: 'restart_plc',         label: 'Restart PLC',          description: 'Restarts the PLC logic. Use when the PLC is unresponsive or stuck.',                    danger: false },
  { command_type: 'reset_state_machine', label: 'Reset State Machine',   description: 'Clears a stuck state machine without a full reboot. Fastest fix for logic hangs.',      danger: false },
  { command_type: 'reboot_device',       label: 'Reboot Device',         description: 'Full device reboot. Clears all running processes. Use as a last resort.',                danger: true  },
  { command_type: 'clear_error_log',     label: 'Clear Error Log',       description: 'Clears the local error log on the device. Does not fix any underlying issue.',           danger: false },
]

export default function SendCommandModal({ device_id, onClose, onSuccess }) {
  const [selected, setSelected] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(null)
  const [error, setError] = useState(null)

  const handleSend = async () => {
    if (!selected) return
    setSubmitting(true)
    setError(null)
    try {
      const response = await client.post(`/devices/${device_id}/commands`, { command_type: selected.command_type })
      setSent(response.data)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to send command.')
      setSubmitting(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent data-testid="send-command-modal">
        {sent ? (
          <div className="px-6 py-10 flex flex-col items-center text-center gap-3">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-emerald-600" />
            </div>
            <div>
              <p className="font-semibold">Command Sent</p>
              <p className="text-sm text-muted-foreground mt-1">
                <span className="font-medium text-foreground">{selected?.label}</span> was sent to{' '}
                <code className="text-xs">{device_id}</code>
              </p>
              <p className="text-xs text-muted-foreground mt-1">The device will execute it on its next poll cycle.</p>
            </div>
            <Button className="mt-2" onClick={onSuccess}>Done</Button>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Send Command</DialogTitle>
              <DialogDescription>
                Device: <code className="text-xs text-foreground">{device_id}</code>
              </DialogDescription>
            </DialogHeader>

            <DialogBody className="space-y-2">
              {COMMANDS.map((cmd) => {
                const isSelected = selected?.command_type === cmd.command_type
                return (
                  <label
                    key={cmd.command_type}
                    className={cn(
                      'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                      isSelected
                        ? cmd.danger ? 'border-destructive bg-destructive/5' : 'border-primary bg-primary/5'
                        : 'border-border hover:bg-muted/50'
                    )}
                  >
                    <input
                      type="radio"
                      name="command"
                      className="mt-0.5 shrink-0"
                      checked={isSelected}
                      onChange={() => setSelected(cmd)}
                    />
                    <span className="text-sm">
                      <span className={cn('font-medium', cmd.danger ? 'text-destructive' : 'text-foreground')}>
                        {cmd.label}
                        {cmd.danger && <Badge variant="destructive" className="ml-2 text-[10px] px-1.5 py-0">disruptive</Badge>}
                      </span>
                      <br />
                      <span className="text-muted-foreground">{cmd.description}</span>
                    </span>
                  </label>
                )
              })}

              {error && (
                <p className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">{error}</p>
              )}
            </DialogBody>

            <DialogFooter>
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button
                onClick={handleSend}
                disabled={!selected || submitting}
                variant={selected?.danger ? 'destructive' : 'default'}
              >
                {submitting ? 'Sending…' : 'Send Command'}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
