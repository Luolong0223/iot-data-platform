// 设备管理页面 - V2
const DevicesPage = {
    currentPage: 1,
    pageSize: 10,
    searchQuery: '',
    statusFilter: '',
    typeFilter: '',

    init() {
        this.loadDevices();
        this.bindEvents();
    },

    bindEvents() {
        document.getElementById('searchInput').addEventListener('input', debounce(() => {
            this.searchQuery = document.getElementById('searchInput').value;
            this.currentPage = 1;
            this.loadDevices();
        }, 300));

        document.getElementById('filterStatus').addEventListener('change', (e) => {
            this.statusFilter = e.target.value;
            this.currentPage = 1;
            this.loadDevices();
        });

        document.getElementById('filterType').addEventListener('change', (e) => {
            this.typeFilter = e.target.value;
            this.currentPage = 1;
            this.loadDevices();
        });

        document.getElementById('selectAll').addEventListener('change', (e) => {
            document.querySelectorAll('.device-checkbox').forEach(cb => cb.checked = e.target.checked);
        });
    },

    async loadDevices() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.pageSize,
                ...(this.searchQuery && { search: this.searchQuery }),
                ...(this.statusFilter && { status: this.statusFilter }),
                ...(this.typeFilter && { type: this.typeFilter })
            });

            const response = await api(`/devices?${params}`);
            
            if (response.success) {
                this.renderTable(response.data.items);
                this.renderPagination(response.data.total, response.data.pages);
                this.updateStats(response.stats);
            }
        } catch (error) {
            console.error('加载设备列表失败:', error);
            showToast('加载设备列表失败', 'error');
        }
    },

    renderTable(devices) {
        const tbody = document.getElementById('deviceTableBody');
        
        if (!devices || devices.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center empty-state">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <rect x="4" y="4" width="16" height="16" rx="2"/>
                            <rect x="9" y="9" width="6" height="6"/>
                        </svg>
                        <p>暂无设备数据</p>
                        <button class="btn btn-primary btn-sm mt-3" onclick="showAddDeviceModal()">添加设备</button>
                    </td>
                </tr>`;
            return;
        }

        tbody.innerHTML = devices.map(device => `
            <tr data-id="${device.id}">
                <td><input type="checkbox" class="device-checkbox" value="${device.id}"></td>
                <td>
                    <div class="device-name-cell">
                        <span class="status-dot ${device.is_online ? 'online' : 'offline'}"></span>
                        <strong>${escapeHtml(device.name)}</strong>
                        ${device.code ? `<small class="text-muted ml-2">${escapeHtml(device.code)}</small>` : ''}
                    </div>
                </td>
                <td>
                    <span class="badge badge-light">${this.getTypeLabel(device.device_type)}</span>
                </td>
                <td>
                    <span class="status-badge ${device.is_online ? 'success' : 'danger'}">
                        ${device.is_online ? '在线' : '离线'}
                    </span>
                </td>
                <td>${escapeHtml(device.location || '-')}</td>
                <td>
                    <span class="text-muted">${formatRelativeTime(device.last_communication_at || device.updated_at)}</span>
                </td>
                <td>
                    <span class="font-medium">${device.data_count || 0}</span>
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-icon" title="查看详情" onclick="viewDeviceDetail(${device.id})">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                            </svg>
                        </button>
                        <button class="btn-icon" title="编辑" onclick="editDevice(${device.id})">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                        </button>
                        <button class="btn-icon text-red-500" title="删除" onclick="deleteDevice(${device.id}, '${escapeHtml(device.name)}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        document.getElementById('deviceCount').textContent = `${devices.length} 个设备`;
    },

    renderPagination(total, pages) {
        const container = document.getElementById('pagination');
        if (pages <= 1) {
            container.innerHTML = '';
            return;
        }

        let html = '<div class="pagination-info">共 <strong>' + total + '</strong> 条记录</div>';
        html += '<div class="pagination-pages">';
        
        html += `<button class="page-btn" ${this.currentPage === 1 ? 'disabled' : ''} onclick="DevicesPage.goToPage(1)">首页</button>`;
        html += `<button class="page-btn" ${this.currentPage === 1 ? 'disabled' : ''} onclick="DevicesPage.goToPage(${this.currentPage - 1})">上一页</button>`;
        
        for (let i = Math.max(1, this.currentPage - 2); i <= Math.min(pages, this.currentPage + 2); i++) {
            html += `<button class="page-btn ${i === this.currentPage ? 'active' : ''}" onclick="DevicesPage.goToPage(${i})">${i}</button>`;
        }
        
        html += `<button class="page-btn" ${this.currentPage === pages ? 'disabled' : ''} onclick="DevicesPage.goToPage(${this.currentPage + 1})">下一页</button>`;
        html += `<button class="page-btn" ${this.currentPage === pages ? 'disabled' : ''} onclick="DevicesPage.goToPage(${pages})">末页</button>`;
        
        html += '</div>';
        container.innerHTML = html;
    },

    updateStats(stats) {
        animateNumber('totalDevices', stats?.total || 0);
        animateNumber('onlineDevices', stats?.online || 0);
        animateNumber('offlineDevices', stats?.offline || 0);
        animateNumber('alertDevices', stats?.alert || 0);
    },

    goToPage(page) {
        this.currentPage = page;
        this.loadDevices();
    },

    getTypeLabel(type) {
        const types = {
            temperature: '温度传感器',
            humidity: '湿度传感器',
            pressure: '压力传感器',
            gateway: '网关',
            camera: '摄像头',
            other: '其他'
        };
        return types[type] || type || '未知';
    }
};

