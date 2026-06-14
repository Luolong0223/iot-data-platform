/**
 * IoT Platform - 平台管理页面 V2
 */

// API 请求封装
async function api(url, options = {}) {
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, { ...defaults, ...options });
        
        if (response.status === 401) {
            window.location.href = '/login';
            return null;
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast('网络请求失败', 'error');
        throw error;
    }
}

// 标签切换
document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    loadShadows();
});

function initTabs() {
    const tabs = document.querySelectorAll('#platformTabs .tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // 移除所有active
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // 添加当前active
            this.classList.add('active');
            const tabId = this.dataset.tab;
            document.getElementById(`tab-${tabId}`).classList.add('active');
            
            // 加载对应数据
            switch(tabId) {
                case 'shadow': loadShadows(); break;
                case 'tags': loadTags(); break;
                case 'commands': loadCommands(); break;
                case 'protocol': loadProtocols(); break;
                case 'notifications': loadNotifications(); break;
                case 'audit': loadAuditLogs(); break;
            }
        });
    });
}

// ========== 设备影子 ==========
async function loadShadows() {
    try {
        const data = await api('/api/shadows');
        const tbody = document.getElementById('shadowTableBody');
        
        if (!data || !data.shadows || data.shadows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">暂无设备影子数据</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.shadows.map(shadow => `
            <tr>
                <td><strong>${shadow.device_name || '-'}</strong></td>
                <td><span class="badge badge-success">${shadow.connected ? '在线' : '离线'}</span></td>
                <td><code class="code-inline">${JSON.stringify(shadow.desired || {}).substring(0, 50)}...</code></td>
                <td><code class="code-inline">${JSON.stringify(shadow.reported || {}).substring(0, 50)}...</code></td>
                <td>v${shadow.version || 0}</td>
                <td>${formatTime(shadow.updated_at)}</td>
                <td>
                    <button class="btn btn-sm btn-ghost" onclick="viewShadow(${shadow.id})" title="查看详情">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Load shadows error:', error);
    }
}

function refreshShadows() {
    loadShadows();
}

// ========== 设备标签 ==========
async function loadTags() {
    try {
        const data = await api('/api/devices/tags');
        const grid = document.getElementById('tagsGrid');
        
        if (!data || !data.tags || data.tags.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                    </div>
                    <h4>暂无标签</h4>
                    <p>点击上方按钮创建新标签</p>
                </div>`;
            return;
        }
        
        grid.innerHTML = `<div class="tags-list">${data.tags.map(tag => `
            <div class="tag-item">
                <span class="tag-color" style="background: ${tag.color || '#6366f1'}"></span>
                <span class="tag-name">${tag.name}</span>
                <span class="tag-count">${tag.device_count || 0} 个设备</span>
                <button class="btn btn-ghost btn-xs" onclick="deleteTag(${tag.id})">&times;</button>
            </div>
        `).join('')}</div>`;
    } catch (error) {
        console.error('Load tags error:', error);
    }
}

function showAddTagModal() {
    showModal('addTagModal');
}

function deleteTag(id) {
    showConfirm('确定删除此标签？', async () => {
        await api(`/api/devices/tags/${id}`, { method: 'DELETE' });
        showToast('标签已删除', 'success');
        loadTags();
    });
}

// ========== 命令中心 ==========
async function loadCommands() {
    try {
        const data = await api('/api/command/commands');
        const tbody = document.getElementById('commandTableBody');
        
        if (!data || !data.commands || data.commands.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">暂无命令记录</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.commands.map(cmd => `
            <tr>
                <td>#${cmd.id}</td>
                <td>${cmd.device_name || '-'}</td>
                <td><span class="badge badge-info">${cmd.command_type}</span></td>
                <td><code class="code-inline">${cmd.parameters ? JSON.stringify(cmd.parameters).substring(0, 30) : '-'}</code></td>
                <td>${getStatusBadge(cmd.status)}</td>
                <td>${formatTime(cmd.created_at)}</td>
                <td>
                    ${cmd.status === 'pending' ? `<button class="btn btn-sm btn-primary" onclick="executeCommand(${cmd.id})">执行</button>` : ''}
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Load commands error:', error);
    }
}

function getStatusBadge(status) {
    const map = {
        pending: 'badge-warning',
        sent: 'badge-info',
        executing: 'badge-primary',
        success: 'badge-success',
        failed: 'badge-danger',
        timeout: 'badge-secondary'
    };
    const label = {
        pending: '待发送',
        sent: '已发送',
        executing: '执行中',
        success: '成功',
        failed: '失败',
        timeout: '超时'
    };
    return `<span class="badge ${map[status] || 'badge-secondary'}">${label[status] || status}</span>`;
}

function showSendCommandModal() {
    showModal('commandModal');
    loadDeviceOptions();
}

async function loadDeviceOptions() {
    const data = await api('/api/devices');
    const select = document.getElementById('cmdDeviceId');
    select.innerHTML = '<option value="">选择设备</option>' + 
        (data?.devices?.map(d => `<option value="${d.id}">${d.name}</option>`).join('') || '');
}

async function sendCommand() {
    const deviceId = document.getElementById('cmdDeviceId').value;
    const cmdType = document.getElementById('cmdType').value;
    let payload = {};
    
    try {
        payload = JSON.parse(document.getElementById('cmdPayload').value || '{}');
    } catch(e) {
        showToast('参数格式错误，请输入有效的JSON', 'error');
        return;
    }
    
    if (!deviceId) {
        showToast('请选择目标设备', 'error');
        return;
    }
    
    await api('/api/command/commands', {
        method: 'POST',
        body: JSON.stringify({
            device_id: parseInt(deviceId),
            command: cmdType,
            payload: payload
        })
    });
    
    closeModal('commandModal');
    showToast('命令已发送', 'success');
    loadCommands();
}

async function executeCommand(id) {
    await api(`/api/command/commands/${id}/send`, { method: 'POST' });
    showToast('命令执行请求已发送', 'success');
    loadCommands();
}

// ========== 协议适配器 ==========
async function loadProtocols() {
    try {
        const data = await api('/api/protocol/adapters');
        const grid = document.getElementById('protocolGrid');
        
        if (!data || !data.adapters || data.adapters.length === 0) {
            grid.innerHTML = `
                <div class="empty-state col-span-3">
                    <h4>暂无协议适配器</h4>
                    <p>点击上方按钮添加协议适配器</p>
                </div>`;
            return;
        }
        
        const protocolIcons = {
            mqtt: '📡',
            coap: '🌐',
            modbus: '⚙️',
            http: '🔗'
        };
        
        grid.innerHTML = data.adapters.map(adapter => `
            <div class="card card-hover">
                <div class="card-body">
                    <div class="d-flex align-items-center mb-3">
                        <span class="protocol-icon">${protocolIcons[adapter.protocol_type] || '📋'}</span>
                        <div>
                            <h4 class="mb-0">${adapter.name}</h4>
                            <span class="text-muted text-sm">${adapter.protocol_type.toUpperCase()}</span>
                        </div>
                        <span class="badge ${adapter.enabled ? 'badge-success' : 'badge-secondary'}">${adapter.enabled ? '启用' : '禁用'}</span>
                    </div>
                    <p class="text-muted text-sm mb-3">${adapter.description || '无描述'}</p>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm btn-outline flex-1" onclick="testProtocol(${adapter.id})">测试连接</button>
                        <button class="btn btn-sm btn-ghost" onclick="editProtocol(${adapter.id})">编辑</button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Load protocols error:', error);
    }
}

function showAddProtocolModal() {
    showToast('添加适配器功能开发中', 'info');
}

async function testProtocol(id) {
    showToast('正在测试连接...', 'info');
    const result = await api(`/api/protocol/adapters/${id}/test`, { method: 'POST' });
    if (result && result.success) {
        showToast('连接测试成功', 'success');
    } else {
        showToast('连接测试失败', 'error');
    }
}

// ========== 通知配置 ==========
async function loadNotifications() {
    try {
        const data = await api('/api/notification/config');
        if (data && data.config) {
            document.getElementById('emailNotify').checked = data.config.email_enabled || false;
            document.getElementById('webhookNotify').checked = data.config.webhook_enabled || false;
            document.getElementById('browserNotify').checked = data.config.browser_enabled || false;
        }
        
        // 加载通知历史
        const logs = await api('/api/notification/logs?limit=10');
        const timeline = document.getElementById('notificationTimeline');
        
        if (!logs || !logs.logs || logs.logs.length === 0) {
            timeline.innerHTML = '<div class="timeline-empty">暂无通知记录</div>';
            return;
        }
        
        timeline.innerHTML = logs.logs.map(log => `
            <div class="timeline-item">
                <div class="timeline-dot ${log.status === 'sent' ? 'success' : 'error'}"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <strong>${log.title || '通知'}</strong>
                        <span class="text-muted text-sm">${formatTime(log.created_at)}</span>
                    </div>
                    <p class="text-sm text-muted">${log.message || log.content || ''}</p>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Load notifications error:', error);
    }
}

// ========== 审计日志 ==========
let auditPage = 1;

async function loadAuditLogs(page = 1) {
    auditPage = page;
    const params = new URLSearchParams({ page, per_page: 20 });
    
    const dateFrom = document.getElementById('auditDateFrom')?.value;
    const dateTo = document.getElementById('auditDateTo')?.value;
    const actionType = document.getElementById('auditActionType')?.value;
    
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (actionType) params.append('action_type', actionType);
    
    try {
        const data = await api(`/api/audit/logs?${params}`);
        const tbody = document.getElementById('auditTableBody');
        
        if (!data || !data.logs || data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无审计日志</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.logs.map(log => `
            <tr>
                <td>${formatTime(log.created_at)}</td>
                <td>${log.username || '-'}</td>
                <td><span class="badge badge-outline">${getActionTypeLabel(log.action_type)}</span></td>
                <td>${log.resource_type || '-'} / ${log.resource_id || '-'}</td>
                <td class="text-truncate" style="max-width:200px">${log.details || log.description || '-'}</td>
                <td><code class="code-inline">${log.ip_address || '-'}</code></td>
            </tr>
        `).join('');
        
        // 渲染分页
        renderPagination('auditPagination', data.total_pages, auditPage, loadAuditLogs);
    } catch (error) {
        console.error('Load audit logs error:', error);
    }
}

function getActionTypeLabel(type) {
    const labels = {
        login: '登录',
        logout: '登出',
        create: '创建',
        update: '更新',
        delete: '删除',
        export: '导出',
        import: '导入'
    };
    return labels[type] || type;
}

function searchAuditLogs() {
    loadAuditLogs(1);
}

// ========== 工具函数 ==========
function formatTime(timeStr) {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function renderPagination(containerId, totalPages, currentPage, callback) {
    const container = document.getElementById(containerId);
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '<div class="pagination">';
    html += `<button class="page-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="${callback.name}(${currentPage - 1})">上一页</button>`;
    
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="${callback.name}(${i})">${i}</button>`;
    }
    
    html += `<button class="page-btn" ${currentPage >= totalPages ? 'disabled' : ''} onclick="${callback.name}(${currentPage + 1})">下一页</button>`;
    html += '</div>';
    
    container.innerHTML = html;
}

function showModal(id) {
    document.getElementById(id).classList.add('show');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('show');
}

function showConfirm(message, onConfirm) {
    if (confirm(message)) {
        onConfirm();
    }
}

function showToast(message, type = 'info') {
    // 简单的toast实现
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function viewShadow(id) {
    showToast(`查看影子详情 #${id}`, 'info');
}

function editProtocol(id) {
    showToast(`编辑协议适配器 #${id}`, 'info');
}

function refreshAll() {
    const activeTab = document.querySelector('#platformTabs .tab-btn.active');
    if (activeTab) {
        activeTab.click();
    }
}
