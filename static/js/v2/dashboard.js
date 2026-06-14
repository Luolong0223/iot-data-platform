/**
 * Dashboard V2 - IoT Data Platform
 * 现代化仪表盘 - 数据可视化 + 快捷操作
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
                this.loadRecentAlarms(),
                this.loadDeviceList()
            ]);
            
            this.startAutoRefresh();
            console.log('[Dashboard] Initialized successfully');
        } catch (error) {
            console.error('[Dashboard] Initialization error:', error);
        }
    }

    async loadStats() {
        try {
            const response = await apiRequest('/api/dashboard/stats');
            if (response && response.success && response.data) {
                const d = response.data;
                // API返回格式: {devices: {total, online, offline, online_rate}, data_points: {total, today}, alarms: {today, unread}, ...}
                this.updateStatsCards({
                    total_devices: d.devices ? d.devices.total : 0,
                    online_devices: d.devices ? d.devices.online : 0,
                    offline_devices: d.devices ? d.devices.offline : 0,
                    online_rate: d.devices ? d.devices.online_rate : 0,
                    total_alarms: d.alarms ? d.alarms.today : 0,
                    unhandled_alarms: d.alarms ? d.alarms.unread : 0,
                    active_rules: d.active_rules || 0,
                    data_points_today: d.data_points ? d.data_points.today : 0,
                    data_points_total: d.data_points ? d.data_points.total : 0
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
            active_rules: 0, data_points_today: 0, data_points_total: 0
        };
        this.updateStatsCards(defaults);
    }

    updateStatsCards(data) {
        const mappings = {
            'totalDevices': data.total_devices,
            'onlineDevices': data.online_devices,
            'offlineDevices': data.offline_devices,
            'totalAlarms': data.total_alarms,
            'unhandledAlarms': data.unhandled_alarms,
            'activeRules': data.active_rules,
            'dataPointsToday': data.data_points_today
        };

        Object.entries(mappings).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value !== undefined && value !== null ? value : '--';
            }
        });

        // 在线率
        const rateEl = document.getElementById('onlineRate');
        if (rateEl) {
            rateEl.textContent = data.online_rate !== undefined ? data.online_rate + '%' : '--%';
        }
    }

    async loadTrend() {
        try {
            const response = await apiRequest('/api/dashboard/trend?hours=24');
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
            grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
            xAxis: {
                type: 'category', boundaryGap: false,
                data: data.timestamps || [],
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
                    data: data.data_points || [],
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

    async loadRecentAlarms() {
        try {
            const response = await apiRequest('/api/dashboard/recent-alarms?limit=5');
            if (response && response.success && response.data) {
                this.renderRecentAlarms(response.data);
            } else {
                this.renderEmptyTable('recentAlarmsTable', '暂无告警');
            }
        } catch (error) {
            console.error('[Dashboard] Alarms load error:', error);
            this.renderEmptyTable('recentAlarmsTable', '暂无告警');
        }
    }

    renderRecentAlarms(alarms) {
        const tbody = document.querySelector('#recentAlarmsTable tbody');
        if (!tbody) return;

        if (!alarms || alarms.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted-foreground py-4">暂无告警信息</td></tr>';
            return;
        }

        const levelLabels = { critical: '严重', warning: '警告', info: '信息' };
        const levelClasses = { critical: 'text-red-400', warning: 'text-yellow-400', info: 'text-blue-400' };

        tbody.innerHTML = alarms.map(a => `
            <tr class="border-b border-border hover:bg-muted/30 transition-colors">
                <td class="py-2 px-3"><span class="${levelClasses[a.severity] || 'text-muted-foreground'}">${levelLabels[a.severity] || a.severity || '-'}</span></td>
                <td class="py-2 px-3 text-foreground">${a.device_name || '-'}</td>
                <td class="py-2 px-3 text-muted-foreground text-sm">${a.message || '-'}</td>
                <td class="py-2 px-3 text-muted-foreground text-sm">${a.created_at || '-'}</td>
            </tr>
        `).join('');
    }

    async loadDeviceList() {
        try {
            const response = await apiRequest('/api/dashboard/active-devices?limit=5');
            if (response && response.success && response.data) {
                this.renderDeviceList(response.data);
            } else {
                this.renderEmptyTable('deviceListTable', '暂无活跃设备');
            }
        } catch (error) {
            console.error('[Dashboard] Device list error:', error);
            this.renderEmptyTable('deviceListTable', '暂无活跃设备');
        }
    }

    renderDeviceList(devices) {
        const tbody = document.querySelector('#deviceListTable tbody');
        if (!tbody) return;

        if (!devices || devices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted-foreground py-4">暂无活跃设备</td></tr>';
            return;
        }

        tbody.innerHTML = devices.map(d => `
            <tr class="border-b border-border hover:bg-muted/30 transition-colors">
                <td class="py-2 px-3 text-foreground">${d.name || '-'}</td>
                <td class="py-2 px-3 text-muted-foreground">${d.device_type || '-'}</td>
                <td class="py-2 px-3">
                    <span class="inline-flex items-center gap-1 ${d.is_online ? 'text-green-400' : 'text-red-400'}">
                        <span class="w-2 h-2 rounded-full ${d.is_online ? 'bg-green-400' : 'bg-red-400'}"></span>
                        ${d.is_online ? '在线' : '离线'}
                    </span>
                </td>
                <td class="py-2 px-3 text-muted-foreground text-sm">${d.last_data_time || d.last_seen_at || '-'}</td>
                <td class="py-2 px-3 text-muted-foreground">${d.data_count || 0}</td>
            </tr>
        `).join('');
    }

    renderEmptyTable(tableId, message) {
        const tbody = document.querySelector(`#${tableId} tbody`);
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted-foreground py-4">${message}</td></tr>`;
        }
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadStats();
            this.loadRecentAlarms();
        }, 30000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new DashboardV2();
});
