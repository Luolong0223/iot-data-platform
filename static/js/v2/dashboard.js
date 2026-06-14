/**
 * 仪表盘 JS
 * 功能: 展示用户选择的数据点, 实时刷新
 */
(function() {
    'use strict';

    const REFRESH_INTERVAL = 3000; // 3秒自动刷新
    let refreshTimer = null;
    let allAvailablePoints = []; // 缓存可添加的数据点

    // ================= 初始化 =================
    document.addEventListener('DOMContentLoaded', () => {
        loadDashboard();
        loadAvailablePoints();
        bindEvents();
        startAutoRefresh();
        console.log('Dashboard initialized');
    });

    // ================= 加载仪表盘数据 =================
    async function loadDashboard() {
        try {
            const r = await apiRequest('/api/dashboard/data');
            if (!r.success) {
                console.error('加载仪表盘失败', r);
                return;
            }
            renderDashboard(r.data);
        } catch (e) {
            console.error('loadDashboard 异常', e);
        }
    }

    // ================= 渲染仪表盘 =================
    function renderDashboard(data) {
        // 汇总卡片
        const summary = data.summary || {};
        document.getElementById('totalDevices').textContent = summary.total_devices ?? 0;
        document.getElementById('onlineDevices').textContent = summary.online_devices ?? 0;
        document.getElementById('offlineDevices').textContent = summary.offline_devices ?? 0;
        document.getElementById('totalWidgets').textContent = summary.total_widgets ?? 0;

        // 最近更新时间
        const widgets = data.widgets || [];
        let latestTime = null;
        widgets.forEach(w => {
            if (w.last_updated && (!latestTime || w.timestamp > latestTime)) {
                latestTime = w.last_updated;
            }
        });
        if (latestTime) {
            const t = new Date(latestTime);
            document.getElementById('latestUpdate').textContent = formatRelativeTime(t);
            document.getElementById('latestUpdate').title = t.toLocaleString();
        } else {
            document.getElementById('latestUpdate').textContent = '--';
        }

        // 渲染 widget 卡片
        renderWidgets(widgets);
    }

    // ================= 渲染 widgets 卡片 =================
    function renderWidgets(widgets) {
        const container = document.getElementById('widgetsContainer');
        const emptyState = document.getElementById('emptyState');

        // 移除所有现有 widget 卡片
        Array.from(container.querySelectorAll('.widget-card')).forEach(el => el.remove());

        if (widgets.length === 0) {
            emptyState.style.display = 'block';
            return;
        }
        emptyState.style.display = 'none';

        widgets.forEach(w => {
            const col = document.createElement('div');
            col.className = 'col-xl-3 col-lg-4 col-md-6 widget-card';
            col.setAttribute('data-widget-id', w.widget_id);

            const valueText = (w.value === null || w.value === undefined) ? '--' : formatNumber(w.current_value);
            const lastTime = w.last_updated ? formatRelativeTime(new Date(w.timestamp)) : '从未';
            const onlineClass = w.device_online ? 'text-success' : 'text-danger';
            const onlineText = w.device_online ? '在线' : '离线';

            col.innerHTML = `
                <div class="card h-100 widget-card-inner">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <div class="widget-title">${escapeHtml(w.data_point_name)}</div>
                                <div class="widget-subtitle">
                                    <i class="bi bi-hdd"></i> ${escapeHtml(w.device_name)}
                                    <span class="text-muted mx-1">·</span>
                                    <i class="bi bi-broadcast"></i> ${escapeHtml(w.channel_name)}
                                </div>
                            </div>
                            <button class="btn btn-sm btn-link text-muted p-0 widget-remove" title="移除">
                                <i class="bi bi-x-lg"></i>
                            </button>
                        </div>
                        <div class="widget-value-row">
                            <span class="widget-value">${valueText}</span>
                            <span class="widget-unit">${escapeHtml(w.unit || '')}</span>
                        </div>
                        <div class="widget-meta">
                            <span class="${onlineClass}">
                                <i class="bi bi-circle-fill" style="font-size:0.5rem;"></i> ${onlineText}
                            </span>
                            <span class="text-muted ms-2">${lastTime}</span>
                            ${w.device_voltage_mv !== null && w.device_voltage_mv !== undefined ?
                                `<span class="text-muted ms-2"><i class="bi bi-lightning"></i> ${w.device_voltage_mv} mV</span>` : ''}
                        </div>
                    </div>
                </div>
            `;

            // 删除按钮
            col.querySelector('.widget-remove').addEventListener('click', () => {
                if (confirm('确定从仪表盘移除该数据点吗?')) {
                    removeWidget(w.widget_id);
                }
            });

            container.appendChild(col);
        });
    }

    // ================= 加载可添加的数据点 =================
    async function loadAvailablePoints() {
        try {
            const r = await apiRequest('/api/dashboard/available-points');
            if (!r.success) return;
            allAvailablePoints = r.data;
        } catch (e) {
            console.error('loadAvailablePoints 失败', e);
        }
    }

    // ================= 渲染可添加列表 (Modal内) =================
    function renderAvailableList(keyword = '') {
        const container = document.getElementById('deviceListContainer');
        const kw = keyword.toLowerCase();
        const filtered = kw ? allAvailablePoints.filter(d => {
            if (d.name.toLowerCase().includes(kw) || d.display_name.toLowerCase().includes(kw)) return true;
            return d.channels.some(c => c.data_points.some(dp => dp.name.toLowerCase().includes(kw)));
        }) : allAvailablePoints;

        if (filtered.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">没有匹配的数据点</div>';
            return;
        }

        const html = filtered.map(d => {
            const channelHtml = d.channels.map(c => {
                if (c.data_points.length === 0) return '';
                const dpHtml = c.data_points.map(dp => `
                    <button class="btn btn-sm ${dp.is_added ? 'btn-success' : 'btn-outline-light'} me-1 mb-1 add-point-btn"
                            data-device-id="${d.id}" data-channel-id="${c.id}" data-point-id="${dp.id}"
                            ${dp.is_added ? 'disabled' : ''}>
                        <i class="bi bi-${dp.is_added ? 'check' : 'plus'}"></i> ${escapeHtml(dp.name)}
                        ${dp.latest_value !== null ? `<span class="text-muted small ms-1">${formatNumber(dp.latest_value)}</span>` : ''}
                    </button>
                `).join('');
                return `
                    <div class="mb-2 ps-3">
                        <div class="text-muted small">
                            <i class="bi bi-broadcast"></i> ${escapeHtml(c.name)}
                            <span class="badge bg-${c.is_online ? 'success' : 'secondary'} ms-1" style="font-size:0.6rem;">${c.is_online ? '在线' : '离线'}</span>
                        </div>
                        <div class="mt-1">${dpHtml}</div>
                    </div>
                `;
            }).join('');

            return `
                <div class="device-block mb-3 pb-2 border-bottom border-secondary">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-hdd text-primary me-2"></i>
                        <strong>${escapeHtml(d.display_name || d.name)}</strong>
                        <span class="text-muted small ms-2">(${escapeHtml(d.name)})</span>
                        <span class="badge bg-${d.is_online ? 'success' : 'secondary'} ms-2" style="font-size:0.6rem;">${d.is_online ? '在线' : '离线'}</span>
                        ${d.voltage_mv ? `<span class="text-muted small ms-2">${d.voltage_mv} mV</span>` : ''}
                    </div>
                    ${channelHtml}
                </div>
            `;
        }).join('');

        container.innerHTML = html || '<div class="text-center text-muted py-4">没有可用的数据点(请先通过 TCP 接收数据)</div>';

        // 绑定添加按钮
        container.querySelectorAll('.add-point-btn:not([disabled])').forEach(btn => {
            btn.addEventListener('click', async () => {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
                const r = await apiRequest('/api/dashboard/widgets', 'POST', {
                    device_id: parseInt(btn.dataset.deviceId),
                    channel_id: parseInt(btn.dataset.channelId),
                    data_point_id: parseInt(btn.dataset.pointId)
                });
                if (r.success) {
                    btn.classList.remove('btn-outline-light');
                    btn.classList.add('btn-success');
                    btn.innerHTML = '<i class="bi bi-check"></i> 已添加';
                    loadDashboard();
                } else {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-plus"></i> 重试';
                    alert('添加失败: ' + (r.error || '未知错误'));
                }
            });
        });
    }

    // ================= 添加 widget =================
    async function addWidget(device_id, channel_id, data_point_name) {
        const r = await apiRequest('/api/dashboard/widgets', 'POST', { device_id, channel_id, data_point_name });
        return r.success;
    }

    // ================= 删除 widget =================
    async function removeWidget(widget_id) {
        const r = await apiRequest(`/api/dashboard/widgets/${widget_id}`, 'DELETE');
        if (r.success) {
            loadDashboard();
        } else {
            alert('删除失败: ' + (r.error || '未知错误'));
        }
    }

    // ================= 事件绑定 =================
    function bindEvents() {
        // 添加数据点按钮
        document.getElementById('addWidgetBtn').addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('addWidgetModal'));
            renderAvailableList();
            modal.show();
        });

        // 搜索框
        document.getElementById('searchDataPoint').addEventListener('input', (e) => {
            renderAvailableList(e.target.value);
        });

        // 立即刷新
        document.getElementById('refreshNowBtn').addEventListener('click', loadDashboard);

        // 自动刷新切换
        document.getElementById('autoRefreshToggle').addEventListener('change', (e) => {
            if (e.target.checked) {
                startAutoRefresh();
            } else {
                stopAutoRefresh();
            }
        });
    }

    // ================= 自动刷新 =================
    function startAutoRefresh() {
        stopAutoRefresh();
        refreshTimer = setInterval(loadDashboard, REFRESH_INTERVAL);
    }
    function stopAutoRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }

    // ================= 工具函数 =================
    function escapeHtml(s) {
        if (s === null || s === undefined) return '';
        return String(s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    function formatNumber(v) {
        if (typeof v !== 'number') return v;
        if (Number.isInteger(v)) return v.toString();
        return v.toFixed(3).replace(/\.?0+$/, '');
    }

    function formatRelativeTime(date) {
        const now = new Date();
        const diff = (now - date) / 1000;
        if (diff < 5) return '刚刚';
        if (diff < 60) return Math.floor(diff) + '秒前';
        if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
        return Math.floor(diff / 86400) + '天前';
    }
})();
