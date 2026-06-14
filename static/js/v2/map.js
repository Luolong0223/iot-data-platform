/**
 * Map V2 - IoT Data Platform
 * 设备地图展示 - Leaflet + OpenStreetMap
 */

class MapV2 {
    constructor() {
        this.map = null;
        this.markers = [];
        this.markerCluster = null;
        this.heatLayer = null;
        this.devices = [];
        this.currentFilter = '';
        this.init();
    }

    async init() {
        console.log('[Map] Initializing...');
        
        // 初始化地图
        this.initMap();
        
        // 加载设备数据
        await this.loadDevices();
        
        // 绑定事件
        this.bindEvents();
        
        // 隐藏加载提示
        const loading = document.getElementById('mapLoading');
        if (loading) loading.style.display = 'none';
        
        console.log('[Map] Initialized successfully');
    }

    initMap() {
        // 中国中心坐标
        const center = [35.8617, 104.1954];
        
        this.map = L.map('mapContainer', {
            center: center,
            zoom: 5,
            zoomControl: true,
            attributionControl: false
        });

        // 使用 CartoDB 暗色主题瓦片（适合深色UI）
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            subdomains: ['a', 'b', 'c', 'd']
        }).addTo(this.map);

        // 添加比例尺
        L.control.scale({
            imperial: false,
            position: 'bottomleft'
        }).addTo(this.map);

        // 初始化聚合图层
        this.markerCluster = L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true
        });
        this.map.addLayer(this.markerCluster);
    }

    async loadDevices() {
        try {
            const response = await apiRequest('/api/devices?limit=200');
            
            if (response && response.success && response.devices) {
                this.devices = response.devices;
            } else if (response && response.data) {
                this.devices = response.data;
            } else {
                // 使用示例数据
                this.devices = this.getSampleDevices();
            }
        } catch (error) {
            console.warn('[Map] API load failed, using sample data:', error.message);
            this.devices = this.getSampleDevices();
        }

        this.renderMarkers();
        this.updateStats();
    }

    getSampleDevices() {
        // 北京周边示例设备数据
        const baseLat = 39.9042;
        const baseLng = 116.4074;
        const types = ['温度传感器', '湿度传感器', '压力传感器', '流量计', '电表'];
        const statuses = ['online', 'online', 'online', 'online', 'offline', 'alarm'];
        
        const samples = [];
        for (let i = 0; i < 15; i++) {
            const status = statuses[Math.floor(Math.random() * statuses.length)];
            samples.push({
                id: 1000 + i,
                name: `${types[i % types.length]}-${String(i + 1).padStart(2, '0')}`,
                device_type: types[i % types.length],
                status: status,
                latitude: baseLat + (Math.random() - 0.5) * 2,
                longitude: baseLng + (Math.random() - 0.5) * 2,
                lat: baseLat + (Math.random() - 0.5) * 2,
                lng: baseLng + (Math.random() - 0.5) * 2,
                latest_value: (Math.random() * 100).toFixed(1),
                updated_at: new Date().toISOString()
            });
        }
        return samples;
    }

    renderMarkers() {
        // 清除旧标记
        this.markerCluster.clearLayers();
        this.markers = [];

        const filteredDevices = this.currentFilter 
            ? this.devices.filter(d => d.status === this.currentFilter)
            : this.devices;

        const heatData = [];

        filteredDevices.forEach(device => {
            const lat = parseFloat(device.latitude || device.lat || 0);
            const lng = parseFloat(device.longitude || device.lng || 0);
            
            if (!lat || !lng) return;

            // 创建自定义图标
            const icon = this.createDeviceIcon(device);
            const marker = L.marker([lat, lng], { icon });

            // 弹窗内容
            const popupContent = `
                <div class="map-popup">
                    <div class="popup-title">${device.name || '未知设备'}</div>
                    <div class="popup-row">类型: <span class="popup-value">${device.device_type || '--'}</span></div>
                    <div class="popup-row">状态: <span class="popup-value" style="color:${this.getStatusColor(device.status)}">${this.getStatusText(device.status)}</span></div>
                    <div class="popup-row">最新值: <span class="popup-value">${device.latest_value || '--'}</span></div>
                </div>
            `;
            marker.bindPopup(popupContent, { offset: [0, -20] });

            // 点击事件
            marker.on('click', () => {
                this.showDeviceInfo(device);
            });

            this.markers.push(marker);
            this.markerCluster.addLayer(marker);

            // 热力图数据
            heatData.push([lat, lng, device.status === 'alarm' ? 1 : 0.3]);
        });

        // 热力图
        if (this.heatLayer) {
            this.map.removeLayer(this.heatLayer);
        }
        this.heatData = heatData;

        // 适应所有标记
        if (this.markers.length > 0) {
            const group = L.featureGroup(this.markers);
            this.map.fitBounds(group.getBounds().pad(0.1), { maxZoom: 12 });
        }
    }

    createDeviceIcon(device) {
        const status = device.status || 'offline';
        const colors = {
            online: '#10b981',
            offline: '#64748b',
            alarm: '#ef4444'
        };
        const color = colors[status] || colors.offline;

        return L.divIcon({
            className: 'custom-device-marker',
            html: `<div style="
                width: 28px; height: 28px;
                background: ${color};
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 0 12px ${color}66;
                transition: transform 0.2s;
            ">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
                    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                </svg>
            </div>`,
            iconSize: [28, 28],
            iconAnchor: [14, 14],
            popupAnchor: [0, -14]
        });
    }

    showDeviceInfo(device) {
        const panel = document.getElementById('deviceInfoPanel');
        if (!panel) return;

        document.getElementById('infoDeviceName').textContent = device.name || '未知设备';
        document.getElementById('infoDeviceStatus').textContent = this.getStatusText(device.status);
        document.getElementById('infoDeviceStatus').style.color = this.getStatusColor(device.status);
        document.getElementById('infoDeviceValue').textContent = device.latest_value || '--';
        document.getElementById('infoDeviceTime').textContent = device.updated_at 
            ? new Date(device.updated_at).toLocaleString('zh-CN')
            : '--';
        
        const detailLink = document.getElementById('infoDetailLink');
        const dataLink = document.getElementById('infoDataLink');
        if (detailLink) detailLink.href = `/devices?id=${device.id}`;
        if (dataLink) dataLink.href = `/data?device_id=${device.id}`;

        panel.style.display = 'block';
    }

    updateStats() {
        const online = this.devices.filter(d => d.status === 'online').length;
        const offline = this.devices.filter(d => d.status === 'offline').length;
        const alarm = this.devices.filter(d => d.status === 'alarm').length;

        const setEl = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setEl('onlineCount', online);
        setEl('offlineCount', offline);
        setEl('alarmCount', alarm);

        // 更新设备列表
        this.renderDeviceList();
    }

    renderDeviceList() {
        const container = document.getElementById('deviceListContainer');
        if (!container) return;

        const filteredDevices = this.currentFilter
            ? this.devices.filter(d => d.status === this.currentFilter)
            : this.devices;

        if (filteredDevices.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-secondary small">暂无设备</div>';
            return;
        }

        container.innerHTML = filteredDevices.slice(0, 50).map(d => `
            <div class="d-flex align-items-center justify-content-between p-2 rounded mb-1 device-list-item"
                 style="background:rgba(15,23,42,0.4);cursor:pointer;"
                 onclick="mapV2.focusDevice(${d.id})">
                <div class="d-flex align-items-center gap-2">
                    <span class="rounded-circle d-inline-block" style="width:8px;height:8px;background:${this.getStatusColor(d.status)};"></span>
                    <span class="small text-white" style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${d.name || '未知'}</span>
                </div>
                <span class="small text-secondary">${d.latest_value || '--'}</span>
            </div>
        `).join('');
    }

    focusDevice(deviceId) {
        const device = this.devices.find(d => d.id === deviceId);
        if (!device) return;

        const lat = parseFloat(device.latitude || device.lat || 0);
        const lng = parseFloat(device.longitude || device.lng || 0);
        if (!lat || !lng) return;

        this.map.setView([lat, lng], 14, { animate: true });
        
        // 找到对应标记并打开弹窗
        setTimeout(() => {
            this.markers.forEach(m => {
                const pos = m.getLatLng();
                if (Math.abs(pos.lat - lat) < 0.0001 && Math.abs(pos.lng - lng) < 0.0001) {
                    m.openPopup();
                }
            });
        }, 500);
    }

    refreshDevices() {
        this.loadDevices();
    }

    fitAllMarkers() {
        if (this.markers.length > 0) {
            const group = L.featureGroup(this.markers);
            this.map.fitBounds(group.getBounds().pad(0.1), { maxZoom: 12 });
        }
    }

    toggleHeatmap(show) {
        if (show) {
            if (!this.heatLayer && this.heatData) {
                this.heatLayer = L.heatLayer(this.heatData, {
                    radius: 25,
                    blur: 15,
                    maxZoom: 10,
                    gradient: { 0.4: '#10b981', 0.6: '#f59e0b', 0.8: '#ef4444' }
                }).addTo(this.map);
            }
        } else {
            if (this.heatLayer) {
                this.map.removeLayer(this.heatLayer);
                this.heatLayer = null;
            }
        }
    }

    bindEvents() {
        // 设备筛选
        const filterEl = document.getElementById('deviceFilter');
        if (filterEl) {
            filterEl.addEventListener('change', (e) => {
                this.currentFilter = e.target.value;
                this.renderMarkers();
                this.renderDeviceList();
            });
        }

        // 热力图切换
        const heatmapEl = document.getElementById('showHeatmap');
        if (heatmapEl) {
            heatmapEl.addEventListener('change', (e) => {
                this.toggleHeatmap(e.target.checked);
            });
        }

        // 窗口大小变化时重新适应
        window.addEventListener('resize', () => {
            if (this.map) this.map.invalidateSize();
        });
    }

    getStatusColor(status) {
        const colors = { online: '#10b981', offline: '#64748b', alarm: '#ef4444' };
        return colors[status] || '#64748b';
    }

    getStatusText(status) {
        const texts = { online: '在线', offline: '离线', alarm: '告警' };
        return texts[status] || '未知';
    }

    destroy() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.mapV2 = new MapV2();
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (window.mapV2) {
        window.mapV2.destroy();
    }
});
