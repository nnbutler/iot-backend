import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <nav className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link to="/" className="text-2xl font-bold text-blue-600">
          Device Manager
        </Link>
        <div className="text-sm text-gray-600">
          Phase 1 MVP
        </div>
      </nav>
    </header>
  )
}
