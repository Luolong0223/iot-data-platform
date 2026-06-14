/**
 * RBAC 角色权限管理 - V2版本
 * 使用 apiRequest(url, method, data) 签名
 */

class RBACManager {
    constructor() {
        this.roles = [];
        this.users = [];
        this.currentTab = 'roles';
        this.init();
    }

    async init() {
        console.log('[RBAC] 初始化角色权限管理');
        await Promise.all([
            this.loadRoles(),
            this.loadUsers()
        ]);
    }

    switchTab(tab) {
        this.currentTab = tab;
        const tabRoles = document.getElementById('tabRoles');
        const tabUsers = document.getElementById('tabUsers');
        const rolesPanel = document.getElementById('rolesPanel');
        const usersPanel = document.getElementById('usersPanel');
        
        if (tab === 'roles') {
            tabRoles.className = 'px-5 py-2 rounded-lg text-sm font-medium transition-colors bg-blue-600 text-white';
            tabUsers.className = 'px-5 py-2 rounded-lg text-sm font-medium transition-colors bg-slate-700/50 text-slate-300 hover:bg-slate-600';
            rolesPanel.classList.remove('hidden');
            usersPanel.classList.add('hidden');
        } else {
            tabUsers.className = 'px-5 py-2 rounded-lg text-sm font-medium transition-colors bg-blue-600 text-white';
            tabRoles.className = 'px-5 py-2 rounded-lg text-sm font-medium transition-colors bg-slate-700/50 text-slate-300 hover:bg-slate-600';
            usersPanel.classList.remove('hidden');
            rolesPanel.classList.add('hidden');
            this.renderUsers();
        }
    }

    async loadRoles() {
        try {
            const res = await apiRequest('/api/rbac/roles');
            if (res && (res.roles || res.data)) {
                this.roles = res.roles || res.data || [];
            } else {
                this.loadDemoData();
            }
        } catch (error) {
            console.error('[RBAC] 加载角色失败:', error);
            this.loadDemoData();
        }
        this.renderRoles();
        this.updateStats();
    }

    async loadUsers() {
        try {
            const res = await apiRequest('/api/users');
            if (res && (res.users || res.data)) {
                this.users = res.users || res.data || [];
            } else {
                this.loadDemoUsers();
            }
        } catch (error) {
            console.error('[RBAC] 加载用户失败:', error);
            this.loadDemoUsers();
        }
    }

    loadDemoData() {
        this.roles = [
            { id: 1, name: '超级管理员', description: '拥有所有权限', user_count: 1,
              permissions: ['device:view','device:create','device:edit','device:delete','data:view','data:export','alarm:view','alarm:manage','user:manage','system:config'],
              created_at: '2026-01-01' },
            { id: 2, name: '设备管理员', description: '管理设备和数据', user_count: 2,
              permissions: ['device:view','device:create','device:edit','data:view','data:export','alarm:view'],
              created_at: '2026-01-15' },
            { id: 3, name: '只读用户', description: '仅查看权限', user_count: 5,
              permissions: ['device:view','data:view','alarm:view'],
              created_at: '2026-02-01' },
            { id: 4, name: '告警处理员', description: '处理告警和通知', user_count: 3,
              permissions: ['device:view','data:view','alarm:view','alarm:manage'],
              created_at: '2026-03-10' },
        ];
    }

    loadDemoUsers() {
        this.users = [
            { id: 1, username: 'admin', email: 'admin@iot.com', role_name: '超级管理员', is_admin: true, status: 'active' },
            { id: 2, username: 'operator', email: 'op@iot.com', role_name: '运维人员', is_admin: false, status: 'active' },
            { id: 3, username: 'viewer', email: 'viewer@iot.com', role_name: '只读用户', is_admin: false, status: 'active' },
            { id: 4, username: 'engineer', email: 'eng@iot.com', role_name: '设备工程师', is_admin: false, status: 'inactive' },
        ];
    }

