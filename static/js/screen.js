/**
 * IoT Data Platform - Screen JavaScript
 * 数据大屏实时展示
 */

(function() {
    'use strict';

    let eventSource = null;
    let trendChart = null;
    let dataBuffer = [];
    let dataRateBuffer = [];
    let lastMinute = null;
    let currentMinuteCount = 0;

    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        initClock();
        initTrendChart();
        loadDashboardStats();
        loadDeviceList();
        loadAlarmList();
        loadRankList();
        connectSSE();

        // Period change handler
        document.getElementById('chartPeriod').addEventListener('change', loadTrendData);

        // Refresh every 30 seconds
        setInterval(function() {
            loadDashboardStats();
            loadDeviceList();
        }, 30000);
    });

    // Clock
    function initClock() {
        function updateClock() {
            const now = new Date();
            document.getElementById('currentTime').textContent = now.toLocaleTimeString('zh-CN', { hour12: false });
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    // Trend chart
    function initTrendChart() {
        const ctx = document.getElementById('trendChart').getContext('2d');
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '数据量',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.2)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255,255,255,0.1)'
                        },
                        ticks: {
                            color: 'rgba(255,255,255,0.7)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255,255,255,0.1)'
                        },
                        ticks: {
                            color: 'rgba(255,255,255,0.7)'
                        }
                    }
                }
            }
        });
        loadTrendData();
    }

    // Load trend data
    function loadTrendData() {
        const period = document.getElementById('chartPeriod').value;
        apiRequest('/api/dashboard/trend?period=' + period).then(function(resp) {
            var trendData = resp.data || [];
            var labels = [];
            var values = [];
            trendData.forEach(function(item) {
                labels.push(item.time || item.hour || '');
                values.push(item.count || 0);
            });
            if (labels.length) {
                trendChart.data.labels = labels;
                trendChart.data.datasets[0].data = values;
                trendChart.update();
            }
        }).catch(function(err) {
            console.error('Load trend failed:', err);
        });
    }

    // Load dashboard stats
    function loadDashboardStats() {
        apiRequest('/api/dashboard/stats').then(function(resp) {
            var data = resp.data || {};
            var devices = data.devices || {};
            var dataPoints = data.data_points || {};
            var alarms = data.alarms || {};
            
            // Devices
            document.getElementById('statDevices').textContent = devices.total || 0;
            document.getElementById('statOnline').textContent = devices.online || 0;
            document.getElementById('statTotal').textContent = devices.total || 0;
            
            // Online rate
            var totalD = devices.total || 0;
            var onlineD = devices.online || 0;
            var rate = totalD > 0 ? Math.round((onlineD / totalD) * 100) : 0;
            document.getElementById('statOnlineRate').textContent = rate + '%';

            // Data count
            var dataCount = dataPoints.today || 0;
            document.getElementById('statData').textContent = formatNumber(dataCount);
            // dataRate is updated by SSE

            // Alarms
            document.getElementById('statAlarms').textContent = alarms.unread || 0;
        }).catch(function(err) {
            console.error('Load stats failed:', err);
        });
    }

    // Load device list
    function loadDeviceList() {
        apiRequest('/api/devices?limit=10').then(function(data) {
            const devices = data.devices || [];
            const container = document.getElementById('deviceList');

            if (devices.length === 0) {
                container.innerHTML = '<div class="text-center text-muted py-4">暂无设备</div>';
                return;
            }

            let html = '<div class="list-group list-group-flush">';
            devices.forEach(function(device) {
                const statusClass = device.is_online ? 'bg-success' : 'bg-danger';
                const statusText = device.is_online ? '在线' : '离线';
                const lastSeen = device.last_seen_at ? formatTimeAgo(device.last_seen_at) : '-';

                html += '<div class="list-group-item bg-transparent text-light border-0 d-flex justify-content-between align-items-center py-2">';
                html += '<div><span class="badge ' + statusClass + ' me-2">' + statusText + '</span>' + device.name + '</div>';
                html += '<small class="text-muted">' + lastSeen + '</small>';
                html += '</div>';
            });
            html += '</div>';

            container.innerHTML = html;
        }).catch(function(err) {
            console.error('Load devices failed:', err);
        });
    }

    // Load alarm list
    function loadAlarmList() {
        apiRequest('/api/alarms/records?per_page=5').then(function(data) {
            const records = data.records || [];
            const container = document.getElementById('alarmList');

            if (records.length === 0) {
                container.innerHTML = '<div class="text-center text-muted py-4">暂无报警</div>';
                return;
            }

            let html = '<div class="list-group list-group-flush">';
            records.forEach(function(record) {
                const levelClass = record.level === 'critical' ? 'bg-danger' : 
                                   record.level === 'warning' ? 'bg-warning' : 'bg-info';
                const time = formatTimeAgo(record.created_at);

                html += '<div class="list-group-item bg-transparent text-light border-0 py-2">';
                html += '<div class="d-flex justify-content-between">';
                html += '<div><span class="badge ' + levelClass + ' me-2">' + record.level + '</span>' + (record.message || '报警') + '</div>';
                html += '<small class="text-muted">' + time + '</small>';
                html += '</div></div>';
            });
            html += '</div>';

            container.innerHTML = html;
        }).catch(function(err) {
            console.error('Load alarms failed:', err);
        });
    }

    // Load rank list
    function loadRankList() {
        apiRequest('/api/dashboard/device-ranking?limit=5').then(function(resp) {
            const ranks = resp.data || [];
            const container = document.getElementById('rankList');

            if (ranks.length === 0) {
                container.innerHTML = '<div class="text-center text-muted py-4">暂无数据</div>';
                return;
            }

            const maxCount = Math.max(...ranks.map(function(r) { return r.count; }));

            let html = '<div class="p-3">';
            ranks.forEach(function(rank, index) {
                const percent = maxCount > 0 ? (rank.count / maxCount * 100) : 0;
                html += '<div class="mb-2">';
                html += '<div class="d-flex justify-content-between mb-1">';
                html += '<span>' + (index + 1) + '. ' + rank.device_name + '</span>';
                html += '<span class="text-muted">' + formatNumber(rank.count) + ' 条</span>';
                html += '</div>';
                html += '<div class="progress" style="height: 6px;">';
                html += '<div class="progress-bar" style="width: ' + percent + '%; background: linear-gradient(90deg, #3498db, #2ecc71);"></div>';
                html += '</div>';
                html += '</div>';
            });
            html += '</div>';

            container.innerHTML = html;
        }).catch(function(err) {
            console.error('Load rank failed:', err);
        });
    }

    // SSE connection
    function connectSSE() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource('/api/realtime/stream');

        eventSource.onopen = function() {
            document.getElementById('sseStatus').innerHTML = '<i class="bi bi-broadcast"></i> 实时连接中';
            document.getElementById('sseStatus').className = 'badge bg-success fs-6';
        };

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);

            // Track data rate
            const now = new Date();
            const currentMin = now.getMinutes();
            if (currentMin !== lastMinute) {
                if (lastMinute !== null) {
                    dataRateBuffer.push(currentMinuteCount);
                    if (dataRateBuffer.length > 10) dataRateBuffer.shift();
                }
                lastMinute = currentMin;
                currentMinuteCount = 0;
                updateDataRate();
            }
            currentMinuteCount++;

            // Add to stream
            addDataToStream(data);

            // Update stats
            loadDashboardStats();
        };

        eventSource.onerror = function(err) {
            console.error('SSE error:', err);
            document.getElementById('sseStatus').innerHTML = '<i class="bi bi-broadcast"></i> 连接断开';
            document.getElementById('sseStatus').className = 'badge bg-danger fs-6';
            
            // Reconnect after 5 seconds
            setTimeout(connectSSE, 5000);
        };
    }

    // Add data to stream display
    function addDataToStream(data) {
        const container = document.getElementById('dataStream');
        
        // Remove placeholder
        if (container.querySelector('.text-center')) {
            container.innerHTML = '';
        }

        const item = document.createElement('div');
        item.className = 'stream-item fade-in';

        const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        const deviceName = data.device_name || data.device?.name || '-';
        const channelName = data.channel_name || '-';
        const pointName = data.point_name || '-';
        const value = data.value !== undefined ? data.value.toFixed(4) : '-';

        item.innerHTML = '<div class="stream-time">' + time + '</div>' +
                        '<div class="stream-device">' + deviceName + '</div>' +
                        '<div class="stream-channel">' + channelName + '</div>' +
                        '<div class="stream-point">' + pointName + '</div>' +
                        '<div class="stream-value">' + value + '</div>';

        container.insertBefore(item, container.firstChild);

        // Keep only last 50 items
        while (container.children.length > 50) {
            container.removeChild(container.lastChild);
        }
    }

    // Update data rate display
    function updateDataRate() {
        if (dataRateBuffer.length > 0) {
            const avg = Math.round(dataRateBuffer.reduce(function(a, b) { return a + b; }, 0) / dataRateBuffer.length);
            document.getElementById('statRate').textContent = avg;
        }
    }

    // Helper functions
    function formatTimeAgo(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (diff < 60) return '刚刚';
        if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
        return Math.floor(diff / 86400) + '天前';
    }
})();
