/**
 * Authentication utilities for AgentHub
 * Handles JWT token management, login, registration, and token refresh
 */

const Auth = (function() {
    'use strict';
    
    const ACCESS_TOKEN_KEY = 'access_token';
    const REFRESH_TOKEN_KEY = 'refresh_token';
    const USER_KEY = 'user_data';
    
    // API base URL
    const API_BASE = '/api/v1';
    
    /**
     * Check if user is authenticated
     * @returns {boolean} True if access token exists
     */
    function isAuthenticated() {
        return !!getAccessToken();
    }
    
    /**
     * Get stored access token
     * @returns {string|null} Access token or null
     */
    function getAccessToken() {
        return localStorage.getItem(ACCESS_TOKEN_KEY) || getCookie('access_token');
    }
    
    /**
     * Get stored refresh token
     * @returns {string|null} Refresh token or null
     */
    function getRefreshToken() {
        return localStorage.getItem(REFRESH_TOKEN_KEY) || getCookie('refresh_token');
    }
    
    /**
     * Store authentication tokens
     * @param {string} accessToken 
     * @param {string} refreshToken 
     */
    function setTokens(accessToken, refreshToken) {
        localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        
        // Also set cookies for fallback
        setCookie('access_token', accessToken, 1); // 1 day
        setCookie('refresh_token', refreshToken, 30); // 30 days
    }
    
    /**
     * Clear authentication tokens
     */
    function clearTokens() {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        
        deleteCookie('access_token');
        deleteCookie('refresh_token');
    }
    
    /**
     * Store user data
     * @param {object} user 
     */
    function setUser(user) {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
    
    /**
     * Get stored user data
     * @returns {object|null} User object or null
     */
    function getUser() {
        const userStr = localStorage.getItem(USER_KEY);
        return userStr ? JSON.parse(userStr) : null;
    }
    
    /**
     * Clear user data
     */
    function clearUser() {
        localStorage.removeItem(USER_KEY);
    }
    
    /**
     * Login with email and password
     * @param {string} email 
     * @param {string} password 
     * @returns {Promise<object>} Response data
     */
    async function login(email, password) {
        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Login failed');
            }
            
            // Store tokens and user data
            if (data.access_token && data.refresh_token) {
                setTokens(data.access_token, data.refresh_token);
            }
            
            if (data.user) {
                setUser(data.user);
            }
            
            return data;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }
    
    /**
     * Register new user
     * @param {object} userData - Registration data
     * @returns {Promise<object>} Response data
     */
    async function register(userData) {
        try {
            const response = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Registration failed');
            }
            
            // Store tokens and user data
            if (data.access_token && data.refresh_token) {
                setTokens(data.access_token, data.refresh_token);
            }
            
            if (data.user) {
                setUser(data.user);
            }
            
            return data;
        } catch (error) {
            console.error('Registration error:', error);
            throw error;
        }
    }
    
    /**
     * Logout current user
     * @returns {Promise<object>} Response data
     */
    async function logout() {
        try {
            const response = await fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getAccessToken()}`
                }
            });
            
            // Clear local storage regardless of response
            clearTokens();
            clearUser();
            
            if (!response.ok) {
                console.warn('Logout API call failed, but local tokens cleared');
            }
            
            return { success: true };
        } catch (error) {
            console.error('Logout error:', error);
            clearTokens();
            clearUser();
            throw error;
        }
    }
    
    /**
     * Refresh access token using refresh token
     * @returns {Promise<string>} New access token
     */
    async function refreshToken() {
        const refreshToken = getRefreshToken();
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }
        
        try {
            const response = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${refreshToken}`
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Token refresh failed');
            }
            
            if (data.access_token) {
                localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
                setCookie('access_token', data.access_token, 1);
                return data.access_token;
            }
            
            throw new Error('No access token in response');
        } catch (error) {
            console.error('Token refresh error:', error);
            clearTokens();
            clearUser();
            window.location.href = '/login?session_expired=true';
            throw error;
        }
    }
    
    /**
     * Get current user from server (fresh data)
     * @returns {Promise<object>} User data
     */
    async function getCurrentUser() {
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${getAccessToken()}`
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                if (response.status === 401) {
                    // Try to refresh token and retry
                    const newToken = await refreshToken();
                    return getCurrentUser();
                }
                throw new Error(data.error || 'Failed to get user data');
            }
            
            if (data.user) {
                setUser(data.user);
            }
            
            return data.user;
        } catch (error) {
            console.error('Get current user error:', error);
            throw error;
        }
    }
    
    /**
     * Initialize authentication state
     * Checks token validity and refreshes if needed
     */
    async function init() {
        if (!isAuthenticated()) {
            return false;
        }
        
        // Check if token is expired or about to expire
        const token = getAccessToken();
        if (token && isTokenExpired(token)) {
            try {
                await refreshToken();
                console.log('Token refreshed on init');
            } catch (error) {
                console.log('Token refresh failed on init, clearing auth');
                clearTokens();
                clearUser();
                return false;
            }
        }
        
        // Update user data if needed
        if (!getUser()) {
            try {
                await getCurrentUser();
            } catch (error) {
                console.warn('Could not fetch user data on init:', error);
            }
        }
        
        return true;
    }
    
    /**
     * Check if JWT token is expired or about to expire
     * @param {string} token - JWT token
     * @param {number} thresholdSeconds - Seconds before expiration to consider expired
     * @returns {boolean} True if expired or about to expire
     */
    function isTokenExpired(token, thresholdSeconds = 300) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const exp = payload.exp;
            const now = Math.floor(Date.now() / 1000);
            return exp - now < thresholdSeconds;
        } catch (error) {
            console.error('Error parsing token:', error);
            return true;
        }
    }
    
    /**
     * Parse JWT token payload
     * @param {string} token 
     * @returns {object|null} Token payload
     */
    function parseToken(token) {
        try {
            return JSON.parse(atob(token.split('.')[1]));
        } catch (error) {
            console.error('Error parsing token:', error);
            return null;
        }
    }
    
    // Helper functions for cookies
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
    
    function setCookie(name, value, days) {
        const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
        document.cookie = `${name}=${value}; expires=${expires}; path=/; Secure; SameSite=Strict`;
    }
    
    function deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    }
    
    // Public API
    return {
        isAuthenticated,
        getAccessToken,
        getRefreshToken,
        getUser,
        login,
        register,
        logout,
        refreshToken,
        getCurrentUser,
        init,
        setTokens,
        clearTokens,
        setUser,
        clearUser,
        isTokenExpired,
        parseToken
    };
})();

// Auto-initialize auth on page load
document.addEventListener('DOMContentLoaded', async function() {
    try {
        await Auth.init();
    } catch (error) {
        console.error('Auth initialization error:', error);
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Auth;
}