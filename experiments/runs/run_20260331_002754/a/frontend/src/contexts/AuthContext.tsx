import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI, AuthTokens, LoginCredentials, RegisterData, UserProfile } from '../api/auth'
import { apiClient } from '../api/client'

interface AuthContextType {
  user: UserProfile | null
  tokens: AuthTokens | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<boolean>
  updateProfile: (user: UserProfile) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [tokens, setTokens] = useState<AuthTokens | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

  // Load stored auth state on mount
  useEffect(() => {
    const loadAuthState = async () => {
      try {
        const storedTokens = localStorage.getItem('auth_tokens')
        if (storedTokens) {
          const parsedTokens = JSON.parse(storedTokens) as AuthTokens
          setTokens(parsedTokens)
          
          // Set token in axios headers
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${parsedTokens.access_token}`
          
          // Fetch user profile
          const profile = await authAPI.getCurrentUser()
          setUser(profile)
        }
      } catch (error) {
        console.error('Failed to load auth state:', error)
        localStorage.removeItem('auth_tokens')
      } finally {
        setIsLoading(false)
      }
    }

    loadAuthState()
  }, [])

  // Setup axios response interceptor for token refresh
  useEffect(() => {
    const interceptor = apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true
          
          try {
            const success = await refreshToken()
            if (success) {
              // Retry original request with new token
              return apiClient(originalRequest)
            }
          } catch (refreshError) {
            // Refresh failed - logout user
            await logout()
            navigate('/login')
          }
        }
        return Promise.reject(error)
      }
    )

    return () => {
      apiClient.interceptors.response.eject(interceptor)
    }
  }, [navigate])

  const storeTokens = (newTokens: AuthTokens) => {
    setTokens(newTokens)
    localStorage.setItem('auth_tokens', JSON.stringify(newTokens))
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${newTokens.access_token}`
  }

  const clearAuth = () => {
    setUser(null)
    setTokens(null)
    localStorage.removeItem('auth_tokens')
    delete apiClient.defaults.headers.common['Authorization']
  }

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true)
    try {
      const response = await authAPI.login(credentials)
      storeTokens(response)
      
      const profile = await authAPI.getCurrentUser()
      setUser(profile)
      
      navigate('/dashboard')
    } catch (error) {
      clearAuth()
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (data: RegisterData) => {
    setIsLoading(true)
    try {
      await authAPI.register(data)
      // After registration, auto-login
      await login({ email: data.email, password: data.password })
    } catch (error) {
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    setIsLoading(true)
    try {
      if (tokens) {
        await authAPI.logout(tokens.access_token)
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearAuth()
      navigate('/login')
      setIsLoading(false)
    }
  }

  const refreshToken = async (): Promise<boolean> => {
    if (!tokens?.refresh_token) return false
    
    try {
      const newTokens = await authAPI.refreshToken(tokens.refresh_token)
      storeTokens(newTokens)
      return true
    } catch (error) {
      clearAuth()
      return false
    }
  }

  const updateProfile = (updatedUser: UserProfile) => {
    setUser(updatedUser)
  }

  const value = {
    user,
    tokens,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    refreshToken,
    updateProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}