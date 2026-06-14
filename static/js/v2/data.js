/**
 * 数据查看页面 - V2
 * 功能：数据筛选、图表展示、表格展示、数据导出
 */

// 全局变量
let dataChart = null;
let currentData = [];
let currentPage = 1;
const pageSize = 50;

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    initChart();
    loadDevices();
    loadData();
    
    // 设置默认时间范围
    const now = new Date();
    const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    document.getElementById('filterStartTime').value = formatDateTimeLocal(start);
    document.getElementById('filterEndTime').value = formatDateTimeLocal(now);
});

// 初始化图表
function initChart() {
    const ctx = document.getElementById('dataChart').getContext('2d');
    dataChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '数值',
                data: [],
                borderColor: '#3B82F6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1E293B',
                    titleColor: '#fff',
                    bodyColor: '#94A3B8',
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748B', maxTicksLimit: 10 }
                },
                y: {
                    grid: { color: '#E2E8F0' },
                    ticks: { color: '#64748B' }
                }
            }
        }
    });
}

// 加载设备列表
async function loadDevices() {
    try {
        const res = await api('/devices');
        if (res.success) {
            const select = document.getElementById('filterDevice');
            res.data.forEach(device => {
                const option = document.createElement('option');
                option.value = device.id;
                option.textContent = device.name + (device.is_online ? '' : ' (离线)');
                select.appendChild(option);
            });
        }
    } catch (e) {
        console.error('加载设备失败:', e);
    }
}

// 加载数据
async function loadData(showLoading = true) {
    if (showLoading) showLoadingState();
    
    try {
        const params = new URLSearchParams();
        const deviceId = document.getElementById('filterDevice').value;
        if (deviceId) params.append('device_id', deviceId);
        
        const timeRange = document.getElementById('filterTimeRange').value;
        params.append('period', timeRange);
        params.append('limit', 500);
        
        const res = await api(`/data?${params}`);
        
        if (res.success && res.data.items) {
            currentData = res.data.items;
            
            // 更新统计
            updateStats(currentData);
            
            // 更新图表
            updateChart(currentData);
            
            // 更新表格
            renderTable(currentData);
        } else {
            currentData = [];
            updateStats([]);
            updateChart([]);
            renderTable([]);
        }
        
        document.getElementById('dataCount').textContent = `${currentData.length} 条记录`;
    } catch (e) {
        console.error('加载数据失败:', e);
        showToast('加载数据失败', 'error');
    }
}

// 更新统计数据
function updateStats(data) {
    if (!data.length) {
        document.getElementById('totalPoints').textContent = '--';
        document.getElementById('avgValue').textContent = '--';
        document.getElementById('maxValue').textContent = '--';
        document.getElementById('minValue').textContent = '--';
        return;
    }
    
    const values = data.map(d => d.value || d.data_value || 0).filter(v => !isNaN(v));
    
    document.getElementById('totalPoints').textContent = values.length.toLocaleString();
    document.getElementById('avgValue').textContent = (values.reduce((a,b)=>a+b,0)/values.length).toFixed(2);
    document.getElementById('maxValue').textContent = Math.max(...values).toFixed(2);
    document.getElementById('minValue').textContent = Math.min(...values).toFixed(2);
}

// 更新图表
function updateChart(data) {
    if (!dataChart) return;
    
    // 按时间排序并取最近100条
    const sorted = [...data].sort((a,b) => new Date(a.timestamp||b.timestamp) - new Date(b.timestamp||b.timestamp)).slice(0, 100).reverse();
    
    const labels = sorted.map(d => formatTime(d.timestamp));
    const values = sorted.map(d => d.value || d.data_value || 0);
    
    dataChart.data.labels = labels;
    dataChart.data.datasets[0].data = values;
    dataChart.update();
}

// 设置图表类型
function setChartType(type) {
    if (!dataChart) return;
    
    dataChart.config.type = type;
    
    if (type === 'bar') {
        dataChart.data.datasets[0].fill = false;
        dataChart.data.datasets[0].borderWidth = 1;
    } else {
        dataChart.data.datasets[0].fill = true;
        dataChart.data.datasets[0].borderWidth = 2;
    }
    
    dataChart.update();
    
    // 更新按钮状态
    document.querySelectorAll('.chart-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === type);
    });
}

// 渲染表格
function renderTable(data) {
    const tbody = document.getElementById('dataTableBody');
    
    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无数据</td></tr>';
        return;
    }
    
    // 分页
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const pageData = data.slice(start, end);
    
    tbody.innerHTML = pageData.map(item => `
        <tr>
            <td>${formatDateTime(item.timestamp)}</td>
            <td><span class="device-name">${item.device_name || item.device_id || '-'}</span></td>
            <td>${item.channel_name || item.name || '-'}</td>
            <td><strong>${(item.value || item.data_value || 0).toFixed(2)}</strong></td>
            <td><span class="status-badge status-normal">正常</span></td>
        </tr>
    `).join('');
    
    // 渲染分页
    renderPagination(data.length);
}

// 渲染分页
function renderPagination(total) {
    const totalPages = Math.ceil(total / pageSize);
    const pagination = document.getElementById('pagination');
    
    let html = '';
    html += `<button class="page-btn" ${currentPage===1?'disabled':''} onclick="goToPage(${currentPage-1})">&lt;</button>`;
    
    for (let i=1; i<=totalPages; i++) {
        html += `<button class="page-btn ${i===currentPage?'active':''}" onclick="goToPage(${i})">${i}</button>`;
    }
    
    html += `<button class="page-btn" ${currentPage>=totalPages?'disabled':''} onclick="goToPage(${currentPage+1})">&gt;</button>`;
    
    pagination.innerHTML = html;
}

// 跳转页面
function goToPage(page) {
    currentPage = page;
    renderTable(currentData);
}

// 重置筛选条件
function resetFilters() {
    document.getElementById('filterDevice').value = '';
    document.getElementById('filterChannel').value = '';
    document.getElementById('filterTimeRange').value = '24h';
    const now = new Date();
    const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    document.getElementById('filterStartTime').value = formatDateTimeLocal(start);
    document.getElementById('filterEndTime').value = formatDateTimeLocal(now);
    currentPage = 1;
    loadData();
}

// 导出数据
async function exportData() {
    showToast('正在导出数据...', 'info');
    
    try {
        const params = new URLSearchParams();
        const deviceId = document.getElementById('filterDevice').value;
        if (deviceId) params.append('device_id', deviceId);
        params.append('format', 'csv');
        
        const response = await fetch(`/api/data/export?${params}`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `iot_data_${Date.now()}.csv`;
            a.click();
            window.URL.revokeObjectURL(url);
            showToast('导出成功', 'success');
        } else {
            throw new Error('导出失败');
        }
    } catch (e) {
        console.error('导出失败:', e);
        showToast('导出失败，请重试', 'error');
    }
}

// 显示加载状态
function showLoadingState() {
    document.getElementById('dataTableBody').innerHTML = `
        <tr><td colspan="5" class="empty-state">
            <div class="loading-spinner"></div>
            <p>正在加载数据...</p>
        </td></tr>
    `;
}

// 格式化时间（本地时间）
function formatDateTimeLocal(date) {
    const d = date instanceof Date ? date : new Date(date);
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
