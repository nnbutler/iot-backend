import { createContext, useContext, useState } from 'react'
import client from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('jwt_token'))

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
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
