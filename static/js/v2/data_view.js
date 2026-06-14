/**
 * 数据查看 JS
 * 功能: 多级筛选 + 历史数据表格 + 趋势图 + 导出 + 清理
 */
(function() {
    'use strict';

    let allDevices = [];
    let allChannels = [];
    let allDataPoints = [];
    let currentPage = 1;
    const PAGE_SIZE = 20;
    let totalCount = 0;
    let chartInstance = null;

    document.addEventListener('DOMContentLoaded', () => {
        loadFilters();
        bindEvents();
        // 默认加载一次
        setTimeout(applyFilter, 200);
        console.log('Data view initialized');
    });

    // ================= 加载筛选选项 =================
    async function loadFilters() {
        try {
            const [d, c, dp] = await Promise.all([
                apiRequest('/api/data/devices'),
                apiRequest('/api/data/channels'),
                apiRequest('/api/data/data-points')
            ]);
            if (d.success) {
                allDevices = d.data;
                const sel = document.getElementById('filterDevice');
                sel.innerHTML = '<option value="">全部设备</option>' +
                    d.data.map(x => `<option value="${x.id}">${escapeHtml(x.custom_name || x.name)}</option>`).join('');
            }
            if (c.success) {
                allChannels = c.data;
            }
            if (dp.success) {
                allDataPoints = dp.data;
            }
        } catch (e) {
            console.error('loadFilters 失败', e);
        }
    }

    // ================= 设备变更 - 联动通道 =================
    function onDeviceChange() {
        const deviceId = document.getElementById('filterDevice').value;
        const chSel = document.getElementById('filterChannel');
        const filtered = deviceId ? allChannels.filter(c => c.device_id === parseInt(deviceId)) : allChannels;
        chSel.innerHTML = '<option value="">全部通道</option>' +
            filtered.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
        onChannelChange();
    }

    function onChannelChange() {
        const channelId = document.getElementById('filterChannel').value;
        const dpSel = document.getElementById('filterDataPoint');
        const filtered = channelId ? allDataPoints.filter(dp => dp.channel_id === parseInt(channelId)) : allDataPoints;
        dpSel.innerHTML = '<option value="">全部数据点</option>' +
            filtered.map(dp => `<option value="${escapeHtml(dp.name)}">${escapeHtml(dp.name)}</option>`).join('');
    }

    // ================= 应用筛选 =================
    async function applyFilter(page = 1) {
        currentPage = page;
        const params = new URLSearchParams();
        const device = document.getElementById('filterDevice').value;
        const channel = document.getElementById('filterChannel').value;
        const dp = document.getElementById('filterDataPoint').value;
        const range = document.getElementById('filterTimeRange').value;
        if (device) params.set('device_id', device);
        if (channel) params.set('channel_id', channel);
        if (dp) params.set('data_point_name', dp);
        if (range === 'custom') {
            const s = document.getElementById('filterStartTime').value;
            const e = document.getElementById('filterEndTime').value;
            if (s) params.set('start_time', new Date(s).toISOString());
            if (e) params.set('end_time', new Date(e).toISOString());
        } else {
            params.set('hours', range);
        }
        params.set('page', page);
        params.set('page_size', PAGE_SIZE);

        const tbody = document.getElementById('dataListTbody');
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm"></span> 加载中...</td></tr>';

        try {
            const r = await apiRequest('/api/data?' + params.toString());
            if (!r.success) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger py-4">加载失败: ' + (r.error || '') + '</td></tr>';
                return;
            }
            totalCount = r.total;
            document.getElementById('dataTotal').textContent = totalCount;
            renderTable(r.data);
            renderPagination();
            renderChart(r.data);
        } catch (e) {
            console.error('applyFilter 异常', e);
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger py-4">加载异常</td></tr>';
        }
    }

    // ================= 渲染表格 =================
    function renderTable(rows) {
        const tbody = document.getElementById('dataListTbody');
        if (!rows || rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">无数据</td></tr>';
            return;
        }
        tbody.innerHTML = rows.map(r => `
            <tr>
                <td>${formatDateTime(r.timestamp)}</td>
                <td>${escapeHtml(r.device_name || '')}</td>
                <td>${escapeHtml(r.channel_name || '')}</td>
                <td>${escapeHtml(r.data_point_name || '')}</td>
                <td><strong>${formatNumber(r.value)}</strong></td>
                <td class="text-muted">${escapeHtml(r.unit || '')}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${r.id}" title="删除该条">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');

        tbody.querySelectorAll('button[data-action="delete"]').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('确定删除该条记录?')) return;
                const r = await apiRequest(`/api/data/${btn.dataset.id}`, 'DELETE');
                if (r.success) applyFilter(currentPage);
                else alert('删除失败: ' + (r.error || ''));
            });
        });
    }

    // ================= 渲染分页 =================
    function renderPagination() {
        const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
        const ul = document.getElementById('pagination');
        if (totalPages <= 1) {
            ul.innerHTML = `<li class="page-item disabled"><span class="page-link">共 ${totalCount} 条 / 1 页</span></li>`;
            return;
        }
        let html = '';
        html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" data-page="${currentPage - 1}">上一页</a></li>`;
        // 显示页码
        const start = Math.max(1, currentPage - 2);
        const end = Math.min(totalPages, start + 4);
        for (let i = start; i <= end; i++) {
            html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" data-page="${i}">${i}</a></li>`;
        }
        html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" data-page="${currentPage + 1}">下一页</a></li>`;
        html += `<li class="page-item disabled"><span class="page-link">共 ${totalCount} 条</span></li>`;
        ul.innerHTML = html;
        ul.querySelectorAll('a[data-page]').forEach(a => {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                const p = parseInt(a.dataset.page);
                if (p >= 1 && p <= totalPages) applyFilter(p);
            });
        });
    }

    // ================= 渲染图表 =================
    function renderChart(rows) {
        const container = document.getElementById('chartContainer');
        if (!rows || rows.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-5">无数据可显示</div>';
            if (chartInstance) { chartInstance.dispose(); chartInstance = null; }
            return;
        }
        if (typeof echarts === 'undefined') {
            container.innerHTML = '<div class="text-center text-muted py-5">ECharts 加载失败</div>';
            return;
        }
        if (!chartInstance) {
            chartInstance = echarts.init(container);
        }
        // 反转顺序(图表从左到右 时间升序)
        const sorted = [...rows].reverse();
        const data = sorted.map(r => [r.timestamp, r.value]);
        const option = {
            backgroundColor: 'transparent',
            textStyle: { color: '#ccc' },
            grid: { left: 60, right: 30, top: 30, bottom: 50 },
            tooltip: { trigger: 'axis' },
            xAxis: {
                type: 'time',
                axisLine: { lineStyle: { color: '#555' } },
                axisLabel: { color: '#999' }
            },
            yAxis: {
                type: 'value',
                scale: true,
                axisLine: { lineStyle: { color: '#555' } },
                axisLabel: { color: '#999' },
                splitLine: { lineStyle: { color: '#333' } }
            },
            series: [{
                type: 'line',
                smooth: true,
                showSymbol: false,
                data,
                itemStyle: { color: '#0d6efd' },
                areaStyle: {
                    color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [{ offset: 0, color: 'rgba(13,110,253,0.5)' }, { offset: 1, color: 'rgba(13,110,253,0)' }]
                    }
                }
            }]
        };
        chartInstance.setOption(option);
    }

    // ================= 导出 CSV =================
    function exportCsv() {
        const params = new URLSearchParams();
        const device = document.getElementById('filterDevice').value;
        const channel = document.getElementById('filterChannel').value;
        const dp = document.getElementById('filterDataPoint').value;
        const range = document.getElementById('filterTimeRange').value;
        if (device) params.set('device_id', device);
        if (channel) params.set('channel_id', channel);
        if (dp) params.set('data_point_name', dp);
        if (range === 'custom') {
            const s = document.getElementById('filterStartTime').value;
            const e = document.getElementById('filterEndTime').value;
            if (s) params.set('start_time', new Date(s).toISOString());
            if (e) params.set('end_time', new Date(e).toISOString());
        } else {
            params.set('hours', range);
        }
        params.set('page', 1);
        params.set('page_size', 10000);

        apiRequest('/api/data?' + params.toString()).then(r => {
            if (!r.success || !r.data || r.data.length === 0) {
                alert('没有可导出的数据');
                return;
            }
            const headers = ['时间', '设备', '通道', '数据点', '值', '单位'];
            const lines = [headers.join(',')];
            r.data.forEach(row => {
                lines.push([
                    row.timestamp,
                    csvEscape(row.device_name || ''),
                    csvEscape(row.channel_name || ''),
                    csvEscape(row.data_point_name || ''),
                    row.value,
                    csvEscape(row.unit || '')
                ].join(','));
            });
            const csv = '\uFEFF' + lines.join('\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `data_${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        });
    }

    function csvEscape(s) {
        if (s === null || s === undefined) return '';
        s = String(s);
        if (s.includes(',') || s.includes('"') || s.includes('\n')) {
            return '"' + s.replace(/"/g, '""') + '"';
        }
        return s;
    }

    // ================= 清理旧数据 =================
    async function cleanupData() {
        const days = prompt('清理多少天前数据? (输入数字, 0 取消)', '30');
        if (days === null || days === '' || parseInt(days) < 1) return;
        if (!confirm(`确定删除 ${days} 天前的所有数据?`)) return;
        const r = await apiRequest('/api/data/cleanup', 'POST', { days: parseInt(days) });
        if (r.success) {
            alert(`已删除 ${r.deleted || 0} 条记录`);
            applyFilter(1);
        } else {
            alert('清理失败: ' + (r.error || ''));
        }
    }

    // ================= 事件绑定 =================
    function bindEvents() {
        document.getElementById('filterDevice').addEventListener('change', onDeviceChange);
        document.getElementById('filterChannel').addEventListener('change', onChannelChange);
        document.getElementById('filterTimeRange').addEventListener('change', (e) => {
            document.getElementById('customTimeRange').style.display = e.target.value === 'custom' ? 'flex' : 'none';
        });
        document.getElementById('applyFilterBtn').addEventListener('click', () => applyFilter(1));
        document.getElementById('resetFilterBtn').addEventListener('click', () => {
            document.getElementById('filterDevice').value = '';
            document.getElementById('filterChannel').value = '';
            document.getElementById('filterDataPoint').value = '';
            document.getElementById('filterTimeRange').value = '24';
            onDeviceChange();
            applyFilter(1);
        });
        document.getElementById('exportDataBtn').addEventListener('click', exportCsv);
        document.getElementById('cleanupBtn').addEventListener('click', cleanupData);
        window.addEventListener('resize', () => { if (chartInstance) chartInstance.resize(); });
    }

    // ================= 工具 =================
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
    function formatDateTime(s) {
        if (!s) return '';
        const d = new Date(s);
        const pad = n => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    }
})();
