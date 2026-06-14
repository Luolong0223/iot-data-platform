"""平台增强功能路由 - 设备影子/标签/协议/消息/审计/报表"""
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func

from models.database import (
    db, Device, DeviceShadow, DeviceTag, DeviceTagMapping,
    DeviceCommand, ProtocolAdapter, SystemMessage, AuditLog,
    NotificationLog, ReportTask, AlarmRecord, DataPoint
)
from services.audit_log import log_action

platform_bp = Blueprint('platform', __name__, url_prefix='/api/platform')


# ==========================================================
# 设备影子 (Device Shadow)
# ==========================================================

@platform_bp.route('/shadow/<int:device_id>', methods=['GET'])
@login_required
def get_shadow(device_id):
    """获取设备影子"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404

    shadow = DeviceShadow.query.filter_by(device_id=device_id).first()
    if not shadow:
        shadow = DeviceShadow(
            device_id=device_id,
            desired_state=json.dumps({}, ensure_ascii=False),
            reported_state=json.dumps({}, ensure_ascii=False),
            is_online=device.is_online
        )
        db.session.add(shadow)
        db.session.commit()
    return jsonify({'success': True, 'data': shadow.to_dict()})


@platform_bp.route('/shadow/<int:device_id>', methods=['PUT'])
@login_required
def update_shadow(device_id):
    """更新设备影子（设置期望状态）"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404

    payload = request.get_json() or {}
    desired = payload.get('desired_state', {})

    shadow = DeviceShadow.query.filter_by(device_id=device_id).first()
    if not shadow:
        shadow = DeviceShadow(device_id=device_id)
        db.session.add(shadow)

    shadow.desired_state = json.dumps(desired, ensure_ascii=False)
    shadow.version = (shadow.version or 0) + 1
    shadow.updated_at = _now()

    # 同时创建下发命令
    cmd = DeviceCommand(
        device_id=device_id,
        command='shadow_update',
        payload=json.dumps(desired, ensure_ascii=False),
        status='pending',
        created_by=current_user.id
    )
    db.session.add(cmd)
    db.session.commit()

    log_action('update', resource='shadow', resource_id=device_id,
               detail=f'设置期望状态: {json.dumps(desired, ensure_ascii=False)[:200]}')
    return jsonify({'success': True, 'data': shadow.to_dict()})


@platform_bp.route('/shadows', methods=['GET'])
@login_required
def list_shadows():
    """批量获取设备影子"""
    user_devices = Device.query.filter_by(user_id=current_user.id).all()
    device_ids = [d.id for d in user_devices]
    shadows = DeviceShadow.query.filter(DeviceShadow.device_id.in_(device_ids)).all() if device_ids else []
    shadow_map = {s.device_id: s for s in shadows}
    result = []
    for d in user_devices:
        s = shadow_map.get(d.id)
        item = d.to_dict()
        item['shadow'] = s.to_dict() if s else None
        result.append(item)
    return jsonify({'success': True, 'data': result})


# ==========================================================
# 设备标签
# ==========================================================

@platform_bp.route('/tags', methods=['GET'])
@login_required
def list_tags():
    """获取标签列表"""
    tags = DeviceTag.query.filter_by(user_id=current_user.id).order_by(DeviceTag.name).all()
    return jsonify({'success': True, 'data': [t.to_dict() for t in tags]})


@platform_bp.route('/tags', methods=['POST'])
@login_required
def create_tag():
    """创建标签"""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': '名称不能为空'}), 400

    if DeviceTag.query.filter_by(user_id=current_user.id, name=name).first():
        return jsonify({'success': False, 'message': '标签已存在'}), 400

    tag = DeviceTag(
        user_id=current_user.id,
        name=name,
        color=data.get('color', '#1890ff'),
        description=data.get('description', '')
    )
    db.session.add(tag)
    db.session.commit()
    log_action('create', resource='tag', resource_id=tag.id, detail=f'创建标签: {name}')
    return jsonify({'success': True, 'data': tag.to_dict()})


