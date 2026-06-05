import { useState } from 'react'
import client from '../api/client'

const COMMANDS = [
  {
    command_type: 'restart_plc',
    label: 'Restart PLC',
    description: 'Restarts the PLC logic. Use when the PLC is unresponsive or stuck.',
    danger: false,
  },
  {
    command_type: 'reset_state_machine',
    label: 'Reset State Machine',
    description: 'Clears a stuck state machine without a full reboot. Fastest fix for logic hangs.',
    danger: false,
  },
  {
    command_type: 'reboot_device',
    label: 'Reboot Device',
    description: 'Full device reboot. Clears all running processes. Use as a last resort.',
    danger: true,
  },
  {
    command_type: 'clear_error_log',
    label: 'Clear Error Log',
    description: 'Clears the local error log on the device. Does not fix any underlying issue.',
    danger: false,
  },
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
      const response = await client.post(`/devices/${device_id}/commands`, {
        command_type: selected.command_type,
      })
      setSent(response.data)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to send command.')
      setSubmitting(false)
    }
  }

  return (
    <div
      data-testid="send-command-modal"
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-lg w-full max-w-md">
        <div className="p-6">
          {sent ? (
            <>
              <div className="text-center py-4">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold mb-1">Command Sent</h2>
                <p className="text-sm text-gray-500 mb-1">
                  <span className="font-medium">{sent.label}</span> was sent to{' '}
                  <span className="font-mono">{device_id}</span>
                </p>
                <p className="text-xs text-gray-400">The device will execute it on its next poll cycle.</p>
              </div>
              <div className="flex justify-center mt-4">
                <button
                  onClick={onSuccess}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm"
                >
                  Done
                </button>
              </div>
            </>
          ) : (
            <>
              <h2 className="text-lg font-semibold mb-1">Send Command</h2>
              <p className="text-sm text-gray-500 mb-5">
                Device: <span className="font-mono">{device_id}</span>
              </p>

              <div className="space-y-2 mb-5">
                {COMMANDS.map((cmd) => (
                  <label
                    key={cmd.command_type}
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      selected?.command_type === cmd.command_type
                        ? cmd.danger
                          ? 'border-red-500 bg-red-50'
                          : 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="command"
                      className="mt-0.5 shrink-0"
                      checked={selected?.command_type === cmd.command_type}
                      onChange={() => setSelected(cmd)}
                    />
                    <span className="text-sm">
                      <span className={`font-medium ${cmd.danger ? 'text-red-700' : 'text-gray-900'}`}>
                        {cmd.label}
                        {cmd.danger && <span className="ml-1 text-xs font-normal text-red-500">(disruptive)</span>}
                      </span>
                      <br />
                      <span className="text-gray-500">{cmd.description}</span>
                    </span>
                  </label>
                ))}
              </div>

              {error && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg mb-4">{error}</p>
              )}

              <div className="flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!selected || submitting}
                  className={`px-4 py-2 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors ${
                    selected?.danger
                      ? 'bg-red-600 hover:bg-red-700'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {submitting ? 'Sending…' : 'Send Command'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
