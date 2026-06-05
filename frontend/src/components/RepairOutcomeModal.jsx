import { useState, useEffect } from 'react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'

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
    <div
      data-testid="repair-outcome-modal"
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-lg w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-1">Record Repair Outcome</h2>
          <p className="text-sm text-gray-500 mb-5">
            Device: <span className="font-mono">{device_id}</span>
            {error_code && <> &mdash; Error: <span className="font-mono">{error_code}</span></>}
            {username && <> &mdash; by <span className="font-medium">{username}</span></>}
          </p>

          {loading && <p className="text-sm text-gray-500">Loading repair actions…</p>}
          {fetchError && <p className="text-sm text-red-600">{fetchError}</p>}

          {!loading && (
            <form onSubmit={handleSubmit} className="space-y-5">
              {actions.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Which repair action did you try?
                  </label>
                  <div className="space-y-2">
                    {actions.map((a) => (
                      <label
                        key={a.id}
                        className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                          selectedActionId === a.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:bg-gray-50'
                        }`}
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
                          {a.estimated_time && (
                            <span className="text-gray-400"> (~{a.estimated_time} min)</span>
                          )}
                        </span>
                      </label>
                    ))}
                    <label
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedActionId === null && worked !== null
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="action"
                        className="mt-0.5 shrink-0"
                        checked={selectedActionId === null}
                        onChange={() => setSelectedActionId(null)}
                      />
                      <span className="text-sm text-gray-600">Other / not listed</span>
                    </label>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Did it work? <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setWorked(true)}
                    className={`flex-1 py-2 rounded-lg border font-medium text-sm transition-colors ${
                      worked === true
                        ? 'bg-green-600 border-green-600 text-white'
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Yes, it worked
                  </button>
                  <button
                    type="button"
                    onClick={() => setWorked(false)}
                    className={`flex-1 py-2 rounded-lg border font-medium text-sm transition-colors ${
                      worked === false
                        ? 'bg-red-600 border-red-600 text-white'
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    No, it didn't
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Time spent (minutes)
                </label>
                <input
                  type="number"
                  min="1"
                  max="999"
                  value={timeSpent}
                  onChange={(e) => setTimeSpent(e.target.value)}
                  placeholder="Optional"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="What did you observe? What exactly fixed it?"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              {submitError && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{submitError}</p>
              )}

              <div className="flex gap-3 justify-end pt-1">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || worked === null}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Saving…' : 'Record Outcome'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
