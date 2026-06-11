/**
 * IoT Data Platform - Chart JavaScript
 * Chart.js integration for data visualization
 */

(function() {
    'use strict';

    let dashboardChart = null;

    window.initDashboardChart = function(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';
        const textColor = isDark ? '#e0e0e0' : '#666';

        dashboardChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '数据接收量',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: textColor }
                    }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: textColor }
                    },
                    y: {
                        grid: { color: gridColor },
                        ticks: { color: textColor },
                        beginAtZero: true
                    }
                }
            }
        });

        loadChartData('24h');

        const periodSelect = document.getElementById('chartPeriod');
        if (periodSelect) {
            periodSelect.addEventListener('change', function() {
                loadChartData(this.value);
            });
        }
    };

    function loadChartData(period) {
        apiRequest('/api/data/history?period=' + period + '&aggregate=1').then(function(data) {
            const labels = data.labels || [];
            const values = data.values || [];
            if (dashboardChart) {
                dashboardChart.data.labels = labels;
                dashboardChart.data.datasets[0].data = values;
                dashboardChart.update();
            }
        }).catch(function() {
            // silent fail
        });
    }

    window.initChannelChart = function(canvasId, channelId, pointName) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';
        const textColor = isDark ? '#e0e0e0' : '#666';

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: pointName || '数值',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: textColor }
                    }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: textColor, maxTicksLimit: 8 }
                    },
                    y: {
                        grid: { color: gridColor },
                        ticks: { color: textColor }
                    }
                }
            }
        });

        apiRequest('/api/data/chart/' + channelId + '/' + encodeURIComponent(pointName)).then(function(data) {
            chart.data.labels = data.labels || [];
            chart.data.datasets[0].data = data.values || [];
            chart.update();
        }).catch(function(err) {
            showToast('加载图表数据失败: ' + err.message, 'error');
        });
    };

    // Listen for theme changes to update chart colors
    document.addEventListener('DOMContentLoaded', function() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'data-bs-theme') {
                    const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
                    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';
                    const textColor = isDark ? '#e0e0e0' : '#666';
                    if (dashboardChart) {
                        dashboardChart.options.scales.x.grid.color = gridColor;
                        dashboardChart.options.scales.x.ticks.color = textColor;
                        dashboardChart.options.scales.y.grid.color = gridColor;
                        dashboardChart.options.scales.y.ticks.color = textColor;
                        dashboardChart.options.plugins.legend.labels.color = textColor;
                        dashboardChart.update();
                    }
                }
            });
        });
        observer.observe(document.documentElement, { attributes: true });
    });
})();
