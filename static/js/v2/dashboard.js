/**
 * Dashboard V2 - IoT Data Platform
 * 现代化仪表盘 - 数据可视化 + 快捷操作
 * ID与templates/dashboard_v2.html严格对齐
 */

class DashboardV2 {
    constructor() {
        this.charts = {};
        this.refreshInterval = null;
        this.init();
    }

    async init() {
        console.log('[Dashboard] Initializing...');

        try {
            await Promise.all([
                this.loadStats(),
                this.loadTrend(),
                this.loadDeviceDistribution(),
                this.loadRecentAlarms(),
                this.loadDeviceList(),
                this.loadSystemInfo()
            ]);

            this.startAutoRefresh();
            console.log('[Dashboard] Initialized successfully');
        } catch (error) {
            console.error('[Dashboard] Initialization error:', error);
        }
    }

    async loadStats() {
        try {
            const response = await apiRequest('/api/dashboard/stats', 'GET');
            if (response && response.success && response.data) {
                const d = response.data;
                this.updateStatsCards({
                    total_devices: d.devices ? d.devices.total : (d.total_devices || 0),
                    online_devices: d.devices ? d.devices.online : (d.online_devices || 0),
                    offline_devices: d.devices ? d.devices.offline : (d.offline_devices || 0),
                    online_rate: d.devices ? d.devices.online_rate : (d.online_rate || 0),
                    total_alarms: d.alarms ? d.alarms.today : (d.total_alarms || 0),
                    unhandled_alarms: d.alarms ? d.alarms.unread : (d.unhandled_alarms || 0),
                    data_points_today: d.data_points ? d.data_points.today : (d.data_points_today || 0),
                    data_points_total: d.data_points ? d.data_points.total : (d.data_points_total || 0)
                });
            } else {
                this.setDefaultStats();
            }
        } catch (error) {
            console.error('[Dashboard] Stats load error:', error);
            this.setDefaultStats();
        }
    }

    setDefaultStats() {
        const defaults = {
            total_devices: 0, online_devices: 0, offline_devices: 0,
            online_rate: 0, total_alarms: 0, unhandled_alarms: 0,
            data_points_today: 0, data_points_total: 0
        };
        this.updateStatsCards(defaults);
    }

