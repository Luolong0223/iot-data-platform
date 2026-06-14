/**
 * IoT Platform Theme Manager
 * Handles dark/light mode switching, toast notifications, and UI utilities
 */

const DS = (function() {
  const STORAGE_KEY = 'iot_platform_theme';

  function getTheme() {
    return localStorage.getItem(STORAGE_KEY) ||
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'dark' ? 'light' : 'dark');
  }

  // Initialize on load
  setTheme(getTheme());

  // Toast notification system
  const toastContainer = (() => {
    let el = document.querySelector('.ds-toast-container');
    if (!el) {
      el = document.createElement('div');
      el.className = 'ds-toast-container';
      document.body.appendChild(el);
    }
    return el;
  })();

  const ICONS = {
    success: '✓', warning: '⚠', danger: '✕', info: 'ℹ'
  };

  function toast(message, type = 'info', title = '', duration = 3500) {
    const el = document.createElement('div');
    el.className = `ds-toast ds-toast-${type}`;
    el.innerHTML = `
      <span class="icon">${ICONS[type] || ICONS.info}</span>
      <div class="body">
        ${title ? `<div class="title">${title}</div>` : ''}
        <div class="message">${message}</div>
      </div>
      <button class="close" aria-label="关闭">×</button>
    `;
    el.querySelector('.close').onclick = () => removeToast(el);
    toastContainer.appendChild(el);
    if (duration > 0) {
      setTimeout(() => removeToast(el), duration);
    }
    return el;
  }

  function removeToast(el) {
    if (!el || !el.parentNode) return;
    el.classList.add('removing');
    setTimeout(() => el.parentNode && el.parentNode.removeChild(el), 250);
  }

  // Loading state helpers
  function setLoading(btn, loading = true) {
    if (!btn) return;
    if (loading) {
      btn.dataset.originalText = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="ds-spinner ds-spinner-sm"></span> 处理中...';
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
    }
  }

  // Skeleton placeholder
  function skeleton(height = 16, width = '100%') {
    return `<div class="ds-skeleton" style="height:${height}px;width:${width}"></div>`;
  }

  // Number formatting
  function formatNumber(n, decimals = 0) {
    if (n === null || n === undefined || isNaN(n)) return '-';
    return Number(n).toLocaleString('zh-CN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  // Time formatting
  function formatTime(date, withSeconds = true) {
    if (!date) return '-';
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    const s = String(d.getSeconds()).padStart(2, '0');
    return withSeconds ? `${h}:${m}:${s}` : `${h}:${m}`;
  }

  function formatDateTime(date) {
    if (!date) return '-';
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleString('zh-CN', { hour12: false });
  }

  function timeAgo(date) {
    if (!date) return '-';
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '-';
    const seconds = Math.floor((Date.now() - d.getTime()) / 1000);
    if (seconds < 60) return `${seconds}秒前`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`;
    return `${Math.floor(seconds / 86400)}天前`;
  }

  return {
    setTheme, toggleTheme, getTheme,
    toast, setLoading, skeleton,
    formatNumber, formatTime, formatDateTime, timeAgo
  };
})();

// Expose to window
window.DS = DS;

// Auto-attach theme toggle handler
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.ds-theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => DS.toggleTheme());
  }
});
