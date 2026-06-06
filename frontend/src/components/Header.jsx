import { Link, useLocation } from 'react-router-dom'

function NavLink({ to, children }) {
  const { pathname } = useLocation()
  const active = pathname === to || pathname.startsWith(to + '/')
  return (
    <Link
      to={to}
      className={`text-sm font-medium transition-colors ${
        active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
      }`}
    >
      {children}
    </Link>
  )
}

export default function Header({ onLogout }) {
  return (
    <header className="bg-background border-b border-border">
      <nav className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
        <Link to="/" className="text-base font-bold text-foreground mr-2">
          Device Manager
        </Link>
        <NavLink to="/devices">Devices</NavLink>
        <NavLink to="/sites">Sites</NavLink>
        <NavLink to="/organizations">Organizations</NavLink>
        <div className="ml-auto">
          <button
            onClick={onLogout}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Sign out
          </button>
        </div>
      </nav>
    </header>
  )
}
