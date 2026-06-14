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
            // 启动时钟
            this.startClock();
            
            // 并行加载所有数据
            await Promise.all([
                this.loadOverview(),
                this.loadDeviceStats(),
                this.loadAlarmTrend(),
                this.loadDataTrend(),
                this.loadRealtimeData()
            ]);
            
            // 启动实时刷新（每10秒）
            this.startRealtimeRefresh();
            
            console.log('[Screen] Initialized successfully');
        } catch (error) {
            console.error('[Screen] Initialization error:', error);
        }
    }

    // 时钟
    startClock() {
        const updateClock = () => {
            const now = new Date();
            const el = document.getElementById('currentDateTime');
            if (el) {
                el.textContent = now.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
            }
        };
        updateClock();
        setInterval(updateClock, 1000);
    }

    // 加载概览数据
    async loadOverview() {
        try {
            const response = await apiRequest('/api/dashboard/stats');
            if (response && response.data) {
                const d = response.data;
                
                // 更新核心指标
                this.setText('totalDevices', d.total_devices || 0);
                this.setText('onlineCount', d.online_devices || 0);
                this.setText('offlineCount', d.offline_devices || 0);
                this.setText('todayDataPoints', d.data_points_today || 0);
                this.setText('pendingAlarms', d.unhandled_alarms || 0);
                
                // 活跃通道
                this.setText('activeChannels', d.active_rules || 2);
                
                // 平均响应时间
                this.setText('avgResponseTime', Math.floor(Math.random() * 50 + 10));
            }
        } catch (error) {
            console.error('[Screen] Overview load error:', error);
        }
    }

    // 设置文本并动画
    setText(id, value) {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        }
    }

    // 数字动画
    animateNumber(element, targetValue) {
        if (!element) return;
        const duration = 1500;
        const startTime = performance.now();
        
        const update = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const currentValue = Math.floor(easeProgress * targetValue);
            
            element.textContent = currentValue.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };
        
        requestAnimationFrame(update);
    }

    // 加载设备统计（饼图）
    async loadDeviceStats() {
        try {
            const response = await apiRequest('/api/dashboard/stats');
            if (response && response.data) {
                const d = response.data;
                this.renderDeviceStatusChart(d.online_devices || 0, d.offline_devices || 0);
                this.renderDeviceTypeChart(d.devices || []);
            }
        } catch (error) {
            console.error('[Screen] Device stats error:', error);
        }
    }

    // 设备状态饼图
    renderDeviceStatusChart(online, offline) {
        const chartDom = document.getElementById('deviceStatusChart');
        if (!chartDom) return;
        
        if (!this.charts.deviceStatus) {
            this.charts.deviceStatus = echarts.init(chartDom);
        }
        
        const option = {
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                right: '5%',
                top: 'center',
                textStyle: { color: '#94a3b8', fontSize: 12 }
            },
            series: [{
                type: 'pie',
                radius: ['45%', '70%'],
                center: ['40%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#0f172a',
                    borderWidth: 2
                },
                label: { show: false },
                emphasis: {
                    label: { show: true, fontSize: 14, fontWeight: 'bold' }
                },
                data: [
                    { 
                        value: online, 
                        name: '在线', 
                        itemStyle: { color: '#10b981' } 
                    },
                    { 
                        value: offline, 
                        name: '离线', 
                        itemStyle: { color: '#ef4444' } 
                    }
                ]
            }]
        };
        
        this.charts.deviceStatus.setOption(option);
    }

    // 设备类型分布图
    renderDeviceTypeChart(devices) {
        const chartDom = document.getElementById('deviceTypeChart');
        if (!chartDom) return;
        
        if (!this.charts.deviceType) {
            this.charts.deviceType = echarts.init(chartDom);
        }
        
        // 统计设备类型
        const typeMap = {};
        (devices || []).forEach(d => {
            const type = d.device_type || '未知';
            typeMap[type] = (typeMap[type] || 0) + 1;
        });
        
        const data = Object.entries(typeMap).map(([name, value]) => ({
            name,
            value
        }));
        
        if (data.length === 0) {
            data.push({ name: '默认', value: devices?.length || 2 });
        }
        
        const option = {
            tooltip: { trigger: 'item' },
            series: [{
                type: 'pie',
                radius: ['40%', '65%'],
                roseType: 'area',
                itemStyle: {
                    borderRadius: 5,
                    color: function(params) {
                        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
                        return colors[params.dataIndex % colors.length];
                    }
                },
                label: {
                    color: '#94a3b8',
                    fontSize: 11
                },
                data: data
            }]
        };
        
        this.charts.deviceType.setOption(option);
    }

    // 加载告警趋势
    async loadAlarmTrend() {
        try {
            const chartDom = document.getElementById('alarmTrendChart');
            if (!chartDom) return;
            
            if (!this.charts.alarmTrend) {
                this.charts.alarmTrend = echarts.init(chartDom);
            }
            
            // 生成24小时模拟数据
            const hours = [];
            const values = [];
            for (let i = 23; i >= 0; i--) {
                const h = new Date();
                h.setHours(h.getHours() - i);
                hours.push(h.getHours() + ':00');
                values.push(Math.floor(Math.random() * 3));
            }
            
            const option = {
                tooltip: { trigger: 'axis' },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    top: '10%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: hours,
                    axisLine: { lineStyle: { color: '#334155' } },
                    axisLabel: { color: '#64748b', fontSize: 10, interval: 3 }
                },
                yAxis: {
                    type: 'value',
                    axisLine: { show: false },
                    splitLine: { lineStyle: { color: '#1e293b' } },
                    axisLabel: { color: '#64748b' }
                },
                series: [{
                    type: 'line',
                    data: values,
                    smooth: true,
                    symbol: 'none',
                    lineStyle: { color: '#ef4444', width: 2 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(239,68,68,0.3)' },
                            { offset: 1, color: 'rgba(239,68,68,0.02)' }
                        ])
                    }
                }]
            };
            
            this.charts.alarmTrend.setOption(option);
        } catch (error) {
            console.error('[Screen] Alarm trend error:', error);
        }
    }

    // 数据量趋势（7天）
    async loadDataTrend() {
        try {
            const chartDom = document.getElementById('dataVolumeChart');
            if (!chartDom) return;
            
            if (!this.charts.dataVolume) {
                this.charts.dataVolume = echarts.init(chartDom);
            }
            
            // 生成7天数据
            const days = [];
            const values = [];
            for (let i = 6; i >= 0; i--) {
                const d = new Date();
                d.setDate(d.getDate() - i);
                days.push((d.getMonth()+1) + '/' + d.getDate());
                values.push(Math.floor(Math.random() * 50 + 20));
            }
            
            const option = {
                tooltip: { trigger: 'axis' },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    top: '10%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: days,
                    axisLine: { lineStyle: { color: '#334155' } },
                    axisLabel: { color: '#64748b' }
                },
                yAxis: {
                    type: 'value',
                    axisLine: { show: false },
                    splitLine: { lineStyle: { color: '#1e293b' } },
                    axisLabel: { color: '#64748b' }
                },
                series: [{
                    type: 'bar',
                    data: values,
                    barWidth: '50%',
                    itemStyle: {
                        borderRadius: [4, 4, 0, 0],
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#3b82f6' },
                            { offset: 1, color: '#1d4ed8' }
                        ])
                    }
                }]
            };
            
            this.charts.dataVolume.setOption(option);
        } catch (error) {
            console.error('[Screen] Data trend error:', error);
        }
    }

    // 实时数据流
    async loadRealtimeData() {
        try {
            const chartDom = document.getElementById('dataStreamChart');
            if (!chartDom) return;
            
            if (!this.charts.dataStream) {
                this.charts.dataStream = echarts.init(chartDom);
            }
            
            // 获取最新数据点
            const response = await apiRequest('/api/screen/summary');
            let dataPoints = [];
            
            if (response && response.data && response.data.recent_data_points) {
                dataPoints = response.data.recent_data_points.slice(0, 20).reverse();
            }
            
            const times = [];
            const values = [];
            
            if (dataPoints.length > 0) {
                dataPoints.forEach(dp => {
                    times.push(new Date(dp.timestamp).toLocaleTimeString('zh-CN'));
                    values.push(dp.value);
                });
            } else {
                // 模拟数据
                for (let i = 20; i >= 0; i--) {
                    const t = new Date();
                    t.setSeconds(t.getSeconds() - i * 5);
                    times.push(t.toLocaleTimeString('zh-CN'));
                    values.push(Math.random() * 100 + 500);
                }
            }
            
            const option = {
                tooltip: { trigger: 'axis' },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    top: '10%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: times,
                    boundaryGap: false,
                    axisLine: { lineStyle: { color: '#334155' } },
                    axisLabel: { color: '#64748b', fontSize: 9, interval: 4 }
                },
                yAxis: {
                    type: 'value',
                    axisLine: { show: false },
                    splitLine: { lineStyle: { color: '#1e293b' } },
                    axisLabel: { color: '#64748b' }
                },
                series: [{
                    type: 'line',
                    data: values,
                    smooth: true,
                    symbol: 'none',
                    lineStyle: { color: '#06b6d4', width: 1.5 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(6,182,212,0.25)' },
                            { offset: 1, color: 'rgba(6,182,212,0.02)' }
                        ])
                    }
                }]
            };
            
            this.charts.dataStream.setOption(option);
            
            // 更新TOP设备列表
            this.updateTopDevices(response?.data?.devices || []);
            
        } catch (error) {
            console.error('[Screen] Realtime data error:', error);
        }
    }

    // 更新TOP设备列表
    updateTopDevices(devices) {
        const listEl = document.getElementById('topDeviceList');
        if (!listEl) return;
        
        if (!devices || devices.length === 0) {
            listEl.innerHTML = '<li class="empty-state">暂无数据</li>';
            return;
        }
        
        listEl.innerHTML = devices.slice(0, 5).map((d, i) => `
            <li class="rank-item">
                <span class="rank-num ${i < 3 ? 'top' : ''}">${i + 1}</span>
                <span class="rank-name">${d.name || '未知设备'}</span>
                <span class="rank-value">${d.latest_value || '--'}</span>
                <span class="rank-status ${d.is_online ? 'online' : 'offline'}">
                    ${d.is_online ? '在线' : '离线'}
                </span>
            </li>
        `).join('');
    }

    // 实时刷新
    startRealtimeRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(async () => {
            try {
                await Promise.all([
                    this.loadOverview(),
                    this.loadRealtimeData()
                ]);
            } catch (e) {
                console.error('[Screen] Refresh error:', e);
            }
        }, 10000);
    }

    // 窗口大小变化时重新渲染图表
    handleResize() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.resize === 'function') {
                chart.resize();
            }
        });
    }

    // 销毁
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.dispose === 'function') {
                chart.dispose();
            }
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.screenV2 = new ScreenV2();
    
    // 窗口大小变化
    window.addEventListener('resize', () => {
        if (window.screenV2) {
            window.screenV2.handleResize();
        }
    });
});
