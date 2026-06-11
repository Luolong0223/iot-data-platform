/**
 * IoT Data Platform - Map JavaScript
 * Leaflet map initialization, device markers, popup content
 */

(function() {
    'use strict';

    let map = null;
    let markers = [];
    let markerLayer = null;

    window.initMap = function(elementId, lat, lng, zoom) {
        if (map) return;
        map = L.map(elementId).setView([lat, lng], zoom);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(map);
        markerLayer = L.layerGroup().addTo(map);
    };

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
        const onlineCount = device.channels ? device.channels.filter(function(c) { return c.online; }).length : 0;
        const totalChannels = device.channels ? device.channels.length : 0;
        const color = totalChannels > 0 && onlineCount === totalChannels ? '#27ae60' :
                      onlineCount > 0 ? '#f39c12' : '#e74c3c';

        const icon = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background-color:' + color + ';width:16px;height:16px;border-radius:50%;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>',
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });

        const marker = L.marker([device.latitude, device.longitude], { icon: icon }).addTo(markerLayer);
        marker.deviceId = device.id;

        const popupContent = buildPopupContent(device, onlineCount, totalChannels);
        marker.bindPopup(popupContent, { maxWidth: 320 });

        marker.on('click', function() {
            loadLatestDataForPopup(device.id, marker);
        });

        markers.push(marker);
    }

    function buildPopupContent(device, onlineCount, totalChannels) {
        let html = '<div class="map-popup">' +
            '<div class="popup-title">' + (device.name || '未命名设备') + '</div>' +
            '<div class="popup-data">' +
                '<div><span class="label">ID:</span> ' + device.id + '</div>' +
                '<div><span class="label">电压:</span> ' + (device.voltage_mv || '-') + ' mV</div>' +
                '<div><span class="label">位置:</span> ' + (device.location_name || '-') + '</div>' +
                '<div><span class="label">通道:</span> ' + onlineCount + '/' + totalChannels + ' 在线</div>' +
                '<hr style="margin:0.5rem 0;">' +
                '<div id="popup-data-' + device.id + '"><em>点击加载最新数据...</em></div>' +
            '</div>' +
        '</div>';
        return html;
    }

    function loadLatestDataForPopup(deviceId, marker) {
        apiRequest('/api/data/latest?device_id=' + deviceId).then(function(data) {
            const container = document.getElementById('popup-data-' + deviceId);
            if (!container) return;
            const points = data.data_points || [];
            if (!points.length) {
                container.innerHTML = '<em>暂无数据</em>';
                return;
            }
            let html = '<table style="font-size:0.8rem;width:100%;">';
            html += '<tr><th>数据点</th><th>数值</th><th>时间</th></tr>';
            points.slice(0, 5).forEach(function(p) {
                html += '<tr>' +
                    '<td>' + p.name + '</td>' +
                    '<td>' + formatNumber(p.value, 4) + '</td>' +
                    '<td>' + formatDateTime(p.timestamp) + '</td>' +
                '</tr>';
            });
            html += '</table>';
            container.innerHTML = html;
            marker.setPopupContent(marker.getPopup().getContent().replace(
                /<div id="popup-data-[^"]*">.*?<\/div>/,
                '<div id="popup-data-' + deviceId + '">' + html + '</div>'
            ));
        }).catch(function() {
            const container = document.getElementById('popup-data-' + deviceId);
            if (container) container.innerHTML = '<em>加载失败</em>';
        });
    }

    function clearMarkers() {
        if (markerLayer) {
            markerLayer.clearLayers();
        }
        markers = [];
    }

    window.fitAllMarkers = function() {
        if (!map || markers.length === 0) return;
        if (markers.length === 1) {
            map.setView(markers[0].getLatLng(), 14);
            return;
        }
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.2));
    };

    window.refreshMapData = function() {
        loadDeviceMarkers();
        showToast('地图数据已刷新', 'success');
    };
})();
