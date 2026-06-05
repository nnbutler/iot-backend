import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

// Request interceptor: Add JWT token if available
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('jwt_token') || import.meta.env.VITE_JWT_TOKEN
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: Handle errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      // Could redirect to login page here
    }
    return Promise.reject(error)
  }
)

export default client
