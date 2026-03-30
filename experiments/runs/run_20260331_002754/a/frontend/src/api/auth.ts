import { apiClient } from './client'

// Types
export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  first_name?: string
  last_name?: string
  username?: string
}

export interface UserProfile {
  id: number
  email: string
  first_name: string | null
  last_name: string | null
  username: string | null
  is_active: boolean
  email_verified: boolean
  created_at: string
}

// Auth API functions
export const authAPI = {
  // Login
  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    const formData = new FormData()
    formData.append('username', credentials.email)
    formData.append('password', credentials.password)
    
    const response = await apiClient.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  // Register
  async register(data: RegisterData): Promise<{ id: number; email: string; message: string }> {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  },

  // Refresh token
  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    const response = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  // Logout
  async logout(accessToken: string): Promise<void> {
    await apiClient.post('/auth/logout', null, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })
  },

  // Get current user profile
  async getCurrentUser(): Promise<UserProfile> {
    const response = await apiClient.get('/auth/me')
    return response.data
  },
}