    updateStatsCards(data) {
        // 与HTML id严格对应
        const setText = (id, val, suffix = '') => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = (val !== undefined && val !== null) ? val + suffix : '--';
            }
        };

        setText('totalDevices', data.total_devices);
        setText('onlineDevices', data.online_devices);
        setText('totalDataPoints', data.data_points_today);
        setText('activeAlarms', data.unhandled_alarms || data.total_alarms);

        // 在线率
        const rateEl = document.getElementById('onlineRateValue');
        if (rateEl) {
            rateEl.textContent = (data.online_rate !== undefined ? data.online_rate : 0) + '%';
        }
    }

    async loadTrend() {
        try {
            const response = await apiRequest('/api/dashboard/trend?hours=24', 'GET');
            if (response && response.success && response.data) {
                this.renderTrendChart(response.data);
            } else {
                this.renderEmptyTrendChart();
            }
        } catch (error) {
            console.error('[Dashboard] Trend load error:', error);
            this.renderEmptyTrendChart();
        }
    }

    renderTrendChart(data) {
        const chartDom = document.getElementById('trendChart');
        if (!chartDom) return;

        if (this.charts.trend) this.charts.trend.dispose();
        this.charts.trend = echarts.init(chartDom);

        const option = {
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                borderColor: '#334155',
                textStyle: { color: '#e2e8f0' }
            },
            legend: {
                data: ['数据点', '告警数'],
                textStyle: { color: '#94a3b8' },
                top: 10
            },
            grid: { left: '3%', right: '4%', bottom: '8%', top: '15%', containLabel: true },
            xAxis: {
                type: 'category', boundaryGap: false,
                data: data.timestamps || data.hours || [],
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b', rotate: 30 }
            },
            yAxis: [
                {
                    type: 'value', name: '数据点',
                    axisLine: { lineStyle: { color: '#334155' } },
                    axisLabel: { color: '#64748b' },
                    splitLine: { lineStyle: { color: '#1e293b' } }
                },
                {
                    type: 'value', name: '告警数',
                    axisLine: { lineStyle: { color: '#334155' } },
                    axisLabel: { color: '#64748b' },
                    splitLine: { show: false }
                }
            ],
            series: [
                {
                    name: '数据点', type: 'line', smooth: true,
                    data: data.data_points || data.values || [],
                    lineStyle: { color: '#3b82f6', width: 2 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                            { offset: 1, color: 'rgba(59, 130, 246, 0)' }
                        ])
                    },
                    itemStyle: { color: '#3b82f6' }
                },
                {
                    name: '告警数', type: 'line', smooth: true, yAxisIndex: 1,
                    data: data.alarms || [],
                    lineStyle: { color: '#ef4444', width: 2 },
                    itemStyle: { color: '#ef4444' }
                }
            ]
        };

        this.charts.trend.setOption(option);
    }

    renderEmptyTrendChart() {
        const chartDom = document.getElementById('trendChart');
        if (!chartDom) return;
        if (this.charts.trend) this.charts.trend.dispose();
        this.charts.trend = echarts.init(chartDom);

        this.charts.trend.setOption({
            title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#64748b', fontSize: 14 } },
            xAxis: { show: false }, yAxis: { show: false },
            series: []
        });
    }

    async loadDeviceDistribution() {
        try {
            const response = await apiRequest('/api/dashboard/device-distribution', 'GET');
            if (response && response.success && response.data) {
                this.renderDeviceDistribution(response.data);
            } else {
                this.renderEmptyPieChart();
            }
        } catch (error) {
            console.error('[Dashboard] Distribution load error:', error);
            this.renderEmptyPieChart();
        }
    }

    renderDeviceDistribution(data) {
        const chartDom = document.getElementById('statusPieChart');
        if (!chartDom) return;

        if (this.charts.pie) this.charts.pie.dispose();
        this.charts.pie = echarts.init(chartDom);

        // 优先使用地域分布
        const dist = data.by_region && data.by_region.length > 0
            ? data.by_region
            : (data.by_status || []);

        const option = {
            tooltip: {
                trigger: 'item',
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                borderColor: '#334155',
                textStyle: { color: '#e2e8f0' }
            },
            legend: {
                orient: 'vertical',
                right: 10,
                top: 'center',
                textStyle: { color: '#94a3b8', fontSize: 11 }
            },
            series: [{
                name: '设备分布',
                type: 'pie',
                radius: ['45%', '70%'],
                center: ['38%', '50%'],
                avoidLabelOverlap: true,
                itemStyle: { borderRadius: 4, borderColor: '#1e293b', borderWidth: 2 },
                label: { show: false, position: 'center' },
                emphasis: {
                    label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' }
                },
                labelLine: { show: false },
                data: dist,
                color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316']
            }]
        };

        this.charts.pie.setOption(option);
    }

    renderEmptyPieChart() {
        const chartDom = document.getElementById('statusPieChart');
        if (!chartDom) return;
        if (this.charts.pie) this.charts.pie.dispose();
        this.charts.pie = echarts.init(chartDom);

        this.charts.pie.setOption({
            title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#64748b', fontSize: 14 } },
            series: []
        });
    }

    async loadRecentAlarms() {
        try {
            const response = await apiRequest('/api/dashboard/recent-alarms?limit=5', 'GET');
            if (response && response.success && response.data) {
                this.renderRecentAlarms(response.data);
            } else {
                this.renderEmptyAlarms();
            }
        } catch (error) {
            console.error('[Dashboard] Alarms load error:', error);
            this.renderEmptyAlarms();
        }
    }

    renderRecentAlarms(alarms) {
        // HTML中tbody的id就是recentAlarmsTable
        const tbody = document.getElementById('recentAlarmsTable');
        if (!tbody) return;

        if (!alarms || alarms.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">暂无告警信息</td></tr>';
            return;
        }

        const levelLabels = { critical: '严重', warning: '警告', info: '信息' };
        const levelBadges = {
            critical: '<span class="badge bg-danger">严重</span>',
            warning: '<span class="badge bg-warning text-dark">警告</span>',
            info: '<span class="badge bg-info">信息</span>'
        };

        tbody.innerHTML = alarms.map(a => {
            const sev = a.severity || 'info';
            return `
                <tr>
                    <td>${levelBadges[sev] || `<span class="badge bg-secondary">${sev}</span>`}</td>
                    <td>${this.escapeHtml(a.device_name || '-')}</td>
                    <td><span class="text-muted small">${this.escapeHtml(a.message || '-')}</span></td>
                    <td><span class="text-muted small">${this.formatTime(a.created_at)}</span></td>
                </tr>
            `;
        }).join('');
    }

    renderEmptyAlarms() {
        const tbody = document.getElementById('recentAlarmsTable');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">暂无告警</td></tr>';
        }
    }

    async loadDeviceList() {
        try {
            const response = await apiRequest('/api/dashboard/active-devices?limit=5', 'GET');
            if (response && response.success && response.data) {
                this.renderDeviceList(response.data);
            } else {
                this.renderEmptyDevices();
            }
        } catch (error) {
            console.error('[Dashboard] Device list error:', error);
            this.renderEmptyDevices();
        }
    }

    renderDeviceList(devices) {
        // HTML中tbody的id就是recentDevicesTable
        const tbody = document.getElementById('recentDevicesTable');
        if (!tbody) return;

        if (!devices || devices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">暂无活跃设备</td></tr>';
            return;
        }

        const typeLabels = {
            'temperature': '温度传感器',
            'humidity': '湿度传感器',
            'pressure': '压力传感器',
            'flow': '流量计',
            'electric': '电表'
        };

        tbody.innerHTML = devices.map(d => {
            const online = d.is_online || d.status === 'online';
            const typeLabel = typeLabels[d.device_type] || d.device_type || '-';
            return `
                <tr>
                    <td><span class="fw-semibold">${this.escapeHtml(d.name || d.device_name || '-')}</span></td>
                    <td><span class="text-muted">${typeLabel}</span></td>
                    <td>
                        <span class="badge ${online ? 'bg-success' : 'bg-secondary'}">
                            <i class="bi bi-circle-fill" style="font-size: 6px;"></i>
                            ${online ? '在线' : '离线'}
                        </span>
                    </td>
                    <td><span class="text-muted small">${this.formatTime(d.last_seen || d.last_data_time)}</span></td>
                    <td>
                        <a href="/devices/${d.id || d.device_id}" class="btn btn-sm btn-outline-primary">查看</a>
                    </td>
                </tr>
            `;
        }).join('');
    }

    renderEmptyDevices() {
        const tbody = document.getElementById('recentDevicesTable');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">暂无活跃设备</td></tr>';
        }
    }

    async loadSystemInfo() {
        try {
            const response = await apiRequest('/api/dashboard/system-info', 'GET');
            if (response && response.success && response.data) {
                this.renderSystemInfo(response.data);
            } else {
                this.renderDefaultSystemInfo();
            }
        } catch (error) {
            console.error('[Dashboard] System info error:', error);
            this.renderDefaultSystemInfo();
        }
    }

    renderSystemInfo(data) {
        // 运行时长
        const uptimeEl = document.getElementById('systemUptime');
        if (uptimeEl) {
            uptimeEl.textContent = data.uptime || data.uptime_human || '--';
        }

        // TCP连接
        const tcpEl = document.getElementById('tcpConnections');
        if (tcpEl) {
            tcpEl.textContent = data.tcp_connections !== undefined ? data.tcp_connections : '--';
        }

        // WS连接
        const wsEl = document.getElementById('wsConnections');
        if (wsEl) {
            wsEl.textContent = data.ws_connections !== undefined ? data.ws_connections : '--';
        }

        // CPU使用率（API返回cpu_percent，兼容cpu_usage）
        const cpu = data.cpu_percent !== undefined ? data.cpu_percent :
                    (data.cpu_usage !== undefined ? data.cpu_usage : 0);
        const cpuUsageEl = document.getElementById('cpuUsage');
        const cpuBarEl = document.getElementById('cpuBar');
        if (cpuUsageEl) cpuUsageEl.textContent = cpu + '%';
        if (cpuBarEl) cpuBarEl.style.width = cpu + '%';

        // 内存使用率（API返回mem_percent，兼容memory_usage）
        const mem = data.mem_percent !== undefined ? data.mem_percent :
                    (data.memory_usage !== undefined ? data.memory_usage : 0);
        const memUsageEl = document.getElementById('memUsage');
        const memBarEl = document.getElementById('memBar');
        if (memUsageEl) memUsageEl.textContent = mem + '%';
        if (memBarEl) memBarEl.style.width = mem + '%';
    }

    renderDefaultSystemInfo() {
        const setText = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setText('systemUptime', '--');
        setText('tcpConnections', '--');
        setText('wsConnections', '--');
        setText('cpuUsage', '--%');
        setText('memUsage', '--%');
        const cpuBar = document.getElementById('cpuBar');
        const memBar = document.getElementById('memBar');
        if (cpuBar) cpuBar.style.width = '0%';
        if (memBar) memBar.style.width = '0%';
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadStats();
            this.loadRecentAlarms();
            this.loadSystemInfo();
        }, 30000);
    }

    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    formatTime(t) {
        if (!t) return '-';
        try {
            const d = new Date(t);
            if (isNaN(d.getTime())) return t;
            const now = new Date();
            const diff = (now - d) / 1000; // 秒
            if (diff < 60) return '刚刚';
            if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
            if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
            if (diff < 604800) return Math.floor(diff / 86400) + '天前';
            return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return t;
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new DashboardV2();
});