    renderRoles() {
        const container = document.getElementById('rolesListContainer');
        if (!container) return;
        if (!this.roles.length) {
            container.innerHTML = `<div class="text-center py-16 text-slate-500"><i class="fas fa-user-tag text-4xl mb-3 opacity-50"></i><p class="text-lg">暂无角色</p><p class="text-sm mt-1">点击"新建角色"创建第一个角色</p></div>`;
            return;
        }
        container.innerHTML = this.roles.map(role => `
            <div class="p-5 hover:bg-slate-700/20 transition-colors">
                <div class="flex items-start justify-between">
                    <div class="flex items-start gap-4 flex-1">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/30 to-pink-500/30 flex items-center justify-center flex-shrink-0">
                            <i class="fas fa-shield-alt text-lg text-purple-400"></i>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-3 mb-2">
                                <h4 class="font-semibold text-white">${role.name}</h4>
                                ${role.id === 1 ? '<span class="px-2 py-0.5 rounded-full text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">系统内置</span>' : ''}
                            </div>
                            <p class="text-sm text-slate-400 mb-3">${role.description || '暂无描述'}</p>
                            <div class="flex flex-wrap gap-1.5 mb-3">
                                ${(role.permissions || []).slice(0, 6).map(p => `<span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 border border-slate-700">${this.formatPerm(p)}</span>`).join('')}
                                ${(role.permissions || []).length > 6 ? `<span class="px-2 py-0.5 rounded text-xs bg-purple-500/10 text-purple-400">+${(role.permissions || []).length - 6} 更多</span>` : ''}
                            </div>
                            <div class="flex items-center gap-6 text-xs text-slate-500">
                                <span><i class="fas fa-users mr-1"></i>${role.user_count || 0} 个用户</span>
                                <span><i class="fas fa-calendar mr-1"></i>创建于 ${role.created_at || '-'}</span>
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 ml-4">
                        ${role.id !== 1 ? `
                            <button onclick="rbacV2.editRole(${role.id})" class="p-2 rounded-lg hover:bg-slate-700 transition-colors" title="编辑">
                                <i class="fas fa-edit text-sm text-blue-400"></i></button>
                            <button onclick="rbacV2.deleteRole(${role.id}, '${role.name}')" class="p-2 rounded-lg hover:bg-slate-700 transition-colors" title="删除">
                                <i class="fas fa-trash-alt text-sm text-red-400"></i></button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderUsers() {
        const container = document.getElementById('usersListContainer');
        if (!container) return;
        if (!this.users.length) {
            container.innerHTML = `<div class="text-center py-16 text-slate-500"><i class="fas fa-users text-4xl mb-3 opacity-50"></i><p class="text-lg">暂无用户</p></div>`;
            return;
        }
        container.innerHTML = this.users.map(user => `
            <div class="p-5 hover:bg-slate-700/20 transition-colors">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-4">
                        <div class="w-11 h-11 rounded-full bg-gradient-to-br from-cyan-500/30 to-blue-500/30 flex items-center justify-center">
                            <span class="text-lg font-semibold text-cyan-300">${(user.username || '?').charAt(0).toUpperCase()}</span>
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <h4 class="font-semibold text-white">${user.username}</h4>
                                ${user.is_admin ? '<span class="px-1.5 py-0.5 rounded text-[10px] bg-red-500/10 text-red-400 border border-red-500/20">ADMIN</span>' : ''}
                                <span class="px-1.5 py-0.5 rounded text-[10px] ${user.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-700 text-slate-400'}">${user.status === 'active' ? '活跃' : '禁用'}</span>
                            </div>
                            <p class="text-sm text-slate-400">${user.email || '-'}</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-4">
                        <select onchange="rbacV2.assignRole(${user.id}, this.value)" class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500">
                            ${this.roles.map(r => `<option value="${r.id}" ${r.name === user.role_name ? 'selected' : ''}>${r.name}</option>`).join('')}
                        </select>
                        <button onclick="rbacV2.editUser(${user.id})" class="p-2 rounded-lg hover:bg-slate-700 transition-colors" title="编辑">
                            <i class="fas fa-edit text-sm text-blue-400"></i></button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    formatPerm(perm) {
        const labels = {
            'device:view': '查看设备', 'device:create': '创建设备', 'device:edit': '编辑设备', 'device:delete': '删除设备',
            'data:view': '查看数据', 'data:export': '导出数据', 'data:delete': '删除数据',
            'alarm:view': '查看告警', 'alarm:manage': '管理规则',
            'user:manage': '用户管理', 'system:config': '系统配置',
        };
        return labels[perm] || perm;
    }

    updateStats() {
        const totalRolesEl = document.getElementById('totalRoles');
        const totalUsersEl = document.getElementById('totalUsers');
        const totalPermsEl = document.getElementById('totalPerms');
        if (totalRolesEl) totalRolesEl.textContent = this.roles.length;
        if (totalUsersEl) totalUsersEl.textContent = this.users.length;
        const allPerms = new Set(this.roles.flatMap(r => r.permissions || []));
        if (totalPermsEl) totalPermsEl.textContent = allPerms.size;
    }

    showAddRoleModal() {
        document.getElementById('modalTitle').textContent = '新建角色';
        document.getElementById('roleId').value = '';
        document.getElementById('roleForm').reset();
        document.getElementById('roleModal').classList.remove('hidden');
    }

    editRole(id) {
        const role = this.roles.find(r => r.id === id);
        if (!role) return;
        document.getElementById('modalTitle').textContent = '编辑角色';
        document.getElementById('roleId').value = role.id;
        document.getElementById('roleName').value = role.name;
        document.getElementById('roleDesc').value = role.description || '';
        document.querySelectorAll('input[name="perms"]').forEach(cb => {
            cb.checked = (role.permissions || []).includes(cb.value);
        });
        document.getElementById('roleModal').classList.remove('hidden');
    }

    closeModal() {
        document.getElementById('roleModal').classList.add('hidden');
    }

    async saveRole(e) {
        e.preventDefault();
        const id = document.getElementById('roleId').value;
        const data = {
            name: document.getElementById('roleName').value,
            description: document.getElementById('roleDesc').value,
            permissions: [...document.querySelectorAll('input[name="perms"]:checked')].map(el => el.value),
        };
        try {
            if (id) {
                await apiRequest(`/api/rbac/roles/${id}`, 'PUT', data);
            } else {
                await apiRequest('/api/rbac/roles', 'POST', data);
            }
            showToast(id ? '角色更新成功' : '角色创建成功', 'success');
            this.closeModal();
            await this.loadRoles();
        } catch (error) {
            showToast('操作失败: ' + (error.message || '未知错误'), 'danger');
        }
    }

    async deleteRole(id, name) {
        if (!confirm(`确定要删除角色 "${name}" 吗？`)) return;
        try {
            await apiRequest(`/api/rbac/roles/${id}`, 'DELETE');
            showToast('角色已删除', 'success');
            await this.loadRoles();
        } catch (error) {
            showToast('删除失败: ' + (error.message || '未知错误'), 'danger');
        }
    }

    async assignRole(userId, roleId) {
        try {
            await apiRequest(`/api/users/${userId}/role`, 'PUT', { role_id: parseInt(roleId) });
            showToast('角色分配成功', 'success');
        } catch (error) {
            showToast('分配失败: ' + (error.message || '未知错误'), 'danger');
        }
    }

    editUser(id) {
        showToast('用户编辑功能开发中', 'info');
    }
}

// 初始化
let rbacV2;
document.addEventListener('DOMContentLoaded', () => {
    rbacV2 = new RBACManager();
});
