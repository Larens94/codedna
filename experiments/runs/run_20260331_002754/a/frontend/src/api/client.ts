import axios from 'axios'

// Create axios instance with default config
export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // For HTTP-only cookies if using them
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    // Try to get token from localStorage
    const storedTokens = localStorage.getItem('auth_tokens')
    if (storedTokens) {
      try {
        const tokens = JSON.parse(storedTokens)
        if (tokens.access_token) {
          config.headers.Authorization = `Bearer ${tokens.access_token}`
        }
      } catch (error) {
        console.error('Failed to parse stored tokens:', error)
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling (global)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // Unauthorized - token expired or invalid
          // Handled by AuthContext interceptor
          break
        case 403:
          // Forbidden - insufficient permissions
          console.error('Access forbidden:', error.response.data)
          break
        case 404:
          // Not found
          console.error('Resource not found:', error.response.data)
          break
        case 422:
          // Validation error
          console.error('Validation failed:', error.response.data)
          break
        case 429:
          // Rate limited
          console.error('Rate limited:', error.response.data)
          break
        case 500:
          // Server error
          console.error('Server error:', error.response.data)
          break
        default:
          console.error('API error:', error.response.data)
      }
    } else if (error.request) {
      // Network error
      console.error('Network error:', error.message)
    } else {
      // Request setup error
      console.error('Request error:', error.message)
    }
    
    return Promise.reject(error)
  }
)