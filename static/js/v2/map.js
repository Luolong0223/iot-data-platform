/**
 * Map V2 - IoT Data Platform
 * 地图展示 - 设备位置可视化（百度地图）
 */

class MapV2 {
    constructor() {
        this.map = null;
        this.markers = [];
        this.heatmapOverlay = null;
        this.devices = [];
        this.selectedDevice = null;
        this.init();
    }

    async init() {
        console.log('[Map] Initializing...');
        
        // 等待百度地图API加载完成
        if (typeof BMap === 'undefined') {
            // 如果百度地图未加载，等待后重试
            await this.waitForBaiduMap();
        }
        
        try {
            this.initMap();
            await this.loadDevices();
            this.bindEvents();
            
            // 隐藏加载提示
            const loading = document.getElementById('mapLoading');
            if (loading) loading.style.display = 'none';
            
            // 启动自动刷新（每60秒）
            setInterval(() => this.refreshDevices(), 60000);
            
            console.log('[Map] Initialized successfully');
        } catch (error) {
            console.error('[Map] Initialization error:', error);
            this.showError('地图加载失败，请刷新页面重试');
        }
    }

    // 等待百度地图API加载
    waitForBaiduMap() {
        return new Promise((resolve, reject) => {
            let attempts = 0;
            const maxAttempts = 30; // 最多等15秒
            
            const checkInterval = setInterval(() => {
                attempts++;
                if (typeof BMap !== 'undefined') {
                    clearInterval(checkInterval);
                    resolve();
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    reject(new Error('Baidu Map API load timeout'));
                }
            }, 500);
        });
    }

    // 初始化地图
    initMap() {
        const container = document.getElementById('mapContainer');
        if (!container) throw new Error('Map container not found');

        // 创建地图实例
        this.map = new BMap.Map('mapContainer', {
            enableMapClick: true,
            minZoom: 3,
            maxZoom: 18
        });

        // 设置中心点（默认北京）
        const point = new BMap.Point(116.404, 39.915);
        this.map.centerAndZoom(point, 12);

        // 启用控件
        this.map.addControl(new BMap.NavigationControl({
            anchor: BMAP_ANCHOR_TOP_LEFT,
            type: BMAP_NAVIGATION_CONTROL_LARGE
        }));
        
        this.map.addControl(new BMap.ScaleControl({
            anchor: BMAP_ANCHOR_BOTTOM_LEFT
        }));

        // 启用滚轮缩放
        this.map.enableScrollWheelZoom(true);

        // 添加地图类型切换事件
        this.map.addEventListener('click', (e) => {
            // 点击空白处关闭信息窗口
            this.closeInfoWindow();
        });
    }

    // 加载设备数据
    async loadDevices() {
        try {
            // 优先使用带位置的设备API
            const response = await apiRequest('/api/devices/location');
            
            if (response && response.devices) {
                this.devices = response.devices;
            } else {
                // 回退到通用设备列表API
                const fallbackResponse = await apiRequest('/api/devices?per_page=200');
                if (fallbackResponse && fallbackResponse.devices) {
                    this.devices = fallbackResponse.devices;
                } else {
                    // 使用示例数据
                    this.loadSampleDevices();
                    return;
                }
            }
            
            this.renderMarkers();
            this.renderDeviceList();
            this.updateStats();
            
            // 自动适应视图
            if (this.devices.length > 0) {
                setTimeout(() => this.fitAllMarkers(), 500);
            }
        } catch (error) {
            console.error('[Map] Load devices error:', error);
            this.loadSampleDevices();
        }
    }

