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
            // 并行加载所有数据
            await Promise.all([
                this.loadStats(),
                this.loadTrend(),
                this.loadRecentAlarms(),
                this.loadDeviceList(),
                this.loadQuickActions()
            ]);
            
            // 启动自动刷新（每30秒）
            this.startAutoRefresh();
            
            console.log('[Dashboard] Initialized successfully');
        } catch (error) {
            console.error('[Dashboard] Initialization error:', error);
            this.showError('加载失败，请刷新页面重试');
        }
    }

    // 加载统计数据
    async loadStats() {
        try {
            const response = await apiRequest('/api/dashboard/stats');
            
            if (response && response.data) {
                this.updateStatsCards(response.data);
            } else {
                // 使用默认数据显示
                this.updateStatsCards({
                    total_devices: 0,
                    online_devices: 0,
                    offline_devices: 0,
                    total_alarms: 0,
                    unhandled_alarms: 0,
                    active_rules: 0,
                    data_points_today: 0
                });
            }
        } catch (error) {
            console.error('[Dashboard] Stats load error:', error);
            this.updateStatsCards({
                total_devices: '--',
                online_devices: '--',
                offline_devices: '--',
                total_alarms: '--',
                unhandled_alarms: '--',
                active_rules: '--',
                data_points_today: '--'
            });
        }
    }

    // 更新统计卡片
    updateStatsCards(data) {
        const cards = [
            { id: 'totalDevices', value: data.total_devices || 0, icon: 'device', label: '设备总数' },
            { id: 'onlineDevices', value: data.online_devices || 0, icon: 'wifi', label: '在线设备' },
            { id: 'offlineDevices', value: data.offline_devices || 0, icon: 'wifi-off', label: '离线设备' },
            { id: 'totalAlarms', value: data.total_alarms || 0, icon: 'alert', label: '告警总数' },
            { id: 'unhandledAlarms', value: data.unhandled_alarms || 0, icon: 'alert-circle', label: '未处理告警' },
            { id: 'activeRules', value: data.active_rules || 0, icon: 'settings', label: '活跃规则' },
            { id: 'dataPointsToday', value: data.data_points_today || 0, icon: 'database', label: '今日数据点' }
        ];

        cards.forEach(card => {
            const element = document.getElementById(card.id);
            if (element) {
                element.textContent = card.value;
                element.classList.add('animate-fade-in');
            }
        });
    }

    // 加载趋势数据
    async loadTrend() {
        try {
            const response = await apiRequest('/api/dashboard/trend?period=24h');
            
            if (response && response.data) {
                this.renderTrendChart(response.data);
            } else {
                this.renderEmptyTrendChart();
            }
        } catch (error) {
            console.error('[Dashboard] Trend load error:', error);
            this.renderEmptyTrendChart();
        }
    }

    // 渲染趋势图表
    renderTrendChart(data) {
        const chartDom = document.getElementById('trendChart');
        if (!chartDom) return;

        if (this.charts.trend) {
            this.charts.trend.dispose();
        }

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
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: data.timestamps || [],
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b' }
            },
            yAxis: [
                {
                    type: 'value',
                    name: '数据点',
                    axisLine: { lineStyle: { color: '#334155' } },
                    axisLabel: { color: '#64748b' },
                    splitLine: { lineStyle: { color: '#1e293b' } }
                },
                {
                    type: 'value',
                    name: '告警数',
                    axisLine: { lineStyle: { color: '#334155' } },
                    axisLabel: { color: '#64748b' },
                    splitLine: { show: false }
                }
            ],
            series: [
                {
                    name: '数据点',
                    type: 'line',
                    smooth: true,
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
                    name: '告警数',
                    type: 'line',
                    smooth: true,
                    yAxisIndex: 1,
                    data: data.alarms || [],
                    lineStyle: { color: '#ef4444', width: 2 },
                    itemStyle: { color: '#ef4444' }
                }
            ]
        };

        this.charts.trend.setOption(option);
    }

    // 渲染空趋势图表
    renderEmptyTrendChart() {
        const chartDom = document.getElementById('trendChart');
        if (!chartDom) return;

        if (this.charts.trend) {
            this.charts.trend.dispose();
        }

        this.charts.trend = echarts.init(chartDom);
        
        const option = {
            title: {
                text: '暂无数据',
                left: 'center',
                top: 'center',
                textStyle: { color: '#64748b', fontSize: 14 }
            },
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { type: 'category', data: [] },
            yAxis: { type: 'value' },
            series: [{ type: 'line', data: [] }]
        };

        this.charts.trend.setOption(option);
    }

    // 加载最近告警
    async loadRecentAlarms() {
        try {
            const response = await apiRequest('/api/alarms/records?per_page=5&status=active');
            
            if (response && response.records) {
                this.renderRecentAlarms(response.records);
            } else {
                this.renderEmptyAlarms();
            }
        } catch (error) {
            console.error('[Dashboard] Alarms load error:', error);
            this.renderEmptyAlarms();
        }
    }

    // 渲染最近告警列表
    renderRecentAlarms(alarms) {
        const container = document.getElementById('recentAlarmsList');
        if (!container) return;

        if (!alarms || alarms.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-slate-500">
                    <i class="fas fa-check-circle text-4xl mb-3 text-emerald-500"></i>
                    <p>暂无活跃告警</p>
                </div>
            `;
            return;
        }

        container.innerHTML = alarms.map(alarm => `
            <div class="alarm-item p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:border-slate-600 transition-all cursor-pointer mb-2" onclick="window.location.href='/alarms_v2'">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <span class="w-2 h-2 rounded-full ${this.getAlarmLevelColor(alarm.level)} animate-pulse"></span>
                        <span class="font-medium text-sm">${alarm.title || alarm.message || '未知告警'}</span>
                    </div>
                    <span class="text-xs text-slate-500">${this.formatTime(alarm.created_at || alarm.timestamp)}</span>
                </div>
                <div class="mt-2 text-xs text-slate-400 truncate">
                    设备: ${alarm.device_name || '-'} | 值: ${alarm.value || '-'}
                </div>
            </div>
        `).join('');
    }

    // 渲染空告警列表
    renderEmptyAlarms() {
        const container = document.getElementById('recentAlarmsList');
        if (!container) return;

        container.innerHTML = `
            <div class="text-center py-8 text-slate-500">
                <i class="fas fa-check-circle text-4xl mb-3 text-emerald-500"></i>
                <p>暂无活跃告警</p>
            </div>
        `;
    }

    // 加载设备列表
    async loadDeviceList() {
        try {
            const response = await apiRequest('/api/devices?per_page=6');
            
            if (response && response.devices) {
                this.renderDeviceList(response.devices);
            } else {
                this.renderEmptyDeviceList();
            }
        } catch (error) {
            console.error('[Dashboard] Devices load error:', error);
            this.renderEmptyDeviceList();
        }
    }

    // 渲染设备列表
    renderDeviceList(devices) {
        const container = document.getElementById('deviceListGrid');
        if (!container) return;

        if (!devices || devices.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12 text-slate-500">
                    <i class="fas fa-device text-4xl mb-3 opacity-50"></i>
                    <p>暂无设备，请先添加设备</p>
                    <a href="/devices_v2" class="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                        <i class="fas fa-plus"></i> 添加设备
                    </a>
                </div>
            `;
            return;
        }

        container.innerHTML = devices.map(device => `
            <div class="device-card p-4 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-blue-500/50 transition-all cursor-pointer group"
                 onclick="window.location.href='/devices_v2?id=${device.id}'">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg ${device.is_online ? 'bg-emerald-500/20' : 'bg-slate-700'} flex items-center justify-center">
                            <i class="fas fa-${this.getDeviceIcon(device.device_type)} ${device.is_online ? 'text-emerald-400' : 'text-slate-500'}"></i>
                        </div>
                        <div>
                            <h4 class="font-medium text-sm group-hover:text-blue-400 transition-colors">${device.name || '未命名设备'}</h4>
                            <p class="text-xs text-slate-500">${device.device_type || '-'}</p>
                        </div>
                    </div>
                    <span class="px-2 py-1 text-xs rounded-full ${device.is_online ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-500'}">
                        ${device.is_online ? '在线' : '离线'}
                    </span>
                </div>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div class="bg-slate-900/50 rounded p-2">
                        <span class="text-slate-500">最新值</span>
                        <p class="font-mono text-sm mt-1">${device.latest_value || '--'}</p>
                    </div>
                    <div class="bg-slate-900/50 rounded p-2">
                        <span class="text-slate-500">更新时间</span>
                        <p class="font-mono text-sm mt-1">${this.formatTime(device.last_update)}</p>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // 渲染空设备列表
    renderEmptyDeviceList() {
        const container = document.getElementById('deviceListGrid');
        if (!container) return;

        container.innerHTML = `
            <div class="col-span-full text-center py-12 text-slate-500">
                <i class="fas fa-device text-4xl mb-3 opacity-50"></i>
                <p>暂无设备，请先添加设备</p>
                <a href="/devices_v2" class="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    <i class="fas fa-plus"></i> 添加设备
                </a>
            </div>
        `;
    }

    // 加载快捷操作
    async loadQuickActions() {
        // 快捷操作按钮事件绑定
        const actionButtons = document.querySelectorAll('.quick-action-btn');
        actionButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const action = btn.dataset.action;
                this.handleQuickAction(action);
            });
        });
    }

    // 处理快捷操作
    handleQuickAction(action) {
        switch(action) {
            case 'add-device':
                window.location.href = '/devices_v2?action=add';
                break;
            case 'view-alarms':
                window.location.href = '/alarms_v2';
                break;
            case 'view-screen':
                window.location.href = '/screen_v2';
                break;
            case 'export-data':
                window.location.href = '/data_v2';
                break;
            default:
                console.log('[Dashboard] Unknown action:', action);
        }
    }

    // 启动自动刷新
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(() => {
            this.loadStats();
            this.loadRecentAlarms();
        }, 30000); // 30秒刷新一次
    }

    // 停止自动刷新
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // 获取告警级别颜色
    getAlarmLevelColor(level) {
        const colors = {
            'critical': 'bg-red-500',
            'warning': 'bg-yellow-500',
            'info': 'bg-blue-500',
            'default': 'bg-gray-500'
        };
        return colors[level] || colors['default'];
    }

    // 获取设备图标
    getDeviceIcon(type) {
        const icons = {
            'temperature': 'thermometer-half',
            'humidity': 'tint',
            'pressure': 'gauge-high',
            'light': 'lightbulb',
            'motion': 'walking',
            'door': 'door-closed',
            'sensor': 'microchip',
            'gateway': 'network-wired',
            'default': 'device'
        };
        return icons[type] || icons['default'];
    }

    // 格式化时间
    formatTime(timeStr) {
        if (!timeStr) return '--';
        
        try {
            const date = new Date(timeStr);
            const now = new Date();
            const diff = now - date;
            
            if (diff < 60000) return '刚刚';
            if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
            if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
            
            return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return timeStr;
        }
    }

    // 显示错误信息
    showError(message) {
        const container = document.getElementById('dashboardContent');
        if (container) {
            container.innerHTML = `
                <div class="flex items-center justify-center h-96">
                    <div class="text-center">
                        <i class="fas fa-exclamation-triangle text-6xl text-red-500 mb-4"></i>
                        <h3 class="text-xl font-semibold text-white mb-2">加载失败</h3>
                        <p class="text-slate-400 mb-4">${message}</p>
                        <button onclick="location.reload()" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                            刷新页面
                        </button>
                    </div>
                </div>
            `;
        }
    }

    // 销毁实例
    destroy() {
        this.stopAutoRefresh();
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.dispose();
        });
        this.charts = {};
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardV2 = new DashboardV2();
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (window.dashboardV2) {
        window.dashboardV2.destroy();
    }
});
