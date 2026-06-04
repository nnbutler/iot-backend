export function formatDate(dateString) {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleString()
  } catch (e) {
    return dateString
  }
}

export function formatStatus(online) {
  return online ? (
    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
      Online
    </span>
  ) : (
    <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">
      Offline
    </span>
  )
}

export function formatSeverity(severity) {
  const colors = {
    critical: 'text-red-700 bg-red-100',
    high: 'text-orange-700 bg-orange-100',
    medium: 'text-yellow-700 bg-yellow-100',
    low: 'text-blue-700 bg-blue-100',
  }
  const color = colors[severity] || colors.low
  return (
    <span className={`px-2 py-1 rounded text-sm ${color}`}>
      {severity || 'unknown'}
    </span>
  )
}
