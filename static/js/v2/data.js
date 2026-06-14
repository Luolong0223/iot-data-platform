/**
 * Data V2 - IoT Data Platform
 * 数据查看页面 - 筛选、图表、表格
 */

class DataPageV2 {
    constructor() {
        this.chart = null;
        this.currentData = [];
        this.currentPage = 1;
        this.pageSize = 20;
        this.init();
    }

    async init() {
        console.log('[Data] Initializing...');
        this.setDefaultTimeRange();
        await this.loadDevices();
        await this.loadData();
        this.bindEvents();
    }

    setDefaultTimeRange() {
        const now = new Date();
        const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        const startEl = document.getElementById('filterStartTime');
        const endEl = document.getElementById('filterEndTime');
        if (startEl) startEl.value = this.formatDateTimeLocal(start);
        if (endEl) endEl.value = this.formatDateTimeLocal(now);
    }

    async loadDevices() {
        try {
            const response = await apiRequest('/api/devices');
            if (response && response.success && response.data) {
                const select = document.getElementById('filterDevice');
                if (select) {
                    response.data.forEach(device => {
                        const option = document.createElement('option');
                        option.value = device.id;
                        option.textContent = device.name + (device.is_online ? '' : ' (离线)');
                        select.appendChild(option);
                    });
                }
            }
        } catch (e) {
            console.error('[Data] Load devices error:', e);
        }
    }

    async loadData() {
        try {
            const params = new URLSearchParams();
            const deviceId = document.getElementById('filterDevice')?.value;
            const channelId = document.getElementById('filterChannel')?.value;
            if (deviceId) params.append('device_id', deviceId);
            if (channelId) params.append('channel_id', channelId);
            params.append('limit', '500');

            const response = await apiRequest(`/api/data/history?${params}`);
            
            if (response && response.success && response.data) {
                this.currentData = response.data;
                this.updateStats(response.data);
                this.renderChart(response.data);
                this.renderTable(response.data);
                this.updateCount(response.data.length);
            } else {
                this.currentData = [];
                this.updateStats([]);
                this.renderChart([]);
                this.renderTable([]);
                this.updateCount(0);
            }
        } catch (e) {
            console.error('[Data] Load error:', e);
            this.currentData = [];
            this.updateStats([]);
            this.renderChart([]);
            this.renderTable([]);
            this.updateCount(0);
        }
    }

    updateStats(data) {
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        if (!data || !data.length) {
            setVal('totalPoints', '--');
            setVal('avgValue', '--');
            setVal('maxValue', '--');
            setVal('minValue', '--');
            return;
        }

        const values = data.map(d => d.value || 0).filter(v => !isNaN(v));
        if (values.length === 0) {
            setVal('totalPoints', '0');
            setVal('avgValue', '--');
            setVal('maxValue', '--');
            setVal('minValue', '--');
            return;
        }

        setVal('totalPoints', values.length.toLocaleString());
        setVal('avgValue', (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2));
        setVal('maxValue', Math.max(...values).toFixed(2));
        setVal('minValue', Math.min(...values).toFixed(2));
    }

