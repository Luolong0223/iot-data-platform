#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
层级管理API - 设备组织架构树形结构
支持区域/建筑/楼层/房间/设备的层级管理
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from datetime import datetime

hierarchy_bp = Blueprint('hierarchy_api', __name__)


def build_tree(nodes, parent_id=None):
    """递归构建树形结构"""
    tree = []
    for node in nodes:
        if node.get('parent_id') == parent_id:
            children = build_tree(nodes, node['id'])
            node_item = {
                'id': str(node.get('id')),
                'name': node.get('name', '未命名'),
                'type': node.get('type', 'region'),
                'description': node.get('description'),
                'lat': node.get('lat'),
                'lng': node.get('lng'),
                'children': children,
                'level': 0  # 将在后续计算
            }
            tree.append(node_item)
    return tree


def calculate_level(node, level=0):
    """计算节点层级深度"""
    node['level'] = level
    for child in node.get('children', []):
        calculate_level(child, level + 1)


@hierarchy_bp.route('/api/hierarchy/tree')
@login_required
def get_tree():
    """获取完整的层级树形结构"""
    from models.database import db, Device, Project, DeviceGroup
    
    try:
        # 获取项目列表（第一级）
        if current_user.is_admin:
            projects = Project.query.order_by(Project.sort_order).all()
        else:
            projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.sort_order).all()
        
        # 构建节点列表
        nodes = []
        
        # 添加项目节点
        for p in projects:
            nodes.append({
                'id': f'project_{p.id}',
                'name': p.name or f'项目{p.id}',
                'type': 'region',
                'description': p.description,
                'lat': None,
                'lng': None,
                'parent_id': None,
                'sort_order': p.sort_order or 0
            })
            
            # 获取该项目下的设备分组
            groups = DeviceGroup.query.filter_by(project_id=p.id).order_by(DeviceGroup.sort_order).all()
            
            group_ids = [g.id for g in groups]
            
            for g in groups:
                nodes.append({
                    'id': f'group_{g.id}',
                    'name': g.name or f'分组{g.id}',
                    'type': 'building',
                    'description': g.description,
                    'lat': None,
                    'lng': None,
                    'parent_id': f'project_{p.id}' if not g.parent_id else f'group_{g.parent_id}',
                    'sort_order': g.sort_order or 0
                })
                
                # 获取该分组下的设备
                devices_query = Device.query.filter_by(group_id=g.id)
                if not current_user.is_admin:
                    devices_query = devices_query.filter_by(user_id=current_user.id)
                    
                devices = devices_query.limit(50).all()  # 限制数量避免过大
                
                for d in devices:
                    device_type = getattr(d, 'device_type', 'sensor') or 'device'
                    nodes.append({
                        'id': f'device_{d.id}',
                        'name': d.name or f'设备{d.id}',
                        'type': 'device',
                        'description': '',
                        'lat': getattr(d, 'latitude', None),  # Device模型使用latitude字段
                        'lng': getattr(d, 'longitude', None),  # Device模型使用longitude字段
                        'parent_id': f'group_{g.id}',
                        'is_online': d.is_online,
                        'device_type': device_type,
                        'latest_value': getattr(d, 'latest_value', None),
                        'last_update': getattr(d, 'last_seen_at', None),
                        'sort_order': 0
                    })
        
        # 构建树形结构
        tree = build_tree(nodes)
        
        # 计算层级深度
        for root in tree:
            calculate_level(root)
        
        # 统计信息
        stats = {
            'total_nodes': len(nodes),
            'region_count': len(projects),
            'building_count': len([n for n in nodes if n['type'] == 'building']),
            'device_count': len([n for n in nodes if n['type'] == 'device']),
            'max_depth': 0
        }
        
        # 计算最大深度
        def get_max_depth(tree_nodes, depth=1):
            max_d = depth
            for node in tree_nodes:
                if node.get('children'):
                    max_d = max(max_d, get_max_depth(node['children'], depth + 1))
            return max_d
        
        stats['max_depth'] = get_max_depth(tree) if tree else 0
        
        return jsonify({
            'success': True,
            'tree': tree,
            'stats': stats
        })
    except Exception as e:
        current_app.logger.error(f"获取层级树失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hierarchy_bp.route('/api/hierarchy/nodes', methods=['POST'])
@login_required
def create_node():
    """创建新节点"""
    from models.database import db, Project, DeviceGroup, Device
    
    data = request.get_json()
    
    name = data.get('name', '').strip()
    node_type = data.get('type', '')
    description = data.get('description', '').strip()
    parent_id = data.get('parent_id')
    lat = data.get('lat')
    lng = data.get('lng')
    
    if not name:
        return jsonify({'success': False, 'error': '节点名称不能为空'}), 400
    
    if not node_type:
        return jsonify({'success': False, 'error': '节点类型不能为空'}), 400
    
    try:
        # 根据类型创建不同的实体
        if node_type == 'region':
            entity = Project(
                user_id=current_user.id,
                name=name,
                description=description or None
            )
            db.session.add(entity)
            db.session.flush()
            
            new_node = {
                'id': f'project_{entity.id}',
                'name': name,
                'type': 'region',
                'description': description,
                'lat': lat,
                'lng': lng,
                'parent_id': None
            }
            
        elif node_type in ['building', 'floor', 'room']:
            # 解析父节点ID
            project_id = None
            group_parent_id = None
            
            if parent_id and parent_id.startswith('project_'):
                project_id = int(parent_id.replace('project_', ''))
            elif parent_id and parent_id.startswith('group_'):
                group_parent_id = int(parent_id.replace('group_', ''))
                # 查找该分组所属的项目
                parent_group = DeviceGroup.query.get(group_parent_id)
                if parent_group:
                    project_id = parent_group.project_id
            
            entity = DeviceGroup(
                user_id=current_user.id,
                project_id=project_id,
                parent_id=group_parent_id,
                name=name,
                description=description or None
            )
            db.session.add(entity)
            db.session.flush()
            
            new_node = {
                'id': f'group_{entity.id}',
                'name': name,
                'type': node_type,
                'description': description,
                'lat': lat,
                'lng': lng,
                'parent_id': parent_id
            }
            
        elif node_type == 'device':
            # 设备应该通过设备管理API创建，这里只是示例
            return jsonify({'success': False, 'error': '请通过设备管理创建设备'}), 400
            
        else:
            return jsonify({'success': False, 'error': f'不支持的节点类型: {node_type}'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '创建成功',
            'node': new_node
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建节点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hierarchy_bp.route('/api/hierarchy/nodes/<node_id>', methods=['PUT'])
@login_required
def update_node(node_id):
    """更新节点"""
    from models.database import db, Project, DeviceGroup, Device
    
    data = request.get_json()
    
    try:
        # 根据ID前缀确定实体类型
        if node_id.startswith('project_'):
            entity_id = int(node_id.replace('project_', ''))
            entity = Project.query.get(entity_id)
            if not entity:
                return jsonify({'success': False, 'error': '项目不存在'}), 404
                
            if data.get('name'):
                entity.name = data['name'].strip()
            if 'description' in data:
                entity.description = data.get('description') or None
            if 'sort_order' in data:
                entity.sort_order = data['sort_order']
                
        elif node_id.startswith('group_'):
            entity_id = int(node_id.replace('group_', ''))
            entity = DeviceGroup.query.get(entity_id)
            if not entity:
                return jsonify({'success': False, 'error': '分组不存在'}), 404
                
            if data.get('name'):
                entity.name = data['name'].strip()
            if 'description' in data:
                entity.description = data.get('description') or None
            if 'sort_order' in data:
                entity.sort_order = data['sort_order']
                
        elif node_id.startswith('device_'):
            entity_id = int(node_id.replace('device_', ''))
            entity = Device.query.get(entity_id)
            if not entity:
                return jsonify({'success': False, 'error': '设备不存在'}), 404
                
            if data.get('name'):
                entity.name = data['name'].strip()
            if 'lat' in data:
                entity.lat = data.get('lat')
            if 'lng' in data:
                entity.lng = data.get('lng')
        else:
            return jsonify({'success': False, 'error': '无效的节点ID'}), 400
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '更新成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新节点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hierarchy_bp.route('/api/hierarchy/nodes/<node_id>', methods=['DELETE'])
@login_required
def delete_node(node_id):
    """删除节点及其子节点"""
    from models.database import db, Project, DeviceGroup, Device
    
    try:
        if node_id.startswith('project_'):
            entity_id = int(node_id.replace('project_', ''))
            entity = Project.query.get(entity_id)
            if not entity:
                return jsonify({'success': False, 'error': '项目不存在'}), 404
            
            # 删除项目下的所有分组和设备
            groups = DeviceGroup.query.filter_by(project_id=entity_id).all()
            for g in groups:
                Device.query.filter_by(group_id=g.id).delete()
            DeviceGroup.query.filter_by(project_id=entity_id).delete()
            db.session.delete(entity)
            
        elif node_id.startswith('group_'):
            entity_id = int(node_id.replace('group_', ''))
            entity = DeviceGroup.query.get(entity_id)
            if not entity:
                return jsonify({'success': False, 'error': '分组不存在'}), 404
            
            # 删除该分组下的设备和子分组
            child_groups = DeviceGroup.query.filter_by(parent_id=entity_id).all()
            for cg in child_groups:
                Device.query.filter_by(group_id=cg.id).delete()
            DeviceGroup.query.filter_by(parent_id=entity_id).delete()
            Device.query.filter_by(group_id=entity_id).delete()
            db.session.delete(entity)
            
        elif node_id.startswith('device_'):
            entity_id = int(node_id.replace('device_', ''))
            entity = Device.query.get(entity_id)
            if not entity:
                return jsonify({'success': False, 'error': '设备不存在'}), 404
            db.session.delete(entity)
        else:
            return jsonify({'success': False, 'error': '无效的节点ID'}), 400
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除节点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