    // 加载示例设备数据
    loadSampleDevices() {
        // 北京周边示例坐标（使用latitude/longitude字段名）
        this.devices = [
            { id: '1', name: '温度传感器#1', device_type: 'temperature', latitude: 39.915, longitude: 116.404, is_online: true, latest_value: '25.6°C', last_seen_at: new Date().toISOString() },
            { id: '2', name: '湿度传感器#1', device_type: 'humidity', latitude: 39.920, longitude: 116.410, is_online: true, latest_value: '65%', last_seen_at: new Date().toISOString() },
            { id: '3', name: '烟雾探测器#1', device_type: 'smoke', latitude: 39.910, longitude: 116.400, is_online: false, latest_value: '--', last_seen_at: new Date(Date.now() - 3600000).toISOString() },
            { id: '4', name: '门磁传感器#1', device_type: 'door', latitude: 39.905, longitude: 116.415, is_online: true, latest_value: '关闭', last_seen_at: new Date().toISOString() },
            { id: '5', name: '摄像头#1', device_type: 'camera', latitude: 39.925, longitude: 116.420, is_online: true, latest_value: '正常', last_seen_at: new Date().toISOString() },
            { id: '6', name: '温度传感器#2', device_type: 'temperature', latitude: 39.900, longitude: 116.380, is_online: false, latest_value: '--', last_seen_at: new Date(Date.now() - 7200000).toISOString() },
            { id: '7', name: 'UPS电源监控', device_type: 'ups', latitude: 39.895, longitude: 116.385, is_online: true, latest_value: '220V', last_seen_at: new Date().toISOString() },
            { id: '8', name: '漏水检测器', device_type: 'water_leak', latitude: 39.898, longitude: 116.390, is_online: true, latest_value: '正常', last_seen_at: new Date().toISOString() },
            { id: '9', name: '压力传感器#1', device_type: 'pressure', latitude: 39.930, longitude: 116.430, is_online: true, latest_value: '101.3kPa', last_seen_at: new Date().toISOString() },
            { id: '10', name: '光照传感器#1', device_type: 'light', latitude: 39.908, longitude: 116.395, is_online: true, latest_value: '850lux', last_seen_at: new Date().toISOString() }
        ];
        
        this.renderMarkers();
        this.renderDeviceList();
        this.updateStats();
        setTimeout(() => this.fitAllMarkers(), 500);
    }

    // 渲染标记点
    renderMarkers() {
        // 清除现有标记
        this.clearMarkers();

        this.devices.forEach(device => {
            const marker = this.createMarker(device);
            if (marker) {
                this.markers.push(marker);
                this.map.addOverlay(marker);
            }
        });

        // 渲染热力图（如果开启）
        const showHeatmap = document.getElementById('showHeatmap');
        if (showHeatmap && showHeatmap.checked) {
            this.renderHeatmap();
        }
    }

    // 创建标记点
    createMarker(device) {
        // 支持两种字段名：lat/lng 或 latitude/longitude
        const lat = device.lat || device.latitude;
        const lng = device.lng || device.longitude;
        
        if (!lat || !lng) return null;

        const point = new BMap.Point(parseFloat(lng), parseFloat(lat));
        
        // 创建自定义图标
        const icon = this.createIcon(device);
        
        const marker = new BMap.Marker(point, { icon });
        
        // 存储设备数据
        marker.deviceData = device;

        // 点击事件
        marker.addEventListener('click', () => {
            this.showDeviceInfo(device);
        });

        // 鼠标悬停效果
        marker.addEventListener('mouseover', () => {
            marker.setZIndex(100);
        });
        
        marker.addEventListener('mouseout', () => {
            marker.setZIndex(0);
        });

        return marker;
    }

    // 创建图标
    createIcon(device) {
        let iconUrl, iconSize;
        
        if (!device.is_online) {
            // 离线设备 - 灰色
            iconUrl = 'data:image/svg+xml;base64,' + btoa(`
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="42" viewBox="0 0 32 42">
                    <path d="M16 0C7.163 0 0 7.163 0 16c0 11 16 26 16 26s16-15 16-26c0-8.837-7.163-16-16-16z" fill="#64748b"/>
                    <circle cx="16" cy="16" r="6" fill="#94a3b8"/>
                </svg>
            `);
            iconSize = new BMap.Size(24, 32);
        } else {
            // 在线设备 - 根据类型选择颜色
            const color = this.getDeviceColor(device.device_type);
            iconUrl = 'data:image/svg+xml;base64,' + btoa(`
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="42" viewBox="0 0 32 42">
                    <path d="M16 0C7.163 0 0 7.163 0 16c0 11 16 26 16 26s16-15 16-26c0-8.837-7.163-16-16-16z" fill="${color}"/>
                    <circle cx="16" cy="16" r="6" fill="#fff"/>
                </svg>
            `);
            iconSize = new BMap.Size(28, 38);
        }

        return new BMap.Icon(iconUrl, iconSize, {
            anchor: new BMap.Size(iconSize.width / 2, iconSize.height),
            infoWindowAnchor: new BMap.Size(iconSize.width / 2, 0)
        });
    }

    // 获取设备颜色
    getDeviceColor(type) {
        const colors = {
            'temperature': '#ef4444',
            'humidity': '#3b82f6',
            'smoke': '#f97316',
            'door': '#10b981',
            'camera': '#8b5cf6',
            'ups': '#eab308',
            'water_leak': '#06b6d4',
            'pressure': '#ec4899',
            'light': '#f59e0b'
        };
        return colors[type] || '#22c55e';
    }

    // 清除所有标记
    clearMarkers() {
        this.markers.forEach(marker => {
            this.map.removeOverlay(marker);
        });
        this.markers = [];

        // 清除热力图
        if (this.heatmapOverlay) {
            this.map.removeOverlay(this.heatmapOverlay);
            this.heatmapOverlay = null;
        }
    }

