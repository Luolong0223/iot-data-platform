/**
 * 告警规则管理 - V2版本
 * 深色工业风主题
 */

class AlarmRulesManager {
    constructor() {
        this.rules = [];
        this.devices = [];
        this.init();
    }

    async init() {
        console.log('[AlarmRules] 初始化告警规则管理');
        
        // 绑定事件
        document.getElementById('searchInput')?.addEventListener('input', (e) => {
            this.filterRules();
        });
        document.getElementById('levelFilter')?.addEventListener('change', () => {
            this.filterRules();
        });
        document.getElementById('statusFilter')?.addEventListener('change', () => {
            this.filterRules();
        });
        
        // 持续时长复选框联动
        const durationCheck = document.getElementById('enableDuration');
        if (durationCheck) {
            durationCheck.addEventListener('change', (e) => {
                document.getElementById('durationSeconds').disabled = !e.target.checked;
            });
        }
        
        // 加载数据
        await Promise.all([
            this.loadRules(),
            this.loadDevices()
        ]);
    }

    async loadRules() {
        try {
            const res = await apiRequest('/api/alarms/rules', { method: 'GET' });
            if (res.success && Array.isArray(res.data)) {
                this.rules = res.data;
                this.renderRules(this.rules);
                this.updateStats();
                console.log(`[AlarmRules] 加载 ${this.rules.length} 条规则`);
            } else {
                // 使用示例数据作为fallback
                this.loadDemoData();
            }
        } catch (error) {
            console.error('[AlarmRules] 加载失败:', error);
            this.loadDemoData();
        }
    }

    loadDemoData() {
        this.rules = [
            { id: 1, name: '温度超限告警', level: 'critical', status: 'active', condition: 'temperature > 80°C', devices: ['sensor-001', 'sensor-002'], triggers: 15, lastTriggered: '2026-06-14 10:30' },
            { id: 2, name: '设备离线检测', level: 'warning', status: 'active', condition: 'status == offline', devices: [], triggers: 8, lastTriggered: '2026-06-14 09:45' },
            { id: 3, name: '湿度异常警告', level: 'warning', status: 'active', condition: 'humidity > 90%', devices: ['sensor-003'], triggers: 3, lastTriggered: '2026-06-13 22:10' },
            { id: 4, name: '电池电量低', level: 'info', status: 'inactive', condition: 'battery < 20%', devices: [], triggers: 0, lastTriggered: '-' },
            { id: 5, name: '数据上报异常', level: 'critical', status: 'active', condition: 'no_data > 300s', devices: [], triggers: 2, lastTriggered: '2026-06-14 08:00' },
            { id: 6, name: '振动超标预警', level: 'warning', status: 'active', condition: 'vibration > 50mm/s', devices: ['motor-001'], triggers: 12, lastTriggered: '2026-06-14 11:20' },
        ];
        this.renderRules(this.rules);
        this.updateStats();
    }

    async loadDevices() {
        try {
            const res = await apiRequest('/api/devices', { method: 'GET' });
            if (res.success && Array.isArray(res.data)) {
                this.devices = res.data;
                this.populateDeviceSelect();
            }
        } catch (error) {
            console.error('[AlarmRules] 加载设备列表失败:', error);
        }
    }

    populateDeviceSelect() {
        const select = document.getElementById('ruleDevices');
        if (!select || !this.devices.length) return;
        
        select.innerHTML = this.devices.map(d => 
            `<option value="${d.id}">${d.name} (${d.device_id})</option>`
        ).join('');
    }

    renderRules(rules) {
        const container = document.getElementById('rulesListContainer');
        const countEl = document.getElementById('ruleCount');
        
        if (!container) return;
        
        if (!rules.length) {
            container.innerHTML = `
                <div class="text-center py-16 text-slate-500">
                    <i class="fas fa-sliders-h text-4xl mb-3 opacity-50"></i>
                    <p class="text-lg">暂无告警规则</p>
                    <p class="text-sm mt-1">点击"新建规则"创建第一条规则</p>
                </div>
            `;
            if (countEl) countEl.textContent = '0 条规则';
            return;
        }
        
        container.innerHTML = rules.map(rule => this.renderRuleCard(rule)).join('');
        if (countEl) countEl.textContent = `${rules.length} 条规则`;
    }

