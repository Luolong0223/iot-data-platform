/**
 * Devices V2 - IoT Data Platform
 * 设备管理页面
 */

class DevicesPageV2 {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 10;
        this.searchQuery = '';
        this.statusFilter = '';
        this.typeFilter = '';
        this.init();
    }

    async init() {
        console.log('[Devices] Initializing...');
        await this.loadDevices();
        this.bindEvents();
    }

    bindEvents() {
        const searchInput = document.getElementById('searchInput');
        const filterStatus = document.getElementById('filterStatus');
        const filterType = document.getElementById('filterType');
        const refreshBtn = document.getElementById('refreshBtn');
        const addDeviceBtn = document.getElementById('addDeviceBtn');

        if (searchInput) {
            searchInput.addEventListener('input', () => {
                this.searchQuery = searchInput.value;
                this.currentPage = 1;
                this.loadDevices();
            });
        }
        if (filterStatus) {
            filterStatus.addEventListener('change', (e) => {
                this.statusFilter = e.target.value;
                this.currentPage = 1;
                this.loadDevices();
            });
        }
        if (filterType) {
            filterType.addEventListener('change', (e) => {
                this.typeFilter = e.target.value;
                this.currentPage = 1;
                this.loadDevices();
            });
        }
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadDevices());
        if (addDeviceBtn) addDeviceBtn.addEventListener('click', () => this.showAddDeviceModal());
    }

    async loadDevices() {
        try {
            const params = new URLSearchParams();
            if (this.searchQuery) params.append('search', this.searchQuery);
            if (this.statusFilter) params.append('status', this.statusFilter);
            if (this.typeFilter) params.append('type', this.typeFilter);
            params.append('page', this.currentPage);
            params.append('per_page', this.pageSize);

            const response = await apiRequest(`/api/devices?${params}`);
            
            if (response && response.success) {
                const devices = response.devices || [];
                this.renderTable(devices);
                this.updateStats(devices);
            } else {
                this.renderTable([]);
                this.updateStats([]);
            }
        } catch (error) {
            console.error('[Devices] Load error:', error);
            this.renderTable([]);
            this.updateStats([]);
        }
    }

    updateStats(devices) {
        const total = devices.length;
        const online = devices.filter(d => d.is_online).length;
        const offline = total - online;
        const alarmCount = devices.filter(d => d.status === 'alarm').length;

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        setVal('totalDevices', total);
        setVal('onlineDevices', online);
        setVal('offlineDevices', offline);
        setVal('alarmDevices', alarmCount);
    }

    renderTable(devices) {
        const tbody = document.getElementById('deviceTableBody');
        if (!tbody) return;

        if (!devices || devices.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted-foreground py-12">
                        <svg class="mx-auto mb-3" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
                            <rect x="4" y="4" width="16" height="16" rx="2"/>
                            <rect x="9" y="9" width="6" height="6"/>
                        </svg>
                        <p>暂无设备数据</p>
                        <button class="mt-3 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:opacity-90" onclick="document.querySelector('#addDeviceBtn').click()">添加设备</button>
                    </td>
                </tr>`;
            return;
        }

        tbody.innerHTML = devices.map(device => `
            <tr class="border-b border-border hover:bg-muted/30 transition-colors" data-id="${device.id}">
                <td class="py-2 px-3">
                    <input type="checkbox" class="device-checkbox rounded border-border" value="${device.id}">
                </td>
                <td class="py-2 px-3 text-foreground font-medium">${device.name || '-'}</td>
                <td class="py-2 px-3 text-muted-foreground">${device.device_type || '未知'}</td>
                <td class="py-2 px-3">
                    <span class="inline-flex items-center gap-1.5 ${device.is_online ? 'text-green-400' : 'text-red-400'}">
                        <span class="w-2 h-2 rounded-full ${device.is_online ? 'bg-green-400 animate-pulse' : 'bg-red-400'}"></span>
                        ${device.is_online ? '在线' : '离线'}
                    </span>
                </td>
                <td class="py-2 px-3 text-muted-foreground text-sm">${device.location_name || '-'}</td>
                <td class="py-2 px-3 text-muted-foreground text-sm">${device.last_seen_at || '-'}</td>
                <td class="py-2 px-3 text-muted-foreground">${device.data_count || 0}</td>
                <td class="py-2 px-3">
                    <button class="text-primary hover:underline text-sm mr-2" onclick="DevicesPageV2.instance.viewDevice(${device.id})">查看</button>
                    <button class="text-muted-foreground hover:text-foreground text-sm" onclick="DevicesPageV2.instance.editDevice(${device.id})">编辑</button>
                </td>
            </tr>
        `).join('');
    }

    viewDevice(id) {
        window.location.href = `/devices/${id}`;
    }

    editDevice(id) {
        window.location.href = `/devices/${id}/edit`;
    }

    showAddDeviceModal() {
        window.location.href = '/devices/add';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    DevicesPageV2.instance = new DevicesPageV2();
});
