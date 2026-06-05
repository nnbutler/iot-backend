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

  const fetchLogs = useCallback(async (levels, cursor = null) => {
    const params = new URLSearchParams({ limit: 50 })
    levels.forEach(l => params.append('level', l))
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

    fetchLogs(levels)
      .then(data => {
        if (cancelled) return
        setLogs(data.logs)
        setHasMore(data.has_more)
        setNextCursor(data.next_before_timestamp)
      })
      .catch(() => { if (!cancelled) setError('Failed to load logs') })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [activeLevels, fetchLogs])

  const loadMore = async () => {
    const levels = [...activeLevels]
    setLoadingMore(true)
    try {
      const data = await fetchLogs(levels, nextCursor)
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
          <CardTitle className="text-sm">Device Logs</CardTitle>
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
                  <TableHead className="w-44 font-mono text-xs">Timestamp</TableHead>
                  <TableHead className="w-24 text-xs">Level</TableHead>
                  <TableHead className="text-xs">Message</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map(log => (
                  <TableRow key={log.timestamp}>
                    <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </TableCell>
                    <TableCell><LevelBadge level={log.level} /></TableCell>
                    <TableCell className="text-sm break-all">{log.message}</TableCell>
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
