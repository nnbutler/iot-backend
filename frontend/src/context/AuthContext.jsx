import { createContext, useContext, useState } from 'react'
import client from '../api/client'

const AuthContext = createContext(null)

function decodeUsername(token) {
  try {
    return JSON.parse(atob(token.split('.')[1])).sub ?? null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('jwt_token'))
  const username = token ? decodeUsername(token) : null

  const login = async (username, password) => {
    const response = await client.post('/auth/login', { username, password })
    const jwt = response.data.access_token
    localStorage.setItem('jwt_token', jwt)
    setToken(jwt)
  }

  const logout = () => {
    localStorage.removeItem('jwt_token')
    setToken(null)
  }

  return (
    <AuthContext.Provider value={{ token, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
