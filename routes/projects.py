#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目管理API路由
"""

from flask import Blueprint, request, jsonify, g
from models.database import db, Project, DeviceGroup, Device, SlaveChannel, DataPoint, User
from routes.auth import login_required
from sqlalchemy import func
from datetime import datetime, timedelta

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')


@projects_bp.route('/', methods=['GET'])
@login_required
def list_projects():
    """获取项目列表"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    query = Project.query
    if not is_admin:
        query = query.filter_by(user_id=user_id)
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    # 获取每个项目的统计信息
    result = []
    for p in projects:
        # 统计该项目的设备数
        device_count = Device.query.filter_by(project_id=p.id).count()
        online_count = Device.query.filter_by(project_id=p.id, is_online=True).count()
        
        # 统计分组数
        group_count = DeviceGroup.query.filter_by(project_id=p.id).count()
        
        result.append({
            **p.to_dict(),
            'device_count': device_count,
            'online_count': online_count,
            'group_count': group_count
        })
    
    return jsonify({'success': True, 'projects': result})


@projects_bp.route('/', methods=['POST'])
@login_required
def create_project():
    """创建项目"""
    user_id = g.user.id
    
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    location = data.get('location', '').strip()
    
    if not name:
        return jsonify({'success': False, 'message': '项目名称不能为空'}), 400
    
    # 检查名称是否重复
    existing = Project.query.filter_by(user_id=user_id, name=name).first()
    if existing:
        return jsonify({'success': False, 'message': '项目名称已存在'}), 400
    
    project = Project(
        name=name,
        description=description,
        location=location,
        user_id=user_id
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({'success': True, 'project': project.to_dict()})


@projects_bp.route('/<int:project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """获取项目详情"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'message': '项目不存在'}), 404
    
    if not is_admin and project.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    # 获取项目下的分组树
    groups = DeviceGroup.query.filter_by(project_id=project_id).order_by(DeviceGroup.sort_order).all()
    
    # 获取每个分组下的设备
    groups_with_devices = []
    for group in groups:
        devices = Device.query.filter_by(group_id=group.id).all()
        device_list = []
        for d in devices:
            device_list.append({
                **d.to_dict(),
                'channel_count': SlaveChannel.query.filter_by(device_id=d.id).count(),
                'data_count': db.session.query(func.count(DataPoint.id)).join(SlaveChannel).filter(SlaveChannel.device_id == d.id).scalar() or 0
            })
        
        groups_with_devices.append({
            **group.to_dict(),
            'devices': device_list,
            'device_count': len(device_list),
            'online_count': sum(1 for d in device_list if d.get('is_online')),
            'offline_count': sum(1 for d in device_list if not d.get('is_online'))
        })
    
    # 获取未分组的设备
    ungrouped_devices = Device.query.filter_by(project_id=project_id, group_id=None).all()
    ungrouped_list = []
    for d in ungrouped_devices:
        ungrouped_list.append({
            **d.to_dict(),
            'channel_count': SlaveChannel.query.filter_by(device_id=d.id).count()
        })
    
    # 统计数据
    total_devices = Device.query.filter_by(project_id=project_id).count()
    online_devices = Device.query.filter_by(project_id=project_id, is_online=True).count()
    total_channels = db.session.query(func.count(SlaveChannel.id)).join(Device).filter(Device.project_id == project_id).scalar() or 0
    total_data = db.session.query(func.count(DataPoint.id)).join(SlaveChannel).join(Device).filter(Device.project_id == project_id).scalar() or 0
    
    # 今日数据量
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_data = db.session.query(func.count(DataPoint.id)).join(SlaveChannel).join(Device).filter(
        Device.project_id == project_id,
        DataPoint.timestamp >= today
    ).scalar() or 0
    
    return jsonify({
        'success': True,
        'project': {
            **project.to_dict(),
            'groups': groups_with_devices,
            'ungrouped_devices': ungrouped_list,
            'stats': {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': total_devices - online_devices,
                'online_rate': round(online_devices / total_devices * 100, 1) if total_devices > 0 else 0,
                'total_channels': total_channels,
                'total_data': total_data,
                'today_data': today_data
            }
        }
    })


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    """更新项目"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'message': '项目不存在'}), 404
    
    if not is_admin and project.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    data = request.get_json() or {}
    
    if 'name' in data:
        name = data['name'].strip()
        if name:
            existing = Project.query.filter(Project.user_id == user_id, Project.name == name, Project.id != project_id).first()
            if existing:
                return jsonify({'success': False, 'message': '项目名称已存在'}), 400
            project.name = name
    
    if 'description' in data:
        project.description = data['description'].strip()
    if 'location' in data:
        project.location = data['location'].strip()
    
    db.session.commit()
    
    return jsonify({'success': True, 'project': project.to_dict()})


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    """删除项目"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'message': '项目不存在'}), 404
    
    if not is_admin and project.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    # 检查是否有设备
    device_count = Device.query.filter_by(project_id=project_id).count()
    if device_count > 0:
        return jsonify({'success': False, 'message': f'项目下还有 {device_count} 个设备，请先删除设备'}), 400
    
    db.session.delete(project)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '删除成功'})


# ==================== 分组管理 ====================

