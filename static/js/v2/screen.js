/**
 * 大屏展示 - 数据可视化
 */
class ScreenDashboard {
    constructor() {
        this.charts = {};
        this.refreshInterval = 30000; // 30秒刷新
        this.init();
    }

    init() {
        this.updateDateTime();
        setInterval(() => this.updateDateTime(), 1000);
        
        this.initCharts();
        this.loadData();
        
        setInterval(() => this.loadData(), this.refreshInterval);
        
        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => chart.resize());
        });
    }

    updateDateTime() {
        const now = new Date();
        const options = { 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit',
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            hour12: false
        };
        document.getElementById('currentDateTime').textContent = now.toLocaleString('zh-CN', options);
    }

    initCharts() {
        // 设备状态饼图
        this.charts.deviceStatus = echarts.init(document.getElementById('deviceStatusChart'));
        this.charts.deviceStatus.setOption({
            tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
            legend: { bottom: 0, textStyle: { color: '#78909c', fontSize: 11 } },
            color: ['#4caf50', '#757575', '#ff9800'],
            series: [{
                type: 'pie',
                radius: ['45%', '70%'],
                center: ['50%', '45%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 6, borderColor: '#0d1b2a', borderWidth: 2 },
                label: { show: false },
                emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
                data: [
                    { value: 0, name: '在线' },
                    { value: 0, name: '离线' },
                    { value: 0, name: '告警' }
                ]
            }]
        });

        // 告警趋势图
        this.charts.alarmTrend = echarts.init(document.getElementById('alarmTrendChart'));
        this.charts.alarmTrend.setOption({
            tooltip: { trigger: 'axis' },
            grid: { top: 20, right: 15, bottom: 25, left: 40 },
            xAxis: { type: 'category', boundaryGap: false, axisLine: { lineStyle: { color: '#37474f' } }, axisLabel: { color: '#78909c', fontSize: 10 }, data: [] },
            yAxis: { type: 'value', splitLine: { lineStyle: { color: '#1e3a5f' } }, axisLabel: { color: '#78909c', fontSize: 10 } },
            series: [{ type: 'line', smooth: true, symbol: 'none', areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(255,87,34,0.3)' }, { offset: 1, color: 'rgba(255,87,34,0)' }]) }, lineStyle: { color: '#ff5722', width: 2 }, data: [] }]
        });

        // 设备类型分布
        this.charts.deviceType = echarts.init(document.getElementById('deviceTypeChart'));
        this.charts.deviceType.setOption({
            tooltip: { trigger: 'item' },
            legend: { orient: 'vertical', right: 10, top: 'center', textStyle: { color: '#78909c', fontSize: 11 } },
            color: ['#2196F3', '#00bcd4', '#4caf50', '#ff9800', '#9c27b0'],
            series: [{
                type: 'pie',
                radius: ['35%', '60%'],
                center: ['35%', '50%'],
                itemStyle: { borderRadius: 6, borderColor: '#0d1b2a', borderWidth: 2 },
                label: { show: false },
                data: []
            }]
        });

        // 数据量趋势
        this.charts.dataVolume = echarts.init(document.getElementById('dataVolumeChart'));
        this.charts.dataVolume.setOption({
            tooltip: { trigger: 'axis' },
            grid: { top: 15, right: 15, bottom: 25, left: 40 },
            xAxis: { type: 'category', axisLine: { lineStyle: { color: '#37474f' } }, axisLabel: { color: '#78909c', fontSize: 10 }, data: [] },
            yAxis: { type: 'value', splitLine: { lineStyle: { color: '#1e3a5f' } }, axisLabel: { color: '#78909c', fontSize: 10 } },
            series: [{ type: 'bar', barWidth: '50%', itemStyle: { borderRadius: [4, 4, 0, 0], color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#2196F3' }, { offset: 1, color: '#1565C0' }]) }, data: [] }]
        });

        // 实时数据流
        this.charts.dataStream = echarts.init(document.getElementById('dataStreamChart'));
        this.charts.dataStream.setOption({
            tooltip: { trigger: 'axis' },
            grid: { top: 10, right: 15, bottom: 25, left: 40 },
            xAxis: { type: 'category', boundaryGap: false, axisLine: { lineStyle: { color: '#37474f' } }, axisLabel: { color: '#78909c', fontSize: 9 }, data: Array.from({ length: 30 }, (_, i) => i + 's') },
            yAxis: { type: 'value', splitLine: { lineStyle: { color: '#1e3a5f' } }, axisLabel: { color: '#78909c', fontSize: 9 } },
            series: [
                { type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#4caf50', width: 1.5 }, data: Array(30).fill(null) },
                { type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#2196F3', width: 1.5 }, data: Array(30).fill(null) }
            ]
        });

        // 初始化地图（使用简单的标记点）
        this.initMap();
    }

    initMap() {
        const mapContainer = document.getElementById('deviceMap');
        if (mapContainer && typeof BMap !== 'undefined') {
            const map = new BMap.Map(mapContainer);
            map.centerAndZoom(new BMap.Point(116.404, 39.915), 5);
            map.enableScrollWheelZoom(true);
            
            map.setMapStyleV2({ styleId: '' }); // 深色主题
        } else {
            mapContainer.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#78909c;font-size:14px;">地图加载中...</div>';
        }
    }

    async loadData() {
        try {
            const [statsRes, devicesRes, alarmsRes] = await Promise.all([
                apiRequest('/api/dashboard/stats'),
                apiRequest('/api/devices'),
                apiRequest('/api/alarms/records?per_page=10')
            ]);

            if (statsRes.success) {
                this.updateStats(statsRes.data);
            }

            if (devicesRes.success) {
                this.updateDeviceCharts(devicesRes.data.items || devicesRes.data);
                this.updateTopDevices(devicesRes.data.items || devicesRes.data);
            }

            if (alarmsRes.success) {
                this.updateAlarmList(alarmsRes.data.items || alarmsRes.data);
            }

        } catch (error) {
            console.error('Failed to load screen data:', error);
        }
    }

    updateStats(data) {
        // 更新核心指标
        this.animateValue('totalDevices', data.total_devices || 0);
        this.animateValue('onlineCount', data.online_count || 0);
        this.animateValue('offlineCount', data.offline_count || 0);
        this.animateValue('todayDataPoints', data.today_data_points || 0);
        this.animateValue('activeChannels', data.active_channels || 0);
        this.animateValue('pendingAlarms', data.pending_alarms || 0);
        document.getElementById('avgResponseTime').textContent = data.avg_response_time || '--';

        // 更新设备状态饼图
        this.charts.deviceStatus.setOption({
            series: [{
                data: [
                    { value: data.online_count || 0, name: '在线' },
                    { value: data.offline_count || 0, name: '离线' },
                    { value: data.alarm_count || 0, name: '告警' }
                ]
            }]
        });

        // 更新告警趋势
        if (data.alarm_trend) {
            this.charts.alarmTrend.setOption({
                xAxis: { data: Object.keys(data.alarm_trend) },
                series: [{ data: Object.values(data.alarm_trend) }]
            });
        }

        // 更新数据量趋势
        if (data.data_trend) {
            this.charts.dataVolume.setOption({
                xAxis: { data: Object.keys(data.data_trend) },
                series: [{ data: Object.values(data.data_trend) }]
            });
        }
    }

    updateDeviceCharts(devices) {
        // 统计设备类型
        const typeCount = {};
        devices.forEach(d => {
            typeCount[d.device_type] = (typeCount[d.device_type] || 0) + 1;
        });

        this.charts.deviceType.setOption({
            series: [{
                data: Object.entries(typeCount).map(([name, value]) => ({ name, value }))
            }]
        });
    }

    updateAlarmList(alarms) {
        const list = document.getElementById('alarmList');
        const badge = document.getElementById('alarmBadge');
        
        if (!alarms.length) {
            list.innerHTML = '<li class="empty-state">暂无告警信息</li>';
            badge.textContent = '0';
            return;
        }

        badge.textContent = alarms.length;
        list.innerHTML = alarms.map(alarm => `
            <li>
                <div class="alarm-info">
                    <div class="alarm-device">${alarm.device_name || alarm.device_id}</div>
                    <div class="alarm-msg">${alarm.message || alarm.title}</div>
                </div>
                <span class="alarm-time">${formatTimeAgo(alarm.created_at)}</span>
            </li>
        `).join('');
    }

    updateTopDevices(devices) {
        const list = document.getElementById('topDeviceList');
        const sorted = [...devices].sort((a, b) => (b.data_point_count || 0) - (a.data_point_count || 0)).slice(0, 5);

        if (!sorted.length) {
            list.innerHTML = '<li class="empty-state">暂无数据</li>';
            return;
        }

        list.innerHTML = sorted.map((d, i) => `
            <li>
                <span class="rank-num">${i + 1}</span>
                <span class="rank-name">${d.name}</span>
                <span class="rank-value">${d.data_point_count || 0}</span>
            </li>
        `).join('');
    }

    animateValue(elementId, targetValue) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        const start = parseInt(el.textContent.replace(/,/g, '')) || 0;
        const end = targetValue;
        const duration = 800;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            
            el.textContent = Math.round(start + (end - start) * easeProgress).toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.screenDashboard = new ScreenDashboard();
});
