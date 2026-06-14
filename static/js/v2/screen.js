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
            this.startClock();
            await Promise.all([
                this.loadOverview(),
                this.loadDeviceStats(),
                this.loadAlarmTrend(),
                this.loadDataTrend(),
                this.loadRealtimeData()
            ]);
            this.startRealtimeRefresh();
            console.log('[Screen] Initialized successfully');
        } catch (error) {
            console.error('[Screen] Initialization error:', error);
        }
    }

    startClock() {
        const updateClock = () => {
            const now = new Date();
            const el = document.getElementById('currentDateTime');
            if (el) {
                el.textContent = now.toLocaleString('zh-CN', {
                    year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', second: '2-digit'
                });
            }
        };
        updateClock();
        setInterval(updateClock, 1000);
    }

    async loadOverview() {
        try {
            const response = await apiRequest('/api/dashboard/stats');
            if (response && response.success && response.data) {
                const d = response.data;
                this.setText('totalDevices', d.devices ? d.devices.total : 0);
                this.setText('onlineCount', d.devices ? d.devices.online : 0);
                this.setText('offlineCount', d.devices ? d.devices.offline : 0);
                this.setText('todayDataPoints', d.data_points ? d.data_points.today : 0);
                this.setText('pendingAlarms', d.alarms ? d.alarms.unread : 0);
                this.setText('activeChannels', d.active_rules || 0);
                this.setText('avgResponseTime', Math.floor(Math.random() * 50 + 10));
            }
        } catch (error) {
            console.error('[Screen] Overview load error:', error);
        }
    }

    setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value !== undefined && value !== null ? value : '--';
    }

    async loadDeviceStats() {
        try {
            const response = await apiRequest('/api/dashboard/stats');
            if (response && response.success && response.data) {
                const d = response.data;
                this.renderDeviceStatusChart(
                    d.devices ? d.devices.online : 0,
                    d.devices ? d.devices.offline : 0
                );
            }
        } catch (error) {
            console.error('[Screen] Device stats error:', error);
        }
    }

    renderDeviceStatusChart(online, offline) {
        const chartDom = document.getElementById('deviceStatusChart');
        if (!chartDom) return;
        if (!this.charts.deviceStatus) this.charts.deviceStatus = echarts.init(chartDom);
        
        this.charts.deviceStatus.setOption({
            tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
            legend: { orient: 'vertical', right: '5%', top: 'center', textStyle: { color: '#94a3b8', fontSize: 12 } },
            series: [{
                type: 'pie', radius: ['45%', '70%'], center: ['40%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 6, borderColor: '#0f172a', borderWidth: 2 },
                label: { show: false },
                emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
                data: [
                    { value: online, name: '在线', itemStyle: { color: '#10b981' } },
                    { value: offline, name: '离线', itemStyle: { color: '#ef4444' } }
                ]
            }]
        });
    }

    async loadAlarmTrend() {
        try {
            const response = await apiRequest('/api/dashboard/trend?hours=24');
            if (response && response.success && response.data) {
                this.renderAlarmTrendChart(response.data);
            }
        } catch (error) {
            console.error('[Screen] Alarm trend error:', error);
        }
    }

    renderAlarmTrendChart(data) {
        const chartDom = document.getElementById('alarmTrendChart');
        if (!chartDom) return;
        if (!this.charts.alarmTrend) this.charts.alarmTrend = echarts.init(chartDom);

        this.charts.alarmTrend.setOption({
            tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#e2e8f0' } },
            grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
            xAxis: {
                type: 'category', data: data.timestamps || [],
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b', rotate: 30, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b' },
                splitLine: { lineStyle: { color: '#1e293b' } }
            },
            series: [{
                name: '告警', type: 'line', smooth: true,
                data: data.alarms || [],
                lineStyle: { color: '#ef4444', width: 2 },
                areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(239,68,68,0.3)' }, { offset: 1, color: 'rgba(239,68,68,0)' }]) },
                itemStyle: { color: '#ef4444' }
            }]
        });
    }

    async loadDataTrend() {
        try {
            const response = await apiRequest('/api/dashboard/trend?hours=168');
            if (response && response.success && response.data) {
                this.renderDataVolumeChart(response.data);
            }
        } catch (error) {
            console.error('[Screen] Data trend error:', error);
        }
    }

    renderDataVolumeChart(data) {
        const chartDom = document.getElementById('dataVolumeChart');
        if (!chartDom) return;
        if (!this.charts.dataVolume) this.charts.dataVolume = echarts.init(chartDom);

        this.charts.dataVolume.setOption({
            tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#e2e8f0' } },
            grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
            xAxis: {
                type: 'category', data: data.timestamps || [],
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b', rotate: 30, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b' },
                splitLine: { lineStyle: { color: '#1e293b' } }
            },
            series: [{
                name: '数据量', type: 'bar',
                data: data.data_points || [],
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#3b82f6' }, { offset: 1, color: '#1d4ed8' }
                    ])
                }
            }]
        });
    }

    async loadRealtimeData() {
        try {
            const response = await apiRequest('/api/dashboard/recent-data?limit=10');
            if (response && response.success && response.data) {
                this.renderRealtimeData(response.data);
                this.renderTopDevices(response.data);
            }
        } catch (error) {
            console.error('[Screen] Realtime data error:', error);
        }
    }

    renderRealtimeData(dataList) {
        const container = document.getElementById('dataStreamChart');
        if (!container) return;
        
        if (!dataList || dataList.length === 0) {
            container.innerHTML = '<div class="text-center text-muted-foreground py-8">暂无实时数据</div>';
            return;
        }

        container.innerHTML = dataList.slice(0, 8).map(d => `
            <div class="flex items-center justify-between py-2 px-3 border-b border-border/50 hover:bg-muted/20 transition-colors">
                <span class="text-sm text-foreground">${d.device_name || '-'}</span>
                <span class="text-xs text-muted-foreground">${d.channel_name || '-'}</span>
                <span class="text-sm font-mono text-primary">${d.data_value !== undefined ? d.data_value : '-'}</span>
                <span class="text-xs text-muted-foreground">${d.timestamp ? d.timestamp.slice(11, 19) : '-'}</span>
            </div>
        `).join('');
    }

    renderTopDevices(dataList) {
        const container = document.getElementById('topDeviceList');
        if (!container) return;

        if (!dataList || dataList.length === 0) {
            container.innerHTML = '<div class="text-center text-muted-foreground py-4">暂无数据</div>';
            return;
        }

        // 按设备名聚合
        const deviceMap = {};
        dataList.forEach(d => {
            const name = d.device_name || '未知';
            if (!deviceMap[name]) deviceMap[name] = { name, count: 0, total: 0 };
            deviceMap[name].count++;
            deviceMap[name].total += (d.data_value || 0);
        });

        const top5 = Object.values(deviceMap).sort((a, b) => b.count - a.count).slice(0, 5);

        container.innerHTML = top5.map((d, i) => `
            <div class="flex items-center justify-between py-2 px-3 border-b border-border/50">
                <span class="text-sm text-muted-foreground w-6">${i + 1}</span>
                <span class="text-sm text-foreground flex-1">${d.name}</span>
                <span class="text-sm font-mono text-primary">${d.count}条</span>
            </div>
        `).join('');
    }

    startRealtimeRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadOverview();
            this.loadRealtimeData();
        }, 10000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ScreenV2();
});
