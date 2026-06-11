/**
 * IoT Data Platform - Admin JavaScript
 * Admin panel JS, user management, TCP status
 */

(function() {
    'use strict';

    let users = [];
    let usersTable = null;

    window.loadUsersTable = function() {
        apiRequest('/api/admin/users').then(function(data) {
            users = data.users || [];
            const tbody = document.getElementById('usersTableBody');
            if (!users.length) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">暂无用户</td></tr>';
                return;
            }
            tbody.innerHTML = users.map(function(u) {
                return '<tr>' +
                    '<td>' + u.id + '</td>' +
                    '<td><strong>' + u.username + '</strong></td>' +
                    '<td>' + (u.is_admin ? '<span class="badge bg-primary">是</span>' : '<span class="badge bg-secondary">否</span>') + '</td>' +
                    '<td>' + (u.tcp_port || '<span class="text-muted">未分配</span>') + '</td>' +
                    '<td>' + (u.storage_enabled ? '<span class="badge bg-success">启用</span>' : '<span class="badge bg-warning text-dark">禁用</span>') + '</td>' +
                    '<td>' + formatDateTime(u.created_at) + '</td>' +
                    '<td class="text-end">' +
                        '<button class="btn btn-sm btn-outline-primary me-1" onclick="editUser(' + u.id + ')" title="编辑"><i class="bi bi-pencil"></i></button>' +
                        '<button class="btn btn-sm btn-outline-danger" onclick="deleteUser(' + u.id + ')" title="删除"><i class="bi bi-trash"></i></button>' +
                    '</td>' +
                '</tr>';
            }).join('');

            if ($.fn.DataTable && !usersTable) {
                usersTable = $('#usersTable').DataTable({
                    language: { url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/zh.json' },
                    pageLength: 25,
                    order: [[0, 'asc']]
                });
            }
        }).catch(function(err) {
            showToast('加载用户失败: ' + err.message, 'error');
        });
    };

    window.resetUserForm = function() {
        document.getElementById('userId').value = '';
        document.getElementById('userName').value = '';
        document.getElementById('userPassword').value = '';
        document.getElementById('userPassword').required = true;
        document.getElementById('pwRequired').style.display = 'inline';
        document.getElementById('pwHint').textContent = '添加用户时必须设置密码';
        document.getElementById('userTcpPort').value = '';
        document.getElementById('userIsAdmin').checked = false;
        document.getElementById('userStorage').checked = true;
        document.getElementById('userModalTitle').textContent = '添加用户';
    };

    window.editUser = function(id) {
        const u = users.find(function(x) { return x.id === id; });
        if (!u) return;
        document.getElementById('userId').value = u.id;
        document.getElementById('userName').value = u.username;
        document.getElementById('userPassword').value = '';
        document.getElementById('userPassword').required = false;
        document.getElementById('pwRequired').style.display = 'none';
        document.getElementById('pwHint').textContent = '留空则不修改密码';
        document.getElementById('userTcpPort').value = u.tcp_port || '';
        document.getElementById('userIsAdmin').checked = u.is_admin;
        document.getElementById('userStorage').checked = u.storage_enabled;
        document.getElementById('userModalTitle').textContent = '编辑用户';
        new bootstrap.Modal(document.getElementById('userModal')).show();
    };

    window.saveUser = function() {
        const id = document.getElementById('userId').value;
        const payload = {
            username: document.getElementById('userName').value,
            is_admin: document.getElementById('userIsAdmin').checked,
            tcp_port: parseInt(document.getElementById('userTcpPort').value) || null,
            storage_enabled: document.getElementById('userStorage').checked
        };
        const pw = document.getElementById('userPassword').value;
        if (pw) payload.password = pw;
        else if (!id) {
            showToast('添加用户时必须设置密码', 'error');
            return;
        }

        const url = id ? '/api/admin/users/' + id : '/api/admin/users';
        const method = id ? 'PUT' : 'POST';
        apiRequest(url, { method: method, body: payload }).then(function() {
            bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
            showToast(id ? '用户已更新' : '用户已添加', 'success');
            loadUsersTable();
        }).catch(function(err) {
            showToast(err.message, 'error');
        });
    };

    window.deleteUser = function(id) {
        confirmDelete('确定要删除此用户吗？该用户的所有设备和数据也将被删除。', function() {
            apiRequest('/api/admin/users/' + id, { method: 'DELETE' }).then(function() {
                showToast('用户已删除', 'success');
                loadUsersTable();
            }).catch(function(err) {
                showToast(err.message, 'error');
            });
        });
    };

    window.refreshTcpStatus = function() {
        apiRequest('/api/admin/tcp-status').then(function(data) {
            const statusEl = document.getElementById('tcpStatus');
            if (statusEl) {
                statusEl.textContent = data.running ? '运行中' : '已停止';
                statusEl.style.color = data.running ? 'var(--success-color)' : 'var(--danger-color)';
            }
            const basePortEl = document.getElementById('tcpBasePort');
            if (basePortEl) basePortEl.textContent = data.base_port || '-';
            const userCountEl = document.getElementById('tcpUserCount');
            if (userCountEl) userCountEl.textContent = data.user_count || '0';

            const tbody = document.getElementById('tcpTableBody');
            const allocations = data.allocations || [];
            if (!allocations.length) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">暂无端口分配</td></tr>';
                return;
            }
            tbody.innerHTML = allocations.map(function(a) {
                return '<tr>' +
                    '<td>' + a.user_id + '</td>' +
                    '<td>' + a.username + '</td>' +
                    '<td><code>' + a.tcp_port + '</code></td>' +
                    '<td>' + (a.storage_enabled ? '<span class="badge bg-success">启用</span>' : '<span class="badge bg-warning text-dark">禁用</span>') + '</td>' +
                    '<td>' + (a.device_count || 0) + '</td>' +
                '</tr>';
            }).join('');
        }).catch(function(err) {
            showToast('加载 TCP 状态失败: ' + err.message, 'error');
        });
    };
})();
