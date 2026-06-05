import { useState, useEffect, useCallback } from 'react'
import client from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'

const LEVELS = ['ERROR', 'CRITICAL', 'WARNING', 'INFO', 'DEBUG']

const LEVEL_VARIANT = {
  ERROR:    'destructive',
  CRITICAL: 'destructive',
  WARNING:  'warning',
  INFO:     'secondary',
  DEBUG:    'outline',
}

function LevelBadge({ level }) {
  return <Badge variant={LEVEL_VARIANT[level] || 'outline'}>{level}</Badge>
}

export default function DeviceLogs({ device_id }) {
  const [logs, setLogs] = useState([])
  const [activeLevels, setActiveLevels] = useState(new Set(LEVELS))
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [nextCursor, setNextCursor] = useState(null)
  const [error, setError] = useState(null)

  const toggleLevel = (level) => {
    setActiveLevels(prev => {
      const next = new Set(prev)
      next.has(level) ? next.delete(level) : next.add(level)
      return next
    })
  }

  const fetchLogs = useCallback(async (levels, startTime, endTime, cursor = null) => {
    const params = new URLSearchParams({ limit: 50 })
    levels.forEach(l => params.append('level', l))
    if (startTime) params.append('start_timestamp', new Date(startTime).toISOString())
    if (endTime) params.append('end_timestamp', new Date(endTime).toISOString())
    if (cursor) params.append('before_timestamp', cursor)
    const resp = await client.get(`/devices/${device_id}/logs?${params}`)
    return resp.data
  }, [device_id])

  useEffect(() => {
    const levels = [...activeLevels]
    let cancelled = false
    setLoading(true)
    setError(null)
    setLogs([])
    setNextCursor(null)

    fetchLogs(levels, startTime, endTime)
      .then(data => {
        if (cancelled) return
        setLogs(data.logs)
        setHasMore(data.has_more)
        setNextCursor(data.next_before_timestamp)
      })
      .catch(() => { if (!cancelled) setError('Failed to load logs') })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [activeLevels, startTime, endTime, fetchLogs])

  const loadMore = async () => {
    const levels = [...activeLevels]
    setLoadingMore(true)
    try {
      const data = await fetchLogs(levels, startTime, endTime, nextCursor)
      setLogs(prev => [...prev, ...data.logs])
      setHasMore(data.has_more)
      setNextCursor(data.next_before_timestamp)
    } catch {
      setError('Failed to load more logs')
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <CardTitle className="text-sm">Device Logs</CardTitle>
            <input
              type="datetime-local"
              value={startTime}
              onChange={e => setStartTime(e.target.value)}
              className="h-7 text-xs px-2 rounded-md border border-input bg-background text-foreground"
            />
            <span className="text-xs text-muted-foreground">to</span>
            <input
              type="datetime-local"
              value={endTime}
              onChange={e => setEndTime(e.target.value)}
              className="h-7 text-xs px-2 rounded-md border border-input bg-background text-foreground"
            />
            {(startTime || endTime) && (
              <Button size="sm" variant="ghost" className="h-7 text-xs px-2" onClick={() => { setStartTime(''); setEndTime('') }}>
                Clear
              </Button>
            )}
          </div>
          <div className="flex gap-1 flex-wrap items-center">
            <Button size="sm" variant="ghost" onClick={() => setActiveLevels(new Set(LEVELS))} className="h-7 text-xs px-2.5">All</Button>
            <Button size="sm" variant="ghost" onClick={() => setActiveLevels(new Set())} className="h-7 text-xs px-2.5">None</Button>
            <div className="w-px h-4 bg-border mx-1" />
            {LEVELS.map(level => (
              <Button
                key={level}
                size="sm"
                variant={activeLevels.has(level) ? 'default' : 'outline'}
                onClick={() => toggleLevel(level)}
                className="h-7 text-xs px-2.5"
              >
                {level}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && <p className="text-destructive text-sm mb-3">{error}</p>}

        {loading ? (
          <p className="text-muted-foreground text-sm">Loading logs...</p>
        ) : logs.length === 0 ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            {activeLevels.size === LEVELS.length ? 'No logs yet' : 'No logs for selected levels'}
          </p>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-40 font-mono text-xs h-7 px-3">Timestamp</TableHead>
                  <TableHead className="w-20 text-xs h-7 px-3">Level</TableHead>
                  <TableHead className="text-xs h-7 px-3">Message</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map(log => (
                  <TableRow key={log.timestamp}>
                    <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap py-1 px-3">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </TableCell>
                    <TableCell className="py-1 px-3"><LevelBadge level={log.level} /></TableCell>
                    <TableCell className="text-xs break-all py-1 px-3">{log.message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {hasMore && (
              <div className="mt-4 text-center">
                <Button variant="outline" size="sm" onClick={loadMore} disabled={loadingMore}>
                  {loadingMore ? 'Loading…' : 'Load more'}
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
