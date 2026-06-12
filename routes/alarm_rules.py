#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
告警规则API路由
"""

from flask import Blueprint, request, jsonify, g
from models.database import db, AlarmRule, AlarmRecord, Device, SlaveChannel, DataPoint
from routes.auth import login_required
from sqlalchemy import func
from datetime import datetime
import json

alarm_rules_bp = Blueprint('alarm_rules', __name__, url_prefix='/api/alarm-rules')


@alarm_rules_bp.route('/', methods=['GET'])
@login_required
def list_rules():
    """获取告警规则列表"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    query = AlarmRule.query
    if not is_admin:
        query = query.filter_by(user_id=user_id)
    
    rules = query.order_by(AlarmRule.created_at.desc()).all()
    
    result = []
    for rule in rules:
        # 统计该规则触发的告警数量
        alarm_count = AlarmRecord.query.filter_by(rule_id=rule.id).count()
        today_alarms = AlarmRecord.query.filter_by(rule_id=rule.id).filter(
            AlarmRecord.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
        ).count()
        
        result.append({
            **rule.to_dict(),
            'alarm_count': alarm_count,
            'today_alarms': today_alarms
        })
    
    return jsonify({'success': True, 'rules': result})


@alarm_rules_bp.route('/', methods=['POST'])
@login_required
def create_rule():
    """创建告警规则"""
    user_id = g.user.id
    
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    device_name = data.get('device_name', '').strip() or None
    channel_name = data.get('channel_name', '').strip() or None
    point_name = data.get('point_name', '').strip() or None
    condition = data.get('condition', '>')
    threshold = data.get('threshold')
    severity = data.get('severity', 'warning')
    notify_email = data.get('notify_email', True)
    notify_sms = data.get('notify_sms', False)
    notify_dingtalk = data.get('notify_dingtalk', False)
    notify_wechat = data.get('notify_wechat', False)
    enabled = data.get('enabled', True)
    
    if threshold is None:
        return jsonify({'success': False, 'message': '阈值不能为空'}), 400
    
    try:
        threshold = float(threshold)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '阈值必须是数字'}), 400
    
    if condition not in ['>', '<', '>=', '<=', '==', '!=']:
        return jsonify({'success': False, 'message': '条件类型无效'}), 400
    
    if severity not in ['critical', 'warning', 'info']:
        return jsonify({'success': False, 'message': '告警级别无效'}), 400
    
    rule = AlarmRule(
        user_id=user_id,
        name=name,
        device_name=device_name,
        channel_name=channel_name,
        point_name=point_name,
        condition=condition,
        threshold=threshold,
        severity=severity,
        notify_email=notify_email,
        notify_sms=notify_sms,
        enabled=enabled
    )
    
    db.session.add(rule)
    db.session.commit()
    
    return jsonify({'success': True, 'rule': rule.to_dict()})


@alarm_rules_bp.route('/<int:rule_id>', methods=['GET'])
@login_required
def get_rule(rule_id):
    """获取告警规则详情"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    rule = AlarmRule.query.get(rule_id)
    if not rule:
        return jsonify({'success': False, 'message': '规则不存在'}), 404
    
    if not is_admin and rule.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    # 获取最近触发的告警
    recent_alarms = AlarmRecord.query.filter_by(rule_id=rule.id).order_by(AlarmRecord.created_at.desc()).limit(10).all()
    
    return jsonify({
        'success': True,
        'rule': {
            **rule.to_dict(),
            'recent_alarms': [a.to_dict() for a in recent_alarms]
        }
    })


@alarm_rules_bp.route('/<int:rule_id>', methods=['PUT'])
@login_required
def update_rule(rule_id):
    """更新告警规则"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    rule = AlarmRule.query.get(rule_id)
    if not rule:
        return jsonify({'success': False, 'message': '规则不存在'}), 404
    
    if not is_admin and rule.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    data = request.get_json() or {}
    
    if 'name' in data:
        rule.name = data['name'].strip()
    if 'device_name' in data:
        rule.device_name = data['device_name'].strip() or None
    if 'channel_name' in data:
        rule.channel_name = data['channel_name'].strip() or None
    if 'point_name' in data:
        rule.point_name = data['point_name'].strip() or None
    if 'condition' in data:
        if data['condition'] in ['>', '<', '>=', '<=', '==', '!=']:
            rule.condition = data['condition']
    if 'threshold' in data:
        try:
            rule.threshold = float(data['threshold'])
        except:
            pass
    if 'severity' in data:
        if data['severity'] in ['critical', 'warning', 'info']:
            rule.severity = data['severity']
    if 'notify_email' in data:
        rule.notify_email = bool(data['notify_email'])
    if 'notify_sms' in data:
        rule.notify_sms = bool(data['notify_sms'])
    if 'notify_dingtalk' in data:
        rule.notify_dingtalk = bool(data['notify_dingtalk'])
    if 'notify_wechat' in data:
        rule.notify_wechat = bool(data['notify_wechat'])
    if 'enabled' in data:
        rule.enabled = bool(data['enabled'])
    
    db.session.commit()
    
    return jsonify({'success': True, 'rule': rule.to_dict()})


