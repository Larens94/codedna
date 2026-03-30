/**
 * Server-Sent Events (SSE) client for AgentHub
 * Handles real-time updates for dashboard, studio, and agent runs
 */

const SSE = (function() {
    'use strict';
    
    // Active connections
    const connections = new Map();
    
    // Default configuration
    const DEFAULT_CONFIG = {
        retryDelay: 3000,          // Base retry delay in ms
        maxRetryDelay: 30000,      // Maximum retry delay
        retryMultiplier: 1.5,      // Exponential backoff multiplier
        maxRetries: 10,            // Maximum retry attempts before giving up
        withAuth: true,            // Include authentication token
        heartbeatInterval: 30000,  // Send heartbeat ping interval (server-side)
        reconnectOnError: true,    // Automatically reconnect on error
        debug: false               // Enable debug logging
    };
    
    /**
     * Create SSE connection
     * @param {string} endpoint - SSE endpoint
     * @param {object} config - Configuration options
     * @returns {object} Connection object with controls
     */
    function connect(endpoint, config = {}) {
        const connectionId = generateId();
        const mergedConfig = { ...DEFAULT_CONFIG, ...config };
        
        let eventSource = null;
        let retryCount = 0;
        let retryTimer = null;
        let heartbeatTimer = null;
        let isConnected = false;
        let isConnecting = false;
        let isClosed = false;
        
        // Event listeners
        const listeners = {
            open: [],
            message: [],
            error: [],
            close: [],
            retrying: []
        };
        
        /**
         * Log debug message
         * @param {string} message 
         */
        function debug(message) {
            if (mergedConfig.debug) {
                console.log(`[SSE:${connectionId}] ${message}`);
            }
        }
        
        /**
         * Emit event to listeners
         * @param {string} eventType 
         * @param {any} data 
         */
        function emit(eventType, data) {
            if (listeners[eventType]) {
                listeners[eventType].forEach(callback => {
                    try {
                        callback(data);
                    } catch (error) {
                        console.error(`Error in SSE ${eventType} listener:`, error);
                    }
                });
            }
        }
        
        /**
         * Calculate retry delay with exponential backoff
         * @returns {number} Delay in milliseconds
         */
        function calculateRetryDelay() {
            const delay = mergedConfig.retryDelay * Math.pow(mergedConfig.retryMultiplier, retryCount);
            return Math.min(delay, mergedConfig.maxRetryDelay);
        }
        
        /**
         * Attempt to connect
         */
        function attemptConnect() {
            if (isConnecting || isClosed) {
                return;
            }
            
            isConnecting = true;
            debug(`Connecting to ${endpoint} (attempt ${retryCount + 1})`);
            
            // Build URL with authentication token if needed
            let url = endpoint;
            if (mergedConfig.withAuth && typeof API !== 'undefined') {
                const token = Auth.getAccessToken();
                if (token) {
                    url += (url.includes('?') ? '&' : '?') + `token=${encodeURIComponent(token)}`;
                }
            }
            
            // Create EventSource
            eventSource = new EventSource(url);
            
            // Connection established
            eventSource.onopen = function(event) {
                debug('Connection opened');
                isConnecting = false;
                isConnected = true;
                retryCount = 0;
                emit('open', event);
                
                // Start heartbeat monitoring
                startHeartbeatMonitor();
            };
            
            // Message received
            eventSource.onmessage = function(event) {
                debug(`Message received: ${event.data ? event.data.length : 0} bytes`);
                
                try {
                    let data = event.data;
                    if (data.startsWith('{') || data.startsWith('[')) {
                        data = JSON.parse(data);
                    }
                    
                    emit('message', {
                        data: data,
                        originalEvent: event
                    });
                } catch (error) {
                    console.error('Error parsing SSE message:', error);
                    emit('message', {
                        data: event.data,
                        originalEvent: event
                    });
                }
            };
            
            // Error occurred
            eventSource.onerror = function(event) {
                debug('Connection error');
                isConnecting = false;
                
                if (isConnected) {
                    isConnected = false;
                    emit('error', event);
                    
                    if (mergedConfig.reconnectOnError && !isClosed) {
                        scheduleReconnect();
                    }
                } else {
                    // Connection failed to establish
                    emit('error', event);
                    
                    if (mergedConfig.reconnectOnError && !isClosed) {
                        scheduleReconnect();
                    }
                }
            };
            
            // Custom event listeners
            if (config.events) {
                Object.keys(config.events).forEach(eventName => {
                    eventSource.addEventListener(eventName, function(event) {
                        debug(`Custom event received: ${eventName}`);
                        
                        try {
                            let data = event.data;
                            if (data.startsWith('{') || data.startsWith('[')) {
                                data = JSON.parse(data);
                            }
                            
                            config.events[eventName]({
                                type: eventName,
                                data: data,
                                originalEvent: event
                            });
                        } catch (error) {
                            console.error(`Error handling SSE event ${eventName}:`, error);
                            config.events[eventName]({
                                type: eventName,
                                data: event.data,
                                originalEvent: event
                            });
                        }
                    });
                });
            }
        }
        
        /**
         * Schedule reconnection with exponential backoff
         */
        function scheduleReconnect() {
            if (isClosed) {
                return;
            }
            
            retryCount++;
            
            if (retryCount > mergedConfig.maxRetries) {
                debug(`Max retries (${mergedConfig.maxRetries}) exceeded, giving up`);
                emit('error', new Error('Max retry attempts exceeded'));
                close();
                return;
            }
            
            const delay = calculateRetryDelay();
            debug(`Scheduling reconnect in ${delay}ms (attempt ${retryCount})`);
            
            emit('retrying', {
                attempt: retryCount,
                delay: delay,
                maxRetries: mergedConfig.maxRetries
            });
            
            retryTimer = setTimeout(() => {
                attemptConnect();
            }, delay);
        }
        
        /**
         * Start heartbeat monitor
         * Checks if connection is still alive by monitoring last message time
         */
        function startHeartbeatMonitor() {
            if (heartbeatTimer) {
                clearInterval(heartbeatTimer);
            }
            
            let lastMessageTime = Date.now();
            
            // Update last message time on any message
            const originalEmit = emit;
            emit = function(eventType, data) {
                if (eventType === 'message') {
                    lastMessageTime = Date.now();
                }
                originalEmit(eventType, data);
            };
            
            heartbeatTimer = setInterval(() => {
                const timeSinceLastMessage = Date.now() - lastMessageTime;
                const heartbeatThreshold = mergedConfig.heartbeatInterval * 2;
                
                if (timeSinceLastMessage > heartbeatThreshold) {
                    debug('Heartbeat timeout, assuming connection dead');
                    if (eventSource) {
                        eventSource.close();
                    }
                    
                    if (mergedConfig.reconnectOnError && !isClosed) {
                        scheduleReconnect();
                    }
                }
            }, mergedConfig.heartbeatInterval);
        }
        
        /**
         * Close connection
         * @param {boolean} permanent - If true, won't auto-reconnect
         */
        function close(permanent = false) {
            debug('Closing connection');
            
            isClosed = permanent;
            isConnecting = false;
            isConnected = false;
            
            // Clear timers
            if (retryTimer) {
                clearTimeout(retryTimer);
                retryTimer = null;
            }
            
            if (heartbeatTimer) {
                clearInterval(heartbeatTimer);
                heartbeatTimer = null;
            }
            
            // Close EventSource
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            
            emit('close', { permanent });
            
            // Remove from connections map
            connections.delete(connectionId);
        }
        
        /**
         * Add event listener
         * @param {string} eventType - 'open', 'message', 'error', 'close', 'retrying'
         * @param {function} callback 
         */
        function on(eventType, callback) {
            if (listeners[eventType]) {
                listeners[eventType].push(callback);
            }
            return connection; // For chaining
        }
        
        /**
         * Remove event listener
         * @param {string} eventType 
         * @param {function} callback 
         */
        function off(eventType, callback) {
            if (listeners[eventType]) {
                const index = listeners[eventType].indexOf(callback);
                if (index > -1) {
                    listeners[eventType].splice(index, 1);
                }
            }
            return connection; // For chaining
        }
        
        // Connection object
        const connection = {
            id: connectionId,
            endpoint: endpoint,
            config: mergedConfig,
            
            // Methods
            connect: attemptConnect,
            close,
            on,
            off,
            
            // Properties
            get isConnected() { return isConnected; },
            get isConnecting() { return isConnecting; },
            get isClosed() { return isClosed; },
            get retryCount() { return retryCount; }
        };
        
        // Store connection
        connections.set(connectionId, connection);
        
        // Start connection
        attemptConnect();
        
        return connection;
    }
    
    /**
     * Close all active SSE connections
     */
    function closeAll() {
        connections.forEach(connection => {
            connection.close(true);
        });
        connections.clear();
    }
    
    /**
     * Get active connection by ID
     * @param {string} connectionId 
     * @returns {object|null} Connection object
     */
    function getConnection(connectionId) {
        return connections.get(connectionId) || null;
    }
    
    /**
     * Get all active connections
     * @returns {array} Array of connection objects
     */
    function getAllConnections() {
        return Array.from(connections.values());
    }
    
    /**
     * Generate unique ID for connection
     * @returns {string}
     */
    function generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
    
    // Public API
    return {
        connect,
        closeAll,
        getConnection,
        getAllConnections,
        
        // Constants
        DEFAULT_CONFIG
    };
})();

// Ensure API and Auth are available for token injection
if (typeof API === 'undefined') {
    console.warn('API module not loaded, SSE authentication may not work');
}

if (typeof Auth === 'undefined') {
    console.warn('Auth module not loaded, SSE authentication may not work');
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SSE;
}