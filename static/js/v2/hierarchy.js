/**
 * Hierarchy V2 - IoT Data Platform
 * 层级管理 - 组织架构树形结构
 */

class HierarchyV2 {
    constructor() {
        this.treeData = [];
        this.selectedNode = null;
        this.expandedNodes = new Set();
        this.init();
    }

    async init() {
        console.log('[Hierarchy] Initializing...');
        
        try {
            await this.loadTree();
            this.bindEvents();
            console.log('[Hierarchy] Initialized successfully');
        } catch (error) {
            console.error('[Hierarchy] Initialization error:', error);
            this.showError('加载失败，请刷新页面重试');
        }
    }

    // 加载树形数据
    async loadTree() {
        try {
            const response = await apiRequest('/api/hierarchy/tree');
            
            if (response && response.tree) {
                this.treeData = response.tree;
                this.renderTree();
                this.updateStats(response.stats || {});
            } else if (response && Array.isArray(response)) {
                // 兼容直接返回数组的情况
                this.treeData = response;
                this.renderTree();
                this.updateStats(this.calculateStats());
            } else {
                // 使用示例数据
                this.loadSampleData();
            }
        } catch (error) {
            console.error('[Hierarchy] Load tree error:', error);
            this.loadSampleData();
        }
    }

    // 加载示例数据（当API不可用时）
    loadSampleData() {
        this.treeData = [
            {
                id: '1',
                name: '总部园区',
                type: 'region',
                children: [
                    {
                        id: '1-1',
                        name: 'A栋办公楼',
                        type: 'building',
                        children: [
                            { id: '1-1-1', name: '1楼', type: 'floor', children: [
                                { id: '1-1-1-1', name: '101会议室', type: 'room', children: [] },
                                { id: '1-1-1-2', name: '102办公室', type: 'room', children: [
                                    { id: 'd1', name: '温湿度传感器', type: 'device' },
                                    { id: 'd2', name: '烟雾探测器', type: 'device' }
                                ]}
                            ]},
                            { id: '1-1-2', name: '2楼', type: 'floor', children: [
                                { id: '1-1-2-1', name: '201服务器机房', type: 'room', children: [
                                    { id: 'd3', name: 'UPS电源监控', type: 'device' },
                                    { id: 'd4', name: '温湿度传感器', type: 'device' },
                                    { id: 'd5', name: '漏水检测器', type: 'device' }
                                ]}
                            ]}
                        ]
                    },
                    {
                        id: '1-2',
                        name: 'B栋生产车间',
                        type: 'building',
                        children: [
                            { id: '1-2-1', name: '1楼生产线', type: 'floor', children: [
                                { id: '1-2-1-1', name: '生产区A', type: 'room', children: [
                                    { id: 'd6', name: '温度传感器#1', type: 'device' },
                                    { id: 'd7', name: '压力传感器#1', type: 'device' }
                                ]},
                                { id: '1-2-1-2', name: '生产区B', type: 'room', children: [
                                    { id: 'd8', name: '温度传感器#2', type: 'device' }
                                ]}
                            ]}
                        ]
                    }
                ]
            }
        ];
        
        this.renderTree();
        this.updateStats(this.calculateStats());
    }

