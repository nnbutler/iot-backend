import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Header from './Header'

const renderWithRouter = () =>
  render(
    <MemoryRouter>
      <Header />
    </MemoryRouter>
  )

describe('Header', () => {
  it('renders the app title', () => {
    renderWithRouter()
    expect(screen.getByText('Device Manager')).toBeInTheDocument()
  })

  it('renders the phase label', () => {
    renderWithRouter()
    expect(screen.getByText('Phase 1 MVP')).toBeInTheDocument()
  })

  it('title links to home', () => {
    renderWithRouter()
    expect(screen.getByText('Device Manager').closest('a')).toHaveAttribute('href', '/')
  })
})
