import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'

const MAX_MESSAGES = 200

const TOPIC_COLOR = (topic) => {
  if (topic.includes('/heartbeat'))    return 'bg-green-100 text-green-800'
  if (topic.includes('/logs'))         return 'bg-blue-100 text-blue-800'
  if (topic.includes('/command-result')) return 'bg-purple-100 text-purple-800'
  if (topic.includes('/commands'))     return 'bg-orange-100 text-orange-800'
  return 'bg-gray-100 text-gray-700'
}

function tryPretty(str) {
  try {
    return JSON.stringify(JSON.parse(str), null, 2)
  } catch {
    return str
  }
}

export default function MqttDebug() {
  const { token } = useAuth()
  const [messages, setMessages] = useState([])
  const [paused, setPaused] = useState(false)
  const [status, setStatus] = useState('connecting')
  const [filter, setFilter] = useState('')
  const [expanded, setExpanded] = useState({})
  const bottomRef = useRef(null)
  const wsRef = useRef(null)
  const pausedRef = useRef(false)

  pausedRef.current = paused

  const connect = useCallback(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const ws = new WebSocket(`${proto}://${host}/api/ws/mqtt-debug?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => setStatus('connected')
    ws.onclose = () => {
      setStatus('disconnected')
      // Reconnect after 3s unless unmounted
      setTimeout(() => {
        if (wsRef.current === ws) connect()
      }, 3000)
    }
    ws.onerror = () => setStatus('error')
    ws.onmessage = (e) => {
      if (pausedRef.current) return
      const msg = JSON.parse(e.data)
      setMessages(prev => {
        const next = [...prev, { ...msg, id: Date.now() + Math.random() }]
        return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next
      })
    }
  }, [token])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null  // prevent reconnect on unmount
        wsRef.current.close()
      }
    }
  }, [connect])

  // Auto-scroll when not paused
  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, paused])

  const filtered = filter
    ? messages.filter(m => m.topic.includes(filter) || m.payload.includes(filter))
    : messages

  const toggleExpand = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }))

  const statusDot = {
    connecting:   'bg-yellow-400',
    connected:    'bg-green-400',
    disconnected: 'bg-red-400',
    error:        'bg-red-600',
  }[status]

  return (
    <div className="bg-white rounded-lg shadow flex flex-col" style={{ height: '70vh' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 flex-shrink-0">
        <span className="flex items-center gap-1.5 text-sm text-gray-600">
          <span className={`w-2 h-2 rounded-full ${statusDot}`} />
          {status}
        </span>

        <input
          type="text"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="Filter by topic or payload…"
          className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <button
          onClick={() => setPaused(p => !p)}
          className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
            paused
              ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          {paused ? 'Resume' : 'Pause'}
        </button>

        <button
          onClick={() => setMessages([])}
          className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          Clear
        </button>

        <span className="text-xs text-gray-400 whitespace-nowrap">
          {filtered.length} / {MAX_MESSAGES} max
        </span>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto font-mono text-xs p-2 space-y-1 bg-gray-50">
        {filtered.length === 0 && (
          <div className="text-center text-gray-400 mt-16 text-sm font-sans">
            {status === 'connected' ? 'Waiting for MQTT messages…' : 'Not connected'}
          </div>
        )}

        {filtered.map(msg => {
          const isExpanded = expanded[msg.id]
          const pretty = tryPretty(msg.payload)
          const multiline = pretty.includes('\n')

          return (
            <div
              key={msg.id}
              className="flex gap-2 items-start bg-white rounded border border-gray-100 px-2 py-1.5 hover:border-gray-300 transition-colors"
            >
              {/* Timestamp */}
              <span className="text-gray-400 whitespace-nowrap pt-0.5">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </span>

              {/* Topic badge */}
              <span className={`px-1.5 py-0.5 rounded text-xs font-medium whitespace-nowrap ${TOPIC_COLOR(msg.topic)}`}>
                {msg.topic}
              </span>

              {/* Payload */}
              <div className="flex-1 min-w-0">
                {multiline ? (
                  <>
                    <button
                      onClick={() => toggleExpand(msg.id)}
                      className="text-blue-500 hover:text-blue-700 text-xs"
                    >
                      {isExpanded ? '▾ collapse' : '▸ expand'}
                    </button>
                    {isExpanded && (
                      <pre className="mt-1 text-gray-800 whitespace-pre-wrap break-all">{pretty}</pre>
                    )}
                    {!isExpanded && (
                      <span className="text-gray-500 truncate block">{msg.payload.slice(0, 120)}</span>
                    )}
                  </>
                ) : (
                  <span className="text-gray-800 break-all">{pretty}</span>
                )}
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
