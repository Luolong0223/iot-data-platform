/**
 * Dashboard - IoT 数据平台增强版仪表盘
 */

// 全局变量
let trendChart = null;
let realtimePaused = false;
let dataStreamCount = 0;
let lastDataId = 0;

// 初始化
$(document).ready(function() {
    initDashboard();
    initTrendChart();
    initRealtimeStream();
    initEventListeners();
    
    // 定时刷新统计数据
    setInterval(refreshStats, 30000);
});

// 初始化仪表盘
function initDashboard() {
    refreshStats();
    loadRecentAlarms();
    loadDeviceStatus();
    loadDeviceRanking();
}

// 刷新统计数据
function refreshStats() {
    $.get('/api/dashboard/stats')
        .done(function(res) {
            if (res.success) {
                const data = res.data;
                
                // 设备统计
                $('#statDevices').text(data.devices.total);
                $('#statOnline').text(data.devices.online);
                $('#statOffline').text(data.devices.offline);
                
                // 数据统计
                $('#statToday').text(formatNumber(data.data_points.today));
                
                // 报警统计
                $('#statAlarms').text(data.alarms.today);
                
                // 电压状态
                updateVoltageStatus();
            }
        })
        .fail(function(err) {
            console.error('获取统计数据失败:', err);
        });
}

// 初始化趋势图表
function initTrendChart() {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;
    
    trendChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '数据量',
                data: [],
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 2,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 12
                    }
                },
                y: {
                    display: true,
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.05)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
    
    loadTrendData(24);
}

// 加载趋势数据
function loadTrendData(hours) {
    $.get('/api/dashboard/trend', { hours: hours })
        .done(function(res) {
            if (res.success && trendChart) {
                const labels = res.data.map(d => d.time.split(' ')[1] || d.time);
                const data = res.data.map(d => d.count);
                
                trendChart.data.labels = labels;
                trendChart.data.datasets[0].data = data;
                trendChart.update('none');
            }
        })
        .fail(function(err) {
            console.error('获取趋势数据失败:', err);
        });
}

// 初始化实时数据流
function initRealtimeStream() {
    // 先加载最近的数据
    $.get('/api/dashboard/recent-data', { limit: 30 })
        .done(function(res) {
            if (res.success) {
                const list = $('#realtimeDataList');
                list.empty();
                
                res.data.reverse().forEach(function(item) {
                    addDataItem(item, false);
                    lastDataId = Math.max(lastDataId, item.id);
                });
            }
        })
        .fail(function(err) {
            console.error('获取最近数据失败:', err);
        });
    
    // 启动SSE实时推送
    startSSEStream();
}

// 启动SSE数据流
function startSSEStream() {
    const eventSource = new EventSource('/api/realtime/stream');
    
    eventSource.onopen = function() {
        $('#sseStatus').html('<i class="bi bi-broadcast"></i> 实时连接中').removeClass('bg-danger').addClass('bg-success');
    };
    
    eventSource.onmessage = function(event) {
        if (realtimePaused) return;
        
        try {
            const data = JSON.parse(event.data);
            if (data && data.id) {
                addDataItem(data, true);
                dataStreamCount++;
                updateStreamCount();
            }
        } catch (e) {
            // 忽略解析错误
        }
    };
    
    eventSource.onerror = function() {
        $('#sseStatus').html('<i class="bi bi-broadcast"></i> 连接断开').removeClass('bg-success').addClass('bg-danger');
        
        // 5秒后重连
        setTimeout(function() {
            eventSource.close();
            startSSEStream();
        }, 5000);
    };
}

// 添加数据项到实时列表
function addDataItem(item, animate) {
    const list = $('#realtimeDataList');
    
    const itemHtml = `
        <li class="list-group-item data-stream-item ${animate ? 'new-item' : ''}" style="font-size: 0.8rem;">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge bg-secondary me-1">${item.device_name || '-'}</span>
                    <span class="text-muted">${item.channel_name || '-'}</span>
                </div>
                <small class="text-muted">${item.timestamp ? item.timestamp.split(' ')[1] || item.timestamp : ''}</small>
            </div>
            <div class="mt-1">
                <strong>${item.data_key}:</strong> 
                <span class="text-primary">${formatValue(item.data_value)}</span>
            </div>
        </li>
    `;
    
    if (animate) {
        list.prepend(itemHtml);
        
        // 移除动画类
        setTimeout(function() {
            list.find('.new-item').removeClass('new-item');
        }, 500);
        
        // 限制列表长度
        while (list.children().length > 50) {
            list.children().last().remove();
        }
    } else {
        list.append(itemHtml);
    }
}

