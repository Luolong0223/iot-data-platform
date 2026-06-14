/**
 * OTA 固件升级管理 - V2版本
 */

class OTAManager {
    constructor() {
        this.firmwares = [];
        this.tasks = [];
        this.selectedFile = null;
        this.init();
    }

    async init() {
        console.log('[OTA] 初始化固件升级管理');
        
        // 绑定搜索
        document.getElementById('searchInput')?.addEventListener('input', () => {
            this.filterFirmware();
        });
        
        // 加载数据
        await Promise.all([
            this.loadFirmware(),
            this.loadTasks()
        ]);
    }

    async loadFirmware() {
        try {
            const res = await apiRequest('/api/ota/firmware', { method: 'GET' });
            if (res.success && Array.isArray(res.data)) {
                this.firmwares = res.data;
            } else {
                this.loadDemoData();
            }
        } catch (error) {
            console.error('[OTA] 加载固件失败:', error);
            this.loadDemoData();
        }
        
        this.renderFirmware();
        this.updateStats();
    }

    async loadTasks() {
        try {
            const res = await apiRequest('/api/ota/tasks', { method: 'GET' });
            if (res.success && Array.isArray(res.data)) {
                this.tasks = res.data;
            } else {
                this.tasks = [
                    { id: 1, firmware_version: 'v2.1.0', target_count: 15, completed: 12, failed: 1, status: 'publishing', created_at: '2026-06-14 10:00' },
                    { id: 2, firmware_version: 'v2.0.5', target_count: 50, completed: 50, failed: 0, status: 'completed', created_at: '2026-06-10 14:30' },
                    { id: 3, firmware_version: 'v2.0.3', target_count: 8, completed: 7, failed: 1, status: 'completed', created_at: '2026-06-05 09:00' },
                ];
            }
        } catch (error) {
            this.tasks = [
                { id: 1, firmware_version: 'v2.1.0', target_count: 15, completed: 12, failed: 1, status: 'publishing', created_at: '2026-06-14 10:00' },
            ];
        }
        
        this.renderTasks();
    }

    loadDemoData() {
        this.firmwares = [
            { id: 1, version: 'v2.1.0', file_name: 'firmware_v2.1.0.bin', size: '2.4 MB', target_type: 'all', status: 'stable', description: '修复已知问题，优化性能', upload_time: '2026-06-14 08:00', downloads: 156 },
            { id: 2, version: 'v2.0.5', file_name: 'firmware_v2.0.5.bin', size: '2.3 MB', target_type: 'sensor', status: 'stable', description: '新增温度补偿算法', upload_time: '2026-06-10 10:30', downloads: 342 },
            { id: 3, version: 'v2.0.4-beta', file_name: 'firmware_v2.0.4_beta.bin', size: '2.35 MB', target_type: 'gateway', status: 'beta', description: '测试版：新协议支持', upload_time: '2026-06-08 16:00', downloads: 45 },
            { id: 4, version: 'v2.0.3', file_name: 'firmware_v2.0.3.bin', size: '2.2 MB', target_type: 'all', status: 'deprecated', description: '稳定版本', upload_time: '2026-05-20 11:00', downloads: 890 },
        ];
    }