@platform_bp.route('/tags/<int:tag_id>', methods=['PUT'])
@login_required
def update_tag(tag_id):
    """更新标签"""
    tag = DeviceTag.query.filter_by(id=tag_id, user_id=current_user.id).first()
    if not tag:
        return jsonify({'success': False, 'message': '标签不存在'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        tag.name = data['name'].strip()
    if 'color' in data:
        tag.color = data['color']
    if 'description' in data:
        tag.description = data['description']

    db.session.commit()
    return jsonify({'success': True, 'data': tag.to_dict()})


@platform_bp.route('/tags/<int:tag_id>', methods=['DELETE'])
@login_required
def delete_tag(tag_id):
    """删除标签"""
    tag = DeviceTag.query.filter_by(id=tag_id, user_id=current_user.id).first()
    if not tag:
        return jsonify({'success': False, 'message': '标签不存在'}), 404

    DeviceTagMapping.query.filter_by(tag_id=tag_id).delete()
    db.session.delete(tag)
    db.session.commit()
    log_action('delete', resource='tag', resource_id=tag_id, detail=f'删除标签: {tag.name}')
    return jsonify({'success': True})


@platform_bp.route('/tags/assign', methods=['POST'])
@login_required
def assign_tags():
    """给设备分配标签"""
    data = request.get_json() or {}
    device_id = data.get('device_id')
    tag_ids = data.get('tag_ids', [])

    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404

    # 删除旧映射
    DeviceTagMapping.query.filter_by(device_id=device_id).delete()

    # 添加新映射
    for tid in tag_ids:
        tag = DeviceTag.query.filter_by(id=tid, user_id=current_user.id).first()
        if tag:
            db.session.add(DeviceTagMapping(device_id=device_id, tag_id=tid))

    db.session.commit()
    return jsonify({'success': True})


@platform_bp.route('/tags/by-device/<int:device_id>', methods=['GET'])
@login_required
def get_device_tags(device_id):
    """获取设备的所有标签"""
    mappings = DeviceTagMapping.query.filter_by(device_id=device_id).all()
    tag_ids = [m.tag_id for m in mappings]
    tags = DeviceTag.query.filter(DeviceTag.id.in_(tag_ids)).all() if tag_ids else []
    return jsonify({'success': True, 'data': [t.to_dict() for t in tags]})


# ==========================================================
# 设备命令（云端下发）
# ==========================================================

@platform_bp.route('/devices/<int:device_id>/commands', methods=['GET'])
@login_required
def list_commands(device_id):
    """查看下发命令历史"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = DeviceCommand.query.filter_by(device_id=device_id).order_by(desc(DeviceCommand.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'success': True,
        'data': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })


@platform_bp.route('/devices/<int:device_id>/commands', methods=['POST'])
@login_required
def send_command(device_id):
    """下发命令到设备"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404

    data = request.get_json() or {}
    command = (data.get('command') or '').strip()
    if not command:
        return jsonify({'success': False, 'message': '命令不能为空'}), 400

    cmd = DeviceCommand(
        device_id=device_id,
        command=command,
        payload=json.dumps(data.get('payload', {}), ensure_ascii=False),
        status='pending',
        created_by=current_user.id
    )
    db.session.add(cmd)
    db.session.commit()

    # 通过 SSE 推送给在线设备
    try:
        from routes.realtime import push_to_user
        push_to_user(device.user_id, {
            'type': 'command',
            'device_id': device_id,
            'command_id': cmd.id,
            'command': command,
            'payload': cmd.payload
        })
    except Exception as e:
        print(f'[command] 推送失败: {e}')

    log_action('send_cmd', resource='device', resource_id=device_id,
               detail=f'下发命令: {command}')
    return jsonify({'success': True, 'data': cmd.to_dict()})


# ==========================================================
# 协议适配器
# ==========================================================

@platform_bp.route('/protocols', methods=['GET'])
@login_required
def list_protocols():
    """获取协议适配器列表"""
    adapters = ProtocolAdapter.query.filter_by(user_id=current_user.id).order_by(desc(ProtocolAdapter.created_at)).all()
    return jsonify({'success': True, 'data': [a.to_dict() for a in adapters]})


@platform_bp.route('/protocols', methods=['POST'])
@login_required
def create_protocol():
    """创建协议适配器"""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    protocol = (data.get('protocol') or '').strip()
    if not name or not protocol:
        return jsonify({'success': False, 'message': '名称和协议类型不能为空'}), 400

    adapter = ProtocolAdapter(
        user_id=current_user.id,
        name=name,
        protocol=protocol,
        config=json.dumps(data.get('config', {}), ensure_ascii=False),
        codec=json.dumps(data.get('codec', {}), ensure_ascii=False),
        enabled=data.get('enabled', True)
    )
    db.session.add(adapter)
    db.session.commit()

    log_action('create', resource='protocol', resource_id=adapter.id, detail=f'创建协议: {name}/{protocol}')
    return jsonify({'success': True, 'data': adapter.to_dict()})


@platform_bp.route('/protocols/<int:adapter_id>', methods=['PUT'])
@login_required
def update_protocol(adapter_id):
    """更新协议适配器"""
    adapter = ProtocolAdapter.query.filter_by(id=adapter_id, user_id=current_user.id).first()
    if not adapter:
        return jsonify({'success': False, 'message': '协议不存在'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        adapter.name = data['name']
    if 'config' in data:
        adapter.config = json.dumps(data['config'], ensure_ascii=False)
    if 'codec' in data:
        adapter.codec = json.dumps(data['codec'], ensure_ascii=False)
    if 'enabled' in data:
        adapter.enabled = data['enabled']

    db.session.commit()
    return jsonify({'success': True, 'data': adapter.to_dict()})


@platform_bp.route('/protocols/<int:adapter_id>', methods=['DELETE'])
@login_required
def delete_protocol(adapter_id):
    """删除协议适配器"""
    adapter = ProtocolAdapter.query.filter_by(id=adapter_id, user_id=current_user.id).first()
    if not adapter:
        return jsonify({'success': False, 'message': '协议不存在'}), 404

    db.session.delete(adapter)
    db.session.commit()
    log_action('delete', resource='protocol', resource_id=adapter_id)
    return jsonify({'success': True})


# ==========================================================
# 系统消息
# ==========================================================

@platform_bp.route('/messages', methods=['GET'])
@login_required
def list_messages():
    """获取系统消息"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    only_unread = request.args.get('unread', 'false').lower() == 'true'

    query = SystemMessage.query.filter_by(user_id=current_user.id)
    if only_unread:
        query = query.filter_by(is_read=False)
    query = query.order_by(desc(SystemMessage.created_at))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 未读总数
    unread = SystemMessage.query.filter_by(user_id=current_user.id, is_read=False).count()

    return jsonify({
        'success': True,
        'data': [m.to_dict() for m in pagination.items],
        'unread': unread,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@platform_bp.route('/messages/<int:msg_id>/read', methods=['POST'])
@login_required
def mark_read(msg_id):
    """标记已读"""
    msg = SystemMessage.query.filter_by(id=msg_id, user_id=current_user.id).first()
    if not msg:
        return jsonify({'success': False, 'message': '消息不存在'}), 404
    msg.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@platform_bp.route('/messages/read-all', methods=['POST'])
@login_required
def mark_all_read():
    """全部标记已读"""
    SystemMessage.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


# ==========================================================
# 审计日志
# ==========================================================

@platform_bp.route('/audit-logs', methods=['GET'])
@login_required
def list_audit_logs():
    """查询审计日志（仅管理员可查全部，普通用户查自己）"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    action = request.args.get('action')
    username = request.args.get('username')

    query = AuditLog.query
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    elif username:
        query = query.filter(AuditLog.username.like(f'%{username}%'))

    if action:
        query = query.filter_by(action=action)

    query = query.order_by(desc(AuditLog.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'data': [l.to_dict() for l in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@platform_bp.route('/audit-logs/actions', methods=['GET'])
@login_required
def audit_actions():
    """所有操作类型枚举"""
    actions = [
        {'key': 'login', 'label': '登录', 'color': 'success'},
        {'key': 'logout', 'label': '登出', 'color': 'secondary'},
        {'key': 'create', 'label': '创建', 'color': 'primary'},
        {'key': 'update', 'label': '更新', 'color': 'warning'},
        {'key': 'delete', 'label': '删除', 'color': 'danger'},
        {'key': 'export', 'label': '导出', 'color': 'info'},
        {'key': 'import', 'label': '导入', 'color': 'info'},
        {'key': 'send_cmd', 'label': '下发命令', 'color': 'warning'},
        {'key': 'view', 'label': '查看', 'color': 'secondary'},
        {'key': 'config', 'label': '配置', 'color': 'primary'}
    ]
    return jsonify({'success': True, 'data': actions})


# ==========================================================
# 通知日志
# ==========================================================

@platform_bp.route('/notification-logs', methods=['GET'])
@login_required
def list_notification_logs():
    """通知发送日志"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = NotificationLog.query.filter_by(user_id=current_user.id).order_by(desc(NotificationLog.sent_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 统计
    total_count = NotificationLog.query.filter_by(user_id=current_user.id).count()
    success_count = NotificationLog.query.filter_by(user_id=current_user.id, status='success').count()

    return jsonify({
        'success': True,
        'data': [l.to_dict() for l in pagination.items],
        'stats': {
            'total': total_count,
            'success': success_count,
            'failed': total_count - success_count,
            'success_rate': f'{(success_count / total_count * 100):.1f}' if total_count else '0.0'
        },
        'total': pagination.total,
        'page': page
    })


# ==========================================================
# 报表任务
# ==========================================================

@platform_bp.route('/reports', methods=['GET'])
@login_required
def list_reports():
    """报表任务列表"""
    reports = ReportTask.query.filter_by(user_id=current_user.id).order_by(desc(ReportTask.created_at)).all()
    return jsonify({'success': True, 'data': [r.to_dict() for r in reports]})


@platform_bp.route('/reports', methods=['POST'])
@login_required
def create_report():
    """创建报表任务"""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': '名称不能为空'}), 400

    report = ReportTask(
        user_id=current_user.id,
        name=name,
        type=data.get('type', 'daily'),
        schedule_time=data.get('schedule_time', '08:00'),
        config=json.dumps(data.get('config', {}), ensure_ascii=False),
        enabled=data.get('enabled', True)
    )
    db.session.add(report)
    db.session.commit()
    log_action('create', resource='report', resource_id=report.id, detail=f'创建报表: {name}')
    return jsonify({'success': True, 'data': report.to_dict()})


@platform_bp.route('/reports/<int:report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    """删除报表"""
    report = ReportTask.query.filter_by(id=report_id, user_id=current_user.id).first()
    if not report:
        return jsonify({'success': False, 'message': '报表不存在'}), 404
    db.session.delete(report)
    db.session.commit()
    return jsonify({'success': True})


@platform_bp.route('/reports/preview', methods=['GET'])
@login_required
def preview_report():
    """预览报表（生成示例统计数据）"""
    report_type = request.args.get('type', 'daily')

    if report_type == 'daily':
        start = datetime.utcnow() - timedelta(days=1)
        title = '日报'
    elif report_type == 'weekly':
        start = datetime.utcnow() - timedelta(weeks=1)
        title = '周报'
    elif report_type == 'monthly':
        start = datetime.utcnow() - timedelta(days=30)
        title = '月报'
    else:
        start = datetime.utcnow() - timedelta(days=1)
        title = '统计'

    # 设备统计
    user_devices = Device.query.filter_by(user_id=current_user.id).all()
    device_ids = [d.id for d in user_devices]
    online_count = sum(1 for d in user_devices if d.is_online)
    offline_count = len(user_devices) - online_count

    # 数据点统计
    point_count = DataPoint.query.filter(
        DataPoint.channel_id.in_(
            db.session.query(Device.id).filter(Device.user_id == current_user.id)
        )
    ).count() if device_ids else 0

    new_points = DataPoint.query.filter(
        DataPoint.timestamp >= start
    ).count() if device_ids else 0

    # 告警统计
    alarms = AlarmRecord.query.filter(
        AlarmRecord.user_id == current_user.id,
        AlarmRecord.created_at >= start
    ).all()
    alarm_total = len(alarms)
    alarm_by_severity = {}
    for a in alarms:
        alarm_by_severity[a.severity] = alarm_by_severity.get(a.severity, 0) + 1

    return jsonify({
        'success': True,
        'data': {
            'title': f'IoT平台{title} - {start.strftime("%Y-%m-%d")} ~ {datetime.utcnow().strftime("%Y-%m-%d")}',
            'period': {'start': start.isoformat(), 'end': datetime.utcnow().isoformat()},
            'devices': {
                'total': len(user_devices),
                'online': online_count,
                'offline': offline_count,
                'online_rate': f'{(online_count / len(user_devices) * 100):.1f}' if user_devices else '0.0'
            },
            'data_points': {
                'total': point_count,
                'new': new_points
            },
            'alarms': {
                'total': alarm_total,
                'by_severity': alarm_by_severity
            }
        }
    })


# ==========================================================
# 综合看板增强（v5.0）
# ==========================================================

@platform_bp.route('/dashboard/enhanced-stats', methods=['GET'])
@login_required
def enhanced_dashboard_stats():
    """增强版主控台统计"""
    user_id = current_user.id
    user_devices = Device.query.filter_by(user_id=user_id).all()
    device_ids = [d.id for d in user_devices]

    # 设备统计
    online = sum(1 for d in user_devices if d.is_online)
    offline = len(user_devices) - online

    # 数据点统计
    new_today = 0
    if device_ids:
        from sqlalchemy import and_
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = DataPoint.query.filter(
            DataPoint.channel_id.in_(
                db.session.query(Device.id).filter(Device.user_id == user_id)
            ),
            DataPoint.timestamp >= today
        ).count()

    # 告警统计
    alarm_today = AlarmRecord.query.filter(
        AlarmRecord.user_id == user_id,
        AlarmRecord.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    alarm_unread = AlarmRecord.query.filter_by(user_id=user_id, is_read=False).count()

    # 标签统计
    tag_count = DeviceTag.query.filter_by(user_id=user_id).count()

    # 影子统计
    shadow_count = 0
    if device_ids:
        shadow_count = DeviceShadow.query.filter(DeviceShadow.device_id.in_(device_ids)).count()

    # 命令统计（最近 24h）
    cmd_count = 0
    if device_ids:
        from models.database import DeviceCommand as DC
        cmd_count = DC.query.filter(
            DC.device_id.in_(device_ids),
            DC.created_at >= datetime.utcnow() - timedelta(days=1)
        ).count()

    # 通知统计（最近 24h）
    notify_count = NotificationLog.query.filter(
        NotificationLog.user_id == user_id,
        NotificationLog.sent_at >= datetime.utcnow() - timedelta(days=1)
    ).count()

    return jsonify({
        'success': True,
        'data': {
            'devices': {
                'total': len(user_devices),
                'online': online,
                'offline': offline,
                'online_rate': f'{(online / len(user_devices) * 100):.1f}' if user_devices else '0.0'
            },
            'data_points': {
                'new_today': new_today
            },
            'alarms': {
                'unread': alarm_unread,
                'today': alarm_today
            },
            'tags': tag_count,
            'shadows': shadow_count,
            'commands_24h': cmd_count,
            'notifications_24h': notify_count
        }
    })


# 辅助函数
def _now():
    from datetime import timezone, timedelta
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
