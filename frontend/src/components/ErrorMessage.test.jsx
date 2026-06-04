import { render, screen, fireEvent } from '@testing-library/react'
import ErrorMessage from './ErrorMessage'

describe('ErrorMessage', () => {
  it('renders nothing when message is falsy', () => {
    const { container } = render(<ErrorMessage />)
    expect(container.firstChild).toBeNull()
  })

  it('renders the message text', () => {
    render(<ErrorMessage message="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('shows dismiss button when onClose is provided', () => {
    render(<ErrorMessage message="Error" onClose={() => {}} />)
    expect(screen.getByText('Dismiss')).toBeInTheDocument()
  })

  it('does not show dismiss button without onClose', () => {
    render(<ErrorMessage message="Error" />)
    expect(screen.queryByText('Dismiss')).toBeNull()
  })

  it('calls onClose when dismiss is clicked', () => {
    const onClose = jest.fn()
    render(<ErrorMessage message="Error" onClose={onClose} />)
    fireEvent.click(screen.getByText('Dismiss'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
