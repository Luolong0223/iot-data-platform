/**
 * IoT Data Platform - Dashboard JavaScript
 * Real-time stats, charts, data stream, alarms, device status
 */

(function() {
    'use strict';

    let trendChart = null;
    let sseSource = null;
    let refreshTimer = null;

    // Load all stats from /api/data/latest
    window.loadStats = function() {
        apiRequest('/api/data/latest').then(function(data) {
            const devices = data.devices || [];
            let onlineCount = 0;
            let offlineCount = 0;
            let todayCount = 0;
            let totalVoltage = 0;
            let voltageCount = 0;
            const today = new Date().toISOString().slice(0, 10);

            devices.forEach(function(device) {
                const channels = device.channels || [];
                channels.forEach(function(ch) {
                    if (ch.online) {
                        onlineCount++;
                    } else {
                        offlineCount++;
                    }
                    const points = ch.latest_points || [];
                    points.forEach(function(p) {
                        if (p.timestamp && p.timestamp.slice(0, 10) === today) {
                            todayCount++;
                        }
                        if (p.name && p.name.toLowerCase().indexOf('voltage') !== -1 || p.name.toLowerCase().indexOf('电压') !== -1) {
                            const v = parseFloat(p.value);
                            if (!isNaN(v)) {
                                totalVoltage += v;
                                voltageCount++;
                            }
                        }
                    });
                });
            });

            document.getElementById('statDevices').textContent = devices.length;
            document.getElementById('statOnline').textContent = onlineCount;
            document.getElementById('statOffline').textContent = offlineCount;
            document.getElementById('statToday').textContent = todayCount;

            if (voltageCount > 0) {
                document.getElementById('statVoltage').textContent = (totalVoltage / voltageCount).toFixed(1) + ' mV';
            } else {
                document.getElementById('statVoltage').textContent = '-';
            }
        }).catch(function() {});

        // Load today's alarm count
        apiRequest('/api/alarms/records?limit=100').then(function(data) {
            const records = data.records || [];
            const today = new Date().toISOString().slice(0, 10);
            let todayAlarms = 0;
            records.forEach(function(r) {
                if (r.created_at && r.created_at.slice(0, 10) === today) {
                    todayAlarms++;
                }
            });
            document.getElementById('statAlarms').textContent = todayAlarms;
        }).catch(function() {});
    };

    // Load recent data stream (last 10 data points)
    window.loadRecentData = function() {
        apiRequest('/api/data/history?limit=10').then(function(data) {
            const list = document.getElementById('realtimeDataList');
            const points = data.data_points || data.points || [];
            if (!points.length) {
                list.innerHTML = '<li class="list-group-item text-center text-muted py-4">暂无实时数据</li>';
                return;
            }
            list.innerHTML = points.slice(0, 10).map(function(p) {
                return '<li class="list-group-item d-flex justify-content-between align-items-center">' +
                    '<div>' +
                        '<span class="badge bg-secondary me-2">' + (p.device_name || p.device_id || '-') + '</span>' +
                        '<span class="badge bg-info me-2">' + (p.channel_name || p.channel_id || '-') + '</span>' +
                        '<span>' + (p.name || '-') + ': <strong>' + formatNumber(p.value, 4) + '</strong></span>' +
                    '</div>' +
                    '<small class="text-muted">' + formatDateTime(p.timestamp) + '</small>' +
                '</li>';
            }).join('');
        }).catch(function() {
            document.getElementById('realtimeDataList').innerHTML = '<li class="list-group-item text-center text-muted py-4">加载失败</li>';
        });
    };

    // Load recent alarms (unread first, limit 5)
    window.loadAlarms = function() {
        apiRequest('/api/alarms/records?limit=5&unread_only=1').then(function(data) {
            const list = document.getElementById('recentAlarmList');
            const records = data.records || [];
            if (!records.length) {
                list.innerHTML = '<li class="list-group-item text-center text-muted py-4">暂无未读报警</li>';
                return;
            }
            list.innerHTML = records.map(function(r) {
                const unreadClass = r.is_read ? '' : 'alarm-unread';
                return '<li class="list-group-item ' + unreadClass + ' d-flex justify-content-between align-items-center">' +
                    '<div>' +
                        '<i class="bi bi-exclamation-triangle-fill text-danger me-2"></i>' +
                        '<span>' + (r.message || '报警') + '</span>' +
                        '<br><small class="text-muted">' + (r.device_name || '') + ' / ' + (r.point_name || '') + ' = ' + formatNumber(r.actual_value, 4) + '</small>' +
                    '</div>' +
                    '<div class="text-end">' +
                        '<small class="text-muted d-block">' + formatDateTime(r.created_at) + '</small>' +
                        (r.is_read ? '<span class="badge bg-secondary">已读</span>' : '<span class="badge bg-danger">未读</span>') +
                    '</div>' +
                '</li>';
            }).join('');
        }).catch(function() {
            document.getElementById('recentAlarmList').innerHTML = '<li class="list-group-item text-center text-muted py-4">加载失败</li>';
        });
    };

    // Load device online/offline status list
    window.loadDeviceStatus = function() {
        apiRequest('/api/devices').then(function(data) {
            const list = document.getElementById('deviceStatusList');
            const devices = data.devices || [];
            if (!devices.length) {
                list.innerHTML = '<li class="list-group-item text-center text-muted py-4">暂无设备</li>';
                return;
            }
            list.innerHTML = devices.map(function(d) {
                const channels = d.channels || [];
                const onlineCount = channels.filter(function(c) { return c.online; }).length;
                const totalCount = channels.length;
                const statusClass = totalCount > 0 && onlineCount === totalCount ? 'device-status-online' : (onlineCount > 0 ? 'device-status-partial' : 'device-status-offline');
                const statusText = totalCount > 0 && onlineCount === totalCount ? '在线' : (onlineCount > 0 ? '部分离线' : '离线');
                const badgeClass = totalCount > 0 && onlineCount === totalCount ? 'bg-success' : (onlineCount > 0 ? 'bg-warning text-dark' : 'bg-danger');

                return '<li class="list-group-item ' + statusClass + ' d-flex justify-content-between align-items-center">' +
                    '<div class="d-flex align-items-center gap-2">' +
                        '<i class="bi bi-hdd-rack"></i>' +
                        '<div>' +
                            '<div class="fw-medium">' + (d.name || '未命名设备') + '</div>' +
                            '<small class="text-muted">ID: ' + (d.id || '-') + '</small>' +
                        '</div>' +
                    '</div>' +
                    '<div class="text-end">' +
                        '<span class="badge ' + badgeClass + ' me-2">' + statusText + '</span>' +
                        '<small class="text-muted">' + onlineCount + '/' + totalCount + ' 通道</small>' +
                    '</div>' +
                '</li>';
            }).join('');
        }).catch(function() {
            document.getElementById('deviceStatusList').innerHTML = '<li class="list-group-item text-center text-muted py-4">加载失败</li>';
        });
    };

    // Initialize Chart.js trend chart
    window.initTrendChart = function() {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;

        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';
        const textColor = isDark ? '#e0e0e0' : '#666';

        trendChart = new Chart(ctx, {
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

        loadTrendData('24h');

        const periodSelect = document.getElementById('chartPeriod');
        if (periodSelect) {
            periodSelect.addEventListener('change', function() {
                loadTrendData(this.value);
            });
        }
    };

    function loadTrendData(period) {
        apiRequest('/api/data/history?period=' + period + '&aggregate=1').then(function(data) {
            const labels = data.labels || [];
            const values = data.values || [];
            if (trendChart) {
                trendChart.data.labels = labels;
                trendChart.data.datasets[0].data = values;
                trendChart.update();
            }
        }).catch(function() {});
    }

    // SSE connection for real-time updates
    function initSSE() {
        if (!window.EventSource) return;
        if (sseSource) {
            sseSource.close();
        }
        sseSource = new EventSource('/api/stream/events');
        sseSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'data_point' || data.type === 'new_data') {
                    loadRecentData();
                    loadStats();
                } else if (data.type === 'alarm') {
                    loadAlarms();
                    loadStats();
                }
            } catch (e) {
                // ignore parse errors
            }
        };
        sseSource.onerror = function() {
            const badge = document.getElementById('sseStatus');
            if (badge) {
                badge.className = 'badge bg-secondary';
                badge.innerHTML = '<i class="bi bi-broadcast"></i> 连接断开';
            }
        };
        sseSource.onopen = function() {
            const badge = document.getElementById('sseStatus');
            if (badge) {
                badge.className = 'badge bg-success';
                badge.innerHTML = '<i class="bi bi-broadcast"></i> 实时连接中';
            }
        };
    }

    // Auto-refresh every 5 seconds
    function startAutoRefresh() {
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(function() {
            loadStats();
            loadRecentData();
            loadAlarms();
            loadDeviceStatus();
        }, 5000);
    }

    // Theme change observer for chart
    function initThemeObserver() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'data-bs-theme') {
                    const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
                    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';
                    const textColor = isDark ? '#e0e0e0' : '#666';
                    if (trendChart) {
                        trendChart.options.scales.x.grid.color = gridColor;
                        trendChart.options.scales.x.ticks.color = textColor;
                        trendChart.options.scales.y.grid.color = gridColor;
                        trendChart.options.scales.y.ticks.color = textColor;
                        trendChart.options.plugins.legend.labels.color = textColor;
                        trendChart.update();
                    }
                }
            });
        });
        observer.observe(document.documentElement, { attributes: true });
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        loadStats();
        loadRecentData();
        loadAlarms();
        loadDeviceStatus();
        initTrendChart();
        initSSE();
        startAutoRefresh();
        initThemeObserver();
    });
})();
