/**
 * 设备管理 JS
 * 功能: 分类树 + 设备列表 + 详情/编辑/分类操作
 */
(function() {
    'use strict';

    let categoryTree = [];        // 分类树原始数据
    let allDevices = [];          // 全部设备
    let currentCategoryId = null; // 当前选中的分类
    let expandedCategories = new Set(); // 展开的分类

    document.addEventListener('DOMContentLoaded', () => {
        loadCategories();
        loadDevices();
        bindEvents();
        console.log('Devices page initialized');
    });

    // ================= 加载分类树 =================
    async function loadCategories() {
        try {
            const r = await apiRequest('/api/devices/categories');
            if (!r.success) return;
            categoryTree = r.data;
            renderCategoryTree();
        } catch (e) {
            console.error('加载分类失败', e);
        }
    }

    // ================= 渲染分类树 (递归) =================
    function renderCategoryTree(nodes = null, container = null) {
        const nodesToRender = nodes === null ? categoryTree : nodes;
        const targetContainer = container || document.getElementById('categoryTree');

        if (nodes === null) {
            targetContainer.innerHTML = '';
        }

        if (!nodesToRender || nodesToRender.length === 0) {
            if (nodes === null) {
                targetContainer.innerHTML = '<div class="text-center text-muted py-3 small">暂无分类,点击"+"新建</div>';
            }
            return;
        }

        const kw = (document.getElementById('searchCategoryInput')?.value || '').toLowerCase();
        const visible = nodesToRender.filter(n => matchCategoryKeyword(n, kw));

        if (nodes === null && visible.length === 0) {
            targetContainer.innerHTML = '<div class="text-center text-muted py-3 small">没有匹配的分类</div>';
            return;
        }

        visible.forEach(node => {
            const hasChildren = node.children && node.children.length > 0;
            const isExpanded = expandedCategories.has(node.id);
            const isActive = currentCategoryId === node.id;
            const ul = document.createElement('ul');
            ul.className = 'tree-list mb-1';
            const li = document.createElement('li');
            li.className = 'tree-item';
            li.innerHTML = `
                <div class="tree-row ${isActive ? 'active' : ''}" data-category-id="${node.id}">
                    ${hasChildren ? `<i class="bi bi-caret-${isExpanded ? 'down' : 'right'}-fill tree-toggle" data-id="${node.id}"></i>` : '<span style="width:14px;display:inline-block;"></span>'}
                    <i class="bi bi-folder${isExpanded ? '-open' : ''} tree-icon"></i>
                    <span class="tree-label">${escapeHtml(node.name)}</span>
                    <span class="tree-count">${node.device_count || 0}</span>
                    <div class="tree-actions">
                        <i class="bi bi-plus-circle" title="新建子分类" data-action="add-child" data-id="${node.id}"></i>
                        <i class="bi bi-pencil" title="编辑" data-action="edit" data-id="${node.id}"></i>
                        <i class="bi bi-trash" title="删除" data-action="delete" data-id="${node.id}"></i>
                    </div>
                </div>
                <div class="tree-children" data-parent-id="${node.id}" style="display:${isExpanded ? 'block' : 'none'};"></div>
            `;
            ul.appendChild(li);
            targetContainer.appendChild(ul);

            if (hasChildren) {
                const childContainer = li.querySelector('.tree-children');
                renderCategoryTree(node.children, childContainer);
            }
        });
    }

    function matchCategoryKeyword(node, kw) {
        if (!kw) return true;
        if (node.name.toLowerCase().includes(kw)) return true;
        if (node.children) {
            return node.children.some(c => matchCategoryKeyword(c, kw));
        }
        return false;
    }

    // ================= 加载设备 =================
    async function loadDevices() {
        try {
            const url = currentCategoryId !== null ?
                `/api/devices/devices?category_id=${currentCategoryId}` :
                '/api/devices/devices';
            const r = await apiRequest(url);
            if (!r.success) return;
            allDevices = r.data;
            renderDeviceList();
        } catch (e) {
            console.error('加载设备失败', e);
        }
    }

    // ================= 渲染设备列表 =================
    function renderDeviceList() {
        const tbody = document.getElementById('deviceListTbody');
        if (allDevices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">暂无设备 (请通过 TCP 接收数据)</td></tr>';
            document.getElementById('deviceCount').textContent = '0';
            return;
        }
        document.getElementById('deviceCount').textContent = allDevices.length;
        const keyword = (document.getElementById('searchDeviceInput')?.value || '').toLowerCase();
        const filtered = keyword ? allDevices.filter(d =>
            (d.name && d.name.toLowerCase().includes(keyword)) ||
            (d.custom_name && d.custom_name.toLowerCase().includes(keyword))
        ) : allDevices;

        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">未匹配到设备</td></tr>';
            return;
        }

        tbody.innerHTML = filtered.map(d => {
            const onlineClass = d.is_online ? 'text-success' : 'text-danger';
            const onlineText = d.is_online ? '在线' : '离线';
            const dot = d.is_online ? '🟢' : '🔴';
            const lastSeen = d.last_seen ? formatRelativeTime(new Date(d.last_seen)) : '从未';
            return `
                <tr data-device-id="${d.id}">
                    <td><span title="${onlineText}">${dot}</span></td>
                    <td>${escapeHtml(d.name)}</td>
                    <td>${escapeHtml(d.custom_name || '--')}</td>
                    <td>${escapeHtml(d.category_name || '<未分类>')}</td>
                    <td>${d.voltage_mv !== null && d.voltage_mv !== undefined ? d.voltage_mv : '--'}</td>
                    <td>${d.channel_count || 0}</td>
                    <td title="${d.last_seen || ''}">${lastSeen}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-info" data-action="view" data-id="${d.id}">详情</button>
                        <button class="btn btn-sm btn-outline-primary" data-action="edit" data-id="${d.id}">编辑</button>
                        <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${d.id}">删除</button>
                    </td>
                </tr>
            `;
        }).join('');

        tbody.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                const action = btn.dataset.action;
                if (action === 'view') showDeviceDetail(id);
                else if (action === 'edit') showEditDevice(id);
                else if (action === 'delete') deleteDevice(id);
            });
        });
    }

    // ================= 设备详情 =================
    async function showDeviceDetail(id) {
        const r = await apiRequest(`/api/devices/devices/${id}`);
        if (!r.success) {
            alert('加载设备详情失败: ' + (r.error || ''));
            return;
        }
        const d = r.data;
        document.getElementById('detailDeviceName').textContent = d.custom_name || d.name;
        const content = document.getElementById('deviceDetailBody');
        const channelHtml = (d.channels || []).map(c => {
            const dpHtml = (c.data_points || []).map(dp => `
                <tr>
                    <td>${escapeHtml(dp.name)}</td>
                    <td>${dp.latest_value !== null ? formatNumber(dp.latest_value) : '--'}</td>
                    <td>${escapeHtml(dp.unit || '')}</td>
                    <td>${dp.timestamp ? formatRelativeTime(new Date(dp.timestamp)) : '从未'}</td>
                </tr>
            `).join('');
            return `
                <div class="mb-3">
                    <h6>
                        <i class="bi bi-broadcast"></i> ${escapeHtml(c.name)}
                        <span class="badge bg-${c.is_online ? 'success' : 'secondary'} ms-1">${c.is_online ? '在线' : '离线'}</span>
                    </h6>
                    <table class="table table-dark table-sm mb-0">
                        <thead>
                            <tr><th>数据点</th><th>最新值</th><th>单位</th><th>时间</th></tr>
                        </thead>
                        <tbody>${dpHtml || '<tr><td colspan="4" class="text-center text-muted">无数据</td></tr>'}</tbody>
                    </table>
                </div>
            `;
        }).join('');

        content.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <table class="table table-dark table-borderless table-sm">
                        <tr><th style="width:120px;">设备名</th><td>${escapeHtml(d.name)}</td></tr>
                        <tr><th>自定义名</th><td>${escapeHtml(d.custom_name || '--')}</td></tr>
                        <tr><th>分类</th><td>${escapeHtml(d.category_name || '未分类')}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <table class="table table-dark table-borderless table-sm">
                        <tr><th style="width:120px;">电压</th><td>${d.voltage_mv !== null ? d.voltage_mv + ' mV' : '--'}</td></tr>
                        <tr><th>状态</th><td><span class="text-${d.is_online ? 'success' : 'danger'}">${d.is_online ? '在线' : '离线'}</span></td></tr>
                        <tr><th>最后更新</th><td>${d.last_seen || '--'}</td></tr>
                    </table>
                </div>
            </div>
            <hr class="border-secondary">
            <h6>通道与数据点</h6>
            ${channelHtml || '<div class="text-muted">无通道数据</div>'}
        `;

        new bootstrap.Modal(document.getElementById('deviceDetailModal')).show();
    }

    // ================= 编辑设备 =================
    async function showEditDevice(id) {
        const r = await apiRequest(`/api/devices/devices/${id}`);
        if (!r.success) {
            alert('加载设备失败');
            return;
        }
        const d = r.data;
        document.getElementById('editDeviceId').value = d.id;
        document.getElementById('editDeviceOriginalName').value = d.name;
        document.getElementById('editDeviceCustomName').value = d.custom_name || '';
        document.getElementById('editDeviceDescription').value = d.description || '';

        // 填充分类下拉
        const sel = document.getElementById('editDeviceCategory');
        sel.innerHTML = '<option value="">-- 未分类 --</option>' + flattenCategoryOptions(categoryTree, d.category_id);
        new bootstrap.Modal(document.getElementById('editDeviceModal')).show();
    }

    async function saveEditDevice() {
        const id = document.getElementById('editDeviceId').value;
        const custom_name = document.getElementById('editDeviceCustomName').value.trim();
        const category_id = document.getElementById('editDeviceCategory').value;
        const description = document.getElementById('editDeviceDescription').value.trim();
        const r = await apiRequest(`/api/devices/devices/${id}`, 'PUT', {
            custom_name: custom_name || null,
            category_id: category_id ? parseInt(category_id) : null,
            description
        });
        if (r.success) {
            bootstrap.Modal.getInstance(document.getElementById('editDeviceModal')).hide();
            loadDevices();
            loadCategories();
        } else {
            alert('保存失败: ' + (r.error || ''));
        }
    }

    // ================= 删除设备 =================
    async function deleteDevice(id) {
        if (!confirm('确定删除该设备及其所有数据吗?该操作不可恢复!')) return;
        const r = await apiRequest(`/api/devices/devices/${id}`, 'DELETE');
        if (r.success) {
            loadDevices();
            loadCategories();
        } else {
            alert('删除失败: ' + (r.error || ''));
        }
    }

    // ================= 分类操作 =================
    function showCategoryModal(parentId = null, cat = null) {
        document.getElementById('categoryId').value = cat ? cat.id : '';
        document.getElementById('categoryParentId').value = parentId || '';
        document.getElementById('categoryName').value = cat ? cat.name : '';
        document.getElementById('categoryDescription').value = cat ? (cat.description || '') : '';
        document.getElementById('categoryParentSelect').innerHTML =
            '<option value="">-- 根分类 --</option>' +
            flattenCategoryOptions(categoryTree, parentId ? parseInt(parentId) : null, cat ? cat.id : null);
        // 选中父分类
        if (parentId) {
            document.getElementById('categoryParentSelect').value = parentId;
        }
        document.getElementById('categoryModalTitle').textContent = cat ? '编辑分类' : '新建分类';
        new bootstrap.Modal(document.getElementById('categoryModal')).show();
    }

    async function saveCategory() {
        const id = document.getElementById('categoryId').value;
        const name = document.getElementById('categoryName').value.trim();
        if (!name) { alert('请输入分类名'); return; }
        const parent_id = document.getElementById('categoryParentSelect').value;
        const description = document.getElementById('categoryDescription').value.trim();
        let r;
        if (id) {
            r = await apiRequest(`/api/devices/categories/${id}`, 'PUT', { name, description });
        } else {
            r = await apiRequest('/api/devices/categories', 'POST', { name, parent_id: parent_id || null, description });
        }
        if (r.success) {
            bootstrap.Modal.getInstance(document.getElementById('categoryModal')).hide();
            loadCategories();
            loadDevices();
        } else {
            alert('保存失败: ' + (r.error || ''));
        }
    }

    async function deleteCategory(id) {
        if (!confirm('确定删除该分类? 子分类将上移一级, 设备将变为未分类。')) return;
        const r = await apiRequest(`/api/devices/categories/${id}`, 'DELETE');
        if (r.success) {
            if (currentCategoryId === id) currentCategoryId = null;
            loadCategories();
            loadDevices();
        } else {
            alert('删除失败: ' + (r.error || ''));
        }
    }

    // ================= 辅助: 平铺分类为 option =================
    function flattenCategoryOptions(nodes, selectedId = null, excludeId = null, prefix = '') {
        let html = '';
        nodes.forEach(n => {
            if (n.id === excludeId) return; // 防止选自己
            const selected = n.id === selectedId ? 'selected' : '';
            html += `<option value="${n.id}" ${selected}>${prefix}${escapeHtml(n.name)}</option>`;
            if (n.children && n.children.length) {
                html += flattenCategoryOptions(n.children, selectedId, excludeId, prefix + '— ');
            }
        });
        return html;
    }

    // ================= 事件绑定 =================
    function bindEvents() {
        // 树节点点击
        document.getElementById('categoryTree').addEventListener('click', (e) => {
            const row = e.target.closest('.tree-row');
            if (!row) return;
            const id = parseInt(row.dataset.categoryId);
            const action = e.target.closest('[data-action]')?.dataset.action;
            if (action === 'add-child') {
                e.stopPropagation();
                showCategoryModal(id);
            } else if (action === 'edit') {
                e.stopPropagation();
                const node = findCategoryNode(categoryTree, id);
                if (node) showCategoryModal(null, node);
            } else if (action === 'delete') {
                e.stopPropagation();
                deleteCategory(id);
            } else if (e.target.classList.contains('tree-toggle')) {
                e.stopPropagation();
                if (expandedCategories.has(id)) expandedCategories.delete(id);
                else expandedCategories.add(id);
                renderCategoryTree();
            } else {
                currentCategoryId = (currentCategoryId === id) ? null : id;
                document.getElementById('deviceListTitle').textContent =
                    currentCategoryId ? (findCategoryNode(categoryTree, id)?.name || '当前分类') : '所有设备';
                renderCategoryTree();
                loadDevices();
            }
        });

        // 新建根分类 (顶部+按钮)
        document.getElementById('addCategoryBtn').addEventListener('click', () => showCategoryModal());

        // 搜索分类
        document.getElementById('searchCategoryInput').addEventListener('input', () => renderCategoryTree());

        // 搜索设备
        document.getElementById('searchDeviceInput').addEventListener('input', renderDeviceList);

        // 分类保存
        document.getElementById('saveCategoryBtn').addEventListener('click', saveCategory);

        // 设备保存
        document.getElementById('saveEditDeviceBtn').addEventListener('click', saveEditDevice);
    }

    function findCategoryNode(nodes, id) {
        for (const n of nodes) {
            if (n.id === id) return n;
            if (n.children) {
                const found = findCategoryNode(n.children, id);
                if (found) return found;
            }
        }
        return null;
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
    function formatRelativeTime(date) {
        const diff = (new Date() - date) / 1000;
        if (diff < 5) return '刚刚';
        if (diff < 60) return Math.floor(diff) + '秒前';
        if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
        return Math.floor(diff / 86400) + '天前';
    }
})();