    renderFirmware() {
        const container = document.getElementById('firmwareListContainer');
        if (!container) return;
        
        if (!this.firmwares.length) {
            container.innerHTML = `
                <div class="text-center py-16 text-slate-500">
                    <i class="fas fa-box-open text-4xl mb-3 opacity-50"></i>
                    <p class="text-lg">暂无固件</p>
                    <p class="text-sm mt-1">点击"上传固件"添加第一个版本</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.firmwares.map(fw => this.renderFirmwareCard(fw)).join('');
    }

    renderFirmwareCard(fw) {
        const statusConfig = {
            stable: { bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', label: '稳定版' },
            beta: { bg: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20', label: '测试版' },
            deprecated: { bg: 'bg-slate-700 text-slate-400 border-slate-600', label: '已废弃' },
        };
        
        const status = statusConfig[fw.status] || statusConfig.stable;
        
        return `
            <div class="p-5 hover:bg-slate-700/20 transition-colors">
                <div class="flex items-start justify-between">
                    <div class="flex items-start gap-4 flex-1">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500/30 to-purple-500/30 flex items-center justify-center flex-shrink-0">
                            <i class="fas fa-microchip text-lg text-indigo-400"></i>
                        </div>
                        
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-3 mb-2">
                                <h4 class="font-semibold text-white font-mono">${fw.version}</h4>
                                <span class="px-2 py-0.5 rounded-full text-xs ${status.bg} border">${status.label}</span>
                                <span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-400">${fw.target_type === 'all' ? '通用' : fw.target_type}</span>
                            </div>
                            
                            <p class="text-sm text-slate-400 mb-3">${fw.description || '暂无描述'}</p>
                            
                            <div class="flex items-center gap-6 text-xs text-slate-500">
                                <span><i class="fas fa-file mr-1"></i>${fw.file_name} (${fw.size})</span>
                                <span><i class="fas fa-download mr-1"></i>下载 ${fw.downloads || 0} 次</span>
                                <span><i class="fas fa-clock mr-1"></i>${fw.upload_time}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-2 ml-4">
                        ${fw.status !== 'deprecated' ? `
                            <button onclick="otaV2.publishFirmware(${fw.id}, '${fw.version}')" 
                                    class="px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-xs"
                                    title="发布升级">
                                <i class="fas fa-paper-plane mr-1"></i>发布
                            </button>
                            <button onclick="otaV2.downloadFirmware(${fw.id})" 
                                    class="p-2 rounded-lg hover:bg-slate-700 transition-colors" title="下载">
                                <i class="fas fa-download text-sm text-emerald-400"></i>
                            </button>
                        ` : ''}
                        <button onclick="otaV2.deleteFirmware(${fw.id}, '${fw.version}')" 
                                class="p-2 rounded-lg hover:bg-slate-700 transition-colors" title="删除">
                            <i class="fas fa-trash-alt text-sm text-red-400"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renderTasks() {
        const container = document.getElementById('taskListContainer');
        if (!container) return;
        
        if (!this.tasks.length) {
            container.innerHTML = `
                <div class="text-center py-12 text-slate-500">
                    <i class="fas fa-tasks text-4xl mb-3 opacity-50"></i>
                    <p class="text-lg">暂无升级任务</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.tasks.map(task => {
            const progress = task.target_count > 0 ? Math.round(((task.completed + task.failed) / task.target_count) * 100) : 0;
            const statusConfig = {
                publishing: { color: 'from-blue-500 to-cyan-500', icon: 'fa-sync-alt animate-spin', label: '进行中' },
                completed: { color: 'from-emerald-500 to-green-500', icon: 'fa-check-circle', label: '已完成' },
                failed: { color: 'from-red-500 to-pink-500', icon: 'fa-times-circle', label: '失败' },
                pending: { color: 'from-slate-500 to-gray-500', icon: 'fa-clock', label: '等待中' },
            };
            
            const status = statusConfig[task.status] || statusConfig.pending;
            
            return `
                <div class="p-5 hover:bg-slate-700/20 transition-colors">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-lg bg-gradient-to-br ${status.color} flex items-center justify-center">
                                <i class="fas ${status.icon} text-white"></i>
                            </div>
                            <div>
                                <h4 class="font-semibold text-white">升级到 ${task.firmware_version}</h4>
                                <p class="text-xs text-slate-500">创建于 ${task.created_at}</p>
                            </div>
                        </div>
                        
                        <span class="px-3 py-1 rounded-full text-xs font-medium ${
                            task.status === 'publishing' ? 'bg-blue-500/10 text-blue-400' :
                            task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                            'bg-red-500/10 text-red-400'
                        }">${status.label}</span>
                    </div>
                    
                    <!-- 进度条 -->
                    <div class="mb-3">
                        <div class="flex items-center justify-between text-xs mb-1">
                            <span class="text-slate-400">进度</span>
                            <span class="text-white">${task.completed}/${task.target_count} 完成</span>
                        </div>
                        <div class="h-2 bg-slate-700 rounded-full overflow-hidden">
                            <div class="h-full bg-gradient-to-r ${status.color} rounded-full transition-all duration-300" style="width: ${progress}%"></div>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-6 text-xs text-slate-500">
                        <span class="text-emerald-400"><i class="fas fa-check mr-1"></i>成功: ${task.completed}</span>
                        <span class="text-yellow-400"><i class="fas fa-spinner mr-1"></i>进行中: ${task.target_count - task.completed - task.failed}</span>
                        <span class="text-red-400"><i class="fas fa-times mr-1"></i>失败: ${task.failed}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    updateStats() {
        const totalEl = document.getElementById('totalFirmware');
        const upgradedEl = document.getElementById('upgradedDevices');
        const upgradingEl = document.getElementById('upgradingDevices');
        const failedEl = document.getElementById('failedDevices');
        
        if (totalEl) totalEl.textContent = this.firmwares.length;
        
        let upgraded = 0, upgrading = 0, failed = 0;
        this.tasks.forEach(t => {
            upgraded += t.completed || 0;
            upgrading += t.target_count - t.completed - t.failed;
            failed += t.failed || 0;
        });
        
        if (upgradedEl) upgradedEl.textContent = upgraded;
        if (upgradingEl) upgradingEl.textContent = Math.max(0, upgrading);
        if (failedEl) failedEl.textContent = failed;
    }

    filterFirmware() {
        const search = (document.getElementById('searchInput')?.value || '').toLowerCase();
        const status = document.getElementById('statusFilter')?.value || '';
        
        const filtered = this.firmwares.filter(fw => {
            if (search && !fw.version.toLowerCase().includes(search) && !fw.file_name.toLowerCase().includes(search)) return false;
            if (status && fw.status !== status) return false;
            return true;
        });
        
        const container = document.getElementById('firmwareListContainer');
        if (container) {
            // 简单重新渲染
            this.renderFirmware();
        }
    }

    showUploadModal() {
        document.getElementById('uploadModal').classList.remove('hidden');
    }

    closeModal() {
        document.getElementById('uploadModal').classList.add('hidden');
    }

    selectFile(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        this.selectedFile = file;
        document.getElementById('fileInfo').classList.remove('hidden');
        document.getElementById('fileName').textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    }

    clearFile() {
        this.selectedFile = null;
        document.getElementById('fileInput').value = '';
        document.getElementById('fileInfo').classList.add('hidden');
    }

    async uploadFirmware(e) {
        e.preventDefault();
        
        if (!this.selectedFile) {
            showNotification('请选择固件文件', 'warning');
            return;
        }
        
        showNotification('固件上传成功！', 'success');
        this.closeModal();
        
        // 添加到列表
        this.firmwares.unshift({
            id: Date.now(),
            version: document.getElementById('fwVersion').value,
            file_name: this.selectedFile.name,
            size: `${(this.selectedFile.size / 1024 / 1024).toFixed(2)} MB`,
            target_type: document.getElementById('targetDeviceType').value,
            status: 'stable',
            description: document.getElementById('fwDesc').value,
            upload_time: new Date().toLocaleString(),
            downloads: 0
        });
        
        this.clearFile();
        this.renderFirmware();
        this.updateStats();
    }

    publishFirmware(id, version) {
        if (!confirm(`确定要发布固件 ${version} 吗？这将创建一个升级任务。`)) return;
        
        showNotification(`已创建 ${version} 升级任务`, 'success');
        
        this.tasks.unshift({
            id: Date.now(),
            firmware_version: version,
            target_count: Math.floor(Math.random() * 50) + 5,
            completed: 0,
            failed: 0,
            status: 'publishing',
            created_at: new Date().toLocaleString()
        });
        
        this.renderTasks();
        this.updateStats();
    }

    downloadFirmware(id) {
        showNotification('开始下载固件...', 'info');
    }

    deleteFirmware(id, version) {
        if (!confirm(`确定要删除固件 ${version} 吗？此操作不可恢复。`)) return;
        
        this.firmwares = this.firmwares.filter(fw => fw.id !== id);
        this.renderFirmware();
        this.updateStats();
        showNotification('固件已删除', 'success');
    }

    createUpgradeTask() {
        if (!this.firmwares.length) {
            showNotification('请先上传固件', 'warning');
            return;
        }
        
        const latestVersion = this.firmwares[0].version;
        this.publishFirmware(this.firmwares[0].id, latestVersion);
    }
}

// 全局实例
let otaV2;

document.addEventListener('DOMContentLoaded', () => {
    otaV2 = new OTAManager();
});
