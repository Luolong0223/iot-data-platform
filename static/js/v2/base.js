/**
 * IoT Data Platform v2.0 - Base JavaScript
 */

(function() {
    'use strict';
    
    // ========================================
    // Sidebar Toggle
    // ========================================
    
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    function toggleSidebar() {
        if (window.innerWidth < 992) {
            sidebar.classList.toggle('show');
            sidebarOverlay.classList.toggle('show');
            document.body.style.overflow = sidebar.classList.contains('show') ? 'hidden' : '';
        } else {
            sidebar.classList.toggle('collapsed');
        }
    }
    
    function closeSidebar() {
        sidebar.classList.remove('show');
        sidebarOverlay.classList.remove('show');
        document.body.style.overflow = '';
    }
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', toggleSidebar);
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }
    
    // Close on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('show')) {
            closeSidebar();
        }
    });
    
    // Handle resize
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 992) {
            closeSidebar();
        }
    });
    
    // ========================================
    // Theme Toggle
    // ========================================
    
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = html.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }
    
    function setTheme(theme) {
        html.setAttribute('data-bs-theme', theme);
        
        const darkIcon = document.querySelector('.theme-icon-dark');
        const lightIcon = document.querySelector('.theme-icon-light');
        
        if (darkIcon && lightIcon) {
            if (theme === 'dark') {
                darkIcon.style.display = '';
                lightIcon.style.display = 'none';
            } else {
                darkIcon.style.display = 'none';
                lightIcon.style.display = '';
            }
        }
    }
    
    // ========================================
    // Global Search (Cmd/Ctrl + K)
    // ========================================
    
    const globalSearch = document.getElementById('globalSearch');
    
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            if (globalSearch) {
                globalSearch.focus();
            }
        }
    });
    
    if (globalSearch) {
        let searchTimeout;
        
        globalSearch.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length > 1) {
                searchTimeout = setTimeout(() => {
                    performSearch(query);
                }, 300);
            }
        });
        
        globalSearch.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = globalSearch.value.trim();
                if (query) {
                    window.location.href = `/devices?search=${encodeURIComponent(query)}`;
                }
            }
        });
    }
    
    function performSearch(query) {
        // Implement search functionality
        console.log('Searching for:', query);
    }
    
    // ========================================
    // API Helper Functions
    // ========================================
    
    window.apiRequest = async function(url, method = 'GET', data = null) {
        const options = {
            method: method.toUpperCase(),
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        };
        
        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            showToast(error.message || '请求失败，请稍后重试', 'danger');
            throw error;
        }
    };
    
    // ========================================
    // Toast Notifications
    // ========================================
    
    window.showToast = function(message, type = 'info', duration = 3000) {
        const toastContainer = document.getElementById('toastContainer') || createToastContainer();
        
        const toastId = `toast-${Date.now()}`;
        const iconMap = {
            success: 'bi-check-circle-fill',
            danger: 'bi-exclamation-triangle-fill',
            warning: 'bi-exclamation-circle-fill',
            info: 'bi-info-circle-fill'
        };
        
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi ${iconMap[type] || iconMap.info} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: duration });
        toast.show();
        
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    };
    
    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }
    
    // ========================================
    // Loading States
    // ========================================
    
    window.showLoading = function(element) {
        if (element) {
            element.classList.add('loading');
            element.disabled = true;
        }
    };
    
    window.hideLoading = function(element) {
        if (element) {
            element.classList.remove('loading');
            element.disabled = false;
        }
    };
    
    // ========================================
    // Confirm Dialog
    // ========================================
    
    window.confirmAction = async function(title, message, confirmText = '确认', cancelText = '取消') {
        return new Promise((resolve) => {
            const modalId = `confirm-modal-${Date.now()}`;
            const modalHTML = `
                <div class="modal fade" id="${modalId}" tabindex="-1">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>${message}</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-ghost" data-bs-dismiss="modal">${cancelText}</button>
                                <button type="button" class="btn btn-primary" id="${modalId}-confirm">${confirmText}</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            const modalEl = document.getElementById(modalId);
            const modal = new bootstrap.Modal(modalEl);
            
            document.getElementById(`${modalId}-confirm`).addEventListener('click', () => {
                modal.hide();
                resolve(true);
            });
            
            modalEl.addEventListener('hidden.bs.modal', () => {
                modalEl.remove();
                resolve(false);
            });
            
            modal.show();
        });
    };
    
    // ========================================
    // Format Helpers
    // ========================================
    
    window.formatNumber = function(num, decimals) {
        if (num === null || num === undefined) return '-';
        var n = Number(num);
        if (isNaN(n)) return String(num);
        var d = decimals !== undefined ? decimals : 6;
        return n.toFixed(d).replace(/\.?0+$/, '');
    };
    
    window.formatDate = function(dateStr, format = 'datetime') {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        
        switch (format) {
            case 'date':
                return date.toLocaleDateString('zh-CN');
            case 'time':
                return date.toLocaleTimeString('zh-CN');
            case 'relative':
                return getRelativeTime(date);
            default:
                return date.toLocaleString('zh-CN');
        }
    };
    
    function getRelativeTime(date) {
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (seconds < 60) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;
        return date.toLocaleDateString('zh-CN');
    }
    
    window.formatFileSize = function(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    
    // ========================================
    // Auto Refresh Data
    // ========================================
    
    window.autoRefresh = function(callback, interval = 30000) {
        let timer = setInterval(callback, interval);
        
        return {
            stop: () => clearInterval(timer),
            changeInterval: (newInterval) => {
                clearInterval(timer);
                timer = setInterval(callback, newInterval);
            }
        };
    };
    
    // ========================================
    // Initialize Tooltips & Popovers
    // ========================================
    
    document.addEventListener('DOMContentLoaded', () => {
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(el => new bootstrap.Tooltip(el));
        
        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(el => new bootstrap.Popover(el));
        
        // Add smooth scroll behavior
        document.documentElement.style.scrollBehavior = 'smooth';
        
        console.log('IoT Platform v2.0 initialized');
    });
    
})();
