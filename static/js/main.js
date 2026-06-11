/**
 * IoT Data Platform - Main JavaScript
 * Common utilities, AJAX helpers, auth handling, theme toggle
 */

(function() {
    'use strict';

    // CSRF Token helper
    window.getCsrfToken = function() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    };

    // AJAX helper with CSRF
    window.apiRequest = function(url, options) {
        options = options || {};
        const headers = options.headers || {};
        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes((options.method || 'GET').toUpperCase())) {
            headers['X-CSRFToken'] = window.getCsrfToken();
        }
        headers['Content-Type'] = headers['Content-Type'] || 'application/json';
        options.headers = headers;

        if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
            options.body = JSON.stringify(options.body);
        }

        return fetch(url, options).then(function(response) {
            if (response.status === 401 || response.status === 403) {
                window.location.href = '/login';
                return Promise.reject(new Error('Unauthorized'));
            }
            if (!response.ok) {
                return response.json().catch(function() {
                    return { error: 'Request failed: ' + response.status };
                }).then(function(data) {
                    return Promise.reject(new Error(data.error || 'Request failed'));
                });
            }
            return response.json();
        });
    };

    // Show toast notification
    window.showToast = function(message, type) {
        type = type || 'info';
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            const container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1055';
            document.body.appendChild(container);
        }

        const toastId = 'toast-' + Date.now();
        const bgClass = type === 'error' || type === 'danger' ? 'bg-danger' :
                        type === 'success' ? 'bg-success' :
                        type === 'warning' ? 'bg-warning text-dark' : 'bg-info';

        const html = '<div id="' + toastId + '" class="toast align-items-center ' + bgClass + ' text-white border-0" role="alert" aria-live="assertive" aria-atomic="true">' +
            '<div class="d-flex">' +
                '<div class="toast-body">' + message + '</div>' +
                '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
            '</div>' +
        '</div>';

        document.getElementById('toastContainer').insertAdjacentHTML('beforeend', html);
        const toastEl = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
        toast.show();
        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    };

    // Format number
    window.formatNumber = function(num, decimals) {
        decimals = decimals !== undefined ? decimals : 2;
        if (num === null || num === undefined) return '-';
        return Number(num).toFixed(decimals);
    };

    // Format datetime
    window.formatDateTime = function(dt) {
        if (!dt) return '-';
        const d = new Date(dt);
        if (isNaN(d.getTime())) return dt;
        return d.getFullYear() + '-' +
            String(d.getMonth() + 1).padStart(2, '0') + '-' +
            String(d.getDate()).padStart(2, '0') + ' ' +
            String(d.getHours()).padStart(2, '0') + ':' +
            String(d.getMinutes()).padStart(2, '0') + ':' +
            String(d.getSeconds()).padStart(2, '0');
    };

    // Theme toggle
    function initTheme() {
        const saved = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = saved || (prefersDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-bs-theme', theme);
        updateThemeIcon(theme);
    }

    function updateThemeIcon(theme) {
        const btn = document.getElementById('themeToggle');
        if (!btn) return;
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
        }
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-bs-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    }

    // Confirm delete
    window.confirmDelete = function(message, callback) {
        if (confirm(message || '确定要删除吗？此操作不可撤销。')) {
            callback();
        }
    };

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        initTheme();

        const themeBtn = document.getElementById('themeToggle');
        if (themeBtn) {
            themeBtn.addEventListener('click', toggleTheme);
        }

        // Auto-dismiss alerts
        document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
            setTimeout(function() {
                const bsAlert = bootstrap.Alert.getInstance(alert);
                if (bsAlert) bsAlert.close();
            }, 5000);
        });
    });
})();