    // 显示设备详情
    showDeviceInfo(device) {
        this.selectedDevice = device;
        
        // 支持两种字段名
        const lat = device.lat || device.latitude;
        const lng = device.lng || device.longitude;
        
        // 更新弹窗内容
        document.getElementById('infoDeviceName').textContent = device.name || '未命名设备';
        document.getElementById('infoDeviceType').textContent = this.getTypeName(device.device_type);
        document.getElementById('infoDeviceStatus').innerHTML = `
            <span class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full ${device.is_online ? 'bg-emerald-500' : 'bg-slate-500'}"></span>
                ${device.is_online ? '在线' : '离线'}
            </span>
        `;
        document.getElementById('infoDeviceValue').textContent = device.latest_value || '--';
        document.getElementById('infoDeviceTime').textContent = this.formatTime(device.last_seen_at || device.last_update);
        document.getElementById('infoDetailLink').href = `/devices_v2?id=${device.id}`;
        document.getElementById('infoDataLink').href = `/data_v2?device_id=${device.id}`;

        // 显示弹窗
        document.getElementById('deviceInfoWindow').classList.remove('hidden');

        // 高亮对应列表项
        this.highlightDeviceInList(device.id);

        // 地图移动到该点
        if (lat && lng) {
            const point = new BMap.Point(parseFloat(lng), parseFloat(lat));
            this.map.panTo(point);
        }
    }

    // 关闭信息窗口
    closeInfoWindow() {
        document.getElementById('deviceInfoWindow').classList.add('hidden');
        this.selectedDevice = null;
        this.clearListHighlight();
    }

    // 高亮列表项
    highlightDeviceInList(deviceId) {
        this.clearListHighlight();
        const item = document.querySelector(`[data-device-id="${deviceId}"]`);
        if (item) {
            item.classList.add('bg-blue-600/20', 'border-blue-500/50');
        }
    }

    // 清除列表高亮
    clearListHighlight() {
        document.querySelectorAll('[data-device-id]').forEach(item => {
            item.classList.remove('bg-blue-600/20', 'border-blue-500/50');
        });
    }

