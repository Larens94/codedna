/**
 * API client for AgentHub with automatic token refresh
 * Provides fetch wrapper with authentication and error handling
 */

const API = (function() {
    'use strict';
    
    const API_BASE = '/api/v1';
    const MAX_RETRIES = 3;
    
    // Request queue for token refresh
    let isRefreshing = false;
    let failedQueue = [];
    
    /**
     * Process failed queue after token refresh
     * @param {string} token - New access token
     */
    function processQueue(token) {
        failedQueue.forEach(prom => {
            if (token) {
                prom.resolve(token);
            } else {
                prom.reject(new Error('Token refresh failed'));
            }
        });
        failedQueue = [];
    }
    
    /**
     * Make authenticated API request with automatic token refresh
     * @param {string} endpoint - API endpoint (without base)
     * @param {object} options - Fetch options
     * @param {number} retryCount - Internal retry counter
     * @returns {Promise<Response>} Fetch response
     */
    async function request(endpoint, options = {}, retryCount = 0) {
        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
        
        // Get current access token
        let token = Auth.getAccessToken();
        
        // Prepare headers
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        // Add authorization header if token exists
        if (token && !headers.Authorization) {
            headers.Authorization = `Bearer ${token}`;
        }
        
        // Merge options
        const fetchOptions = {
            ...options,
            headers
        };
        
        try {
            const response = await fetch(url, fetchOptions);
            
            // Handle 401 Unauthorized (token expired)
            if (response.status === 401 && token && retryCount < MAX_RETRIES) {
                if (isRefreshing) {
                    // Wait for token refresh to complete
                    return new Promise((resolve, reject) => {
                        failedQueue.push({ resolve, reject });
                    }).then(newToken => {
                        headers.Authorization = `Bearer ${newToken}`;
                        return request(endpoint, { ...options, headers }, retryCount + 1);
                    });
                }
                
                isRefreshing = true;
                
                try {
                    // Attempt to refresh token
                    const newToken = await Auth.refreshToken();
                    isRefreshing = false;
                    
                    // Update authorization header with new token
                    headers.Authorization = `Bearer ${newToken}`;
                    processQueue(newToken);
                    
                    // Retry original request with new token
                    return request(endpoint, { ...options, headers }, retryCount + 1);
                } catch (refreshError) {
                    isRefreshing = false;
                    processQueue(null);
                    
                    // Redirect to login if refresh failed
                    if (retryCount === 0) {
                        window.location.href = '/login?session_expired=true';
                    }
                    
                    throw refreshError;
                }
            }
            
            // Handle other error statuses
            if (!response.ok) {
                const error = await parseError(response);
                throw error;
            }
            
            return response;
        } catch (error) {
            // Network error or other fetch failure
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    /**
     * Parse error response from API
     * @param {Response} response 
     * @returns {Promise<Error>} Error object with details
     */
    async function parseError(response) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        let errorDetails = null;
        
        try {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.detail || errorMessage;
                errorDetails = errorData;
            }
        } catch (parseError) {
            // Ignore JSON parsing errors
        }
        
        const error = new Error(errorMessage);
        error.status = response.status;
        error.details = errorDetails;
        error.response = response;
        
        return error;
    }
    
    /**
     * GET request
     * @param {string} endpoint 
     * @param {object} headers 
     * @returns {Promise<object>} JSON response
     */
    async function get(endpoint, headers = {}) {
        const response = await request(endpoint, { method: 'GET', headers });
        return response.json();
    }
    
    /**
     * POST request
     * @param {string} endpoint 
     * @param {object} data 
     * @param {object} headers 
     * @returns {Promise<object>} JSON response
     */
    async function post(endpoint, data = {}, headers = {}) {
        const response = await request(endpoint, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });
        return response.json();
    }
    
    /**
     * PUT request
     * @param {string} endpoint 
     * @param {object} data 
     * @param {object} headers 
     * @returns {Promise<object>} JSON response
     */
    async function put(endpoint, data = {}, headers = {}) {
        const response = await request(endpoint, {
            method: 'PUT',
            headers,
            body: JSON.stringify(data)
        });
        return response.json();
    }
    
    /**
     * PATCH request
     * @param {string} endpoint 
     * @param {object} data 
     * @param {object} headers 
     * @returns {Promise<object>} JSON response
     */
    async function patch(endpoint, data = {}, headers = {}) {
        const response = await request(endpoint, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(data)
        });
        return response.json();
    }
    
    /**
     * DELETE request
     * @param {string} endpoint 
     * @param {object} headers 
     * @returns {Promise<object>} JSON response
     */
    async function del(endpoint, headers = {}) {
        const response = await request(endpoint, { method: 'DELETE', headers });
        return response.json();
    }
    
    /**
     * Upload file with multipart/form-data
     * @param {string} endpoint 
     * @param {FormData} formData 
     * @param {object} headers 
     * @returns {Promise<object>} JSON response
     */
    async function upload(endpoint, formData, headers = {}) {
        // Remove Content-Type header for browser to set boundary
        delete headers['Content-Type'];
        
        const response = await request(endpoint, {
            method: 'POST',
            headers,
            body: formData
        });
        return response.json();
    }
    
    /**
     * Stream response (for SSE or large data)
     * @param {string} endpoint 
     * @param {object} options 
     * @returns {Promise<ReadableStream>} Stream reader
     */
    async function stream(endpoint, options = {}) {
        const response = await request(endpoint, options);
        return response.body.getReader();
    }
    
    /**
     * Create SSE EventSource connection
     * @param {string} endpoint 
     * @param {object} options 
     * @returns {EventSource} SSE connection
     */
    function createSSE(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
        const token = Auth.getAccessToken();
        
        let sseUrl = url;
        if (token && options.withAuth !== false) {
            sseUrl += (url.includes('?') ? '&' : '?') + `token=${encodeURIComponent(token)}`;
        }
        
        return new EventSource(sseUrl);
    }
    
    // Public API
    return {
        request,
        get,
        post,
        put,
        patch,
        delete: del,
        upload,
        stream,
        createSSE,
        
        // Constants
        BASE_URL: API_BASE
    };
})();

// Ensure Auth is available
if (typeof Auth === 'undefined') {
    console.error('Auth module must be loaded before API module');
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}