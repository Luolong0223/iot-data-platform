/**
 * IoT Data Platform v2.0 - Dashboard JavaScript
 */

(function() {
    'use strict';
    
    // ========================================
    // Chart Instances
    // ========================================
    
    let trendChart = null;
    let statusPieChart = null;
    let refreshTimer = null;
    
    // ========================================
    // Initialize Dashboard
    // ========================================
    
    document.addEventListener('DOMContentLoaded', () => {
        initTrendChart();
        initStatusPieChart();
        loadDashboardData();
        
        // Auto refresh every 30 seconds
        refreshTimer = autoRefresh(loadDashboardData, 30000);
        
        // Time range change
        const timeRangeSelect = document.getElementById('timeRangeSelect');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', () => {
                loadDashboardData();
            });
        }
        
        // Chart type toggle
        document.querySelectorAll('[data-chart-type]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('[data-chart-type]').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                updateTrendChartType(e.target.dataset.chartType);
            });
        });
    });
    
    // ========================================
    // Load Dashboard Data
    // ========================================
    
    async function loadDashboardData() {
        try {
            const timeRange = document.getElementById('timeRangeSelect')?.value || '24h';
            
            // Load stats
            const [stats, trend, alarms, devices] = await Promise.all([
                apiRequest(`/api/dashboard/stats`),
                apiRequest(`/api/dashboard/trend?period=${timeRange}`),
                apiRequest('/api/alarms/records?per_page=5'),
                apiRequest('/api/devices?per_page=5')
            ]);
            
            updateStatsCards(stats);
            updateTrendChart(trend);
            updateAlarmsTable(alarms);
            updateDevicesTable(devices);
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }
    
    function refreshDashboard() {
        showLoading(document.querySelector('[onclick="refreshDashboard()"]'));
        loadDashboardData().finally(() => {
            hideLoading(document.querySelector('[onclick="refreshDashboard()"]'));
            showToast('数据已刷新', 'success');
        });
    }
    
    window.refreshDashboard = refreshDashboard;
    
    // ========================================
    // Update Stats Cards
    // ========================================
    
    function updateStatsCards(stats) {
        if (!stats) return;
        
        // Total Devices
        setAnimatedValue('totalDevices', stats.total_devices || 0);
        setChangeValue('deviceChange', stats.device_change || 0);
        
        // Online Devices
        setAnimatedValue('onlineDevices', stats.online_devices || 0);
        const onlineRate = stats.total_devices > 0 
            ? Math.round((stats.online_devices / stats.total_devices) * 100) 
            : 0;
        document.getElementById('onlineRateValue').textContent = `${onlineRate}%`;
        
        // Data Points
        setAnimatedValue('totalDataPoints', formatNumber(stats.total_data_points || 0, 0));
        setChangeValue('dataChange', stats.data_change || 0);
        
        // Active Alarms
        setAnimatedValue('activeAlarms', stats.active_alarms || 0);
        setChangeValue('alarmChange', -(stats.alarm_change || 0));
        
        // System Info
        if (stats.system) {
            document.getElementById('systemUptime').textContent = stats.system.uptime || '--';
            document.getElementById('tcpConnections').textContent = stats.system.tcp_connections || '0';
            document.getElementById('wsConnections').textContent = stats.system.ws_connections || '0';
            document.getElementById('cpuUsage').textContent = `${stats.system.cpu_usage || 0}%`;
            document.getElementById('memUsage').textContent = `${stats.system.memory_usage || 0}%`;
            
            setTimeout(() => {
                document.getElementById('cpuBar').style.width = `${stats.system.cpu_usage || 0}%`;
                document.getElementById('memBar').style.width = `${stats.system.memory_usage || 0}%`;
            }, 100);
        }
    }
    
    function setAnimatedValue(elementId, value) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        el.textContent = value;
        el.classList.add('animate-pulse');
        setTimeout(() => el.classList.remove('animate-pulse'), 500);
    }
    
    function setChangeValue(elementId, value) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        const isPositive = value >= 0;
        el.className = `stat-change ${isPositive ? 'up' : 'down'}`;
        el.innerHTML = `<i class="bi bi-arrow-${isPositive ? 'up' : 'down'}"></i> ${Math.abs(value)}%`;
    }
    
    // ========================================
    // Trend Chart
    // ========================================
    
    function initTrendChart() {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;
        
        trendChart = new echarts.init(ctx, null, { renderer: 'canvas' });
        
        const option = getTrendOption('line');
        trendChart.setOption(option);
        
        window.addEventListener('resize', () => trendChart.resize());
    }
    
    function getTrendOption(type) {
        return {
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#e5e7eb',
                textStyle: { color: '#374151' },
                axisPointer: { type: 'cross' }
            },
            legend: {
                data: ['数据点数', '告警数'],
                bottom: 0,
                textStyle: { color: '#6b7280' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                top: '10%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: [],
                axisLine: { lineStyle: { color: '#e5e7eb' } },
                axisLabel: { color: '#9ca3af' }
            },
            yAxis: [
                {
                    type: 'value',
                    name: '数据点',
                    nameTextStyle: { color: '#9ca3af' },
                    splitLine: { lineStyle: { color: '#f3f4f6' } },
                    axisLabel: { color: '#9ca3af' }
                },
                {
                    type: 'value',
                    name: '告警',
                    nameTextStyle: { color: '#9ca3af' },
                    splitLine: { show: false },
                    axisLabel: { color: '#9ca3af' }
                }
            ],
            series: [
                {
                    name: '数据点数',
                    type: type,
                    smooth: true,
                    symbol: 'none',
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(59, 130, 246, 0.25)' },
                            { offset: 1, color: 'rgba(59, 130, 246, 0.02)' }
                        ])
                    },
                    lineStyle: { width: 2, color: '#3b82f6' },
                    itemStyle: { color: '#3b82f6' },
                    data: []
                },
                {
                    name: '告警数',
                    type: type,
                    smooth: true,
                    symbol: 'none',
                    yAxisIndex: 1,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(239, 68, 68, 0.2)' },
                            { offset: 1, color: 'rgba(239, 68, 68, 0.02)' }
                        ])
                    },
                    lineStyle: { width: 2, color: '#ef4444' },
                    itemStyle: { color: '#ef4444' },
                    data: []
                }
            ]
        };
    }
    
    function updateTrendChart(data) {
        if (!trendChart || !data) return;
        
        const labels = data.labels || [];
        const values = data.values || [];
        const alarmValues = data.alarm_values || [];
        
        trendChart.setOption({
            xAxis: { data: labels },
            series: [
                { data: values },
                { data: alarmValues }
            ]
        });
    }
    
    function updateTrendChartType(type) {
        if (!trendChart) return;
        
        trendChart.setOption({
            series: trendChart.getOption().series.map(s => ({
                ...s,
                type: type
            }))
        });
    }
    
    // ========================================
    // Status Pie Chart
    // ========================================
    
    function initStatusPieChart() {
        const ctx = document.getElementById('statusPieChart');
        if (!ctx) return;
        
        statusPieChart = new echarts.init(ctx, null, { renderer: 'canvas' });
        
        statusPieChart.setOption({
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)'
            },
            legend: { show: false },
            series: [{
                type: 'pie',
                radius: ['55%', '75%'],
                center: ['50%', '50%'],
                avoidLabelOverlap: false,
                label: { show: false },
                emphasis: {
                    label: { show: true, fontSize: 14, fontWeight: 'bold' }
                },
                labelLine: { show: false },
                data: [],
                itemStyle: {
                    borderRadius: 8,
                    borderColor: 'var(--color-bg-card)',
                    borderWidth: 3
                },
                color: ['#22c55e', '#ef4444', '#f97316', '#94a3b8']
            }]
        });
        
        window.addEventListener('resize', () => statusPieChart.resize());
    }
    
    function updateStatusPieChart(data) {
        if (!statusPieChart || !data) return;
        
        statusPieChart.setOption({
            series: [{
                data: [
                    { value: data.online || 0, name: '在线' },
                    { value: data.offline || 0, name: '离线' },
                    { value: data.warning || 0, name: '告警' },
                    { value: data.unknown || 0, name: '未知' }
                ]
            }]
        });
        
        // Update legend
        const legendEl = document.getElementById('statusLegend');
        if (legendEl) {
            legendEl.innerHTML = `
                <div class="d-flex justify-content-around">
                    <div><span class="badge bg-success me-1"></span>在线 ${data.online || 0}</div>
                    <div><span class="badge bg-danger me-1"></span>离线 ${data.offline || 0}</div>
                    <div><span class="badge bg-warning me-1"></span>告警 ${data.warning || 0}</div>
                </div>
            `;
        }
    }
    
    // ========================================
    // Alarms Table
    // ========================================
    
    function updateAlarmsTable(data) {
        const tbody = document.getElementById('recentAlarmsTable');
        if (!tbody || !data || !data.records) return;
        
        if (data.records.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">暂无告警</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.records.map(alarm => {
            const severityClass = alarm.severity === 'critical' ? 'danger' 
                                  : alarm.severity === 'warning' ? 'warning' 
                                  : 'info';
            return `
                <tr>
                    <td><span class="badge badge-soft-${severityClass}">${getSeverityText(alarm.severity)}</span></td>
                    <td>${escapeHtml(alarm.device_name || '-')}</td>
                    <td class="text-truncate" style="max-width: 200px;">${escapeHtml(alarm.message || '-')}</td>
                    <td class="text-muted small">${formatDate(alarm.created_at, 'relative')}</td>
                </tr>
            `;
        }).join('');
    }
    
    function getSeverityText(severity) {
        const map = { critical: '严重', warning: '警告', info: '信息' };
        return map[severity] || severity;
    }
    
    // ========================================
    // Devices Table
    // ========================================
    
    function updateDevicesTable(data) {
        const tbody = document.getElementById('recentDevicesTable');
        if (!tbody || !data || !data.devices) return;
        
        if (data.devices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">暂无设备</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.devices.map(device => {
            const statusClass = device.is_online ? 'success' : 'secondary';
            const statusText = device.is_online ? '在线' : '离线';
            return `
                <tr>
                    <td>
                        <div class="d-flex align-items-center gap-2">
                            <i class="bi bi-cpu text-primary"></i>
                            ${escapeHtml(device.name)}
                        </div>
                    </td>
                    <td>${escapeHtml(device.device_type || '-')}</td>
                    <td><span class="badge badge-soft-${statusClass}">${statusText}</span></td>
                    <td class="text-muted small">${formatDate(device.last_data_at, 'relative')}</td>
                    <td>
                        <a href="/device/${device.id}" class="btn btn-sm btn-ghost">详情</a>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    // ========================================
    // Utility Functions
    // ========================================
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
})();
