/**
 * IoT Data Platform - Alarms JavaScript
 * Alarm rules CRUD and records management
 */

(function() {
    'use strict';

    let rulesTable = null;
    let recordsTable = null;
    let ruleModal = null;

    // Initialize DataTables and load data
    document.addEventListener('DOMContentLoaded', function() {
        ruleModal = new bootstrap.Modal(document.getElementById('ruleModal'));

        rulesTable = $('#rulesTable').DataTable({
            ajax: {
                url: '/api/alarms/rules',
                dataSrc: 'rules'
            },
            columns: [
                { data: 'id' },
                { data: 'device_name' },
                { data: 'channel_name' },
                { data: 'point_name' },
                { data: 'condition', render: function(data) {
                    return data === 'gt' ? '大于' : (data === 'lt' ? '小于' : '等于');
                }},
                { data: 'threshold' },
                { data: 'enabled', render: function(data) {
                    return data ? '<span class="badge bg-success">启用</span>' : '<span class="badge bg-secondary">禁用</span>';
                }},
                { data: null, orderable: false, render: function(data) {
                    return '<button class="btn btn-sm btn-outline-primary me-1" onclick="editRule(' + data.id + ')"><i class="bi bi-pencil"></i></button>' +
                           '<button class="btn btn-sm btn-outline-danger" onclick="deleteRule(' + data.id + ')"><i class="bi bi-trash"></i></button>';
                }}
            ],
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/zh.json'
            }
        });

        recordsTable = $('#recordsTable').DataTable({
            ajax: {
                url: '/api/alarms/records',
                dataSrc: 'records'
            },
            columns: [
                { data: 'id' },
                { data: 'rule_id', render: function(data, type, row) {
                    return '规则 #' + data;
                }},
                { data: 'message' },
                { data: 'actual_value', render: function(data) {
                    return formatNumber(data, 4);
                }},
                { data: 'threshold', render: function(data) {
                    return formatNumber(data, 4);
                }},
                { data: 'created_at', render: function(data) {
                    return formatDateTime(data);
                }},
                { data: 'is_read', render: function(data) {
                    return data ? '<span class="badge bg-secondary">已读</span>' : '<span class="badge bg-danger">未读</span>';
                }},
                { data: null, orderable: false, render: function(data) {
                    if (data.is_read) {
                        return '<span class="text-muted">-</span>';
                    }
                    return '<button class="btn btn-sm btn-outline-success" onclick="markRecordRead(' + data.id + ')"><i class="bi bi-check"></i> 标记已读</button>';
                }}
            ],
            order: [[5, 'desc']],
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/zh.json'
            }
        });
    });

    // Open modal for new rule
    window.openRuleModal = function() {
        document.getElementById('ruleId').value = '';
        document.getElementById('ruleForm').reset();
        document.getElementById('ruleModalTitle').textContent = '新增报警规则';
        ruleModal.show();
    };

    // Edit rule
    window.editRule = function(id) {
        apiRequest('/api/alarms/rules').then(function(data) {
            const rules = data.rules || [];
            const rule = rules.find(function(r) { return r.id === id; });
            if (!rule) {
                showToast('规则不存在', 'error');
                return;
            }
            document.getElementById('ruleId').value = rule.id;
            document.getElementById('ruleDeviceName').value = rule.device_name || '';
            document.getElementById('ruleChannelName').value = rule.channel_name || '';
            document.getElementById('rulePointName').value = rule.point_name || '';
            document.getElementById('ruleCondition').value = rule.condition || 'gt';
            document.getElementById('ruleThreshold').value = rule.threshold || 0;
            document.getElementById('ruleEnabled').checked = rule.enabled;
            document.getElementById('ruleModalTitle').textContent = '编辑报警规则';
            ruleModal.show();
        }).catch(function(err) {
            showToast('加载规则失败: ' + err.message, 'error');
        });
    };

    // Save rule (create or update)
    window.saveRule = function() {
        const id = document.getElementById('ruleId').value;
        const payload = {
            device_name: document.getElementById('ruleDeviceName').value,
            channel_name: document.getElementById('ruleChannelName').value,
            point_name: document.getElementById('rulePointName').value,
            condition: document.getElementById('ruleCondition').value,
            threshold: parseFloat(document.getElementById('ruleThreshold').value),
            enabled: document.getElementById('ruleEnabled').checked
        };

        const url = id ? '/api/alarms/rules/' + id : '/api/alarms/rules';
        const method = id ? 'PUT' : 'POST';

        apiRequest(url, { method: method, body: payload }).then(function() {
            showToast(id ? '规则已更新' : '规则已创建', 'success');
            ruleModal.hide();
            if (rulesTable) rulesTable.ajax.reload();
        }).catch(function(err) {
            showToast('保存失败: ' + err.message, 'error');
        });
    };

    // Delete rule
    window.deleteRule = function(id) {
        confirmDelete('确定要删除此报警规则吗？', function() {
            apiRequest('/api/alarms/rules/' + id, { method: 'DELETE' }).then(function() {
                showToast('规则已删除', 'success');
                if (rulesTable) rulesTable.ajax.reload();
            }).catch(function(err) {
                showToast('删除失败: ' + err.message, 'error');
            });
        });
    };

    // Mark single record as read
    window.markRecordRead = function(id) {
        apiRequest('/api/alarms/records/' + id + '/read', { method: 'PUT' }).then(function() {
            showToast('已标记为已读', 'success');
            if (recordsTable) recordsTable.ajax.reload();
        }).catch(function(err) {
            showToast('操作失败: ' + err.message, 'error');
        });
    };

    // Mark all records as read
    window.markAllRead = function() {
        apiRequest('/api/alarms/records').then(function(data) {
            const records = data.records || [];
            const unread = records.filter(function(r) { return !r.is_read; });
            if (!unread.length) {
                showToast('没有未读报警', 'info');
                return;
            }
            let completed = 0;
            let failed = 0;
            unread.forEach(function(r) {
                apiRequest('/api/alarms/records/' + r.id + '/read', { method: 'PUT' }).then(function() {
                    completed++;
                    if (completed + failed === unread.length) {
                        showToast('已标记 ' + completed + ' 条报警为已读', 'success');
                        if (recordsTable) recordsTable.ajax.reload();
                    }
                }).catch(function() {
                    failed++;
                    if (completed + failed === unread.length) {
                        showToast('已标记 ' + completed + ' 条报警为已读', 'success');
                        if (recordsTable) recordsTable.ajax.reload();
                    }
                });
            });
        }).catch(function(err) {
            showToast('操作失败: ' + err.message, 'error');
        });
    };
})();
