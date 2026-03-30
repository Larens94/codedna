/**
 * Main JavaScript utilities for AgentHub
 * General helpers, form handling, UI components
 */

const AgentHubUI = (function() {
    'use strict';
    
    /**
     * Initialize all UI components on page load
     */
    function init() {
        initForms();
        initModals();
        initDropdowns();
        initTabs();
        initTooltips();
        initNotifications();
        
        // Check authentication state
        checkAuthState();
        
        // Update user info in sidebar
        updateUserInfo();
        
        console.log('AgentHub UI initialized');
    }
    
    /**
     * Initialize AJAX forms
     */
    function initForms() {
        document.querySelectorAll('form[data-ajax]').forEach(form => {
            form.addEventListener('submit', handleAjaxFormSubmit);
        });
        
        // Real-time validation
        document.querySelectorAll('input[data-validate]').forEach(input => {
            input.addEventListener('blur', validateField);
            input.addEventListener('input', validateField);
        });
    }
    
    /**
     * Handle AJAX form submission
     * @param {Event} event 
     */
    async function handleAjaxFormSubmit(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const form = event.target;
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton?.textContent;
        
        // Disable submit button
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
        }
        
        // Clear previous errors
        clearFormErrors(form);
        
        try {
            const formData = new FormData(form);
            const data = Object.fromEntries(formData);
            const action = form.getAttribute('action') || window.location.pathname;
            const method = form.getAttribute('method') || 'POST';
            
            const response = await fetch(action, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': getCSRFToken()
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || result.detail || 'Form submission failed');
            }
            
            // Show success message
            showNotification('success', result.message || 'Operation successful');
            
            // Handle redirect if specified
            if (result.redirect) {
                setTimeout(() => {
                    window.location.href = result.redirect;
                }, 1500);
            }
            
            // Call success callback if specified
            const successCallback = form.getAttribute('data-success');
            if (successCallback && typeof window[successCallback] === 'function') {
                window[successCallback](result);
            }
            
            // Reset form if needed
            if (form.hasAttribute('data-reset')) {
                form.reset();
            }
            
        } catch (error) {
            console.error('Form submission error:', error);
            
            // Show error message
            showNotification('error', error.message);
            
            // Display field errors if available
            if (error.details && error.details.errors) {
                displayFormErrors(form, error.details.errors);
            }
            
            // Call error callback if specified
            const errorCallback = form.getAttribute('data-error');
            if (errorCallback && typeof window[errorCallback] === 'function') {
                window[errorCallback](error);
            }
        } finally {
            // Re-enable submit button
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        }
    }
    
    /**
     * Validate form field
     * @param {Event} event 
     */
    function validateField(event) {
        const field = event.target;
        const value = field.value.trim();
        const validationType = field.getAttribute('data-validate');
        
        let isValid = true;
        let errorMessage = '';
        
        switch (validationType) {
            case 'email':
                isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                errorMessage = 'Please enter a valid email address';
                break;
                
            case 'password':
                isValid = value.length >= 8;
                errorMessage = 'Password must be at least 8 characters';
                break;
                
            case 'required':
                isValid = value.length > 0;
                errorMessage = 'This field is required';
                break;
                
            case 'number':
                isValid = !isNaN(parseFloat(value)) && isFinite(value);
                errorMessage = 'Please enter a valid number';
                break;
        }
        
        const errorElement = field.parentElement.querySelector('.field-error');
        
        if (!isValid && value.length > 0) {
            field.classList.add('border-red-500');
            field.classList.remove('border-gray-600');
            
            if (errorElement) {
                errorElement.textContent = errorMessage;
                errorElement.classList.remove('hidden');
            }
        } else {
            field.classList.remove('border-red-500');
            field.classList.add('border-gray-600');
            
            if (errorElement) {
                errorElement.classList.add('hidden');
            }
        }
    }
    
    /**
     * Clear form errors
     * @param {HTMLFormElement} form 
     */
    function clearFormErrors(form) {
        form.querySelectorAll('.field-error').forEach(el => {
            el.classList.add('hidden');
        });
        form.querySelectorAll('input, select, textarea').forEach(field => {
            field.classList.remove('border-red-500');
            field.classList.add('border-gray-600');
        });
    }
    
    /**
     * Display form errors
     * @param {HTMLFormElement} form 
     * @param {Array} errors - Array of error objects with field and message
     */
    function displayFormErrors(form, errors) {
        errors.forEach(error => {
            const field = form.querySelector(`[name="${error.field}"]`);
            if (field) {
                field.classList.add('border-red-500');
                field.classList.remove('border-gray-600');
                
                const errorElement = field.parentElement.querySelector('.field-error') ||
                                   createErrorElement(field);
                errorElement.textContent = error.message;
                errorElement.classList.remove('hidden');
            }
        });
    }
    
    /**
     * Create error element for field
     * @param {HTMLElement} field 
     * @returns {HTMLElement} Error element
     */
    function createErrorElement(field) {
        const errorElement = document.createElement('p');
        errorElement.className = 'field-error text-red-500 text-sm mt-1';
        field.parentElement.appendChild(errorElement);
        return errorElement;
    }
    
    /**
     * Initialize modal dialogs
     */
    function initModals() {
        // Open modal buttons
        document.querySelectorAll('[data-modal-target]').forEach(button => {
            button.addEventListener('click', function() {
                const modalId = this.getAttribute('data-modal-target');
                const modal = document.getElementById(modalId);
                if (modal) {
                    openModal(modal);
                }
            });
        });
        
        // Close modal buttons
        document.querySelectorAll('[data-modal-close]').forEach(button => {
            button.addEventListener('click', function() {
                const modal = this.closest('.modal');
                if (modal) {
                    closeModal(modal);
                }
            });
        });
        
        // Close modal on backdrop click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', function(event) {
                if (event.target === this) {
                    closeModal(this);
                }
            });
        });
        
        // Close modal on Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                document.querySelectorAll('.modal.open').forEach(modal => {
                    closeModal(modal);
                });
            }
        });
    }
    
    /**
     * Open modal dialog
     * @param {HTMLElement} modal 
     */
    function openModal(modal) {
        modal.classList.add('open');
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
        
        // Focus first input if any
        const input = modal.querySelector('input, textarea, select');
        if (input) {
            setTimeout(() => input.focus(), 100);
        }
    }
    
    /**
     * Close modal dialog
     * @param {HTMLElement} modal 
     */
    function closeModal(modal) {
        modal.classList.remove('open');
        modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }
    
    /**
     * Initialize dropdown menus
     */
    function initDropdowns() {
        document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
            toggle.addEventListener('click', function(event) {
                event.stopPropagation();
                const dropdown = this.closest('.dropdown');
                dropdown.classList.toggle('open');
            });
        });
        
        // Close dropdowns when clicking outside
        document.addEventListener('click', function() {
            document.querySelectorAll('.dropdown.open').forEach(dropdown => {
                dropdown.classList.remove('open');
            });
        });
    }
    
    /**
     * Initialize tab components
     */
    function initTabs() {
        document.querySelectorAll('.tab-header button[data-tab]').forEach(tabButton => {
            tabButton.addEventListener('click', function() {
                const tabId = this.getAttribute('data-tab');
                const tabContainer = this.closest('.tabs');
                
                // Update active tab header
                tabContainer.querySelectorAll('.tab-header button').forEach(btn => {
                    btn.classList.remove('active');
                    btn.classList.add('text-gray-400');
                });
                this.classList.add('active');
                this.classList.remove('text-gray-400');
                
                // Show corresponding tab content
                tabContainer.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.add('hidden');
                });
                const targetContent = tabContainer.querySelector(`#${tabId}`);
                if (targetContent) {
                    targetContent.classList.remove('hidden');
                }
            });
        });
    }
    
    /**
     * Initialize tooltips
     */
    function initTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            element.addEventListener('mouseenter', showTooltip);
            element.addEventListener('mouseleave', hideTooltip);
        });
    }
    
    /**
     * Show tooltip
     * @param {Event} event 
     */
    function showTooltip(event) {
        const element = event.target;
        const tooltipText = element.getAttribute('data-tooltip');
        
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip absolute z-50 px-3 py-2 text-sm bg-gray-800 text-white rounded-lg shadow-lg';
        tooltip.textContent = tooltipText;
        
        document.body.appendChild(tooltip);
        
        const rect = element.getBoundingClientRect();
        tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
        tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
        
        element._tooltip = tooltip;
    }
    
    /**
     * Hide tooltip
     * @param {Event} event 
     */
    function hideTooltip(event) {
        const element = event.target;
        if (element._tooltip) {
            element._tooltip.remove();
            delete element._tooltip;
        }
    }
    
    /**
     * Initialize notification system
     */
    function initNotifications() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'fixed top-4 right-4 z-50 space-y-2 max-w-sm';
            document.body.appendChild(container);
        }
    }
    
    /**
     * Show notification
     * @param {string} type - 'success', 'error', 'warning', 'info'
     * @param {string} message 
     * @param {number} duration - Duration in ms (0 for manual dismissal)
     */
    function showNotification(type, message, duration = 5000) {
        const container = document.getElementById('notification-container');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `notification p-4 rounded-lg shadow-lg transform transition-all duration-300 ${
            type === 'success' ? 'bg-green-500/20 border border-green-500 text-green-300' :
            type === 'error' ? 'bg-red-500/20 border border-red-500 text-red-300' :
            type === 'warning' ? 'bg-yellow-500/20 border border-yellow-500 text-yellow-300' :
            'bg-blue-500/20 border border-blue-500 text-blue-300'
        }`;
        
        notification.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex items-start space-x-3">
                    <i class="fas ${
                        type === 'success' ? 'fa-check-circle' :
                        type === 'error' ? 'fa-exclamation-circle' :
                        type === 'warning' ? 'fa-exclamation-triangle' :
                        'fa-info-circle'
                    } mt-1"></i>
                    <div>
                        <p class="font-medium">${message}</p>
                    </div>
                </div>
                <button class="text-lg hover:opacity-70 ml-4" data-dismiss>&times;</button>
            </div>
        `;
        
        container.appendChild(notification);
        
        // Add dismiss button handler
        notification.querySelector('[data-dismiss]').addEventListener('click', () => {
            dismissNotification(notification);
        });
        
        // Auto-dismiss if duration > 0
        if (duration > 0) {
            setTimeout(() => {
                dismissNotification(notification);
            }, duration);
        }
        
        // Animate in
        requestAnimationFrame(() => {
            notification.classList.add('translate-x-full');
            requestAnimationFrame(() => {
                notification.classList.remove('translate-x-full');
            });
        });
    }
    
    /**
     * Dismiss notification
     * @param {HTMLElement} notification 
     */
    function dismissNotification(notification) {
        notification.classList.add('opacity-0', 'translate-x-full');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
    
    /**
     * Check authentication state and update UI
     */
    function checkAuthState() {
        const isAuthenticated = Auth && Auth.isAuthenticated();
        
        // Show/hide auth-dependent elements
        document.querySelectorAll('[data-auth]').forEach(element => {
            const requiredAuth = element.getAttribute('data-auth') === 'true';
            if (requiredAuth && !isAuthenticated) {
                element.classList.add('hidden');
            } else if (!requiredAuth && isAuthenticated) {
                element.classList.add('hidden');
            } else {
                element.classList.remove('hidden');
            }
        });
        
        // Update login/logout buttons
        const loginBtn = document.getElementById('login-btn');
        const logoutBtn = document.getElementById('logout-btn');
        
        if (loginBtn) loginBtn.style.display = isAuthenticated ? 'none' : 'block';
        if (logoutBtn) logoutBtn.style.display = isAuthenticated ? 'block' : 'none';
    }
    
    /**
     * Update user info in sidebar
     */
    async function updateUserInfo() {
        if (!Auth || !Auth.isAuthenticated()) return;
        
        const usernameEl = document.getElementById('currentUsername');
        const planEl = document.getElementById('currentUserPlan');
        const creditsEl = document.getElementById('currentUserCredits');
        
        if (!usernameEl && !planEl && !creditsEl) return;
        
        try {
            const user = await Auth.getCurrentUser();
            if (user) {
                if (usernameEl) usernameEl.textContent = user.username || user.email;
                if (planEl) planEl.textContent = user.plan_type || 'Free Plan';
                if (creditsEl) creditsEl.textContent = user.credits ? user.credits.toFixed(2) : '0.00';
            }
        } catch (error) {
            console.error('Failed to update user info:', error);
        }
    }
    
    /**
     * Get CSRF token from meta tag
     * @returns {string|null} CSRF token
     */
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : null;
    }
    
    /**
     * Format bytes to human readable string
     * @param {number} bytes 
     * @param {number} decimals 
     * @returns {string}
     */
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    /**
     * Format date to relative time
     * @param {string|Date} date 
     * @returns {string}
     */
    function formatRelativeTime(date) {
        const now = new Date();
        const target = new Date(date);
        const diffMs = now - target;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        
        if (diffSec < 60) return 'just now';
        if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
        if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
        if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
        
        return target.toLocaleDateString();
    }
    
    /**
     * Debounce function
     * @param {Function} func 
     * @param {number} wait 
     * @returns {Function}
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Throttle function
     * @param {Function} func 
     * @param {number} limit 
     * @returns {Function}
     */
    function throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    // Public API
    return {
        init,
        
        // Form handling
        initForms,
        handleAjaxFormSubmit,
        clearFormErrors,
        displayFormErrors,
        
        // Modals
        initModals,
        openModal,
        closeModal,
        
        // Notifications
        showNotification,
        dismissNotification,
        
        // Utilities
        formatBytes,
        formatRelativeTime,
        debounce,
        throttle,
        
        // State
        checkAuthState,
        updateUserInfo
    };
})();

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AgentHubUI.init());
} else {
    AgentHubUI.init();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgentHubUI;
}