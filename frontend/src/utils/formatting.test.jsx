import { render, screen } from '@testing-library/react'
import { formatDate, formatStatus, formatSeverity } from './formatting'

describe('formatDate', () => {
  it('returns N/A for null', () => {
    expect(formatDate(null)).toBe('N/A')
  })

  it('returns N/A for undefined', () => {
    expect(formatDate(undefined)).toBe('N/A')
  })

  it('formats a valid ISO date string', () => {
    const result = formatDate('2024-01-15T10:30:00.000Z')
    expect(result).toBeTruthy()
    expect(result).not.toBe('N/A')
  })
})

describe('formatStatus', () => {
  it('renders Online badge when online is true', () => {
    render(formatStatus(true))
    expect(screen.getByText('Online')).toBeInTheDocument()
  })

  it('renders Offline badge when online is false', () => {
    render(formatStatus(false))
    expect(screen.getByText('Offline')).toBeInTheDocument()
  })
})

describe('formatSeverity', () => {
  it.each(['critical', 'high', 'medium', 'low'])('renders %s severity', (level) => {
    render(formatSeverity(level))
    expect(screen.getByText(level)).toBeInTheDocument()
  })

  it('renders "unknown" for null severity', () => {
    render(formatSeverity(null))
    expect(screen.getByText('unknown')).toBeInTheDocument()
  })
})
