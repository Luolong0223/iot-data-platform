/**
 * Alarms V2 - IoT Data Platform
 * 告警管理页面
 */

class AlarmsPageV2 {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 15;
        this.currentAlarmId = null;
        this.trendChart = null;
        this.init();
    }

    async init() {
        console.log('[Alarms] Initializing...');
        await Promise.all([
            this.loadAlarmStats(),
            this.loadAlarms(),
            this.loadRules(),
            this.loadDevices()
        ]);
        this.initTrendChart();
        this.bindEvents();

        // 自动刷新（30秒）
        setInterval(() => {
            this.loadAlarms();
            this.loadAlarmStats();
        }, 30000);
    }

    bindEvents() {
        const severityFilter = document.getElementById('severity-filter');
        const statusFilter = document.getElementById('status-filter');
        const refreshBtn = document.getElementById('refreshBtn');
        const newRuleBtn = document.getElementById('newRuleBtn');

        if (severityFilter) severityFilter.addEventListener('change', () => { this.currentPage = 1; this.loadAlarms(); });
        if (statusFilter) statusFilter.addEventListener('change', () => { this.currentPage = 1; this.loadAlarms(); });
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadAlarms());
        if (newRuleBtn) newRuleBtn.addEventListener('click', () => this.showNewRuleModal());
    }

    async loadAlarmStats() {
        try {
            const response = await apiRequest('/api/alarms/stats');
            // stats API returns data directly without success wrapper
            const data = response || {};
            this.setVal('critical-count', data.critical || 0);
            this.setVal('warning-count', data.warning || 0);
            this.setVal('info-count', data.info || 0);
            this.setVal('resolved-count', data.resolved || 0);
        } catch (e) {
            console.error('[Alarms] Stats error:', e);
        }
    }

    async loadAlarms() {
        try {
            const severity = document.getElementById('severity-filter')?.value || '';
            const status = document.getElementById('status-filter')?.value || '';

            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.pageSize
            });
            if (severity) params.append('severity', severity);
            if (status) params.append('status', status);

            const response = await apiRequest(`/api/alarms/records?${params}`);
            if (response && response.success) {
                const items = response.records || [];
                this.renderAlarmsTable(items);
                this.renderPagination(response.total || items.length);
            } else {
                this.renderAlarmsTable([]);
                this.renderPagination(0);
            }
        } catch (e) {
            console.error('[Alarms] Load error:', e);
            this.renderAlarmsTable([]);
            this.renderPagination(0);
        }
    }

    renderAlarmsTable(alarms) {
        const tbody = document.getElementById('alarms-tbody');
        if (!tbody) return;

        if (!alarms || !alarms.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted-foreground py-8">暂无告警数据</td></tr>';
            return;
        }

        tbody.innerHTML = alarms.map(alarm => `
            <tr class="border-b border-border hover:bg-muted/30 transition-colors" data-id="${alarm.id}">
                <td class="py-2 px-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${this.getStatusClass(alarm.status)}">${this.getStatusLabel(alarm.status)}</span>
                </td>
                <td class="py-2 px-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${this.getSeverityClass(alarm.severity)}">${this.getSeverityLabel(alarm.severity)}</span>
                </td>
                <td class="py-2 px-3">
                    <div class="font-medium text-foreground">${this.escapeHtml(alarm.title || alarm.message || '-')}</div>
                    <div class="text-xs text-muted-foreground">${this.escapeHtml(alarm.message || '')}</div>
                </td>
                <td class="py-2 px-3 text-muted-foreground">${this.escapeHtml(alarm.device_name || '-')}</td>
                <td class="py-2 px-3 text-muted-foreground text-sm">${this.formatTime(alarm.created_at)}</td>
                <td class="py-2 px-3">
                    <button class="text-primary hover:underline text-sm mr-2" onclick="AlarmsPageV2.instance.viewAlarm(${alarm.id})">查看</button>
                    ${alarm.status !== 'resolved' ? `<button class="text-green-400 hover:underline text-sm" onclick="AlarmsPageV2.instance.resolveAlarm(${alarm.id})">解决</button>` : ''}
                </td>
            </tr>
        `).join('');
    }

    renderPagination(total) {
        const wrapper = document.getElementById('alarms-pagination');
        if (!wrapper) return;

        const totalPages = Math.ceil(total / this.pageSize);
        if (totalPages <= 1) {
            wrapper.innerHTML = '';
            return;
        }

        let html = `<span class="text-sm text-muted-foreground mr-3">共 ${total} 条</span>`;
        html += `<button class="px-3 py-1 rounded border border-border text-sm ${this.currentPage === 1 ? 'opacity-50' : 'hover:bg-muted'}" ${this.currentPage === 1 ? 'disabled' : ''} data-page="${this.currentPage - 1}">上一页</button>`;

        for (let i = Math.max(1, this.currentPage - 2); i <= Math.min(totalPages, this.currentPage + 2); i++) {
            html += `<button class="px-3 py-1 rounded text-sm ${i === this.currentPage ? 'bg-primary text-primary-foreground' : 'border border-border hover:bg-muted'}" data-page="${i}">${i}</button>`;
        }

        html += `<button class="px-3 py-1 rounded border border-border text-sm ${this.currentPage >= totalPages ? 'opacity-50' : 'hover:bg-muted'}" ${this.currentPage >= totalPages ? 'disabled' : ''} data-page="${this.currentPage + 1}">下一页</button>`;

        wrapper.innerHTML = html;
        wrapper.querySelectorAll('button[data-page]').forEach(btn => {
            btn.addEventListener('click', () => this.goToPage(parseInt(btn.dataset.page)));
        });
    }

    goToPage(page) {
        this.currentPage = page;
        this.loadAlarms();
    }

    async loadRules() {
        try {
            const response = await apiRequest('/api/alarm-rules');
            if (response && response.success) {
                this.renderRulesList(response.data || []);
            } else {
                this.renderRulesList([]);
            }
        } catch (e) {
            console.error('[Alarms] Rules error:', e);
            this.renderRulesList([]);
        }
    }

    renderRulesList(rules) {
        const container = document.getElementById('rules-list');
        if (!container) return;

        if (!rules || !rules.length) {
            container.innerHTML = '<div class="text-center text-muted-foreground py-8">暂无规则</div>';
            return;
        }

        container.innerHTML = rules.map(rule => `
            <div class="rule-item p-4 rounded-lg border border-border bg-card mb-3 ${rule.enabled ? '' : 'opacity-60'}">
                <div class="flex items-center justify-between mb-2">
                    <span class="font-medium text-foreground">${this.escapeHtml(rule.name)}</span>
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${this.getSeverityClass(rule.severity)}">${this.getSeverityLabel(rule.severity)}</span>
                </div>
                <div class="text-sm text-muted-foreground mb-2">
                    <code class="bg-muted px-1.5 py-0.5 rounded text-xs">${this.escapeHtml(rule.device_name || '*')} . ${this.escapeHtml(rule.point_name || rule.channel_name || 'value')} ${this.getConditionSymbol(rule.condition)} ${rule.threshold}</code>
                </div>
                <div class="flex gap-2">
                    <button class="text-primary hover:underline text-sm" onclick="AlarmsPageV2.instance.editRule(${rule.id})">编辑</button>
                    <button class="text-red-400 hover:underline text-sm" onclick="AlarmsPageV2.instance.deleteRule(${rule.id})">删除</button>
                </div>
            </div>
        `).join('');
    }

    async loadDevices() {
        try {
            const response = await apiRequest('/api/devices?per_page=100');
            const devices = response?.data?.items || response?.data || [];
            const select = document.getElementById('rule-device');
            if (select && devices.length) {
                devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.name;
                    option.textContent = device.name;
                    select.appendChild(option);
                });
            }
        } catch (e) {
            console.error('[Alarms] Devices error:', e);
        }
    }

    initTrendChart() {
        const dom = document.getElementById('alarm-trend-chart');
        if (!dom) return;

        if (this.trendChart) this.trendChart.dispose();
        this.trendChart = echarts.init(dom);

        // Load trend data
        apiRequest('/api/alarms/stats/chart?days=7').then(response => {
            if (response && response.success && response.data) {
                const data = response.data;
                this.trendChart.setOption({
                    tooltip: {
                        trigger: 'axis',
                        backgroundColor: 'rgba(15,23,42,0.9)',
                        borderColor: '#334155',
                        textStyle: { color: '#e2e8f0' }
                    },
                    grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
                    xAxis: {
                        type: 'category',
                        data: data.labels || [],
                        axisLine: { lineStyle: { color: '#334155' } },
                        axisLabel: { color: '#64748b', fontSize: 10 }
                    },
                    yAxis: {
                        type: 'value',
                        axisLine: { lineStyle: { color: '#334155' } },
                        axisLabel: { color: '#64748b' },
                        splitLine: { lineStyle: { color: '#1e293b' } }
                    },
                    series: [{
                        type: 'bar',
                        data: data.values || [],
                        itemStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: '#ef4444' },
                                { offset: 1, color: '#991b1b' }
                            ])
                        }
                    }]
                });
            }
        }).catch(() => {
            this.trendChart.setOption({
                title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#64748b', fontSize: 14 } },
                xAxis: { show: false }, yAxis: { show: false }, series: []
            });
        });
    }

    viewAlarm(id) {
        window.location.href = `/alarms/${id}`;
    }

    async resolveAlarm(id) {
        try {
            const response = await apiRequest(`/api/alarms/${id}/resolve`, 'POST');
            if (response && response.success) {
                this.loadAlarms();
                this.loadAlarmStats();
            }
        } catch (e) {
            console.error('[Alarms] Resolve error:', e);
        }
    }

    editRule(id) {
        window.location.href = `/alarm-rules/${id}/edit`;
    }

    async deleteRule(id) {
        if (!confirm('确定要删除此规则吗？')) return;
        try {
            const response = await apiRequest(`/api/alarm-rules/${id}`, 'DELETE');
            if (response && response.success) {
                this.loadRules();
            }
        } catch (e) {
            console.error('[Alarms] Delete rule error:', e);
        }
    }

    showNewRuleModal() {
        window.location.href = '/alarm-rules/add';
    }

    // Helpers
    setVal(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    formatTime(timestamp) {
        if (!timestamp) return '-';
        return timestamp.length > 16 ? timestamp.slice(0, 19).replace('T', ' ') : timestamp;
    }

    getStatusClass(status) {
        const map = { active: 'bg-red-500/20 text-red-400', acknowledged: 'bg-yellow-500/20 text-yellow-400', resolved: 'bg-green-500/20 text-green-400' };
        return map[status] || 'bg-muted text-muted-foreground';
    }

    getStatusLabel(status) {
        const map = { active: '未处理', acknowledged: '已确认', resolved: '已解决' };
        return map[status] || status || '未知';
    }

    getSeverityClass(severity) {
        const map = { critical: 'bg-red-500/20 text-red-400', warning: 'bg-yellow-500/20 text-yellow-400', info: 'bg-blue-500/20 text-blue-400' };
        return map[severity] || 'bg-muted text-muted-foreground';
    }

    getSeverityLabel(severity) {
        const map = { critical: '严重', warning: '警告', info: '通知' };
        return map[severity] || severity || '未知';
    }

    getConditionSymbol(condition) {
        const map = { gt: '>', gte: '>=', lt: '<', lte: '<=', eq: '=', neq: '!=' };
        return map[condition] || condition || '?';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    AlarmsPageV2.instance = new AlarmsPageV2();
});
