/**
 * IoT Data Platform - Map JavaScript (Baidu Map)
 * Baidu Map API v3.0 integration, device markers, info windows
 */

(function() {
    'use strict';

    let map = null;
    let markers = [];

    // Initialize Baidu Map
    window.initBaiduMap = function(elementId, lng, lat, zoom) {
        if (map) return;
        map = new BMap.Map(elementId);
        const point = new BMap.Point(lng, lat);
        map.centerAndZoom(point, zoom);
        map.enableScrollWheelZoom(true);
        map.addControl(new BMap.NavigationControl());
        map.addControl(new BMap.ScaleControl());
        map.addControl(new BMap.OverviewMapControl());
    };

    // Load device markers from API
    window.loadDeviceMarkers = function() {
        apiRequest('/api/devices').then(function(data) {
            const devices = data.devices || [];
            clearMarkers();
            devices.forEach(function(device) {
                if (device.latitude && device.longitude) {
                    addDeviceMarker(device);
                }
            });
            if (markers.length > 1) {
                fitAllMarkers();
            }
        }).catch(function(err) {
            showToast('加载设备位置失败: ' + err.message, 'error');
        });
    };

    function addDeviceMarker(device) {
        const channels = device.channels || [];
        const onlineCount = channels.filter(function(c) { return c.online; }).length;
        const totalChannels = channels.length;

        // Determine marker color based on status
        let color = '#e74c3c';
        if (totalChannels > 0 && onlineCount === totalChannels) {
            color = '#27ae60';
        } else if (onlineCount > 0) {
            color = '#f39c12';
        }

        const point = new BMap.Point(device.longitude, device.latitude);

        // Create custom icon using SimpleMarker (or fallback to standard marker with label)
        let marker;
        try {
            const icon = new BMap.Icon(
                'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><circle cx="12" cy="12" r="10" fill="' + color + '" stroke="white" stroke-width="2"/></svg>'),
                new BMap.Size(24, 24)
            );
            marker = new BMap.Marker(point, { icon: icon });
        } catch (e) {
            marker = new BMap.Marker(point);
        }

        marker.deviceId = device.id;
        map.addOverlay(marker);
        markers.push(marker);

        // Build info window content
        const infoContent = buildInfoWindowContent(device, onlineCount, totalChannels);
        const infoWindow = new BMap.InfoWindow(infoContent, {
            width: 320,
            title: '<strong>' + (device.name || '未命名设备') + '</strong>',
            enableMessage: false
        });

        marker.addEventListener('click', function() {
            map.openInfoWindow(infoWindow, point);
            loadLatestDataForInfoWindow(device.id, infoWindow);
        });
    }

    function buildInfoWindowContent(device, onlineCount, totalChannels) {
        return '<div class="map-popup">' +
            '<div class="popup-data">' +
                '<div><span class="label">ID:</span> ' + (device.id || '-') + '</div>' +
                '<div><span class="label">电压:</span> ' + (device.voltage_mv || '-') + ' mV</div>' +
                '<div><span class="label">位置:</span> ' + (device.location_name || '-') + '</div>' +
                '<div><span class="label">通道:</span> ' + onlineCount + '/' + totalChannels + ' 在线</div>' +
                '<hr style="margin:0.5rem 0;">' +
                '<div id="popup-data-' + device.id + '"><em>点击加载最新数据...</em></div>' +
            '</div>' +
        '</div>';
    }

    function loadLatestDataForInfoWindow(deviceId, infoWindow) {
        apiRequest('/api/data/latest?device_id=' + deviceId).then(function(data) {
            const points = data.data_points || [];
            let html;
            if (!points.length) {
                html = '<em>暂无数据</em>';
            } else {
                html = '<table style="font-size:0.8rem;width:100%;">';
                html += '<tr><th>数据点</th><th>数值</th><th>时间</th></tr>';
                points.slice(0, 5).forEach(function(p) {
                    html += '<tr>' +
                        '<td>' + (p.name || '-') + '</td>' +
                        '<td>' + formatNumber(p.value, 4) + '</td>' +
                        '<td>' + formatDateTime(p.timestamp) + '</td>' +
                    '</tr>';
                });
                html += '</table>';
            }
            // Update the info window content by rebuilding
            const contentDiv = document.getElementById('popup-data-' + deviceId);
            if (contentDiv) {
                contentDiv.innerHTML = html;
            }
        }).catch(function() {
            const contentDiv = document.getElementById('popup-data-' + deviceId);
            if (contentDiv) {
                contentDiv.innerHTML = '<em>加载失败</em>';
            }
        });
    }

    function clearMarkers() {
        markers.forEach(function(marker) {
            map.removeOverlay(marker);
        });
        markers = [];
    }

    window.fitAllMarkers = function() {
        if (!map || markers.length === 0) return;
        if (markers.length === 1) {
            map.centerAndZoom(markers[0].getPosition(), 14);
            return;
        }
        const points = markers.map(function(m) { return m.getPosition(); });
        const view = map.getViewport(points);
        map.centerAndZoom(view.center, view.zoom);
    };

    window.refreshMapData = function() {
        loadDeviceMarkers();
        showToast('地图数据已刷新', 'success');
    };
})();
