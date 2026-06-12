/**
 * IoT Data Platform - Map JavaScript
 * 使用 Leaflet 开源地图（免费，无需API Key）
 */

(function() {
    'use strict';

    let map = null;
    let markers = [];
    let markerLayer = null;

    // 初始化地图
    window.initBaiduMap = function(elementId, lng, lat, zoom) {
        if (map) return;
        
        // 使用 Leaflet 创建地图
        map = L.map(elementId, {
            center: [lat, lng],
            zoom: zoom,
            zoomControl: true
        });
        
        // 添加高德瓦片图层（国内访问更快）
        L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
            subdomains: ['1', '2', '3', '4'],
            maxZoom: 18,
            attribution: '&copy; 高德地图'
        }).addTo(map);
        
        // 创建标记图层组
        markerLayer = L.layerGroup().addTo(map);
    };

    // 加载设备标记
    window.loadDeviceMarkers = function() {
        apiRequest('/api/devices').then(function(data) {
            const devices = data.devices || [];
            clearMarkers();
            
            let hasValidLocation = false;
            devices.forEach(function(device) {
                if (device.latitude && device.longitude) {
                    addDeviceMarker(device);
                    hasValidLocation = true;
                }
            });
            
            if (markers.length > 1) {
                fitAllMarkers();
            }
            
            // 如果没有设备有位置信息，显示提示
            if (!hasValidLocation) {
                showNoLocationTip();
            }
        }).catch(function(err) {
            showToast('加载设备位置失败: ' + err.message, 'error');
        });
    };

    // 显示无位置提示
    function showNoLocationTip() {
        if (!map) return;
        
        const tip = L.control({position: 'topright'});
        tip.onAdd = function() {
            const div = L.DomUtil.create('div', 'map-tip-card');
            div.innerHTML = `
                <div class="card shadow-sm" style="width: 250px;">
                    <div class="card-body p-2">
                        <h6 class="card-title mb-1"><i class="bi bi-info-circle text-primary"></i> 提示</h6>
                        <p class="card-text small mb-2">暂无设备位置信息，请在设备管理中设置设备经纬度。</p>
                        <a href="/devices" class="btn btn-sm btn-primary">前往设置</a>
                    </div>
                </div>
            `;
            return div;
        };
        tip.addTo(map);
    }

    // 添加设备标记
    function addDeviceMarker(device) {
        const channels = device.channels || [];
        const onlineCount = channels.filter(function(c) { return c.online; }).length;
        const totalChannels = channels.length;

        // 根据状态确定颜色
        let color = '#dc3545'; // 红色 - 离线
        let status = '离线';
        if (device.is_online || (totalChannels > 0 && onlineCount === totalChannels)) {
            color = '#198754'; // 绿色 - 全部在线
            status = '在线';
        } else if (onlineCount > 0) {
            color = '#ffc107'; // 黄色 - 部分在线
            status = '部分在线';
        }

        // 创建自定义图标
        const icon = L.divIcon({
            className: 'device-marker',
            html: `<div class="marker-pin" style="background-color: ${color};">
                <i class="bi bi-cpu"></i>
            </div>
            <div class="marker-label">${device.name || '未命名'}</div>`,
            iconSize: [30, 42],
            iconAnchor: [15, 42],
            popupAnchor: [0, -42]
        });

        const marker = L.marker([device.latitude, device.longitude], { icon: icon });
        
        // 创建弹出框内容
        const popupContent = buildPopupContent(device, onlineCount, totalChannels, status, color);
        marker.bindPopup(popupContent, { maxWidth: 350 });
        
        // 点击时加载最新数据
        marker.on('click', function() {
            loadLatestDataForPopup(device.id);
        });
        
        markerLayer.addLayer(marker);
        markers.push(marker);
    }

    // 构建弹出框内容
    function buildPopupContent(device, onlineCount, totalChannels, status, color) {
        return `
            <div class="device-popup">
                <div class="popup-header">
                    <h6 class="mb-0">
                        <span class="status-dot" style="background-color: ${color};"></span>
                        ${device.name || '未命名设备'}
                    </h6>
                    <span class="badge" style="background-color: ${color};">${status}</span>
                </div>
                <div class="popup-body">
                    <div class="row g-2 mb-2">
                        <div class="col-6">
                            <small class="text-muted">设备ID</small>
                            <div class="fw-bold">#${device.id}</div>
                        </div>
                        <div class="col-6">
                            <small class="text-muted">电压</small>
                            <div class="fw-bold">${device.voltage_mv || '-'} mV</div>
                        </div>
                        <div class="col-6">
                            <small class="text-muted">通道</small>
                            <div class="fw-bold">${onlineCount}/${totalChannels}</div>
                        </div>
                        <div class="col-6">
                            <small class="text-muted">位置</small>
                            <div class="fw-bold">${device.location_name || '未设置'}</div>
                        </div>
                    </div>
                    <hr class="my-2">
                    <div id="popup-data-${device.id}">
                        <div class="text-center py-2">
                            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                            <span class="ms-2 small text-muted">加载数据中...</span>
                        </div>
                    </div>
                </div>
                <div class="popup-footer">
                    <a href="/devices/${device.id}" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-eye"></i> 详情
                    </a>
                    <a href="/data?device_id=${device.id}" class="btn btn-sm btn-outline-secondary">
                        <i class="bi bi-graph-up"></i> 数据
                    </a>
                </div>
            </div>
        `;
    }

    // 加载最新数据
    function loadLatestDataForPopup(deviceId) {
        apiRequest('/api/data/latest?device_id=' + deviceId).then(function(data) {
            const points = data.data_points || [];
            const container = document.getElementById('popup-data-' + deviceId);
            if (!container) return;
            
            if (!points.length) {
                container.innerHTML = '<p class="text-muted text-center mb-0 small">暂无数据</p>';
                return;
            }
            
            let html = '<table class="table table-sm table-hover mb-0"><tbody>';
            points.slice(0, 5).forEach(function(p) {
                html += `
                    <tr>
                        <td><small>${p.channel_name || '-'}</small></td>
                        <td><small>${p.name || '-'}</small></td>
                        <td class="text-end"><strong>${formatNumber(p.value, 4)}</strong></td>
                        <td class="text-muted"><small>${formatTime(p.timestamp)}</small></td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            
            if (points.length > 5) {
                html += `<p class="text-muted text-center mb-0 small">还有 ${points.length - 5} 条数据</p>`;
            }
            
            container.innerHTML = html;
        }).catch(function() {
            const container = document.getElementById('popup-data-' + deviceId);
            if (container) {
                container.innerHTML = '<p class="text-danger text-center mb-0 small">加载失败</p>';
            }
        });
    }

    // 清除所有标记
    function clearMarkers() {
        if (markerLayer) {
            markerLayer.clearLayers();
        }
        markers = [];
    }

    // 适应所有标记
    window.fitAllMarkers = function() {
        if (!map || markers.length === 0) return;
        
        if (markers.length === 1) {
            map.setView(markers[0].getLatLng(), 14);
            return;
        }
        
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    };

    // 刷新地图数据
    window.refreshMapData = function() {
        loadDeviceMarkers();
        showToast('地图数据已刷新', 'success');
    };

    // 辅助函数
    function formatNumber(num, decimals) {
        if (num === null || num === undefined) return '-';
        return Number(num).toFixed(decimals || 2);
    }

    function formatTime(timestamp) {
        if (!timestamp) return '-';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function showToast(message, type) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            console.log('[' + type + '] ' + message);
        }
    }

    function apiRequest(url, options) {
        const defaults = {
            headers: { 'Accept': 'application/json' }
        };
        options = Object.assign({}, defaults, options);
        return fetch(url, options).then(function(response) {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.json();
        }).then(function(data) {
            if (!data.success) throw new Error(data.message || 'Request failed');
            return data;
        });
    }
})();
