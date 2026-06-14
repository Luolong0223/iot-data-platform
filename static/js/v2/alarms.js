// 告警管理页面
(function() {
    'use strict';

    // 状态
    let currentPage = 1;
    const pageSize = 15;
    let currentAlarmId = null;

    // 初始化
    document.addEventListener('DOMContentLoaded', function() {
        loadAlarmStats();
        loadAlarms();
        loadRules();
        loadDevices();
        initTrendChart();
        
        // 自动刷新（30秒）
        setInterval(loadAlarms, 30000);
        setInterval(loadAlarmStats, 30000);
    });

    // 加载告警统计
    function loadAlarmStats() {
        api.get('/api/alarms/stats').then(res => {
            if (res.success) {
                updateElement('critical-count', res.data.critical || 0);
                updateElement('warning-count', res.data.warning || 0);
                updateElement('info-count', res.data.info || 0);
                updateElement('resolved-count', res.data.resolved_today || 0);
            }
        }).catch(err => {
            console.error('加载统计失败:', err);
        });
    }

    // 加载告警列表
    function loadAlarms() {
        const severity = document.getElementById('severity-filter').value;
        const status = document.getElementById('status-filter').value;
        
        let url = `/api/alarms/records?page=${currentPage}&per_page=${pageSize}`;
        if (severity) url += `&severity=${severity}`;
        if (status) url += `&status=${status}`;
        
        api.get(url).then(res => {
            renderAlarmsTable(res.data.items || []);
            renderPagination(res.data.total || 0);
        }).catch(err => {
            console.error('加载告警失败:', err);
            document.getElementById('alarms-tbody').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">加载失败</td></tr>';
        });
    }

    // 渲染告警表格
    function renderAlarmsTable(alarms) {
        const tbody = document.getElementById('alarms-tbody');
        
        if (!alarms.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">暂无告警数据</td></tr>';
            return;
        }
        
        tbody.innerHTML = alarms.map(alarm => `
            <tr data-id="${alarm.id}">
                <td>
                    <span class="badge badge-${getStatusBadgeClass(alarm.status)}">${getStatusLabel(alarm.status)}</span>
                </td>
                <td>
                    <span class="badge badge-${getSeverityBadgeClass(alarm.severity)}">${getSeverityLabel(alarm.severity)}</span>
                </td>
                <td>
                    <div class="alarm-content">
                        <strong>${escapeHtml(alarm.title || alarm.message)}</strong>
                        <small class="text-muted d-block">${escapeHtml(alarm.message)}</small>
                    </div>
                </td>
                <td>${escapeHtml(alarm.device_name || '-')}</td>
                <td><time datetime="${alarm.created_at}">${formatTime(alarm.created_at)}</time></td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-ghost" onclick="viewAlarmDetail(${alarm.id})" title="查看详情">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        </button>
                        ${alarm.status !== 'resolved' ? `
                            <button class="btn btn-sm btn-success" onclick="quickResolve(${alarm.id})" title="标记解决">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `).join('');
    }

    // 渲染分页
    function renderPagination(total) {
        const totalPages = Math.ceil(total / pageSize);
        const wrapper = document.getElementById('alarms-pagination');
        
        if (totalPages <= 1) {
            wrapper.innerHTML = '';
            return;
        }
        
        let html = `<div class="pagination-info">共 ${total} 条记录</div>`;
        html += '<div class="pagination">';
        
        html += `<button class="btn btn-sm pagination-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">上一页</button>`;
        
        for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
            html += `<button class="btn btn-sm pagination-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
        }
        
        html += `<button class="btn btn-sm pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">下一页</button>`;
        html += '</div>';
        
        wrapper.innerHTML = html;
    }

    // 加载规则列表
    function loadRules() {
        api.get('/api/alarm-rules').then(res => {
            renderRulesList(res.data || []);
        }).catch(err => {
            console.error('加载规则失败:', err);
        });
    }

    // 渲染规则列表
    function renderRulesList(rules) {
        const container = document.getElementById('rules-list');
        
        if (!rules.length) {
            container.innerHTML = '<div class="text-center text-muted py-4">暂无规则</div>';
            return;
        }
        
        container.innerHTML = rules.map(rule => `
            <div class="rule-item ${rule.enabled ? '' : 'disabled'}">
                <div class="rule-header">
                    <span class="rule-name">${escapeHtml(rule.name)}</span>
                    <span class="badge badge-${getSeverityBadgeClass(rule.severity)}">${getSeverityLabel(rule.severity)}</span>
                    <label class="switch">
                        <input type="checkbox" ${rule.enabled ? 'checked' : ''} onchange="toggleRule(${rule.id}, this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="rule-body">
                    <code>${escapeHtml(rule.device_name || '*')} . ${escapeHtml(rule.point_name || rule.channel_name)} ${getConditionSymbol(rule.condition)} ${rule.threshold}</code>
                </div>
                <div class="rule-actions">
                    <button class="btn btn-sm btn-ghost" onclick="editRule(${rule.id})">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteRule(${rule.id})">删除</button>
                </div>
            </div>
        `).join('');
    }

    // 加载设备列表（用于规则选择）
    function loadDevices() {
        api.get('/api/devices?per_page=100').then(res => {
            const select = document.getElementById('rule-device');
            const devices = res.data.items || res.data || [];
            
            devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.name;
                option.textContent = device.name;
                select.appendChild(option);
            });
        });
    }

    // 初始化趋势图
    function initTrendChart() {
        const ctx = document.getElementById('alarm-trend-chart');
        if (!ctx) return;

        api.get('/api/alarms/trend?days=7').then(res => {
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: res.data.labels || [],
                    datasets: [
                        {
                            label: '严重',
                            data: res.data.critical || [],
                            borderColor: '#EF4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: '警告',
                            data: res.data.warning || [],
                            borderColor: '#F59E0B',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: '信息',
                            data: res.data.info || [],
                            borderColor: '#3B82F6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            fill: true,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        });
    }

    // 显示添加规则弹窗
    window.showAddRuleModal = function() {
        document.getElementById('rule-modal-title').textContent = '新建告警规则';
        document.getElementById('rule-form').reset();
        document.getElementById('rule-id').value = '';
        showModal('rule-modal');
    };

    // 关闭规则弹窗
    window.closeRuleModal = function() {
        hideModal('rule-modal');
    };

    // 编辑规则
    window.editRule = function(id) {
        api.get(`/api/alarm-rules/${id}`).then(res => {
            const rule = res.data;
            document.getElementById('rule-modal-title').textContent = '编辑告警规则';
            document.getElementById('rule-id').value = rule.id;
            document.querySelector('[name="name"]').value = rule.name;
            document.querySelector('[name="device_name"]').value = rule.device_name || '';
            document.querySelector('[name="condition"]').value = rule.condition;
            document.querySelector('[name="threshold"]').value = rule.threshold;
            document.querySelector('[name="severity"]').value = rule.severity;
            document.querySelector('[name="enabled"]').checked = rule.enabled;
            showModal('rule-modal');
        });
    };

    // 保存规则
    window.saveRule = function() {
        const form = document.getElementById('rule-form');
        const formData = new FormData(form);
        const id = document.getElementById('rule-id').value;
        const data = Object.fromEntries(formData.entries());
        data.enabled = form.querySelector('[name="enabled"]').checked;

        const promise = id 
            ? api.put(`/api/alarm-rules/${id}`, data)
            : api.post('/api/alarm-rules', data);

        promise.then(() => {
            closeRuleModal();
            loadRules();
            showToast(id ? '规则已更新' : '规则已创建', 'success');
        }).catch(err => {
            showToast('保存失败: ' + (err.message || '未知错误'), 'error');
        });
    };

    // 删除规则
    window.deleteRule = function(id) {
        if (!confirm('确定要删除此规则吗？')) return;
        
        api.delete(`/api/alarm-rules/${id}`).then(() => {
            loadRules();
            showToast('规则已删除', 'success');
        });
    };

    // 切换规则状态
    window.toggleRule = function(id, enabled) {
        api.put(`/api/alarm-rules/${id}`, { enabled }).then(() => {
            showToast(enabled ? '规则已启用' : '规则已禁用', 'success');
        });
    };

    // 查看告警详情
    window.viewAlarmDetail = function(id) {
        currentAlarmId = id;
        api.get(`/api/alarms/records/${id}`).then(res => {
            const alarm = res.data;
            document.getElementById('alarm-detail-body').innerHTML = `
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">告警标题</span>
                        <span class="detail-value">${escapeHtml(alarm.title || '-')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">告警级别</span>
                        <span class="detail-value">
                            <span class="badge badge-${getSeverityBadgeClass(alarm.severity)}">${getSeverityLabel(alarm.severity)}</span>
                        </span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">设备名称</span>
                        <span class="detail-value">${escapeHtml(alarm.device_name || '-')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">通道</span>
                        <span class="detail-value">${escapeHtml(alarm.channel_name || '-')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">当前值</span>
                        <span class="detail-value">${alarm.value != null ? alarm.value : '-'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">阈值</span>
                        <span class="detail-value">${alarm.threshold != null ? alarm.threshold : '-'}</span>
                    </div>
                    <div class="detail-item full-width">
                        <span class="detail-label">告警消息</span>
                        <span class="detail-value">${escapeHtml(alarm.message || '-')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">触发时间</span>
                        <span class="detail-value">${formatTime(alarm.created_at)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">状态</span>
                        <span class="detail-value">
                            <span class="badge badge-${getStatusBadgeClass(alarm.status)}">${getStatusLabel(alarm.status)}</span>
                        </span>
                    </div>
                </div>
            `;
            
            // 控制解决按钮显示
            document.getElementById('resolve-btn').style.display = alarm.status === 'resolved' ? 'none' : 'inline-block';
            
            showModal('alarm-detail-modal');
        });
    };

    // 关闭告警详情
    window.closeAlarmDetail = function() {
        hideModal('alarm-detail-modal');
        currentAlarmId = null;
    };

    // 快速解决告警
    window.quickResolve = function(id) {
        api.put(`/api/alarms/records/${id}/acknowledge`, { status: 'resolved' }).then(() => {
            loadAlarms();
            loadAlarmStats();
            showToast('告警已标记为已解决', 'success');
        });
    };

    // 解决告警（从详情弹窗）
    window.resolveAlarm = function() {
        if (!currentAlarmId) return;
        quickResolve(currentAlarmId);
        closeAlarmDetail();
    };

    // 刷新告警
    window.refreshAlarms = function() {
        loadAlarms();
        loadAlarmStats();
        showToast('已刷新', 'success');
    };

    // 筛选告警
    window.filterAlarms = function() {
        currentPage = 1;
        loadAlarms();
    };

    // 跳转页码
    window.goToPage = function(page) {
        currentPage = page;
        loadAlarms();
    };

    // 辅助函数
    function getSeverityBadgeClass(severity) {
        const map = { critical: 'danger', warning: 'warning', info: 'info' };
        return map[severity] || 'secondary';
    }

    function getSeverityLabel(severity) {
        const map = { critical: '严重', warning: '警告', info: '信息' };
        return map[severity] || severity;
    }

    function getStatusBadgeClass(status) {
        const map = { active: 'danger', acknowledged: 'warning', resolved: 'success' };
        return map[status] || 'secondary';
    }

    function getStatusLabel(status) {
        const map = { active: '未处理', acknowledged: '已确认', resolved: '已解决' };
        return map[status] || status;
    }

    function getConditionSymbol(condition) {
        const map = { gt: '>', gte: '≥', lt: '<', lte: '≤', eq: '=', neq: '!=' };
        return map[condition] || condition;
    }

})();