// 全局函数
function refreshDevices() {
    DevicesPage.loadDevices();
}

function showAddDeviceModal() {
    document.getElementById('modalTitle').textContent = '添加设备';
    document.getElementById('deviceForm').reset();
    document.getElementById('deviceId').value = '';
    showModal('deviceModal');
}

async function editDevice(id) {
    try {
        const response = await api(`/devices/${id}`);
        if (response.success) {
            const device = response.data;
            document.getElementById('modalTitle').textContent = '编辑设备';
            document.getElementById('deviceId').value = device.id;
            document.getElementById('deviceName').value = device.name;
            document.getElementById('deviceType').value = device.device_type || '';
            document.getElementById('deviceCode').value = device.code || '';
            document.getElementById('deviceLocation').value = device.location || '';
            document.getElementById('deviceRemark').value = device.remark || '';
            showModal('deviceModal');
        }
    } catch (error) {
        showToast('获取设备信息失败', 'error');
    }
}

async function saveDevice(e) {
    e.preventDefault();
    
    const id = document.getElementById('deviceId').value;
    const data = {
        name: document.getElementById('deviceName').value,
        device_type: document.getElementById('deviceType').value,
        code: document.getElementById('deviceCode').value,
        location: document.getElementById('deviceLocation').value,
        remark: document.getElementById('deviceRemark').value
    };

    try {
        const response = id 
            ? await api(`/devices/${id}`, { method: 'PUT', body: data })
            : await api('/devices', { method: 'POST', body: data });
        
        if (response.success) {
            closeModal();
            showToast(id ? '设备更新成功' : '设备添加成功', 'success');
            refreshDevices();
        } else {
            showToast(response.message || '操作失败', 'error');
        }
    } catch (error) {
        showToast('操作失败: ' + error.message, 'error');
    }
}

async function deleteDevice(id, name) {
    if (!confirm(`确定要删除设备 "${name}" 吗？此操作不可恢复。`)) return;

    try {
        const response = await api(`/devices/${id}`, { method: 'DELETE' });
        if (response.success) {
            showToast('设备已删除', 'success');
            refreshDevices();
        } else {
            showToast(response.message || '删除失败', 'error');
        }
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

async function viewDeviceDetail(id) {
    try {
        const [deviceRes, dataRes] = await Promise.all([
            api(`/devices/${id}`),
            api(`/data?device_id=${id}&limit=10`)
        ]);

        const device = deviceRes.data;
        const recentData = dataRes.data?.items || [];

        const content = document.getElementById('deviceDetailContent');
        content.innerHTML = `
            <div class="detail-section">
                <h4>基本信息</h4>
                <div class="info-grid">
                    <div class="info-item">
                        <label>设备名称</label>
                        <value>${escapeHtml(device.name)}</value>
                    </div>
                    <div class="info-item">
                        <label>设备类型</label>
                        <value>${DevicesPage.getTypeLabel(device.device_type)}</value>
                    </div>
                    <div class="info-item">
                        <label>状态</label>
                        <value><span class="status-badge ${device.is_online ? 'success' : 'danger'}">${device.is_online ? '在线' : '离线'}</span></value>
                    </div>
                    <div class="info-item">
                        <label>位置</label>
                        <value>${escapeHtml(device.location || '-')}</value>
                    </div>
                    <div class="info-item">
                        <label>创建时间</label>
                        <value>${formatDateTime(device.created_at)}</value>
                    </div>
                    <div class="info-item">
                        <label>最后通信</label>
                        <value>${formatDateTime(device.last_communication_at || device.updated_at)}</value>
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <h4>最近数据</h4>
                <div class="mini-chart-container" id="deviceMiniChart"></div>
                <table class="data-table mini-table">
                    <thead>
                        <tr>
                            <th>通道</th>
                            <th>数值</th>
                            <th>时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${recentData.slice(0, 5).map(d => `
                            <tr>
                                <td>${escapeHtml(d.channel_name || d.name || '-')}</td>
                                <td><strong>${d.value != null ? d.value.toFixed(2) : '-'}</strong></td>
                                <td class="text-muted">${formatDateTime(d.timestamp)}</td>
                            </tr>
                        `).join('') || '<tr><td colspan="3" class="text-center">暂无数据</td></tr>'}
                    </tbody>
                </table>
            </div>

            <div class="detail-section">
                <h4>快捷操作</h4>
                <div class="quick-actions">
                    <button class="btn btn-outline btn-sm" onclick="editDevice(${device.id}); closeDetailPanel();">编辑设备</button>
                    <button class="btn btn-outline btn-sm" onclick="window.location.href='/device/${device.id}'">查看完整详情</button>
                    <button class="btn btn-outline btn-sm" onclick="window.location.href='/data?device_id=${device.id}'">查看历史数据</button>
                </div>
            </div>
        `;

        // 渲染迷你图表
        if (recentData.length > 0) {
            renderMiniChart('deviceMiniChart', recentData.map(d => d.value));
        }

        showSidebarPanel('deviceDetailPanel');
    } catch (error) {
        console.error('获取设备详情失败:', error);
        showToast('获取设备详情失败', 'error');
    }
}

function closeModal() {
    hideModal('deviceModal');
}

function closeDetailPanel() {
    hideSidebarPanel('deviceDetailPanel');
}

// 页面初始化
document.addEventListener('DOMContentLoaded', () => {
    DevicesPage.init();
});