    renderRuleCard(rule) {
        const levelConfig = {
            critical: { bg: 'bg-red-500/10 text-red-400 border-red-500/20', icon: 'fa-exclamation-circle', label: '严重' },
            warning: { bg: 'bg-orange-500/10 text-orange-400 border-orange-500/20', icon: 'fa-exclamation-triangle', label: '警告' },
            info: { bg: 'bg-blue-500/10 text-blue-400 border-blue-500/20', icon: 'fa-info-circle', label: '信息' },
        };
        
        const level = levelConfig[rule.level] || levelConfig.info;
        const isActive = rule.status === 'active';
        
        return `
            <div class="rule-item p-5 hover:bg-slate-700/20 transition-colors" data-id="${rule.id}">
                <div class="flex items-start justify-between">
                    <div class="flex items-start gap-4 flex-1">
                        <!-- 状态指示 -->
                        <div class="mt-1">
                            <div class="w-3 h-3 rounded-full ${isActive ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}"></div>
                        </div>
                        
                        <!-- 规则信息 -->
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-3 mb-2">
                                <h4 class="font-semibold text-white">${rule.name}</h4>
                                <span class="px-2 py-0.5 rounded-full text-xs font-medium ${level.bg} border flex items-center gap-1">
                                    <i class="fas ${level.icon} text-[10px]"></i> ${level.label}
                                </span>
                                <span class="px-2 py-0.5 rounded-full text-xs ${isActive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-700 text-slate-400'}">
                                    ${isActive ? '已启用' : '已禁用'}
                                </span>
                            </div>
                            
                            <div class="flex items-center gap-4 text-sm text-slate-400">
                                <code class="px-2 py-1 bg-slate-900 rounded text-xs font-mono text-cyan-400">${rule.condition}</code>
                                <span><i class="fas fa-microchip mr-1"></i>${rule.devices?.length || 0} 个设备</span>
                            </div>
                            
                            <div class="flex items-center gap-6 mt-3 text-xs text-slate-500">
                                <span><i class="fas fa-bell mr-1"></i>今日触发: <strong class="text-white">${rule.triggers || 0}</strong></span>
                                <span><i class="fas fa-clock mr-1"></i>最后触发: ${rule.lastTriggered || '-'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 操作按钮 -->
                    <div class="flex items-center gap-2 ml-4">
                        <button onclick="alarmRulesV2.toggleStatus(${rule.id})" 
                                class="p-2 rounded-lg hover:bg-slate-700 transition-colors" 
                                title="${isActive ? '禁用' : '启用'}">
                            <i class="fas fa-${isActive ? 'pause' : 'play'} text-sm ${isActive ? 'text-orange-400' : 'text-emerald-400'}"></i>
                        </button>
                        <button onclick="alarmRulesV2.editRule(${rule.id})" 
                                class="p-2 rounded-lg hover:bg-slate-700 transition-colors"
                                title="编辑">
                            <i class="fas fa-edit text-sm text-blue-400"></i>
                        </button>
                        <button onclick="alarmRulesV2.deleteRule(${rule.id}, '${rule.name}')" 
                                class="p-2 rounded-lg hover:bg-slate-700 transition-colors"
                                title="删除">
                            <i class="fas fa-trash-alt text-sm text-red-400"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    updateStats() {
        const total = this.rules.length;
        const active = this.rules.filter(r => r.status === 'active').length;
        const critical = this.rules.filter(r => r.level === 'critical').length;
        const todayTriggers = this.rules.reduce((sum, r) => sum + (r.triggers || 0), 0);
        
        this.animateNumber('totalRules', total);
        this.animateNumber('activeRules', active);
        this.animateNumber('criticalRules', critical);
        this.animateNumber('todayTriggers', todayTriggers);
    }

    animateNumber(elementId, targetValue) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        let current = 0;
        const step = Math.ceil(targetValue / 20);
        const interval = setInterval(() => {
            current += step;
            if (current >= targetValue) {
                current = targetValue;
                clearInterval(interval);
            }
            el.textContent = current;
        }, 30);
    }

    filterRules() {
        const search = (document.getElementById('searchInput')?.value || '').toLowerCase();
        const level = document.getElementById('levelFilter')?.value || '';
        const status = document.getElementById('statusFilter')?.value || '';
        
        const filtered = this.rules.filter(rule => {
            if (search && !rule.name.toLowerCase().includes(search)) return false;
            if (level && rule.level !== level) return false;
            if (status && rule.status !== status) return false;
            return true;
        });
        
        this.renderRules(filtered);
    }

    showAddModal() {
        document.getElementById('modalTitle').textContent = '新建告警规则';
        document.getElementById('ruleId').value = '';
        document.getElementById('ruleForm').reset();
        document.getElementById('ruleModal').classList.remove('hidden');
        this.populateDeviceSelect();
    }

    editRule(id) {
        const rule = this.rules.find(r => r.id === id);
        if (!rule) return;
        
        document.getElementById('modalTitle').textContent = '编辑告警规则';
        document.getElementById('ruleId').value = rule.id;
        document.getElementById('ruleName').value = rule.name;
        document.getElementById('ruleLevel').value = rule.level;
        document.getElementById('ruleDesc').value = rule.description || '';
        document.getElementById('ruleModal').classList.remove('hidden');
        this.populateDeviceSelect();
    }

    closeModal() {
        document.getElementById('ruleModal').classList.add('hidden');
    }

    async saveRule(e) {
        e.preventDefault();
        
        const id = document.getElementById('ruleId').value;
        const data = {
            name: document.getElementById('ruleName').value,
            level: document.getElementById('ruleLevel').value,
            description: document.getElementById('ruleDesc').value,
            condition_field: document.getElementById('conditionField').value,
            condition_operator: document.getElementById('conditionOperator').value,
            condition_value: document.getElementById('conditionValue').value,
            notify_methods: [...document.querySelectorAll('input[name="notify_methods"]:checked')].map(el => el.value),
        };
        
        try {
            const url = id ? `/api/alarms/rules/${id}` : '/api/alarms/rules';
            const method = id ? 'PUT' : 'POST';
            
            const res = await apiRequest(url, { method, body: data });
            
            if (res.success) {
                showNotification(id ? '规则更新成功' : '规则创建成功', 'success');
                this.closeModal();
                await this.loadRules();
            } else {
                showNotification(res.message || '操作失败', 'error');
            }
        } catch (error) {
            showNotification('操作失败，请重试', 'error');
        }
    }

    async toggleStatus(id) {
        const rule = this.rules.find(r => r.id === id);
        if (!rule) return;
        
        const newStatus = rule.status === 'active' ? 'inactive' : 'active';
        
        try {
            const res = await apiRequest(`/api/alarms/rules/${id}/toggle`, { method: 'POST' });
            
            if (res.success) {
                showNotification(newStatus === 'active' ? '规则已启用' : '规则已禁用', 'success');
                await this.loadRules();
            } else {
                showNotification(res.message || '操作失败', 'error');
            }
        } catch (error) {
            // 本地更新
            rule.status = newStatus;
            this.renderRules(this.rules);
            this.updateStats();
            showNotification(newStatus === 'active' ? '规则已启用' : '规则已禁用', 'success');
        }
    }

    async deleteRule(id, name) {
        if (!confirm(`确定要删除规则「${name}」吗？`)) return;
        
        try {
            const res = await apiRequest(`/api/alarms/rules/${id}`, { method: 'DELETE' });
            
            if (res.success) {
                showNotification('规则已删除', 'success');
                await this.loadRules();
            } else {
                showNotification(res.message || '删除失败', 'error');
            }
        } catch (error) {
            // 本地删除
            this.rules = this.rules.filter(r => r.id !== id);
            this.renderRules(this.rules);
            this.updateStats();
            showNotification('规则已删除', 'success');
        }
    }
}

// 全局实例
let alarmRulesV2;

document.addEventListener('DOMContentLoaded', () => {
    alarmRulesV2 = new AlarmRulesManager();
});
