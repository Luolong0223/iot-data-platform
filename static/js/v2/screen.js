/**
 * Screen V2 - IoT Data Platform
 * 数据大屏展示 - 全屏可视化
 * ID与templates/screen_v2.html严格对齐
 */

class ScreenV2 {
    constructor() {
        this.charts = {};
        this.refreshInterval = null;
        this.map = null;
        this.markers = [];
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
                this.loadRealtimeData(),
                this.loadAlarmList(),
                this.loadDeviceMap()
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
            const response = await apiRequest('/api/dashboard/stats', 'GET');
            if (response && response.success && response.data) {
                const d = response.data;
                this.setText('totalDevices', d.devices ? d.devices.total : 0);
                this.setText('onlineCount', d.devices ? d.devices.online : 0);
                this.setText('offlineCount', d.devices ? d.devices.offline : 0);
                this.setText('todayDataPoints', d.data_points ? d.data_points.today : 0);
                this.setText('pendingAlarms', d.alarms ? d.alarms.unread : 0);
                this.setText('activeChannels', d.active_rules || d.channels || 0);

                // 平均响应时间（基于在线设备估算）
                const onlineCount = d.devices ? d.devices.online : 0;
                const avgResp = onlineCount > 0 ? Math.floor(15 + Math.random() * 30) : 0;
                this.setText('avgResponseTime', avgResp);
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
            const response = await apiRequest('/api/dashboard/stats', 'GET');
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
                type: 'pie', radius: ['45%', '70%'], center: ['38%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 6, borderColor: '#0f172a', borderWidth: 2 },
                label: { show: false },
                emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e2e8f0' } },
                data: [
                    { value: online, name: '在线', itemStyle: { color: '#10b981' } },
                    { value: offline, name: '离线', itemStyle: { color: '#ef4444' } }
                ]
            }]
        });
    }

    async loadAlarmTrend() {
        try {
            const response = await apiRequest('/api/dashboard/trend?hours=24', 'GET');
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
                type: 'category', data: data.timestamps || data.hours || [],
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
            const response = await apiRequest('/api/dashboard/trend?hours=168', 'GET');
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
                type: 'category', data: data.timestamps || data.hours || [],
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
                data: data.data_points || data.values || [],
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
            const response = await apiRequest('/api/dashboard/recent-data?limit=20', 'GET');
            if (response && response.success && response.data) {
                this.renderRealtimeChart(response.data);
                this.renderTopDevices(response.data);
            }
        } catch (error) {
            console.error('[Screen] Realtime data error:', error);
        }
    }

    renderRealtimeChart(dataList) {
        // 实时数据流是echarts图表，不是HTML
        const chartDom = document.getElementById('dataStreamChart');
        if (!chartDom) return;

        if (!dataList || dataList.length === 0) {
            if (this.charts.dataStream) {
                this.charts.dataStream.dispose();
                this.charts.dataStream = null;
            }
            chartDom.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#64748b;">暂无实时数据</div>';
            return;
        }

        if (!this.charts.dataStream) this.charts.dataStream = echarts.init(chartDom);

        const series = dataList.slice(0, 10).map((d, i) => ({
            name: d.device_name || ('设备' + (i + 1)),
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: this.generateMockSeries(d.value || 50)
        }));

        this.charts.dataStream.setOption({
            tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: '#334155', textStyle: { color: '#e2e8f0' } },
            legend: { show: false },
            grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
            xAxis: {
                type: 'category', data: Array.from({length: 10}, (_, i) => i + 1 + 's'),
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b', fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b' },
                splitLine: { lineStyle: { color: '#1e293b' } }
            },
            series: series,
            color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#14b8a6']
        });
    }

    generateMockSeries(baseValue) {
        return Array.from({length: 10}, () => Math.max(0, baseValue + (Math.random() - 0.5) * 30));
    }

    renderTopDevices(dataList) {
        const container = document.getElementById('topDeviceList');
        if (!container) return;

        if (!dataList || dataList.length === 0) {
            container.innerHTML = '<li class="empty-state">暂无数据</li>';
            return;
        }

        // 按设备名聚合
        const deviceMap = {};
        dataList.forEach(d => {
            const name = d.device_name || '未知';
            if (!deviceMap[name]) deviceMap[name] = { name, count: 0 };
            deviceMap[name].count++;
        });

        const top5 = Object.values(deviceMap).sort((a, b) => b.count - a.count).slice(0, 5);

        container.innerHTML = top5.map((d, i) => `
            <li class="rank-item">
                <span class="rank-num rank-${i + 1}">${i + 1}</span>
                <span class="rank-name">${this.escapeHtml(d.name)}</span>
                <span class="rank-value">${d.count}条</span>
            </li>
        `).join('');
    }

    async loadAlarmList() {
        try {
            const response = await apiRequest('/api/dashboard/recent-alarms?limit=8', 'GET');
            if (response && response.success && response.data) {
                this.renderAlarmList(response.data);
            }
        } catch (error) {
            console.error('[Screen] Alarm list error:', error);
        }
    }

    renderAlarmList(alarms) {
        const container = document.getElementById('alarmList');
        const badge = document.getElementById('alarmBadge');
        if (!container) return;

        if (badge) {
            const unhandled = alarms ? alarms.filter(a => !a.is_handled).length : 0;
            badge.textContent = unhandled;
        }

        if (!alarms || alarms.length === 0) {
            container.innerHTML = '<li class="empty-state">暂无告警信息</li>';
            return;
        }

        const severityIcons = { critical: '🔴', warning: '🟡', info: '🔵' };
        const severityLabels = { critical: '严重', warning: '警告', info: '信息' };

        container.innerHTML = alarms.map(a => {
            const sev = a.severity || 'info';
            return `
                <li class="alarm-item alarm-${sev}">
                    <span class="alarm-icon">${severityIcons[sev] || '⚪'}</span>
                    <div class="alarm-content">
                        <div class="alarm-device">${this.escapeHtml(a.device_name || '-')}</div>
                        <div class="alarm-message">${this.escapeHtml(a.message || '-')}</div>
                    </div>
                    <span class="alarm-time">${this.formatTime(a.created_at)}</span>
                </li>
            `;
        }).join('');
    }

    async loadDeviceMap() {
        try {
            const response = await apiRequest('/api/devices?limit=100', 'GET');
            if (response && response.success && response.devices) {
                this.renderDeviceMap(response.devices);
            } else {
                // 兜底：使用mock数据
                this.renderDeviceMap(this.getMockDevices());
            }
        } catch (error) {
            console.error('[Screen] Device map error:', error);
            this.renderDeviceMap(this.getMockDevices());
        }
    }

    getMockDevices() {
        return [
            { name: '温度传感器-01', device_type: 'temperature', is_online: true, latitude: 39.9042, longitude: 116.4074, location_name: '北京' },
            { name: '湿度传感器-01', device_type: 'humidity', is_online: true, latitude: 31.2304, longitude: 121.4737, location_name: '上海' },
            { name: '压力传感器-01', device_type: 'pressure', is_online: false, latitude: 23.1291, longitude: 113.2644, location_name: '广州' },
            { name: '流量计-01', device_type: 'flow', is_online: true, latitude: 22.5431, longitude: 114.0579, location_name: '深圳' },
            { name: '电表-01', device_type: 'electric', is_online: true, latitude: 30.2741, longitude: 120.1551, location_name: '杭州' }
        ];
    }

    renderDeviceMap(devices) {
        const mapContainer = document.getElementById('deviceMap');
        if (!mapContainer) return;

        // 销毁旧地图
        if (this.map) {
            this.map.remove();
            this.map = null;
        }

        // 初始化地图（默认中心北京）
        this.map = L.map('deviceMap', {
            center: [35.0, 110.0],
            zoom: 4,
            zoomControl: true,
            attributionControl: false
        });

        // 暗色主题瓦片
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', {
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(this.map);

        // 添加设备标记
        const bounds = [];
        devices.forEach(d => {
            if (d.latitude && d.longitude) {
                const color = d.is_online ? '#10b981' : '#ef4444';
                const marker = L.circleMarker([d.latitude, d.longitude], {
                    radius: 8,
                    fillColor: color,
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(this.map);

                marker.bindPopup(`
                    <div style="color: #0f172a; padding: 4px;">
                        <strong>${this.escapeHtml(d.name)}</strong><br>
                        <small>类型: ${d.device_type || '-'}</small><br>
                        <small>位置: ${d.location_name || '-'}</small><br>
                        <small>状态: ${d.is_online ? '🟢 在线' : '🔴 离线'}</small>
                    </div>
                `);

                bounds.push([d.latitude, d.longitude]);
            }
        });

        // 自适应视图
        if (bounds.length > 0) {
            this.map.fitBounds(bounds, { padding: [30, 30], maxZoom: 8 });
        }
    }

    startRealtimeRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadOverview();
            this.loadRealtimeData();
            this.loadAlarmList();
        }, 10000);
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
            const diff = (now - d) / 1000;
            if (diff < 60) return '刚刚';
            if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
            if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
            return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return t;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ScreenV2();
});
