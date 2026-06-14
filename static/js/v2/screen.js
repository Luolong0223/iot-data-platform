/**
 * Screen V2 - IoT Data Platform
 * 数据大屏展示 - 全屏可视化
 */

class ScreenV2 {
    constructor() {
        this.charts = {};
        this.refreshInterval = null;
        this.init();
    }

    async init() {
        console.log('[Screen] Initializing...');
        
        try {
            // 并行加载所有数据
            await Promise.all([
                this.loadOverview(),
                this.loadDeviceStats(),
                this.loadAlarmTrend(),
                this.loadDataDistribution(),
                this.loadRealtimeData()
            ]);
            
            // 启动实时刷新（每10秒）
            this.startRealtimeRefresh();
            
            console.log('[Screen] Initialized successfully');
        } catch (error) {
            console.error('[Screen] Initialization error:', error);
            this.showError('加载失败，请刷新页面重试');
        }
    }

    // 加载概览数据
    async loadOverview() {
        try {
            const response = await apiRequest('/api/dashboard/stats');
            if (response && response.data) {
                this.updateOverview(response.data);
            } else {
                this.updateOverview({
                    total_devices: 0,
                    online_devices: 0,
                    total_alarms: 0,
                    data_points_today: 0
                });
            }
        } catch (error) {
            console.error('[Screen] Overview load error:', error);
        }
    }

