import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DeviceList from './DeviceList'
import client from '../api/client'

jest.mock('../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}))

const mockDevices = [
  {
    device_id: 'dev-001',
    customer_name: 'Test Corp',
    location: 'Test City',
    online: true,
    last_seen: '2024-01-15T10:00:00.000Z',
    last_error: null,
    uptime_percent: 99.5,
  },
  {
    device_id: 'dev-002',
    customer_name: 'Another Corp',
    location: 'Other City',
    online: false,
    last_seen: '2024-01-14T10:00:00.000Z',
    last_error: 'sensor_error',
    uptime_percent: 95.0,
  },
]

const renderWithRouter = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('DeviceList', () => {
  afterEach(() => jest.clearAllMocks())

  it('shows loading state initially', () => {
    client.get.mockImplementation(() => new Promise(() => {}))
    renderWithRouter(<DeviceList />)
    expect(screen.getByText('Loading devices...')).toBeInTheDocument()
  })

  it('renders devices returned by the API', async () => {
    client.get.mockResolvedValue({ data: { devices: mockDevices } })
    renderWithRouter(<DeviceList />)
    await waitFor(() => expect(screen.getByText('dev-001')).toBeInTheDocument())
    expect(screen.getByText('dev-002')).toBeInTheDocument()
    expect(screen.getByText('Test Corp')).toBeInTheDocument()
  })

  it('shows device count', async () => {
    client.get.mockResolvedValue({ data: { devices: mockDevices } })
    renderWithRouter(<DeviceList />)
    await waitFor(() => expect(screen.getByText('Showing 2 devices')).toBeInTheDocument())
  })

  it('falls back to built-in mock data on API error', async () => {
    client.get.mockRejectedValue(new Error('Network error'))
    renderWithRouter(<DeviceList />)
    await waitFor(() => expect(screen.getByText('plc-001')).toBeInTheDocument())
    expect(screen.getByText('plc-042')).toBeInTheDocument()
  })

  it('shows View link to each device detail page', async () => {
    client.get.mockResolvedValue({ data: { devices: mockDevices } })
    renderWithRouter(<DeviceList />)
    await waitFor(() => {
      const links = screen.getAllByText('View')
      expect(links).toHaveLength(2)
      expect(links[0].closest('a')).toHaveAttribute('href', '/devices/dev-001')
    })
  })

  it('shows empty state when no devices returned', async () => {
    client.get.mockResolvedValue({ data: { devices: [] } })
    renderWithRouter(<DeviceList />)
    await waitFor(() => expect(screen.getByText('No devices found')).toBeInTheDocument())
  })

  it('shows last_error code when present', async () => {
    client.get.mockResolvedValue({ data: { devices: mockDevices } })
    renderWithRouter(<DeviceList />)
    await waitFor(() => expect(screen.getByText('sensor_error')).toBeInTheDocument())
  })
})
