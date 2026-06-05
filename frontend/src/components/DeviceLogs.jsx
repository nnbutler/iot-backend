import { useState, useEffect, useCallback } from 'react'
import client from '../api/client'

const LEVELS = ['ALL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'CRITICAL']

const LEVEL_STYLES = {
  ERROR:    'bg-red-100 text-red-800',
  CRITICAL: 'bg-red-200 text-red-900 font-bold',
  WARNING:  'bg-yellow-100 text-yellow-800',
  INFO:     'bg-blue-100 text-blue-800',
  DEBUG:    'bg-gray-100 text-gray-600',
}

function LevelBadge({ level }) {
  const style = LEVEL_STYLES[level] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-medium ${style}`}>
      {level}
    </span>
  )
}

export default function DeviceLogs({ device_id }) {
  const [logs, setLogs] = useState([])
  const [levelFilter, setLevelFilter] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [nextCursor, setNextCursor] = useState(null)
  const [error, setError] = useState(null)

  const fetchLogs = useCallback(async (level, cursor = null) => {
    try {
      const params = new URLSearchParams({ limit: 50 })
      if (level !== 'ALL') params.append('level', level)
      if (cursor) params.append('before_timestamp', cursor)

      const resp = await client.get(`/devices/${device_id}/logs?${params}`)
      return resp.data
    } catch (err) {
      throw new Error('Failed to load logs')
    }
  }, [device_id])

  // Reload when filter changes
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setLogs([])
    setNextCursor(null)

    fetchLogs(levelFilter)
      .then(data => {
        if (cancelled) return
        setLogs(data.logs)
        setHasMore(data.has_more)
        setNextCursor(data.next_before_timestamp)
      })
      .catch(err => {
        if (cancelled) return
        setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [levelFilter, fetchLogs])

  const loadMore = async () => {
    setLoadingMore(true)
    try {
      const data = await fetchLogs(levelFilter, nextCursor)
      setLogs(prev => [...prev, ...data.logs])
      setHasMore(data.has_more)
      setNextCursor(data.next_before_timestamp)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Device Logs</h2>

        {/* Severity filter buttons */}
        <div className="flex gap-1 flex-wrap justify-end">
          {LEVELS.map(level => (
            <button
              key={level}
              onClick={() => setLevelFilter(level)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                levelFilter === level
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="text-red-600 text-sm mb-3">{error}</p>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading logs...</p>
      ) : logs.length === 0 ? (
        <p className="text-gray-400 text-sm py-4 text-center">
          {levelFilter === 'ALL' ? 'No logs yet' : `No ${levelFilter} logs`}
        </p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm font-mono">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                  <th className="pb-2 pr-4 font-medium whitespace-nowrap">Timestamp</th>
                  <th className="pb-2 pr-4 font-medium">Level</th>
                  <th className="pb-2 font-medium">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {logs.map(log => (
                  <tr key={log.timestamp} className="hover:bg-gray-50">
                    <td className="py-2 pr-4 text-gray-400 text-xs whitespace-nowrap">
                      {log.timestamp
                        ? new Date(log.timestamp).toLocaleString()
                        : '—'}
                    </td>
                    <td className="py-2 pr-4">
                      <LevelBadge level={log.level} />
                    </td>
                    <td className="py-2 text-gray-800 break-all">{log.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {hasMore && (
            <div className="mt-4 text-center">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50"
              >
                {loadingMore ? 'Loading...' : 'Load more'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