    // 更新概览数据
    updateOverview(data) {
        const elements = {
            'screenTotalDevices': data.total_devices || 0,
            'screenOnlineDevices': data.online_devices || 0,
            'screenTotalAlarms': data.total_alarms || 0,
            'screenDataPoints': data.data_points_today || 0
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                this.animateNumber(el, value);
            }
        });

        // 更新在线率
        const onlineRate = document.getElementById('screenOnlineRate');
        if (onlineRate && data.total_devices > 0) {
            const rate = ((data.online_devices / data.total_devices) * 100).toFixed(1);
            onlineRate.textContent = rate + '%';
        }
    }

    // 数字动画
    animateNumber(element, targetValue) {
        const duration = 1000;
        const start = 0;
        const startTime = performance.now();
        
        const update = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            const currentValue = Math.floor(easeProgress * targetValue);
            
            element.textContent = currentValue.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };
        
        requestAnimationFrame(update);
    }

    // 加载设备统计
    async loadDeviceStats() {
        try {
            const response = await apiRequest('/api/devices?per_page=100');
            if (response && response.devices) {
                this.renderDevicePieChart(response.devices);
                this.renderDeviceStatusChart(response.devices);
            } else {
                this.renderEmptyDeviceCharts();
            }
        } catch (error) {
            console.error('[Screen] Device stats load error:', error);
            this.renderEmptyDeviceCharts();
        }
    }

    // 渲染设备类型饼图
    renderDevicePieChart(devices) {
        const chartDom = document.getElementById('deviceTypeChart');
        if (!chartDom) return;

        if (this.charts.deviceType) {
            this.charts.deviceType.dispose();
        }

        this.charts.deviceType = echarts.init(chartDom);

        // 统计设备类型
        const typeCount = {};
        devices.forEach(d => {
            const type = d.device_type || 'other';
            typeCount[type] = (typeCount[type] || 0) + 1;
        });

        const data = Object.entries(typeCount).map(([name, value]) => ({
            name: name,
            value: value
        }));

        const option = {
            tooltip: {
                trigger: 'item',
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                borderColor: '#334155',
                textStyle: { color: '#e2e8f0' },
                formatter: '{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                right: '5%',
                top: 'center',
                textStyle: { color: '#94a3b8' }
            },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['40%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#0f172a',
                    borderWidth: 2
                },
                label: { show: false },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold'
                    }
                },
                labelLine: { show: false },
                data: data.length > 0 ? data : [{ name: '暂无数据', value: 1 }],
                color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
            }]
        };

        this.charts.deviceType.setOption(option);
    }

    // 渲染设备状态图
    renderDeviceStatusChart(devices) {
        const chartDom = document.getElementById('deviceStatusChart');
        if (!chartDom) return;

        if (this.charts.deviceStatus) {
            this.charts.deviceStatus.dispose();
        }

        this.charts.deviceStatus = echarts.init(chartDom);

        const online = devices.filter(d => d.is_online).length;
        const offline = devices.length - online;

        const option = {
            tooltip: {
                trigger: 'item',
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                borderColor: '#334155',
                textStyle: { color: '#e2e8f0' }
            },
            series: [{
                type: 'pie',
                radius: ['55%', '75%'],
                center: ['50%', '50%'],
                itemStyle: {
                    borderRadius: 4,
                    borderColor: '#0f172a',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    position: 'center',
                    formatter: () => `${devices.length}`,
                    fontSize: 24,
                    fontWeight: 'bold',
                    color: '#fff'
                },
                data: [
                    { 
                        name: '在线', 
                        value: online, 
                        itemStyle: { color: '#10b981' } 
                    },
                    { 
                        name: '离线', 
                        value: offline, 
                        itemStyle: { color: '#374151' } 
                    }
                ]
            }]
        };

        this.charts.deviceStatus.setOption(option);
    }

    // 渲染空设备图表
    renderEmptyDeviceCharts() {
        this.renderEmptyChart('deviceTypeChart');
        this.renderEmptyChart('deviceStatusChart');
    }

    // 加载告警趋势
    async loadAlarmTrend() {
        try {
            const response = await apiRequest('/api/alarms/records?per_page=50');
            if (response && response.records) {
                this.renderAlarmTrendChart(response.records);
            } else {
                this.renderEmptyAlarmTrend();
            }
        } catch (error) {
            console.error('[Screen] Alarm trend load error:', error);
            this.renderEmptyAlarmTrend();
        }
    }

    // 渲染告警趋势图
    renderAlarmTrendChart(alarms) {
        const chartDom = document.getElementById('alarmTrendChart');
        if (!chartDom) return;

        if (this.charts.alarmTrend) {
            this.charts.alarmTrend.dispose();
        }

        this.charts.alarmTrend = echarts.init(chartDom);

        // 按小时统计告警
        const hourlyData = {};
        for (let i = 0; i < 24; i++) {
            hourlyData[i] = 0;
        }
        
        alarms.forEach(alarm => {
            try {
                const date = new Date(alarm.created_at || alarm.timestamp);
                const hour = date.getHours();
                hourlyData[hour]++;
            } catch (e) {}
        });

        const option = {
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                borderColor: '#334155',
                textStyle: { color: '#e2e8f0' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '10%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: Object.keys(hourlyData),
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { 
                    color: '#64748b',
                    formatter: v => v + ':00'
                }
            },
            yAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b' },
                splitLine: { lineStyle: { color: '#1e293b' } }
            },
            series: [{
                type: 'bar',
                data: Object.values(hourlyData),
                barWidth: '60%',
                itemStyle: {
                    borderRadius: [4, 4, 0, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#ef4444' },
                        { offset: 1, color: '#ef444480' }
                    ])
                }
            }]
        };

        this.charts.alarmTrend.setOption(option);
    }

    // 渲染空告警趋势
    renderEmptyAlarmTrend() {
        this.renderEmptyChart('alarmTrendChart');
    }

    // 加载数据分布
    async loadDataDistribution() {
        try {
            const response = await apiRequest('/api/data?limit=100');
            if (response && (response.data_points || response.data)) {
                const dataPoints = response.data_points || response.data;
                this.renderDataDistribution(dataPoints);
            } else {
                this.renderEmptyDataDist();
            }
        } catch (error) {
            console.error('[Screen] Data distribution load error:', error);
            this.renderEmptyDataDist();
        }
    }

    // 渲染数据分布图
    renderDataDistribution(dataPoints) {
        const chartDom = document.getElementById('dataDistChart');
        if (!chartDom) return;

        if (this.charts.dataDist) {
            this.charts.dataDist.dispose();
        }

        this.charts.dataDist = echarts.init(chartDom);

        // 统计数据值分布
        const values = dataPoints.map(d => parseFloat(d.value) || parseFloat(d.data_value) || 0);
        
        // 创建分布区间
        const ranges = ['<15', '15-20', '20-25', '25-30', '>30'];
        const counts = [0, 0, 0, 0, 0];
        
        values.forEach(v => {
            if (v < 15) counts[0]++;
            else if (v < 20) counts[1]++;
            else if (v < 25) counts[2]++;
            else if (v < 30) counts[3]++;
            else counts[4]++;
        });

        const option = {
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                borderColor: '#334155',
                textStyle: { color: '#e2e8f0' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '10%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: ranges,
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b' }
            },
            yAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b' },
                splitLine: { lineStyle: { color: '#1e293b' } }
            },
            series: [{
                type: 'bar',
                data: counts,
                barWidth: '50%',
                itemStyle: {
                    borderRadius: [4, 4, 0, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#3b82f6' },
                        { offset: 1, color: '#3b82f680' }
                    ])
                }
            }]
        };

        this.charts.dataDist.setOption(option);
    }

    // 渲染空数据分布
    renderEmptyDataDist() {
        this.renderEmptyChart('dataDistChart');
    }

    // 加载实时数据列表
    async loadRealtimeData() {
        try {
            const response = await apiRequest('/api/data?limit=10&order_by=desc');
            if (response && (response.data_points || response.data)) {
                this.renderRealtimeList(response.data_points || response.data);
            } else {
                this.renderEmptyRealtimeList();
            }
        } catch (error) {
            console.error('[Screen] Realtime data load error:', error);
            this.renderEmptyRealtimeList();
        }
    }

    // 渲染实时数据列表
    renderRealtimeList(dataPoints) {
        const container = document.getElementById('realtimeDataList');
        if (!container) return;

        if (!dataPoints || dataPoints.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-slate-500">暂无数据</div>';
            return;
        }

        container.innerHTML = dataPoints.map(dp => `
            <div class="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
                <div class="flex items-center gap-3">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span class="text-sm">${dp.name || dp.channel_name || '-'}</span>
                </div>
                <div class="flex items-center gap-4">
                    <span class="font-mono text-sm font-medium ${parseFloat(dp.value || dp.data_value || 0) > 25 ? 'text-red-400' : 'text-emerald-400'}">
                        ${(dp.value || dp.data_value || '--')}
                    </span>
                    <span class="text-xs text-slate-500 w-20">${this.formatTime(dp.timestamp || dp.created_at)}</span>
                </div>
            </div>
        `).join('');
    }

    // 渲染空实时数据列表
    renderEmptyRealtimeList() {
        const container = document.getElementById('realtimeDataList');
        if (container) {
            container.innerHTML = '<div class="text-center py-4 text-slate-500">暂无数据</div>';
        }
    }

    // 渲染空图表
    renderEmptyChart(chartId) {
        const chartDom = document.getElementById(chartId);
        if (!chartDom) return;

        if (this.charts[chartId]) {
            this.charts[chartId].dispose();
        }

        this.charts[chartId] = echarts.init(chartDom);
        
        this.charts[chartId].setOption({
            title: {
                text: '暂无数据',
                left: 'center',
                top: 'center',
                textStyle: { color: '#64748b', fontSize: 14 }
            },
            xAxis: { type: 'category', data: [] },
            yAxis: { type: 'value' },
            series: [{ type: 'bar', data: [] }]
        });
    }

    // 启动实时刷新
    startRealtimeRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(() => {
            this.loadOverview();
            this.loadRealtimeData();
        }, 10000); // 10秒刷新一次
    }

    // 停止刷新
    stopRealtimeRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // 格式化时间
    formatTime(timeStr) {
        if (!timeStr) return '--';
        try {
            const date = new Date(timeStr);
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch (e) {
            return timeStr;
        }
    }

    // 显示错误
    showError(message) {
        const container = document.getElementById('screenContent');
        if (container) {
            container.innerHTML = `
                <div class="flex items-center justify-center h-screen">
                    <div class="text-center">
                        <i class="fas fa-exclamation-triangle text-6xl text-red-500 mb-4"></i>
                        <h3 class="text-2xl font-bold text-white mb-2">加载失败</h3>
                        <p class="text-slate-400 mb-6">${message}</p>
                        <button onclick="location.reload()" class="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-lg">
                            刷新页面
                        </button>
                    </div>
                </div>
            `;
        }
    }

    // 销毁实例
    destroy() {
        this.stopRealtimeRefresh();
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.dispose();
        });
        this.charts = {};
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.screenV2 = new ScreenV2();
});

// 窗口大小变化时重新渲染图表
window.addEventListener('resize', () => {
    if (window.screenV2) {
        Object.values(window.screenV2.charts).forEach(chart => {
            if (chart) chart.resize();
        });
    }
});
