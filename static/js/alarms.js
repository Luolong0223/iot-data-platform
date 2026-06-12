/**
 * IoT Data Platform - Alarms JavaScript
 * Enhanced alarm management with real-time updates and statistics
 */

(function() {
    'use strict';

    let rulesTable = null;
    let ruleModal = null;
    let alarmDetailModal = null;
    let eventSource = null;
    let currentAlarmId = null;
    let alarmTypeChart = null;
    let alarmTrendChart = null;
    let deviceAlarmChart = null;

    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        ruleModal = new bootstrap.Modal(document.getElementById('ruleModal'));
        alarmDetailModal = new bootstrap.Modal(document.getElementById('alarmDetailModal'));

        // Load initial data
        loadAlarmStats();
        loadAlarmList();
        initRulesTable();
        initCharts();

        // Start SSE connection
        connectSSE();

        // Filter handlers
        document.getElementById('levelFilter').addEventListener('change', loadAlarmList);
        document.getElementById('statusFilter').addEventListener('change', loadAlarmList);
    });

    // Load alarm statistics
    function loadAlarmStats() {
        apiRequest('/api/alarms/stats').then(function(data) {
            document.getElementById('statCritical').textContent = data.critical || 0;
            document.getElementById('statWarning').textContent = data.warning || 0;
            document.getElementById('statInfo').textContent = data.info || 0;
            document.getElementById('statResolved').textContent = data.resolved || 0;
            document.getElementById('unreadBadge').textContent = (data.critical + data.warning + data.info) + ' 未读';
        }).catch(function(err) {
            console.error('Load stats failed:', err);
        });
    }

    // Load alarm list
    function loadAlarmList() {
        const level = document.getElementById('levelFilter').value;
        const status = document.getElementById('statusFilter').value;

        let url = '/api/alarms/records?limit=50';
        if (level) url += '&level=' + level;
        if (status) url += '&status=' + status;

        const container = document.getElementById('alarmList');
        container.innerHTML = '<div class="text-center text-muted py-5"><div class="loading-spinner"></div></div>';

        apiRequest(url).then(function(data) {
            const records = data.records || [];
            if (records.length === 0) {
                container.innerHTML = '<div class="text-center text-muted py-5"><i class="bi bi-check-circle text-success" style="font-size: 2rem;"></i><p class="mt-2">暂无报警记录</p></div>';
                return;
            }

            let html = '';
            records.forEach(function(record) {
                const levelClass = getLevelClass(record.level);
                const levelIcon = getLevelIcon(record.level);
                const timeAgo = formatTimeAgo(record.created_at);

                html += '<div class="list-group-item list-group-item-action d-flex align-items-start gap-3 ' + (record.is_read ? 'opacity-50' : '') + '" onclick="showAlarmDetail(' + record.id + ')">';
                html += '<div class="alarm-indicator ' + levelClass + '"></div>';
                html += '<div class="flex-grow-1">';
                html += '<div class="d-flex justify-content-between">';
                html += '<strong>' + (record.message || '报警') + '</strong>';
                html += '<small class="text-muted">' + timeAgo + '</small>';
                html += '</div>';
                html += '<small class="text-muted">' + (record.device_name || '') + ' - ' + (record.point_name || '') + '</small>';
                html += '<div class="mt-1"><span class="badge ' + levelClass + '">' + (record.level || 'warning') + '</span>';
                if (!record.is_read) {
                    html += ' <span class="badge bg-secondary">未读</span>';
                }
                html += '</div></div></div>';
            });

            container.innerHTML = html;
        }).catch(function(err) {
            console.error('Load alarms failed:', err);
            container.innerHTML = '<div class="text-center text-danger py-5"><i class="bi bi-exclamation-triangle"></i><p class="mt-2">加载失败</p></div>';
        });
    }

    // Initialize rules table
    function initRulesTable() {
        rulesTable = $('#rulesTable').DataTable({
            ajax: {
                url: '/api/alarms/rules',
                dataSrc: 'rules'
            },
            columns: [
                { data: 'id' },
                { data: 'device_name' },
                { data: 'channel_name' },
                { data: 'point_name' },
                { data: 'condition', render: function(data) {
                    const condMap = {
                        'gt': '大于',
                        'lt': '小于',
                        'gte': '大于等于',
                        'lte': '小于等于',
                        'eq': '等于',
                        'neq': '不等于'
                    };
                    return condMap[data] || data;
                }},
                { data: 'threshold', render: function(data) {
                    return parseFloat(data).toFixed(2);
                }},
                { data: 'enabled', render: function(data) {
                    return data ? '<span class="badge bg-success">启用</span>' : '<span class="badge bg-secondary">禁用</span>';
                }},
                { data: null, orderable: false, render: function(data) {
                    return '<button class="btn btn-sm btn-outline-primary me-1" onclick="editRule(' + data.id + ')"><i class="bi bi-pencil"></i></button>' +
                           '<button class="btn btn-sm btn-outline-danger" onclick="deleteRule(' + data.id + ')"><i class="bi bi-trash"></i></button>';
                }}
            ],
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/zh.json'
            }
        });
    }

    // Initialize charts
    function initCharts() {
        // Type distribution chart
        const typeCtx = document.getElementById('alarmTypeChart').getContext('2d');
        alarmTypeChart = new Chart(typeCtx, {
            type: 'doughnut',
            data: {
                labels: ['严重', '警告', '提示'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#dc3545', '#ffc107', '#0dcaf0']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // Trend chart
        const trendCtx = document.getElementById('alarmTrendChart').getContext('2d');
        alarmTrendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '报警数量',
                    data: [],
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Device alarm chart
        const deviceCtx = document.getElementById('deviceAlarmChart').getContext('2d');
        deviceAlarmChart = new Chart(deviceCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: '报警次数',
                    data: [],
                    backgroundColor: '#6c757d'
                }]
            },
            options: {
                responsive: true,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Load chart data
        loadChartData();
    }

    // Load chart data
    function loadChartData() {
        apiRequest('/api/alarms/stats/chart').then(function(data) {
            // Update type chart
            if (data.by_level) {
                alarmTypeChart.data.datasets[0].data = [
                    data.by_level.critical || 0,
                    data.by_level.warning || 0,
                    data.by_level.info || 0
                ];
                alarmTypeChart.update();
            }

            // Update trend chart
            if (data.trend && data.trend.length > 0) {
                alarmTrendChart.data.labels = data.trend.map(function(d) { return d.date; });
                alarmTrendChart.data.datasets[0].data = data.trend.map(function(d) { return d.count; });
                alarmTrendChart.update();
            }

            // Update device chart
            if (data.by_device && data.by_device.length > 0) {
                deviceAlarmChart.data.labels = data.by_device.slice(0, 10).map(function(d) { return d.device_name; });
                deviceAlarmChart.data.datasets[0].data = data.by_device.slice(0, 10).map(function(d) { return d.count; });
                deviceAlarmChart.update();
            }
        }).catch(function(err) {
            console.error('Load chart data failed:', err);
        });
    }

    // SSE connection for real-time updates
    function connectSSE() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource('/api/realtime/stream');

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);

            // Handle alarm events
            if (data.type === 'alarm') {
                showToast('报警: ' + data.message, 'warning');
                playAlarmSound();
                loadAlarmStats();
                loadAlarmList();
                loadChartData();
            }
        };

        eventSource.onerror = function(err) {
            console.error('SSE error:', err);
            // Reconnect after 5 seconds
            setTimeout(connectSSE, 5000);
        };
    }

    // Play alarm sound
    function playAlarmSound() {
        // Create a simple beep sound using Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            gainNode.gain.value = 0.3;

            oscillator.start();
            setTimeout(function() { oscillator.stop(); }, 200);
        } catch (e) {
            console.log('Audio not supported');
        }
    }

    // Show alarm detail
    window.showAlarmDetail = function(id) {
        currentAlarmId = id;
        apiRequest('/api/alarms/records/' + id).then(function(record) {
            let html = '<table class="table table-sm">';
            html += '<tr><th>设备</th><td>' + (record.device_name || '-') + '</td></tr>';
            html += '<tr><th>通道</th><td>' + (record.channel_name || '-') + '</td></tr>';
            html += '<tr><th>数据点</th><td>' + (record.point_name || '-') + '</td></tr>';
            html += '<tr><th>实际值</th><td>' + (record.actual_value !== undefined ? record.actual_value.toFixed(4) : '-') + '</td></tr>';
            html += '<tr><th>阈值</th><td>' + (record.threshold !== undefined ? record.threshold.toFixed(4) : '-') + '</td></tr>';
            html += '<tr><th>条件</th><td>' + record.condition + '</td></tr>';
            html += '<tr><th>级别</th><td><span class="badge ' + getLevelClass(record.level) + '">' + record.level + '</span></td></tr>';
            html += '<tr><th>时间</th><td>' + formatDateTime(record.created_at) + '</td></tr>';
            html += '<tr><th>消息</th><td>' + (record.message || '-') + '</td></tr>';
            html += '</table>';

            document.getElementById('alarmDetailContent').innerHTML = html;
            alarmDetailModal.show();
        }).catch(function(err) {
            showToast('获取详情失败', 'error');
        });
    };

    // Mark current alarm as read
    window.markCurrentRead = function() {
        if (currentAlarmId) {
            markRecordRead(currentAlarmId);
            alarmDetailModal.hide();
        }
    };

    // Open modal for new rule
    window.openRuleModal = function() {
        document.getElementById('ruleId').value = '';
        document.getElementById('ruleForm').reset();
        document.getElementById('ruleModalTitle').textContent = '新增报警规则';
        ruleModal.show();
    };

    // Edit rule
    window.editRule = function(id) {
        apiRequest('/api/alarms/rules').then(function(data) {
            const rules = data.rules || [];
            const rule = rules.find(function(r) { return r.id === id; });
            if (!rule) {
                showToast('规则不存在', 'error');
                return;
            }
            document.getElementById('ruleId').value = rule.id;
            document.getElementById('ruleDeviceName').value = rule.device_name || '';
            document.getElementById('ruleChannelName').value = rule.channel_name || '';
            document.getElementById('rulePointName').value = rule.point_name || '';
            document.getElementById('ruleCondition').value = rule.condition || 'gt';
            document.getElementById('ruleThreshold').value = rule.threshold || 0;
            document.getElementById('ruleLevel').value = rule.level || 'warning';
            document.getElementById('ruleEnabled').checked = rule.enabled !== false;
            document.getElementById('ruleModalTitle').textContent = '编辑报警规则';
            ruleModal.show();
        });
    };

    // Save rule
    window.saveRule = function() {
        const id = document.getElementById('ruleId').value;
        const data = {
            device_name: document.getElementById('ruleDeviceName').value,
            channel_name: document.getElementById('ruleChannelName').value,
            point_name: document.getElementById('rulePointName').value,
            condition: document.getElementById('ruleCondition').value,
            threshold: parseFloat(document.getElementById('ruleThreshold').value),
            level: document.getElementById('ruleLevel').value,
            enabled: document.getElementById('ruleEnabled').checked
        };

        const url = id ? '/api/alarms/rules/' + id : '/api/alarms/rules';
        const method = id ? 'PUT' : 'POST';

        apiRequest(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).then(function(result) {
            showToast(id ? '规则已更新' : '规则已创建', 'success');
            ruleModal.hide();
            rulesTable.ajax.reload();
        }).catch(function(err) {
            showToast('保存失败: ' + err.message, 'error');
        });
    };

    // Delete rule
    window.deleteRule = function(id) {
        if (!confirm('确定要删除这条规则吗？')) return;

        apiRequest('/api/alarms/rules/' + id, {
            method: 'DELETE'
        }).then(function() {
            showToast('规则已删除', 'success');
            rulesTable.ajax.reload();
        }).catch(function(err) {
            showToast('删除失败', 'error');
        });
    };

    // Mark record as read
    window.markRecordRead = function(id) {
        apiRequest('/api/alarms/records/' + id + '/read', {
            method: 'POST'
        }).then(function() {
            loadAlarmStats();
            loadAlarmList();
            showToast('已标记为已读', 'success');
        }).catch(function(err) {
            showToast('操作失败', 'error');
        });
    };

    // Mark all as read
    window.markAllRead = function() {
        if (!confirm('确定要将所有报警标记为已读吗？')) return;

        apiRequest('/api/alarms/records/read-all', {
            method: 'POST'
        }).then(function() {
            loadAlarmStats();
            loadAlarmList();
            showToast('全部已标记为已读', 'success');
        }).catch(function(err) {
            showToast('操作失败', 'error');
        });
    };

    // Clear all read alarms
    window.clearAllAlarms = function() {
        if (!confirm('确定要清空所有已读的报警记录吗？')) return;

        apiRequest('/api/alarms/records/clear-read', {
            method: 'POST'
        }).then(function() {
            loadAlarmStats();
            loadAlarmList();
            showToast('已清空已读记录', 'success');
        }).catch(function(err) {
            showToast('操作失败', 'error');
        });
    };

    // Refresh alarms
    window.refreshAlarms = function() {
        loadAlarmStats();
        loadAlarmList();
        loadChartData();
        showToast('已刷新', 'success');
    };

    // Helper functions
    function getLevelClass(level) {
        const classes = {
            'critical': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info'
        };
        return classes[level] || 'bg-secondary';
    }

    function getLevelIcon(level) {
        const icons = {
            'critical': 'exclamation-triangle-fill',
            'warning': 'exclamation-circle-fill',
            'info': 'info-circle-fill'
        };
        return icons[level] || 'bell-fill';
    }

    function formatTimeAgo(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (diff < 60) return '刚刚';
        if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
        return Math.floor(diff / 86400) + ' 天前';
    }
})();
