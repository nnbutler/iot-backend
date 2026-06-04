import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import DeviceDetail from './DeviceDetail'
import client from '../api/client'

jest.mock('../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}))

const mockDevice = {
  device_id: 'plc-001',
  online: true,
  last_seen: '2024-01-15T10:00:00.000Z',
  device_type: 'plc',
  firmware_version: '1.2.3',
  location: 'Phoenix, AZ',
  customer_name: 'Acme Inc',
  last_error: {
    code: 'sensor_disconnected',
    message: 'Sensor X not responding',
    occurred_at: '2024-01-15T09:30:00.000Z',
  },
  troubleshooting: {
    display_name: 'Sensor Disconnected',
    success_rate: 0.88,
    repair_actions: [
      {
        id: 1,
        step: 1,
        action: 'Check cable connection',
        description: 'Verify the cable is plugged in at both ends',
        estimated_time: 5,
        success_rate: 0.88,
      },
    ],
  },
}

const renderWithRouter = (deviceId = 'plc-001') =>
  render(
    <MemoryRouter initialEntries={[`/devices/${deviceId}`]}>
      <Routes>
        <Route path="/devices/:device_id" element={<DeviceDetail />} />
      </Routes>
    </MemoryRouter>
  )

describe('DeviceDetail', () => {
  afterEach(() => jest.clearAllMocks())

  it('shows loading state initially', () => {
    client.get.mockImplementation(() => new Promise(() => {}))
    renderWithRouter()
    expect(screen.getByText('Loading device...')).toBeInTheDocument()
  })

  it('renders device info after API resolves', async () => {
    client.get.mockResolvedValue({ data: mockDevice })
    renderWithRouter()
    await waitFor(() => expect(screen.getByText('plc-001')).toBeInTheDocument())
    expect(screen.getByText('Acme Inc')).toBeInTheDocument()
    expect(screen.getByText('Phoenix, AZ')).toBeInTheDocument()
    expect(screen.getByText('1.2.3')).toBeInTheDocument()
  })

  it('falls back to built-in mock data on API error', async () => {
    client.get.mockRejectedValue(new Error('Network error'))
    renderWithRouter()
    await waitFor(() => expect(screen.getByText('Acme Inc')).toBeInTheDocument())
  })

  it('shows last error code and message', async () => {
    client.get.mockResolvedValue({ data: mockDevice })
    renderWithRouter()
    await waitFor(() => expect(screen.getByText('sensor_disconnected')).toBeInTheDocument())
    expect(screen.getByText('Sensor X not responding')).toBeInTheDocument()
  })

  it('shows "No recent errors" when last_error is null', async () => {
    client.get.mockResolvedValue({ data: { ...mockDevice, last_error: null } })
    renderWithRouter()
    await waitFor(() => expect(screen.getByText('No recent errors')).toBeInTheDocument())
  })

  it('shows repair steps section with troubleshooting data', async () => {
    client.get.mockResolvedValue({ data: mockDevice })
    renderWithRouter()
    await waitFor(() =>
      expect(screen.getByText('Repair Steps for: Sensor Disconnected')).toBeInTheDocument()
    )
    expect(screen.getByText(/Check cable connection/)).toBeInTheDocument()
    expect(screen.getByText('Verify the cable is plugged in at both ends')).toBeInTheDocument()
  })

  it('opens send command modal when Send Command is clicked', async () => {
    client.get.mockResolvedValue({ data: mockDevice })
    renderWithRouter()
    await waitFor(() => screen.getByText('Send Command'))
    fireEvent.click(screen.getByText('Send Command'))
    expect(screen.getByTestId('send-command-modal')).toBeInTheDocument()
  })

  it('opens repair modal when Record Repair is clicked', async () => {
    client.get.mockResolvedValue({ data: mockDevice })
    renderWithRouter()
    await waitFor(() => screen.getByText('Record Repair'))
    fireEvent.click(screen.getByText('Record Repair'))
    expect(screen.getByTestId('repair-outcome-modal')).toBeInTheDocument()
  })
})