    renderChart(data) {
        const chartDom = document.getElementById('dataChart');
        if (!chartDom) return;

        if (this.chart) this.chart.dispose();
        this.chart = echarts.init(chartDom);

        if (!data || !data.length) {
            this.chart.setOption({
                title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#64748b', fontSize: 14 } },
                xAxis: { show: false }, yAxis: { show: false }, series: []
            });
            return;
        }

        const sorted = [...data]
            .sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0))
            .slice(-100);

        const labels = sorted.map(d => {
            const t = d.timestamp || '';
            return t.length > 16 ? t.slice(5, 16) : t;
        });
        const values = sorted.map(d => d.value || 0);

        this.chart.setOption({
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(15,23,42,0.9)',
                borderColor: '#334155',
                textStyle: { color: '#e2e8f0' }
            },
            grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
            xAxis: {
                type: 'category', data: labels,
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b', rotate: 30, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: '#334155' } },
                axisLabel: { color: '#64748b' },
                splitLine: { lineStyle: { color: '#1e293b' } }
            },
            series: [{
                type: 'line', smooth: true,
                data: values,
                lineStyle: { color: '#3b82f6', width: 2 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(59,130,246,0.3)' },
                        { offset: 1, color: 'rgba(59,130,246,0)' }
                    ])
                },
                itemStyle: { color: '#3b82f6' },
                symbol: 'none'
            }]
        });
    }

    renderTable(data) {
        const tbody = document.getElementById('dataTableBody');
        if (!tbody) return;

        if (!data || !data.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted-foreground py-8">暂无数据</td></tr>';
            return;
        }

        const start = (this.currentPage - 1) * this.pageSize;
        const pageData = data.slice(start, start + this.pageSize);

        tbody.innerHTML = pageData.map(item => `
            <tr class="border-b border-border hover:bg-muted/30 transition-colors">
                <td class="py-2 px-3 text-muted-foreground text-sm">${this.formatDateTime(item.timestamp)}</td>
                <td class="py-2 px-3 text-foreground">${item.device_name || '-'}</td>
                <td class="py-2 px-3 text-muted-foreground">${item.name || '-'}</td>
                <td class="py-2 px-3 font-mono text-primary">${(item.value || 0).toFixed(2)}</td>
                <td class="py-2 px-3"><span class="text-green-400 text-sm">正常</span></td>
            </tr>
        `).join('');

        this.renderPagination(data.length);
    }

    renderPagination(total) {
        const container = document.getElementById('pagination');
        if (!container) return;

        const totalPages = Math.ceil(total / this.pageSize);
        let html = '';
        html += `<button class="px-3 py-1 rounded border border-border text-sm ${this.currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-muted'}" ${this.currentPage === 1 ? 'disabled' : ''} data-page="${this.currentPage - 1}">&lt;</button>`;
        
        for (let i = 1; i <= Math.min(totalPages, 7); i++) {
            html += `<button class="px-3 py-1 rounded text-sm ${i === this.currentPage ? 'bg-primary text-primary-foreground' : 'border border-border hover:bg-muted'}" data-page="${i}">${i}</button>`;
        }
        
        html += `<button class="px-3 py-1 rounded border border-border text-sm ${this.currentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'hover:bg-muted'}" ${this.currentPage >= totalPages ? 'disabled' : ''} data-page="${this.currentPage + 1}">&gt;</button>`;
        
        container.innerHTML = html;
        container.querySelectorAll('button[data-page]').forEach(btn => {
            btn.addEventListener('click', () => this.goToPage(parseInt(btn.dataset.page)));
        });
    }

    goToPage(page) {
        this.currentPage = page;
        this.renderTable(this.currentData);
    }

    updateCount(count) {
        const el = document.getElementById('dataCount');
        if (el) el.textContent = `${count} 条记录`;
    }

    bindEvents() {
        const queryBtn = document.getElementById('queryBtn');
        const resetBtn = document.getElementById('resetBtn');
        const exportBtn = document.getElementById('exportBtn');

        if (queryBtn) queryBtn.addEventListener('click', () => { this.currentPage = 1; this.loadData(); });
        if (resetBtn) resetBtn.addEventListener('click', () => this.resetFilters());
        if (exportBtn) exportBtn.addEventListener('click', () => this.exportData());
    }

    resetFilters() {
        const deviceEl = document.getElementById('filterDevice');
        const channelEl = document.getElementById('filterChannel');
        if (deviceEl) deviceEl.value = '';
        if (channelEl) channelEl.value = '';
        this.setDefaultTimeRange();
        this.currentPage = 1;
        this.loadData();
    }

    async exportData() {
        try {
            const params = new URLSearchParams();
            const deviceId = document.getElementById('filterDevice')?.value;
            if (deviceId) params.append('device_id', deviceId);
            params.append('format', 'csv');

            const response = await fetch(`/api/data/export?${params}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `iot_data_${Date.now()}.csv`;
                a.click();
                window.URL.revokeObjectURL(url);
            }
        } catch (e) {
            console.error('[Data] Export error:', e);
        }
    }

    formatDateTime(timestamp) {
        if (!timestamp) return '-';
        return timestamp.length > 16 ? timestamp.slice(0, 19).replace('T', ' ') : timestamp;
    }

    formatDateTimeLocal(date) {
        const d = date instanceof Date ? date : new Date(date);
        const pad = n => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new DataPageV2();
});
