/**
 * IoT Data Platform - Dashboard JavaScript
 * 增强版数据看板，支持实时数据流、图表、统计
 */

(function() {
    'use strict';

    // 全局变量
    let trendChart = null;
    let distributionChart = null;
    let realtimePaused = false;
    let dataStreamCount = 0;
    let lastMinuteCount = 0;
    let sseConnected = false;

    // 颜色配置
    const colors = {
        primary: '#0d6efd',
        success: '#198754',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#0dcaf0',
        secondary: '#6c757d'
    };

    // 初始化图表
    window.initCharts = function() {
        initTrendChart();
        initDistributionChart();
    };

    // 初始化趋势图
    function initTrendChart() {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;

        trendChart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '数据量',
                    data: [],
                    borderColor: colors.primary,
                    backgroundColor: colors.primary + '20',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxTicksLimit: 12 }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });

        // 加载初始数据
        updateTrendChart('24h');
    }

    // 初始化分布图
    function initDistributionChart() {
        const ctx = document.getElementById('distributionChart');
        if (!ctx) return;

        distributionChart = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['在线设备', '离线设备', '告警设备'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [colors.success, colors.danger, colors.warning],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 15, usePointStyle: true }
                    }
                },
                cutout: '60%'
            }
        });
    }

    // 加载看板统计数据
    window.loadDashboardStats = function() {
        apiRequest('/api/dashboard/stats').then(function(resp) {
            var data = resp.data || {};
            updateStatCards(data);
            // 从独立的alarms API获取最近报警
            apiRequest('/api/alarms/records?per_page=5').then(function(ar) {
                updateAlarmList(ar.records || []);
            }).catch(function() {});
            updateDistributionChart(data);
        }).catch(function(err) {
            console.error('加载统计数据失败:', err);
        });
    };

    // 更新统计卡片
    function updateStatCards(data) {
        var devices = data.devices || {};
        var dataPoints = data.data_points || {};
        var alarms = data.alarms || {};
        
        // 设备总数
        animateNumber('statDevices', devices.total || 0);
        
        // 在线率
        var totalD = devices.total || 0;
        var onlineD = devices.online || 0;
        var onlineRate = totalD > 0 ? Math.round(onlineD / totalD * 100) : 0;
        document.getElementById('statOnlineRate').textContent = onlineRate + '%';
        document.getElementById('statOnline').textContent = onlineD;
        document.getElementById('statTotal').textContent = totalD;
        
        // 今日数据
        animateNumber('statTodayData', dataPoints.today || 0, true);
        
        // 今日报警
        animateNumber('statTodayAlarms', alarms.today || 0);
        
        // 更新时间
        var updateEl = document.getElementById('lastUpdateTime');
        if (updateEl) {
            updateEl.innerHTML = '<i class="bi bi-clock"></i> ' + new Date().toLocaleTimeString();
        }
        
        // 更新设备状态列表
        updateDeviceStatusList();
    }

    // 数字动画
    function animateNumber(elementId, targetValue, format) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        const currentValue = parseInt(el.textContent.replace(/,/g, '')) || 0;
        const diff = targetValue - currentValue;
        const duration = 500;
        const steps = 20;
        const stepValue = diff / steps;
        const stepTime = duration / steps;
        
        let current = currentValue;
        let step = 0;
        
        const timer = setInterval(function() {
            step++;
            current += stepValue;
            
            if (step >= steps) {
                current = targetValue;
                clearInterval(timer);
            }
            
            el.textContent = format ? Math.round(current).toLocaleString() : Math.round(current);
        }, stepTime);
    }

    // 更新设备状态列表
    function updateDeviceStatusList() {
        apiRequest('/api/devices').then(function(resp) {
            var devices = resp.devices || [];
            var container = document.getElementById('deviceStatusList');
            if (!container) return;
            
            if (!devices.length) {
                container.innerHTML = '<div class="text-center text-muted py-4">暂无设备</div>';
                return;
            }

            var html = '';
            devices.slice(0, 6).forEach(function(device) {
                var statusClass = device.is_online ? 'online' : 'offline';
                var statusText = device.is_online ? '在线' : '离线';
                
                html += '<div class="device-status-item">' +
                    '<div class="device-status-dot ' + statusClass + '"></div>' +
                    '<div class="flex-grow-1">' +
                        '<div class="fw-bold">' + (device.name || '未命名') + '</div>' +
                        '<small class="text-muted">' + (device.channels_count || 0) + ' 通道</small>' +
                    '</div>' +
                    '<span class="badge bg-' + (device.is_online ? 'success' : 'secondary') + '">' + statusText + '</span>' +
                '</div>';
            });

            container.innerHTML = html;
        }).catch(function() {});
    }

    // 更新报警列表
    function updateAlarmList(alarms) {
        const container = document.getElementById('recentAlarmList');
        if (!container || !alarms.length) {
            if (container) container.innerHTML = '<div class="text-center text-muted py-4">暂无报警</div>';
            return;
        }

        let html = '';
        alarms.slice(0, 5).forEach(function(alarm) {
            const levelClass = alarm.level || 'info';
            const icon = alarm.level === 'critical' ? 'exclamation-triangle' : 
                        alarm.level === 'warning' ? 'exclamation-circle' : 'info-circle';
            
            html += `
                <div class="alarm-item ${levelClass}">
                    <div class="flex-grow-1">
                        <div class="fw-bold">${alarm.title || alarm.message}</div>
                        <small class="text-muted">${alarm.device_name || ''} • ${formatDateTime(alarm.timestamp)}</small>
                    </div>
                    <span class="badge bg-${levelClass === 'critical' ? 'danger' : levelClass === 'warning' ? 'warning' : 'info'}">
                        ${alarm.level === 'critical' ? '严重' : alarm.level === 'warning' ? '警告' : '提示'}
                    </span>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    // 更新分布图
    function updateDistributionChart(data) {
        if (!distributionChart) return;
        
        var devices = data.devices || {};
        var totalD = devices.total || 0;
        var onlineD = devices.online || 0;
        var offlineD = devices.offline || 0;
        
        distributionChart.data.datasets[0].data = [
            onlineD,
            offlineD,
            0
        ];
        distributionChart.update();
    }

    // 更新趋势图
    window.updateTrendChart = function(period) {
        if (!trendChart) return;
        
        var deviceId = document.getElementById('chartDevice')?.value || 'all';
        
        apiRequest('/api/dashboard/trend?period=' + (period || '24h') + '&device_id=' + deviceId)
            .then(function(resp) {
                var trendData = resp.data || [];
                var labels = [];
                var values = [];
                trendData.forEach(function(item) {
                    labels.push(item.time || item.hour || '');
                    values.push(item.count || 0);
                });
                if (!labels.length) return;
                
                trendChart.data.labels = labels;
                trendChart.data.datasets[0].data = values;
                trendChart.update();
            })
            .catch(function(err) {
                console.error('加载趋势数据失败:', err);
            });
    };

    // 加载设备选项
    window.loadDeviceOptions = function() {
        apiRequest('/api/devices').then(function(resp) {
            var devices = resp.devices || [];
            var select = document.getElementById('chartDevice');
            if (!select) return;
            
            select.innerHTML = '<option value="all">所有设备</option>';
            devices.forEach(function(device) {
                select.innerHTML += '<option value="' + device.id + '">' + device.name + '</option>';
            });
        });
    };

    // 启动SSE数据流
    window.startSSEStream = function() {
        const eventSource = new EventSource('/api/realtime/stream');
        
        eventSource.onopen = function() {
            sseConnected = true;
            $('#sseStatus').html('<i class="bi bi-broadcast"></i> 实时连接中')
                .removeClass('bg-danger bg-secondary').addClass('bg-success');
        };
        
        eventSource.onmessage = function(event) {
            if (realtimePaused) return;
            
            try {
                const msg = JSON.parse(event.data);
                
                if (msg.type === 'connected') {
                    console.log('SSE已连接:', msg.message);
                } else if (msg.type === 'heartbeat') {
                    // 心跳
                } else if (msg.type === 'history' && msg.data) {
                    processStreamData(msg.data, false);
                } else if (msg.type === 'new_data' && msg.data) {
                    processStreamData(msg.data, true);
                    dataStreamCount++;
                    updateStreamCount();
                } else if (msg.device_name) {
                    // 兼容旧格式
                    addDataItem(msg, true);
                    dataStreamCount++;
                    updateStreamCount();
                }
            } catch (e) {
                console.error('SSE解析错误:', e);
            }
        };
        
        eventSource.onerror = function() {
            sseConnected = false;
            $('#sseStatus').html('<i class="bi bi-broadcast"></i> 断开重连中')
                .removeClass('bg-success').addClass('bg-danger');
            
            setTimeout(function() {
                eventSource.close();
                startSSEStream();
            }, 5000);
        };
    };

    // 处理流数据
    function processStreamData(data, animate) {
        if (!data || !data.channels) return;
        
        const deviceName = data.device_name || '-';
        const timestamp = data.timestamp || new Date().toISOString();
        
        data.channels.forEach(function(channel) {
            const channelName = channel.name || '-';
            
            if (channel.data) {
                Object.keys(channel.data).forEach(function(key) {
                    const item = {
                        device_name: deviceName,
                        channel_name: channelName,
                        data_key: key,
                        data_value: channel.data[key],
                        timestamp: timestamp
                    };
                    
                    addDataItem(item, animate);
                });
            }
        });
    }

    // 添加数据项到列表
    function addDataItem(item, animate) {
        const container = document.getElementById('realtimeDataList');
        if (!container) return;
        
        // 清除"等待数据"提示
        if (container.querySelector('.text-muted')) {
            container.innerHTML = '';
        }
        
        const itemHtml = `
            <div class="data-stream-item ${animate ? 'new-item' : ''}">
                <div>
                    <span class="badge bg-primary bg-opacity-10 text-primary">${item.device_name}</span>
                    <span class="badge bg-secondary bg-opacity-10 text-secondary ms-1">${item.channel_name}</span>
                    <span class="text-muted ms-1">${item.data_key}</span>
                </div>
                <div>
                    <strong class="text-success">${formatNumber(item.data_value, 4)}</strong>
                    <small class="text-muted ms-2">${formatTime(item.timestamp)}</small>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('afterbegin', itemHtml);
        
        // 保持最多50条
        while (container.children.length > 50) {
            container.removeChild(container.lastChild);
        }
    }

    // 更新流计数
    function updateStreamCount() {
        const el = document.getElementById('streamCount');
        if (el) {
            el.textContent = dataStreamCount + ' 条/分钟';
        }
    }

    // 切换实时流暂停
    window.toggleRealtimeStream = function() {
        realtimePaused = !realtimePaused;
        const btn = document.getElementById('toggleStream');
        if (btn) {
            btn.innerHTML = realtimePaused 
                ? '<i class="bi bi-play-fill"></i>' 
                : '<i class="bi bi-pause-fill"></i>';
            btn.title = realtimePaused ? '继续' : '暂停';
        }
    };

    // 辅助函数
    function formatNumber(num, decimals) {
        if (num === null || num === undefined) return '-';
        return Number(num).toFixed(decimals || 2);
    }

    function formatTime(timestamp) {
        if (!timestamp) return '-';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function formatDateTime(timestamp) {
        if (!timestamp) return '-';
        const date = new Date(timestamp);
        return date.toLocaleString('zh-CN');
    }

    function apiRequest(url) {
        return fetch(url, { headers: { 'Accept': 'application/json' } })
            .then(function(response) {
                if (!response.ok) throw new Error('HTTP ' + response.status);
                return response.json();
            })
            .then(function(data) {
                if (data.success === false) throw new Error(data.message || '请求失败');
                return data;
            });
    }

    // 每分钟重置计数
    setInterval(function() {
        lastMinuteCount = dataStreamCount;
        dataStreamCount = 0;
    }, 60000);

})();