// 更新电压状态
function updateVoltageStatus() {
    $.get('/api/devices')
        .done(function(res) {
            if (res.success && res.data && res.data.length > 0) {
                // 找最新的电压值
                let minVoltage = Infinity;
                res.data.forEach(function(device) {
                    if (device.voltage_mv && device.voltage_mv < minVoltage) {
                        minVoltage = device.voltage_mv;
                    }
                });
                
                if (minVoltage !== Infinity) {
                    const voltageStatus = minVoltage < 3000 ? '偏低' : (minVoltage < 3500 ? '正常' : '良好');
                    const voltageClass = minVoltage < 3000 ? 'text-warning' : 'text-success';
                    $('#statVoltage').html(`<span class="${voltageClass}">${minVoltage}mV</span>`);
                }
            }
        });
}

// 加载最近报警
function loadRecentAlarms() {
    $.get('/api/dashboard/recent-alarms', { limit: 5 })
        .done(function(res) {
            if (res.success) {
                const list = $('#recentAlarmList');
                list.empty();
                
                if (res.data.length === 0) {
                    list.html('<li class="list-group-item text-center text-muted py-4">暂无报警</li>');
                    return;
                }
                
                res.data.forEach(function(alarm) {
                    const levelClass = {
                        'critical': 'danger',
                        'warning': 'warning',
                        'info': 'info'
                    }[alarm.alarm_level] || 'secondary';
                    
                    const iconClass = {
                        'voltage': 'bi-lightning',
                        'offline': 'bi-wifi-off',
                        'data': 'bi-exclamation-triangle',
                        'threshold': 'bi-speedometer'
                    }[alarm.alarm_type] || 'bi-bell';
                    
                    list.append(`
                        <li class="list-group-item alarm-item">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <span class="badge bg-${levelClass} me-2"><i class="bi ${iconClass}"></i></span>
                                    <strong>${alarm.device_name || '未知设备'}</strong>
                                    <p class="mb-0 small text-muted">${alarm.message}</p>
                                </div>
                                <small class="text-muted">${formatTime(alarm.created_at)}</small>
                            </div>
                        </li>
                    `);
                });
            }
        })
        .fail(function(err) {
            console.error('获取报警失败:', err);
        });
}

// 加载设备状态
function loadDeviceStatus() {
    $.get('/api/devices')
        .done(function(res) {
            if (res.success) {
                const list = $('#deviceStatusList');
                list.empty();
                
                if (res.data.length === 0) {
                    list.html('<li class="list-group-item text-center text-muted py-4">暂无设备</li>');
                    return;
                }
                
                // 只显示前5个
                const devices = res.data.slice(0, 5);
                
                devices.forEach(function(device) {
                    const statusClass = device.is_online ? 'success' : 'danger';
                    const statusText = device.is_online ? '在线' : '离线';
                    
                    list.append(`
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <span class="badge bg-${statusClass} badge-online me-2">${statusText}</span>
                                <strong>${device.name}</strong>
                            </div>
                            <div>
                                ${device.voltage_mv ? `<small class="text-muted me-2">${device.voltage_mv}mV</small>` : ''}
                                <small class="text-muted">${device.channel_count || 0} 通道</small>
                            </div>
                        </li>
                    `);
                });
            }
        })
        .fail(function(err) {
            console.error('获取设备状态失败:', err);
        });
}

// 加载设备排行
function loadDeviceRanking() {
    $.get('/api/dashboard/device-ranking', { limit: 5 })
        .done(function(res) {
            if (res.success) {
                // 可以在需要的地方显示
            }
        });
}

// 更新数据流计数
function updateStreamCount() {
    // 可以在页面上显示每分钟数据量
}

// 初始化事件监听
function initEventListeners() {
    // 图表时间范围切换
    $('#chartPeriod').on('change', function() {
        const period = $(this).val();
        const hours = {
            '24h': 24,
            '7d': 24 * 7,
            '30d': 24 * 30
        }[period] || 24;
        
        loadTrendData(hours);
    });
    
    // 暂停/恢复实时数据
    $('#pauseStream').on('click', function() {
        realtimePaused = !realtimePaused;
        $(this).html(realtimePaused ? '<i class="bi bi-play-fill"></i>' : '<i class="bi bi-pause-fill"></i>');
        $(this).toggleClass('btn-warning', realtimePaused).toggleClass('btn-outline-secondary', !realtimePaused);
    });
}

// 格式化数字
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// 格式化值
function formatValue(val) {
    if (val === null || val === undefined) return '-';
    const num = parseFloat(val);
    return isNaN(num) ? val : num.toFixed(4);
}

// 格式化时间
function formatTime(timeStr) {
    if (!timeStr) return '';
    const parts = timeStr.split(' ');
    return parts.length > 1 ? parts[1] : parts[0];
}

// 显示加载状态
function showLoading(selector) {
    $(selector).html('<div class="text-center py-3"><div class="loading-spinner"></div></div>');
}

// 显示错误
function showError(selector, message) {
    $(selector).html(`<div class="text-center text-danger py-3"><i class="bi bi-exclamation-circle"></i> ${message}</div>`);
}