@alarm_rules_bp.route('/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_rule(rule_id):
    """删除告警规则"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    rule = AlarmRule.query.get(rule_id)
    if not rule:
        return jsonify({'success': False, 'message': '规则不存在'}), 404
    
    if not is_admin and rule.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    db.session.delete(rule)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '删除成功'})


@alarm_rules_bp.route('/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_rule(rule_id):
    """启用/禁用告警规则"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    rule = AlarmRule.query.get(rule_id)
    if not rule:
        return jsonify({'success': False, 'message': '规则不存在'}), 404
    
    if not is_admin and rule.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    rule.enabled = not rule.enabled
    db.session.commit()
    
    return jsonify({'success': True, 'enabled': rule.enabled})


@alarm_rules_bp.route('/check', methods=['POST'])
@login_required
def check_data_point():
    """检查数据点是否触发告警规则"""
    data = request.get_json() or {}
    device_name = data.get('device_name')
    channel_name = data.get('channel_name')
    point_name = data.get('point_name')
    value = data.get('value')
    user_id = data.get('user_id')
    
    if not all([device_name, channel_name, point_name, value is not None]):
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    
    # 查找匹配的告警规则
    rules = AlarmRule.query.filter_by(user_id=user_id, enabled=True).all()
    
    triggered = []
    for rule in rules:
        # 检查是否匹配
        if rule.device_name and rule.device_name != device_name:
            continue
        if rule.channel_name and rule.channel_name != channel_name:
            continue
        if rule.point_name and rule.point_name != point_name:
            continue
        
        # 检查条件
        triggered_flag = False
        try:
            value_float = float(value)
            threshold = float(rule.threshold)
            
            if rule.condition == '>' and value_float > threshold:
                triggered_flag = True
            elif rule.condition == '<' and value_float < threshold:
                triggered_flag = True
            elif rule.condition == '>=' and value_float >= threshold:
                triggered_flag = True
            elif rule.condition == '<=' and value_float <= threshold:
                triggered_flag = True
            elif rule.condition == '==' and value_float == threshold:
                triggered_flag = True
            elif rule.condition == '!=' and value_float != threshold:
                triggered_flag = True
        except:
            pass
        
        if triggered_flag:
            triggered.append(rule.to_dict())
    
    return jsonify({'success': True, 'triggered': triggered})


@alarm_rules_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """获取告警规则统计"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    query = AlarmRule.query
    if not is_admin:
        query = query.filter_by(user_id=user_id)
    
    total = query.count()
    enabled = query.filter_by(enabled=True).count()
    disabled = total - enabled
    
    # 按级别统计
    critical = query.filter_by(severity='critical').count()
    warning = query.filter_by(severity='warning').count()
    info = query.filter_by(severity='info').count()
    
    return jsonify({
        'success': True,
        'stats': {
            'total': total,
            'enabled': enabled,
            'disabled': disabled,
            'critical': critical,
            'warning': warning,
            'info': info
        }
    })