    // 渲染设备列表
    renderDeviceList() {
        const container = document.getElementById('deviceListContainer');
        if (!container) return;

        if (this.devices.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-slate-500">
                    <i class="fas fa-map-marker-alt text-3xl mb-2 opacity-50"></i>
                    <p class="text-sm">暂无带位置的设备</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.devices.map(device => `
            <div data-device-id="${device.id}" 
                 class="p-3 rounded-lg bg-slate-900/50 border border-slate-700/50 hover:border-slate-600 cursor-pointer transition-all"
                 onclick="mapV2.focusDevice('${device.id}')">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2 min-w-0 flex-1">
                        <span class="w-2 h-2 rounded-full ${device.is_online ? 'bg-emerald-500' : 'bg-slate-500'} flex-shrink-0"></span>
                        <span class="text-sm font-medium text-white truncate">${device.name}</span>
                    </div>
                </div>
                <div class="flex items-center justify-between text-xs text-slate-400">
                    <span>${this.getTypeName(device.device_type)}</span>
                    <span class="font-mono">${device.latest_value || '--'}</span>
                </div>
            </div>
        `).join('');
    }

    // 聚焦到设备
    focusDevice(deviceId) {
        const device = this.devices.find(d => d.id === deviceId);
        if (device) {
            this.showDeviceInfo(device);
        }
    }

    // 更新统计数据
    updateStats() {
        const online = this.devices.filter(d => d.is_online).length;
        const offline = this.devices.length - online;
        // 假设部分在线设备有告警
        const alarm = Math.floor(online * 0.1); // 10%的在线设备有告警

        const elOnline = document.getElementById('onlineCount');
        const elOffline = document.getElementById('offlineCount');
        const elAlarm = document.getElementById('alarmCount');

        if (elOnline) elOnline.textContent = online;
        if (elOffline) elOffline.textContent = offline;
        if (elAlarm) elAlarm.textContent = alarm;
    }

    // 渲染热力图
    renderHeatmap() {
        if (!this.heatmapOverlay && typeof BMapLib !== 'undefined' && BMapLib.HeatmapOverlay) {
            this.heatmapOverlay = new BMapLib.HeatmapOverlay({"radius": 20});
            this.map.addOverlay(this.heatmapOverlay);
        }

        if (this.heatmapOverlay) {
            const points = this.devices
                .filter(d => d.is_online)
                .map(d => ({
                    lng: parseFloat(d.lng || d.longitude),
                    lat: parseFloat(d.lat || d.latitude),
                    count: 1
                }));
            
            this.heatmapOverlay.setDataSet({data: points, max: 10});
        }
    }

    // 绑定事件
    bindEvents() {
        // 地图类型切换
        const mapTypeSelect = document.getElementById('mapType');
        if (mapTypeSelect) {
            mapTypeSelect.addEventListener('change', (e) => {
                switch(e.target.value) {
                    case 'satellite':
                        this.map.setMapType(B_SATELLITE_MAP);
                        break;
                    case 'terrain':
                        this.map.setMapType(B_HYBRID_MAP);
                        break;
                    default:
                        this.map.setMapType(B_NORMAL_MAP);
                }
            });
        }

        // 设备筛选
        const deviceFilter = document.getElementById('deviceFilter');
        if (deviceFilter) {
            deviceFilter.addEventListener('change', (e) => {
                this.filterDevices(e.target.value);
            });
        }

        // 热力图开关
        const heatmapCheckbox = document.getElementById('showHeatmap');
        if (heatmapCheckbox) {
            heatmapCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.renderHeatmap();
                } else if (this.heatmapOverlay) {
                    this.map.removeOverlay(this.heatmapOverlay);
                    this.heatmapOverlay = null;
                }
            });
        }
    }

    // 过滤设备
    filterDevices(filter) {
        let filteredDevices = [...this.devices];
        
        switch(filter) {
            case 'online':
                filteredDevices = filteredDevices.filter(d => d.is_online);
                break;
            case 'offline':
                filteredDevices = filteredDevices.filter(d => !d.is_online);
                break;
            case 'alarm':
                // 假设有告警的设备（实际应从API获取）
                filteredDevices = filteredDevices.filter((d, i) => i % 5 === 0 && d.is_online);
                break;
        }

        // 重新渲染标记
        this.clearMarkers();
        filteredDevices.forEach(device => {
            const marker = this.createMarker(device);
            if (marker) {
                this.markers.push(marker);
                this.map.addOverlay(marker);
            }
        });

        // 更新列表显示
        this.renderFilteredDeviceList(filteredDevices);
    }

    // 渲染过滤后的设备列表
    renderFilteredDeviceList(devices) {
        const container = document.getElementById('deviceListContainer');
        if (!container) return;

        container.innerHTML = devices.map(device => `
            <div data-device-id="${device.id}" 
                 class="p-3 rounded-lg bg-slate-900/50 border border-slate-700/50 hover:border-slate-600 cursor-pointer transition-all"
                 onclick="mapV2.focusDevice('${device.id}')">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2 min-w-0 flex-1">
                        <span class="w-2 h-2 rounded-full ${device.is_online ? 'bg-emerald-500' : 'bg-slate-500'} flex-shrink-0"></span>
                        <span class="text-sm font-medium text-white truncate">${device.name}</span>
                    </div>
                </div>
                <div class="flex items-center justify-between text-xs text-slate-400">
                    <span>${this.getTypeName(device.device_type)}</span>
                    <span class="font-mono">${device.latest_value || '--'}</span>
                </div>
            </div>
        `).join('');
    }

    // 刷新设备
    async refreshDevices() {
        try {
            await this.loadDevices();
            showToast('设备数据已刷新', 'success');
        } catch (error) {
            console.error('[Map] Refresh error:', error);
            showToast('刷新失败', 'error');
        }
    }

    // 适应视图（显示所有标记）
    fitAllMarkers() {
        if (this.markers.length === 0) return;

        const points = this.markers.map(m => m.getPosition());
        const viewport = this.map.getViewport(points);
        this.map.centerAndZoom(viewport.center, viewport.zoom);
    }

    // 获取类型名称
    getTypeName(type) {
        const names = {
            'temperature': '温度传感器',
            'humidity': '湿度传感器',
            'smoke': '烟雾探测器',
            'door': '门磁传感器',
            'camera': '摄像头',
            'ups': 'UPS电源',
            'water_leak': '漏水检测器',
            'pressure': '压力传感器',
            'light': '光照传感器'
        };
        return names[type] || type || '未知';
    }

    // 格式化时间
    formatTime(timeStr) {
        if (!timeStr) return '--';
        try {
            const date = new Date(timeStr);
            return date.toLocaleString('zh-CN');
        } catch (e) {
            return timeStr;
        }
    }

    // 显示错误
    showError(message) {
        const loading = document.getElementById('mapLoading');
        if (loading) {
            loading.innerHTML = `
                <div class="text-center">
                    <i class="fas fa-exclamation-triangle text-4xl text-red-500 mb-3"></i>
                    <p class="text-white text-lg font-semibold mb-2">加载失败</p>
                    <p class="text-slate-400 mb-4">${message}</p>
                    <button onclick="location.reload()" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                        刷新页面
                    </button>
                </div>
            `;
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.mapV2 = new MapV2();
});
