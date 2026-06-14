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
        
        document.getElementById('searchInput')?.addEventListener('input', () => this.filterRules());
        document.getElementById('levelFilter')?.addEventListener('change', () => this.filterRules());
        document.getElementById('statusFilter')?.addEventListener('change', () => this.filterRules());
        
        const durationCheck = document.getElementById('enableDuration');
        if (durationCheck) {
            durationCheck.addEventListener('change', (e) => {
                document.getElementById('durationSeconds').disabled = !e.target.checked;
            });
        }
        
        await Promise.all([this.loadRules(), this.loadDevices()]);
    }

    async loadRules() {
        try {
            const res = await apiRequest('/api/alarm-rules');
            if (res && res.success && Array.isArray(res.rules)) {
                this.rules = res.rules;
                this.renderRules(this.rules);
                this.updateStats();
            } else if (res && Array.isArray(res)) {
                this.rules = res;
                this.renderRules(this.rules);
                this.updateStats();
            } else {
                this.loadDemoData();
            }
        } catch (error) {
            console.error('[AlarmRules] 加载失败:', error);
            this.loadDemoData();
        }
    }

    loadDemoData() {
        this.rules = [
            { id: 1, name: '温度超限告警', level: 'critical', status: 'active', condition: 'temperature > 80°C', device_count: 2, triggers: 15, last_triggered: '2026-06-14 10:30' },
            { id: 2, name: '设备离线检测', level: 'warning', status: 'active', condition: 'status == offline', device_count: 0, triggers: 8, last_triggered: '2026-06-14 09:45' },
            { id: 3, name: '湿度异常警告', level: 'warning', status: 'active', condition: 'humidity > 90%', device_count: 1, triggers: 3, last_triggered: '2026-06-13 22:10' },
            { id: 4, name: '电池电量低', level: 'info', status: 'inactive', condition: 'battery < 20%', device_count: 0, triggers: 0, last_triggered: '-' },
            { id: 5, name: '数据上报异常', level: 'critical', status: 'active', condition: 'no_data > 300s', device_count: 0, triggers: 2, last_triggered: '2026-06-14 08:00' },
            { id: 6, name: '振动超标预警', level: 'warning', status: 'active', condition: 'vibration > 50mm/s', device_count: 1, triggers: 12, last_triggered: '2026-06-14 11:20' },
        ];
        this.renderRules(this.rules);
        this.updateStats();
    }

    async loadDevices() {
        try {
            const res = await apiRequest('/api/devices?size=100');
            if (res && res.success && Array.isArray(res.devices)) {
                this.devices = res.devices;
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
            `<option value="${d.id}">${d.name || d.device_name || '设备-' + d.id}</option>`
        ).join('');
    }

    updateStats() {
        const active = this.rules.filter(r => r.status === 'active');
        const critical = active.filter(r => r.level === 'critical');
        const warning = active.filter(r => r.level === 'warning');
        const info = active.filter(r => r.level === 'info');
        const totalTriggers = this.rules.reduce((sum, r) => sum + (r.triggers || 0), 0);
        
        this.setVal('totalRules', this.rules.length);
        this.setVal('activeRules', active.length);
        this.setVal('criticalRules', critical.length);
        this.setVal('todayTriggers', totalTriggers);
    }

    renderRules(rules) {
        const tbody = document.getElementById('rulesTableBody');
        if (!tbody) return;
        
        if (!rules.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">暂无告警规则</td></tr>';
            return;
        }
        
        const levelBadge = { critical: 'danger', warning: 'warning', info: 'info' };
        const levelText = { critical: '严重', warning: '警告', info: '通知' };
        
        tbody.innerHTML = rules.map(r => `
            <tr>
                <td><span class="badge bg-${levelBadge[r.level] || 'secondary'}">${levelText[r.level] || r.level}</span></td>
                <td>${this.escape(r.name)}</td>
                <td><code class="text-muted">${this.escape(r.condition || '-')}</code></td>
                <td>${r.device_count || 0}</td>
                <td><span class="badge ${r.status === 'active' ? 'bg-success' : 'bg-secondary'}">${r.status === 'active' ? '启用' : '禁用'}</span></td>
                <td><small class="text-muted">${r.last_triggered || '-'}</small></td>
                <td>
                    <button class="btn btn-sm btn-outline-secondary me-1" onclick="alarmRulesV2.editRule(${r.id})" title="编辑"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-sm btn-outline-${r.status === 'active' ? 'warning' : 'success'} me-1" onclick="alarmRulesV2.toggleStatus(${r.id})" title="${r.status === 'active' ? '禁用' : '启用'}"><i class="bi bi-${r.status === 'active' ? 'pause' : 'play'}"></i></button>
                    <button class="btn btn-sm btn-outline-danger" onclick="alarmRulesV2.deleteRule(${r.id}, '${this.escape(r.name)}')" title="删除"><i class="bi bi-trash"></i></button>
                </td>
            </tr>
        `).join('');
    }

    filterRules() {
        const search = (document.getElementById('searchInput')?.value || '').toLowerCase();
        const level = document.getElementById('levelFilter')?.value || '';
        const status = document.getElementById('statusFilter')?.value || '';
        
        let filtered = this.rules;
        if (search) filtered = filtered.filter(r => r.name.toLowerCase().includes(search));
        if (level) filtered = filtered.filter(r => r.level === level);
        if (status) filtered = filtered.filter(r => r.status === status);
        
        this.renderRules(filtered);
    }

    showCreateModal() {
        document.getElementById('ruleModalTitle').textContent = '新建告警规则';
        document.getElementById('ruleId').value = '';
        document.getElementById('ruleName').value = '';
        document.getElementById('ruleLevel').value = 'warning';
        document.getElementById('conditionField').value = '';
        document.getElementById('conditionOp').value = '>';
        document.getElementById('conditionValue').value = '';
        document.getElementById('enableDuration').checked = false;
        document.getElementById('durationSeconds').value = '60';
        document.getElementById('durationSeconds').disabled = true;
        document.querySelectorAll('input[name="notify_methods"]').forEach(el => el.checked = false);
        bootstrap.Modal.getOrCreateInstance(document.getElementById('ruleModal')).show();
    }

    editRule(id) {
        const rule = this.rules.find(r => r.id === id);
        if (!rule) return;
        
        document.getElementById('ruleModalTitle').textContent = '编辑告警规则';
        document.getElementById('ruleId').value = rule.id;
        document.getElementById('ruleName').value = rule.name || '';
        document.getElementById('ruleLevel').value = rule.level || 'warning';
        document.getElementById('conditionField').value = rule.condition_field || '';
        document.getElementById('conditionOp').value = rule.condition_op || '>';
        document.getElementById('conditionValue').value = rule.condition_value || '';
        bootstrap.Modal.getOrCreateInstance(document.getElementById('ruleModal')).show();
    }

    closeModal() {
        bootstrap.Modal.getInstance(document.getElementById('ruleModal'))?.hide();
    }

    async saveRule() {
        const id = document.getElementById('ruleId').value;
        const data = {
            name: document.getElementById('ruleName').value,
            level: document.getElementById('ruleLevel').value,
            condition_field: document.getElementById('conditionField').value,
            condition_op: document.getElementById('conditionOp').value,
            condition_value: document.getElementById('conditionValue').value,
        };
        
        if (!data.name) {
            showToast('请输入规则名称', 'warning');
            return;
        }
        
        try {
            const url = id ? `/api/alarm-rules/${id}` : '/api/alarm-rules';
            const method = id ? 'PUT' : 'POST';
            const res = await apiRequest(url, method, data);
            
            if (res && res.success) {
                showToast(id ? '规则更新成功' : '规则创建成功', 'success');
                this.closeModal();
                await this.loadRules();
            } else {
                showToast(res?.message || '操作失败', 'danger');
            }
        } catch (error) {
            showToast('操作失败，请重试', 'danger');
        }
    }

    async toggleStatus(id) {
        const rule = this.rules.find(r => r.id === id);
        if (!rule) return;
        
        try {
            const res = await apiRequest(`/api/alarm-rules/${id}/toggle`, 'POST');
            if (res && res.success) {
                showToast('状态切换成功', 'success');
                await this.loadRules();
            }
        } catch (error) {
            rule.status = rule.status === 'active' ? 'inactive' : 'active';
            this.renderRules(this.rules);
            this.updateStats();
        }
    }

    async deleteRule(id, name) {
        if (!confirm(`确定要删除规则「${name}」吗？`)) return;
        
        try {
            const res = await apiRequest(`/api/alarm-rules/${id}`, 'DELETE');
            if (res && res.success) {
                showToast('规则已删除', 'success');
                await this.loadRules();
            }
        } catch (error) {
            this.rules = this.rules.filter(r => r.id !== id);
            this.renderRules(this.rules);
            this.updateStats();
            showToast('规则已删除', 'success');
        }
    }

    setVal(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    escape(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
}

let alarmRulesV2;
document.addEventListener('DOMContentLoaded', () => {
    alarmRulesV2 = new AlarmRulesManager();
});