@projects_bp.route('/<int:project_id>/groups', methods=['GET'])
@login_required
def list_groups(project_id):
    """获取分组列表"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'message': '项目不存在'}), 404
    
    if not is_admin and project.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    groups = DeviceGroup.query.filter_by(project_id=project_id).order_by(DeviceGroup.sort_order).all()
    
    result = []
    for g in groups:
        device_count = Device.query.filter_by(group_id=g.id).count()
        online_count = Device.query.filter_by(group_id=g.id, is_online=True).count()
        
        result.append({
            **g.to_dict(),
            'device_count': device_count,
            'online_count': online_count
        })
    
    return jsonify({'success': True, 'groups': result})


@projects_bp.route('/<int:project_id>/groups', methods=['POST'])
@login_required
def create_group(project_id):
    """创建分组"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'message': '项目不存在'}), 404
    
    if not is_admin and project.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    color = data.get('color', '#3498db')
    parent_id = data.get('parent_id')
    
    if not name:
        return jsonify({'success': False, 'message': '分组名称不能为空'}), 400
    
    # 获取最大排序号
    max_order = db.session.query(func.max(DeviceGroup.sort_order)).filter_by(project_id=project_id).scalar() or 0
    
    group = DeviceGroup(
        name=name,
        description=description,
        color=color,
        project_id=project_id,
        parent_id=parent_id,
        user_id=user_id,
        sort_order=max_order + 1
    )
    
    db.session.add(group)
    db.session.commit()
    
    return jsonify({'success': True, 'group': group.to_dict()})


@projects_bp.route('/<int:project_id>/groups/<int:group_id>', methods=['PUT'])
@login_required
def update_group(project_id, group_id):
    """更新分组"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    group = DeviceGroup.query.get(group_id)
    if not group or group.project_id != project_id:
        return jsonify({'success': False, 'message': '分组不存在'}), 404
    
    if not is_admin and group.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    data = request.get_json() or {}
    
    if 'name' in data:
        group.name = data['name'].strip()
    if 'description' in data:
        group.description = data['description'].strip()
    if 'color' in data:
        group.color = data['color']
    if 'sort_order' in data:
        group.sort_order = data['sort_order']
    
    db.session.commit()
    
    return jsonify({'success': True, 'group': group.to_dict()})


@projects_bp.route('/<int:project_id>/groups/<int:group_id>', methods=['DELETE'])
@login_required
def delete_group(project_id, group_id):
    """删除分组"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    group = DeviceGroup.query.get(group_id)
    if not group or group.project_id != project_id:
        return jsonify({'success': False, 'message': '分组不存在'}), 404
    
    if not is_admin and group.user_id != user_id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    # 将分组下的设备移到未分组
    Device.query.filter_by(group_id=group_id).update({'group_id': None})
    
    db.session.delete(group)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '删除成功'})


# ==================== 层级树 ====================

@projects_bp.route('/tree', methods=['GET'])
@login_required
def get_tree():
    """获取完整层级树"""
    user_id = g.user.id
    is_admin = g.user.is_admin
    
    # 获取用户的所有项目
    project_query = Project.query
    if not is_admin:
        project_query = project_query.filter_by(user_id=user_id)
    
    projects = project_query.order_by(Project.created_at.desc()).all()
    
    tree = []
    for project in projects:
        # 获取项目下的分组
        groups = DeviceGroup.query.filter_by(project_id=project.id).order_by(DeviceGroup.sort_order).all()
        
        group_nodes = []
        for group in groups:
            # 获取分组下的设备
            devices = Device.query.filter_by(group_id=group.id).all()
            
            device_nodes = []
            for device in devices:
                # 获取设备下的通道
                channels = SlaveChannel.query.filter_by(device_id=device.id).all()
                
                channel_nodes = []
                for channel in channels:
                    channel_nodes.append({
                        'id': f'channel_{channel.id}',
                        'name': channel.name,
                        'type': 'channel',
                        'is_online': channel.is_online,
                        'data_point_count': DataPoint.query.filter_by(channel_id=channel.id).count()
                    })
                
                device_nodes.append({
                    'id': f'device_{device.id}',
                    'name': device.name,
                    'type': 'device',
                    'is_online': device.is_online,
                    'last_seen_at': device.last_seen_at.isoformat() if device.last_seen_at else None,
                    'children': channel_nodes
                })
            
            group_nodes.append({
                'id': f'group_{group.id}',
                'name': group.name,
                'type': 'group',
                'color': group.color,
                'device_count': len(device_nodes),
                'online_count': sum(1 for d in device_nodes if d.get('is_online')),
                'children': device_nodes
            })
        
        # 未分组的设备
        ungrouped_devices = Device.query.filter_by(project_id=project.id, group_id=None).all()
        ungrouped_nodes = []
        for device in ungrouped_devices:
            ungrouped_nodes.append({
                'id': f'device_{device.id}',
                'name': device.name,
                'type': 'device',
                'is_online': device.is_online,
                'last_seen_at': device.last_seen_at.isoformat() if device.last_seen_at else None
            })
        
        if ungrouped_nodes:
            group_nodes.append({
                'id': f'ungrouped_{project.id}',
                'name': '未分组',
                'type': 'ungrouped',
                'device_count': len(ungrouped_nodes),
                'children': ungrouped_nodes
            })
        
        # 项目统计
        total_devices = Device.query.filter_by(project_id=project.id).count()
        online_devices = Device.query.filter_by(project_id=project.id, is_online=True).count()
        
        tree.append({
            'id': f'project_{project.id}',
            'name': project.name,
            'type': 'project',
            'location': project.location,
            'device_count': total_devices,
            'online_count': online_devices,
            'online_rate': round(online_devices / total_devices * 100, 1) if total_devices > 0 else 0,
            'children': group_nodes
        })
    
    return jsonify({'success': True, 'tree': tree})
