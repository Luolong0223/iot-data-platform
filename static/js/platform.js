/* 平台增强中心 - 前端逻辑 */
(function() {
    'use strict';

    const API = '/api/platform';
    let _currentShadowId = null;

    function authHeaders() {
        return { 'Content-Type': 'application/json' };
    }

    async function api(path, opts = {}) {
        const resp = await fetch(API + path, {
            credentials: 'same-origin',
            headers: authHeaders(),
            ...opts
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
    }

    async function devicesApi(path, opts = {}) {
        const resp = await fetch('/api/devices' + path, {
            credentials: 'same-origin',
            headers: authHeaders(),
            ...opts
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
    }

    function fmtTime(s) {
        if (!s) return '-';
        try { return new Date(s).toLocaleString('zh-CN', { hour12: false }); } catch (e) { return s; }
    }

    function badge(status) {
        const map = {
            success: 'success', failed: 'danger', pending: 'warning',
            running: 'info', completed: 'success', failed_: 'danger',
            online: 'success', offline: 'secondary', enabled: 'success',
            disabled: 'secondary'
        };
        const cls = map[status] || 'secondary';
        return `<span class="badge bg-${cls}">${status || '-'}</span>`;
    }

    // ============== 设备影子 ==============
    async function loadShadows() {
        try {
            const r = await api('/shadows');
            const tb = document.getElementById('shadowTbody');
            if (!r.success || !r.data || !r.data.length) {
                tb.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-3">暂无设备</td></tr>';
                return;
            }
            tb.innerHTML = r.data.map(d => `
                <tr>
                    <td>${d.name || '-'}</td>
                    <td>${d.is_online ? '<span class="badge bg-success">在线</span>' : '<span class="badge bg-secondary">离线</span>'}</td>
                    <td>${d.shadow ? d.shadow.version : 0}</td>
                    <td><code class="small">${d.shadow ? (d.shadow.desired_state || '{}').slice(0, 30) : '-'}</code></td>
                    <td><code class="small">${d.shadow ? (d.shadow.reported_state || '{}').slice(0, 30) : '-'}</code></td>
                    <td class="small">${d.shadow && d.shadow.updated_at ? fmtTime(d.shadow.updated_at) : '-'}</td>
                    <td><button class="btn btn-sm btn-outline-primary" data-shadow-id="${d.id}" data-shadow-name="${d.name || ''}">编辑</button></td>
                </tr>
            `).join('');
            tb.querySelectorAll('[data-shadow-id]').forEach(b => {
                b.addEventListener('click', () => openShadowModal(b.dataset.shadowId, b.dataset.shadowName));
            });
        } catch (e) {
            console.error(e);
        }
    }

    async function openShadowModal(id, name) {
        _currentShadowId = id;
        document.getElementById('shadowDeviceName').value = name;
        try {
            const r = await api('/shadow/' + id);
            if (r.success) {
                const s = r.data;
                document.getElementById('shadowDesired').value = s.desired_state || '{}';
                document.getElementById('shadowReported').value = s.reported_state || '{}';
            }
        } catch (e) { console.error(e); }
        const modal = new bootstrap.Modal(document.getElementById('shadowModal'));
        modal.show();
    }

    document.addEventListener('DOMContentLoaded', function() {
        const saveBtn = document.getElementById('btnSaveShadow');
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                if (!_currentShadowId) return;
                let desired = {};
                try { desired = JSON.parse(document.getElementById('shadowDesired').value || '{}'); }
                catch (e) { alert('JSON 格式错误'); return; }
                try {
                    const r = await api('/shadow/' + _currentShadowId, {
                        method: 'PUT',
                        body: JSON.stringify({ desired_state: desired })
                    });
                    if (r.success) {
                        bootstrap.Modal.getInstance(document.getElementById('shadowModal')).hide();
                        loadShadows();
                    }
                } catch (e) { alert('保存失败'); }
            });
        }

        // 标签
        const tagForm = document.getElementById('tagForm');
        if (tagForm) {
            tagForm.addEventListener('submit', async e => {
                e.preventDefault();
                const fd = new FormData(tagForm);
                try {
                    await api('/tags', {
                        method: 'POST',
                        body: JSON.stringify({ name: fd.get('name'), color: fd.get('color') })
                    });
                    tagForm.reset();
                    loadTags();
                } catch (e) { alert('创建失败'); }
            });
        }

        const btnAssign = document.getElementById('btnAssign');
        if (btnAssign) {
            btnAssign.addEventListener('click', async () => {
                const deviceId = document.getElementById('assignDevice').value;
                const tagId = document.getElementById('assignTag').value;
                if (!deviceId || !tagId) return;
                try {
                    await api('/tags/' + tagId + '/assign', {
                        method: 'POST',
                        body: JSON.stringify({ device_id: parseInt(deviceId) })
                    });
                    loadTags();
                } catch (e) { alert('分配失败'); }
            });
        }

        // 命令
        const cmdForm = document.getElementById('cmdForm');
        if (cmdForm) {
            cmdForm.addEventListener('submit', async e => {
                e.preventDefault();
                const fd = new FormData(cmdForm);
                let payload = {};
                try { payload = fd.get('payload') ? JSON.parse(fd.get('payload')) : {}; }
                catch (e) { alert('JSON 格式错误'); return; }
                try {
                    await api('/devices/commands', {
                        method: 'POST',
                        body: JSON.stringify({
                            device_id: parseInt(fd.get('device_id')),
                            command: fd.get('command'),
                            payload: payload
                        })
                    });
                    cmdForm.reset();
                    loadCommands();
                } catch (e) { alert('下发失败'); }
            });
        }

        // 协议
        const protocolForm = document.getElementById('protocolForm');
        if (protocolForm) {
            protocolForm.addEventListener('submit', async e => {
                e.preventDefault();
                const fd = new FormData(protocolForm);
                let config = {};
                try { config = fd.get('config') ? JSON.parse(fd.get('config')) : {}; }
                catch (e) { alert('配置 JSON 格式错误'); return; }
                try {
                    await api('/protocols', {
                        method: 'POST',
                        body: JSON.stringify({
                            name: fd.get('name'),
                            protocol_type: fd.get('protocol_type'),
                            host: fd.get('host'),
                            port: parseInt(fd.get('port') || 0),
                            config: config
                        })
                    });
                    protocolForm.reset();
                    loadProtocols();
                } catch (e) { alert('创建失败'); }
            });
        }

        // 消息中心
        const btnMsgAll = document.getElementById('btnMsgAll');
        const btnMsgUnread = document.getElementById('btnMsgUnread');
        const btnMsgReadAll = document.getElementById('btnMsgReadAll');
        if (btnMsgAll) btnMsgAll.addEventListener('click', () => loadMessages(false));
        if (btnMsgUnread) btnMsgUnread.addEventListener('click', () => loadMessages(true));
        if (btnMsgReadAll) btnMsgReadAll.addEventListener('click', async () => {
            try { await api('/messages/read-all', { method: 'POST' }); loadMessages(true); }
            catch (e) { console.error(e); }
        });

        // 审计
        const auditFilter = document.getElementById('auditFilter');
        if (auditFilter) auditFilter.addEventListener('submit', e => {
            e.preventDefault();
            const fd = new FormData(auditFilter);
            const params = new URLSearchParams();
            if (fd.get('action')) params.set('action', fd.get('action'));
            if (fd.get('resource')) params.set('resource', fd.get('resource'));
            loadAuditLogs(params.toString());
        });

        // 报表
        const reportForm = document.getElementById('reportForm');
        if (reportForm) {
            reportForm.addEventListener('submit', async e => {
                e.preventDefault();
                const fd = new FormData(reportForm);
                try {
                    await api('/reports', {
                        method: 'POST',
                        body: JSON.stringify({
                            name: fd.get('name'),
                            report_type: fd.get('report_type'),
                            period: fd.get('period'),
                            format: fd.get('format')
                        })
                    });
                    reportForm.reset();
                    loadReports();
                } catch (e) { alert('创建失败'); }
            });
        }
    });

    async function loadTags() {
        try {
            const r = await api('/tags');
            const list = document.getElementById('tagList');
            if (!r.success || !r.data.length) {
                list.innerHTML = '<div class="text-muted small">暂无标签</div>';
            } else {
                list.innerHTML = r.data.map(t => `
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-tag-fill" style="color:${t.color || '#0d6efd'}"></i> ${t.name} <span class="badge bg-secondary">${t.device_count || 0}</span></span>
                        <button class="btn btn-sm text-danger" data-del-tag="${t.id}"><i class="bi bi-trash"></i></button>
                    </div>
                `).join('');
                list.querySelectorAll('[data-del-tag]').forEach(b => {
                    b.addEventListener('click', async () => {
                        if (!confirm('删除标签？')) return;
                        try { await api('/tags/' + b.dataset.delTag, { method: 'DELETE' }); loadTags(); }
                        catch (e) { console.error(e); }
                    });
                });
            }
            // 同步到下拉
            const sel = document.getElementById('assignTag');
            if (sel) {
                sel.innerHTML = '<option value="">选择标签</option>' +
                    r.data.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
            }
            // 同步设备下拉
            const devR = await devicesApi('?limit=1000');
            const devSel = document.getElementById('assignDevice');
            if (devSel && devR.success) {
                devSel.innerHTML = '<option value="">选择设备</option>' +
                    (devR.devices || devR.data || []).map(d => `<option value="${d.id}">${d.name}</option>`).join('');
            }
            const cmdDev = document.getElementById('cmdDevice');
            if (cmdDev && devR.success) {
                cmdDev.innerHTML = '<option value="">选择设备</option>' +
                    (devR.devices || devR.data || []).map(d => `<option value="${d.id}">${d.name}</option>`).join('');
            }
        } catch (e) { console.error(e); }
    }

    async function loadCommands() {
        try {
            const r = await api('/devices/commands?limit=20');
            const tb = document.getElementById('cmdTbody');
            if (!r.success || !r.data.length) {
                tb.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">暂无命令</td></tr>';
                return;
            }
            tb.innerHTML = r.data.map(c => `
                <tr>
                    <td class="small">${fmtTime(c.created_at)}</td>
                    <td>${c.device_name || c.device_id}</td>
                    <td><code>${c.command}</code></td>
                    <td><code class="small">${(c.payload || '').slice(0, 50)}</code></td>
                    <td>${badge(c.status)}</td>
                    <td class="small">${(c.result || '').slice(0, 50)}</td>
                </tr>
            `).join('');
        } catch (e) { console.error(e); }
    }

    async function loadProtocols() {
        try {
            const r = await api('/protocols');
            const tb = document.getElementById('protocolTbody');
            if (!r.success || !r.data.length) {
                tb.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">暂无协议</td></tr>';
                return;
            }
            tb.innerHTML = r.data.map(p => `
                <tr>
                    <td>${p.name}</td>
                    <td><span class="badge bg-info">${p.protocol_type}</span></td>
                    <td>${p.host || '-'}:${p.port || '-'}</td>
                    <td>${badge(p.is_enabled ? 'enabled' : 'disabled')}</td>
                    <td class="small">${fmtTime(p.last_heartbeat_at)}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" data-toggle-proto="${p.id}">${p.is_enabled ? '停用' : '启用'}</button>
                        <button class="btn btn-sm text-danger" data-del-proto="${p.id}"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `).join('');
            tb.querySelectorAll('[data-toggle-proto]').forEach(b => {
                b.addEventListener('click', async () => {
                    try { await api('/protocols/' + b.dataset.toggleProto + '/toggle', { method: 'POST' }); loadProtocols(); }
                    catch (e) { console.error(e); }
                });
            });
            tb.querySelectorAll('[data-del-proto]').forEach(b => {
                b.addEventListener('click', async () => {
                    if (!confirm('删除协议？')) return;
                    try { await api('/protocols/' + b.dataset.delProto, { method: 'DELETE' }); loadProtocols(); }
                    catch (e) { console.error(e); }
                });
            });
        } catch (e) { console.error(e); }
    }

    async function loadNotifications() {
        try {
            const r = await api('/notifications/logs?limit=50');
            const tb = document.getElementById('notifTbody');
            if (!r.success || !r.data.length) {
                tb.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">暂无通知</td></tr>';
                return;
            }
            tb.innerHTML = r.data.map(n => `
                <tr>
                    <td class="small">${fmtTime(n.sent_at)}</td>
                    <td><span class="badge bg-secondary">${n.channel}</span></td>
                    <td class="small">${(n.target || '').slice(0, 30)}</td>
                    <td>${n.subject || '-'}</td>
                    <td>${badge(n.status)}</td>
                    <td class="small text-danger">${n.error_msg || ''}</td>
                </tr>
            `).join('');
        } catch (e) { console.error(e); }
    }

    async function loadMessages(unreadOnly) {
        try {
            const r = await api('/messages' + (unreadOnly ? '?unread=1' : ''));
            const el = document.getElementById('msgList');
            if (!r.success || !r.data.length) {
                el.innerHTML = '<div class="text-muted text-center py-3">暂无消息</div>';
                return;
            }
            el.innerHTML = r.data.map(m => `
                <div class="alert alert-${m.level === 'critical' ? 'danger' : (m.level === 'warning' ? 'warning' : 'info')} d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${m.title}</strong>
                        <span class="badge bg-secondary ms-1">${m.type}</span>
                        <div class="small text-muted">${fmtTime(m.created_at)}</div>
                        <div class="mt-1">${m.content || ''}</div>
                    </div>
                    ${!m.is_read ? `<button class="btn btn-sm btn-outline-primary" data-read-msg="${m.id}">已读</button>` : ''}
                </div>
            `).join('');
            el.querySelectorAll('[data-read-msg]').forEach(b => {
                b.addEventListener('click', async () => {
                    try {
                        await api('/messages/' + b.dataset.readMsg + '/read', { method: 'POST' });
                        loadMessages(unreadOnly);
                    } catch (e) { console.error(e); }
                });
            });
        } catch (e) { console.error(e); }
    }

    async function loadAuditLogs(params) {
        try {
            const r = await api('/audit-logs?' + (params || ''));
            const tb = document.getElementById('auditTbody');
            if (!r.success || !r.data.length) {
                tb.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">暂无日志</td></tr>';
                return;
            }
            tb.innerHTML = r.data.map(a => `
                <tr>
                    <td class="small">${fmtTime(a.created_at)}</td>
                    <td>${a.username || '-'}</td>
                    <td><span class="badge bg-secondary">${a.action}</span></td>
                    <td>${a.resource || '-'}${a.resource_id ? '#' + a.resource_id : ''}</td>
                    <td class="small">${(a.detail || '').slice(0, 80)}</td>
                    <td class="small">${a.ip_address || '-'}</td>
                </tr>
            `).join('');
        } catch (e) { console.error(e); }
    }

    async function loadReports() {
        try {
            const r = await api('/reports');
            const tb = document.getElementById('reportTbody');
            if (!r.success || !r.data.length) {
                tb.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-3">暂无任务</td></tr>';
                return;
            }
            tb.innerHTML = r.data.map(t => `
                <tr>
                    <td>${t.name}</td>
                    <td>${t.report_type}</td>
                    <td>${t.period}</td>
                    <td class="small">${fmtTime(t.next_run_at)}</td>
                    <td class="small">${fmtTime(t.last_run_at)}</td>
                    <td>${badge(t.is_enabled ? 'enabled' : 'disabled')}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-success" data-run-report="${t.id}">立即运行</button>
                        <button class="btn btn-sm text-danger" data-del-report="${t.id}"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `).join('');
            tb.querySelectorAll('[data-run-report]').forEach(b => {
                b.addEventListener('click', async () => {
                    try { await api('/reports/' + b.dataset.runReport + '/run', { method: 'POST' }); alert('已开始运行'); }
                    catch (e) { alert('运行失败'); }
                });
            });
            tb.querySelectorAll('[data-del-report]').forEach(b => {
                b.addEventListener('click', async () => {
                    if (!confirm('删除任务？')) return;
                    try { await api('/reports/' + b.dataset.delReport, { method: 'DELETE' }); loadReports(); }
                    catch (e) { console.error(e); }
                });
            });
        } catch (e) { console.error(e); }
    }

    // Tab 切换加载
    document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(t => {
        t.addEventListener('shown.bs.tab', e => {
            const id = e.target.getAttribute('href');
            if (id === '#tab-shadow') loadShadows();
            else if (id === '#tab-tags') loadTags();
            else if (id === '#tab-commands') loadCommands();
            else if (id === '#tab-protocols') loadProtocols();
            else if (id === '#tab-notifications') loadNotifications();
            else if (id === '#tab-messages') loadMessages(false);
            else if (id === '#tab-audit') loadAuditLogs();
            else if (id === '#tab-reports') loadReports();
        });
    });

    // 首次加载
    loadShadows();
})();