    // 渲染树形结构
    renderTree() {
        const container = document.getElementById('treeContainer');
        if (!container) return;

        if (!this.treeData || this.treeData.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-slate-500">
                    <i class="fas fa-sitemap text-4xl mb-3 opacity-50"></i>
                    <p class="mb-4">暂无层级数据</p>
                    <button onclick="hierarchyV2.showAddModal()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                        <i class="fas fa-plus mr-2"></i>创建根节点
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = this.renderNodeList(this.treeData, 0);
        
        // 更新节点计数
        const countEl = document.getElementById('nodeCount');
        if (countEl) {
            countEl.textContent = this.countNodes(this.treeData) + ' 个节点';
        }
    }

    // 渲染节点列表
    renderNodeList(nodes, level) {
        if (!nodes || nodes.length === 0) return '';
        
        return nodes.map(node => `
            <div class="tree-node" data-id="${node.id}" data-type="${node.type}">
                <div class="flex items-center gap-2 py-2 px-3 rounded-lg hover:bg-slate-700/50 cursor-pointer transition-colors group ${this.selectedNode?.id === node.id ? 'bg-blue-600/20 border-l-2 border-blue-500' : ''}"
                     style="padding-left: ${level * 20 + 12}px"
                     onclick="hierarchyV2.selectNode('${node.id}')">
                    
                    ${node.children && node.children.length > 0 ? `
                        <button onclick="event.stopPropagation(); hierarchyV2.toggleNode('${node.id}')" 
                                class="w-5 h-5 flex items-center justify-center rounded hover:bg-slate-600 transition-colors">
                            <i class="fas ${this.expandedNodes.has(node.id) ? 'fa-chevron-down' : 'fa-chevron-right'} text-xs text-slate-400"></i>
                        </button>
                    ` : `
                        <span class="w-5"></span>
                    `}
                    
                    <span class="w-6 h-6 rounded flex items-center justify-center ${this.getNodeTypeStyle(node.type)}">
                        <i class="${this.getNodeIcon(node.type)} text-xs"></i>
                    </span>
                    
                    <span class="flex-1 text-sm ${this.selectedNode?.id === node.id ? 'text-white font-medium' : 'text-slate-300'} truncate">
                        ${node.name}
                    </span>
                    
                    ${node.children && node.children.length > 0 ? `
                        <span class="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-400">${node.children.length}</span>
                    ` : ''}
                </div>
                
                ${node.children && node.children.length > 0 && this.expandedNodes.has(node.id) ? `
                    <div class="children-container">
                        ${this.renderNodeList(node.children, level + 1)}
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    // 获取节点类型样式
    getNodeTypeStyle(type) {
        const styles = {
            'region': 'bg-purple-500/20 text-purple-400',
            'building': 'bg-blue-500/20 text-blue-400',
            'floor': 'bg-emerald-500/20 text-emerald-400',
            'room': 'bg-orange-500/20 text-orange-400',
            'device': 'bg-cyan-500/20 text-cyan-400'
        };
        return styles[type] || 'bg-slate-600/20 text-slate-400';
    }

    // 获取节点图标
    getNodeIcon(type) {
        const icons = {
            'region': 'fa-map-marked-alt',
            'building': 'fa-building',
            'floor': 'fa-layer-group',
            'room': 'fa-door-open',
            'device': 'fa-microchip'
        };
        return icons[type] || 'fa-circle';
    }

    // 选择节点
    selectNode(nodeId) {
        const node = this.findNode(this.treeData, nodeId);
        if (node) {
            this.selectedNode = node;
            this.renderTree();
            this.renderNodeDetail(node);
            document.getElementById('nodeActions').classList.remove('hidden');
        }
    }

    // 查找节点
    findNode(nodes, id) {
        for (const node of nodes) {
            if (node.id === id) return node;
            if (node.children) {
                const found = this.findNode(node.children, id);
                if (found) return found;
            }
        }
        return null;
    }

    // 展开/折叠节点
    toggleNode(nodeId) {
        if (this.expandedNodes.has(nodeId)) {
            this.expandedNodes.delete(nodeId);
        } else {
            this.expandedNodes.add(nodeId);
        }
        this.renderTree();
    }

    // 展开全部
    expandAll() {
        this.collectAllIds(this.treeData).forEach(id => this.expandedNodes.add(id));
        this.renderTree();
    }

    // 折叠全部
    collapseAll() {
        this.expandedNodes.clear();
        this.renderTree();
    }

    // 收集所有有子节点的ID
    collectAllIds(nodes) {
        let ids = [];
        for (const node of nodes) {
            if (node.children && node.children.length > 0) {
                ids.push(node.id);
                ids = ids.concat(this.collectAllIds(node.children));
            }
        }
        return ids;
    }

    // 渲染节点详情
    renderNodeDetail(node) {
        const container = document.getElementById('nodeDetail');
        if (!container) return;

        const childCount = node.children ? node.children.length : 0;
        const deviceCount = this.countDevices(node);

        container.innerHTML = `
            <div class="space-y-6">
                <!-- 基本信息 -->
                <div class="bg-slate-900/50 rounded-xl p-5 border border-slate-700/50">
                    <div class="flex items-start justify-between mb-4">
                        <div class="flex items-center gap-4">
                            <div class="w-16 h-16 rounded-xl ${this.getNodeTypeStyle(node.type)} flex items-center justify-center">
                                <i class="${this.getNodeIcon(node.type)} text-2xl"></i>
                            </div>
                            <div>
                                <h4 class="text-xl font-semibold text-white">${node.name}</h4>
                                <p class="text-sm text-slate-400 mt-1">${this.getTypeName(node.type)}</p>
                            </div>
                        </div>
                        <span class="px-3 py-1 rounded-full text-sm ${this.getNodeTypeStyle(node.type)}">
                            ${this.getTypeName(node.type)}
                        </span>
                    </div>
                    
                    <div class="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-700">
                        <div class="text-center">
                            <p class="text-2xl font-bold text-white">${childCount}</p>
                            <p class="text-xs text-slate-400 mt-1">子节点</p>
                        </div>
                        <div class="text-center">
                            <p class="text-2xl font-bold text-white">${deviceCount}</p>
                            <p class="text-xs text-slate-400 mt-1">设备数</p>
                        </div>
                        <div class="text-center">
                            <p class="text-2xl font-bold text-white">${node.level || this.getNodeLevel(node)}</p>
                            <p class="text-xs text-slate-400 mt-1">层级深度</p>
                        </div>
                    </div>
                </div>

                <!-- 位置信息 -->
                ${(node.lng || node.lat) ? `
                <div class="bg-slate-900/50 rounded-xl p-5 border border-slate-700/50">
                    <h5 class="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                        <i class="fas fa-map-marker-alt text-red-400"></i> 位置信息
                    </h5>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <p class="text-xs text-slate-500">经度</p>
                            <p class="font-mono text-sm text-white mt-1">${node.lng || '--'}</p>
                        </div>
                        <div>
                            <p class="text-xs text-slate-500">纬度</p>
                            <p class="font-mono text-sm text-white mt-1">${node.lat || '--'}</p>
                        </div>
                    </div>
                </div>
                ` : ''}

                <!-- 描述 -->
                ${node.description ? `
                <div class="bg-slate-900/50 rounded-xl p-5 border border-slate-700/50">
                    <h5 class="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                        <i class="fas fa-align-left text-blue-400"></i> 描述
                    </h5>
                    <p class="text-sm text-slate-400 leading-relaxed">${node.description}</p>
                </div>
                ` : ''}

                <!-- 子节点列表 -->
                ${childCount > 0 ? `
                <div class="bg-slate-900/50 rounded-xl p-5 border border-slate-700/50">
                    <h5 class="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                        <i class="fas fa-list text-emerald-400"></i> 子节点 (${childCount})
                    </h5>
                    <div class="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
                        ${node.children.map(child => `
                            <div class="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800/50 cursor-pointer transition-colors"
                                 onclick="hierarchyV2.selectNode('${child.id}')">
                                <span class="w-8 h-8 rounded ${this.getNodeTypeStyle(child.type)} flex items-center justify-center">
                                    <i class="${this.getChildIcon(child.type)} text-xs"></i>
                                </span>
                                <span class="text-sm text-slate-300">${child.name}</span>
                                <span class="ml-auto text-xs text-slate-500">${this.getTypeName(child.type)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                <!-- 设备列表（如果是叶子节点或包含设备） -->
                ${deviceCount > 0 ? `
                <div class="bg-slate-900/50 rounded-xl p-5 border border-slate-700/50">
                    <h5 class="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                        <i class="fas fa-microchip text-cyan-400"></i> 关联设备 (${deviceCount})
                    </h5>
                    <div class="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
                        ${this.getDevicesFromNode(node).map(device => `
                            <div class="flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/50 transition-colors">
                                <div class="flex items-center gap-3">
                                    <span class="w-2 h-2 rounded-full ${device.is_online ? 'bg-emerald-500' : 'bg-slate-500'}"></span>
                                    <span class="text-sm text-slate-300">${device.name}</span>
                                </div>
                                <span class="text-xs px-2 py-0.5 rounded ${device.is_online ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-500'}">
                                    ${device.is_online ? '在线' : '离线'}
                                </span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    }

    // 获取子节点图标
    getChildIcon(type) {
        return this.getNodeIcon(type);
    }

    // 获取类型名称
    getTypeName(type) {
        const names = {
            'region': '区域',
            'building': '建筑',
            'floor': '楼层',
            'room': '房间',
            'device': '设备'
        };
        return names[type] || type;
    }

    // 获取节点层级
    getNodeLevel(node) {
        let level = 0;
        let current = node;
        while (current.parent_id) {
            level++;
            current = this.findParent(this.treeData, current.parent_id);
            if (!current) break;
        }
        return level;
    }

    // 查找父节点
    findParent(nodes, parentId) {
        for (const node of nodes) {
            if (node.id === parentId) return node;
            if (node.children) {
                const found = this.findParent(node.children, parentId);
                if (found) return found;
            }
        }
        return null;
    }

    // 统计设备数量
    countDevices(node) {
        return this.getDevicesFromNode(node).length;
    }

    // 从节点获取设备列表
    getDevicesFromNode(node) {
        let devices = [];
        
        if (node.type === 'device') {
            devices.push({
                id: node.id,
                name: node.name,
                is_online: node.is_online !== false
            });
        }
        
        if (node.children) {
            node.children.forEach(child => {
                devices = devices.concat(this.getDevicesFromNode(child));
            });
        }
        
        return devices;
    }

    // 统计总节点数
    countNodes(nodes) {
        let count = 0;
        nodes.forEach(node => {
            count++;
            if (node.children) {
                count += this.countNodes(node.children);
            }
        });
        return count;
    }

    // 计算统计数据
    calculateStats() {
        return {
            total_nodes: this.countNodes(this.treeData),
            region_count: this.countByType(this.treeData, 'region'),
            device_count: this.countByType(this.treeData, 'device'),
            max_depth: this.getMaxDepth(this.treeData)
        };
    }

    // 按类型统计
    countByType(nodes, type) {
        let count = 0;
        nodes.forEach(node => {
            if (node.type === type) count++;
            if (node.children) count += this.countByType(node.children, type);
        });
        return count;
    }

    // 获取最大深度
    getMaxDepth(nodes, depth = 1) {
        let maxDepth = depth;
        nodes.forEach(node => {
            if (node.children && node.children.length > 0) {
                maxDepth = Math.max(maxDepth, this.getMaxDepth(node.children, depth + 1));
            }
        });
        return maxDepth;
    }

    // 更新统计显示
    updateStats(stats) {
        const elements = {
            'totalNodes': stats.total_nodes || this.countNodes(this.treeData),
            'regionCount': stats.region_count || this.countByType(this.treeData, 'region'),
            'deviceCount': stats.device_count || this.countByType(this.treeData, 'device'),
            'maxDepth': stats.max_depth || this.getMaxDepth(this.treeData)
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        });
    }

    // 显示添加模态框
    showAddModal(parentId = null) {
        document.getElementById('modalTitle').textContent = '添加节点';
        document.getElementById('nodeForm').reset();
        document.getElementById('nodeId').value = '';
        document.getElementById('parentId').value = parentId || (this.selectedNode ? this.selectedNode.id : '');
        document.getElementById('nodeModal').classList.remove('hidden');
    }

    // 编辑节点
    editNode() {
        if (!this.selectedNode) return;
        
        document.getElementById('modalTitle').textContent = '编辑节点';
        document.getElementById('nodeId').value = this.selectedNode.id;
        document.getElementById('parentId').value = this.selectedNode.parent_id || '';
        document.getElementById('nodeName').value = this.selectedNode.name;
        document.getElementById('nodeType').value = this.selectedNode.type;
        document.getElementById('nodeDesc').value = this.selectedNode.description || '';
        document.getElementById('nodeLng').value = this.selectedNode.lng || '';
        document.getElementById('nodeLat').value = this.selectedNode.lat || '';
        document.getElementById('nodeModal').classList.remove('hidden');
    }

    // 删除节点
    async deleteNode() {
        if (!this.selectedNode) return;
        
        if (!confirm(`确定要删除 "${this.selectedNode.name}" 吗？${this.selectedNode.children?.length > 0 ? '其子节点也将被删除。' : ''}`)) {
            return;
        }

        try {
            await apiRequest(`/api/hierarchy/nodes/${this.selectedNode.id}`, 'DELETE');
            showToast('删除成功', 'success');
            this.selectedNode = null;
            document.getElementById('nodeActions').classList.add('hidden');
            await this.loadTree();
            this.clearDetail();
        } catch (error) {
            console.error('[Hierarchy] Delete error:', error);
            showToast('删除失败: ' + (error.message || '未知错误'), 'error');
        }
    }

    // 添加子节点
    addChild() {
        if (!this.selectedNode) return;
        this.showAddModal(this.selectedNode.id);
    }

    // 保存节点
    async saveNode(event) {
        event.preventDefault();
        
        const nodeId = document.getElementById('nodeId').value;
        const data = {
            name: document.getElementById('nodeName').value.trim(),
            type: document.getElementById('nodeType').value,
            description: document.getElementById('nodeDesc').value.trim(),
            parent_id: document.getElementById('parentId').value || null,
            lng: parseFloat(document.getElementById('nodeLng').value) || null,
            lat: parseFloat(document.getElementById('nodeLat').value) || null
        };

        try {
            if (nodeId) {
                // 更新
                await apiRequest(`/api/hierarchy/nodes/${nodeId}`, 'PUT', data);
                showToast('更新成功', 'success');
            } else {
                // 创建
                await apiRequest('/api/hierarchy/nodes', 'POST', data);
                showToast('创建成功', 'success');
            }
            
            this.closeModal();
            await this.loadTree();
            
            if (nodeId && this.selectedNode?.id === nodeId) {
                this.selectNode(nodeId);
            }
        } catch (error) {
            console.error('[Hierarchy] Save error:', error);
            showToast('保存失败: ' + (error.message || '未知错误'), 'error');
        }
    }

    // 关闭模态框
    closeModal() {
        document.getElementById('nodeModal').classList.add('hidden');
    }

    // 清空详情面板
    clearDetail() {
        const container = document.getElementById('nodeDetail');
        if (container) {
            container.innerHTML = `
                <div class="flex items-center justify-center h-full text-slate-500">
                    <div class="text-center">
                        <i class="fas fa-mouse-pointer text-4xl mb-3 opacity-50"></i>
                        <p>请选择一个节点查看详情</p>
                    </div>
                </div>
            `;
        }
    }

    // 绑定事件
    bindEvents() {
        // 搜索功能
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterTree(e.target.value);
            });
        }

        // 类型筛选
        const filterSelect = document.getElementById('filterType');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.filterByType(e.target.value);
            });
        }
    }

    // 过滤树
    filterTree(keyword) {
        if (!keyword.trim()) {
            this.renderTree();
            return;
        }
        
        const filtered = this.searchNodes(this.treeData, keyword.toLowerCase());
        if (filtered.length > 0) {
            this.renderFilteredTree(filtered);
        } else {
            document.getElementById('treeContainer').innerHTML = `
                <div class="text-center py-12 text-slate-500">
                    <i class="fas fa-search text-4xl mb-3 opacity-50"></i>
                    <p>未找到匹配的节点</p>
                </div>
            `;
        }
    }

    // 搜索节点
    searchNodes(nodes, keyword) {
        let results = [];
        nodes.forEach(node => {
            if (node.name.toLowerCase().includes(keyword)) {
                results.push({...node});
            }
            if (node.children) {
                results = results.concat(this.searchNodes(node.children, keyword));
            }
        });
        return results;
    }

    // 渲染过滤后的树
    renderFilteredTree(nodes) {
        const container = document.getElementById('treeContainer');
        container.innerHTML = this.renderNodeList(nodes, 0);
    }

    // 按类型过滤
    filterByType(type) {
        if (!type) {
            this.renderTree();
            return;
        }
        
        const filtered = this.filterNodesByType(this.treeData, type);
        this.renderFilteredTree(filtered);
    }

    // 按类型过滤节点
    filterNodesByType(nodes, type) {
        let results = [];
        nodes.forEach(node => {
            if (node.type === type) {
                results.push({...node});
            }
            if (node.children) {
                results = results.concat(this.filterNodesByType(node.children, type));
            }
        });
        return results;
    }

    // 显示错误
    showError(message) {
        const container = document.getElementById('treeContainer');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-12 text-red-400">
                    <i class="fas fa-exclamation-triangle text-4xl mb-3"></i>
                    <p>${message}</p>
                    <button onclick="location.reload()" class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                        刷新页面
                    </button>
                </div>
            `;
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.hierarchyV2 = new HierarchyV2();
});
