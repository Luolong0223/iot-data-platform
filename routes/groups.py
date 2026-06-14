"""
设备分组路由 - 设备分组管理API
"""
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models.database import db, DeviceGroup, Device

logger = logging.getLogger(__name__)

groups_bp = Blueprint('groups', __name__, url_prefix='/api/groups')


@groups_bp.route('', methods=['GET'])
@login_required
def list_groups():
    """获取用户的所有设备分组"""
    groups = DeviceGroup.query.filter_by(user_id=current_user.id).order_by(DeviceGroup.sort_order).all()
    return jsonify({
        'success': True,
        'groups': [g.to_dict() for g in groups]
    })


@groups_bp.route('', methods=['POST'])
@login_required
def create_group():
    """创建设备分组"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': '分组名称不能为空'}), 400
    
    # 检查名称是否重复
    existing = DeviceGroup.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({'success': False, 'message': '分组名称已存在'}), 409
    
    # 获取最大排序号
    max_order = db.session.query(db.func.max(DeviceGroup.sort_order)).filter_by(
        user_id=current_user.id
    ).scalar() or 0
    
    group = DeviceGroup(
        user_id=current_user.id,
        name=name,
        description=data.get('description', '').strip(),
        color=data.get('color', '#3498db'),
        sort_order=max_order + 1
    )
    
    db.session.add(group)
    db.session.commit()
    
    logger.info(f"User {current_user.id} created group '{name}'")
    return jsonify({'success': True, 'group': group.to_dict()}), 201


@groups_bp.route('/<int:group_id>', methods=['PUT'])
@login_required
def update_group(group_id):
    """更新设备分组"""
    group = DeviceGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
    if not group:
        return jsonify({'success': False, 'message': '分组不存在'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    if 'name' in data:
        new_name = data['name'].strip()
        if new_name and new_name != group.name:
            existing = DeviceGroup.query.filter_by(
                user_id=current_user.id, name=new_name
            ).first()
            if existing:
                return jsonify({'success': False, 'message': '分组名称已存在'}), 409
            group.name = new_name
    
    if 'description' in data:
        group.description = data['description'].strip()
    
    if 'color' in data:
        group.color = data['color']
    
    if 'sort_order' in data:
        group.sort_order = data['sort_order']
    
    db.session.commit()
    return jsonify({'success': True, 'group': group.to_dict()})


@groups_bp.route('/<int:group_id>', methods=['DELETE'])
@login_required
def delete_group(group_id):
    """删除设备分组"""
    group = DeviceGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
    if not group:
        return jsonify({'success': False, 'message': '分组不存在'}), 404
    
    # 将分组内的设备的group_id设为None
    Device.query.filter_by(group_id=group_id).update({'group_id': None})
    
    db.session.delete(group)
    db.session.commit()
    
    logger.info(f"User {current_user.id} deleted group {group_id}")
    return jsonify({'success': True, 'message': '分组已删除'})


@groups_bp.route('/<int:group_id>/devices', methods=['GET'])
@login_required
def get_group_devices(group_id):
    """获取分组内的设备"""
    group = DeviceGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
    if not group:
        return jsonify({'success': False, 'message': '分组不存在'}), 404
    
    devices = Device.query.filter_by(group_id=group_id).all()
    return jsonify({
        'success': True,
        'group': group.to_dict(),
        'devices': [d.to_dict() for d in devices]
    })


@groups_bp.route('/<int:group_id>/devices', methods=['POST'])
@login_required
def add_devices_to_group(group_id):
    """将设备添加到分组"""
    group = DeviceGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
    if not group:
        return jsonify({'success': False, 'message': '分组不存在'}), 404
    
    data = request.get_json()
    if not data or 'device_ids' not in data:
        return jsonify({'success': False, 'message': '缺少设备ID列表'}), 400
    
    device_ids = data['device_ids']
    if not isinstance(device_ids, list):
        return jsonify({'success': False, 'message': 'device_ids 必须是数组'}), 400
    
    # 更新设备的分组
    updated = Device.query.filter(
        Device.id.in_(device_ids),
        Device.user_id == current_user.id
    ).update({'group_id': group_id}, synchronize_session=False)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已将 {updated} 个设备添加到分组'
    })


@groups_bp.route('/<int:group_id>/devices/<int:device_id>', methods=['DELETE'])
@login_required
def remove_device_from_group(group_id, device_id):
    """从分组中移除设备"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    
    if device.group_id != group_id:
        return jsonify({'success': False, 'message': '设备不在该分组中'}), 400
    
    device.group_id = None
    db.session.commit()
    
    return jsonify({'success': True, 'message': '设备已从分组中移除'})


@groups_bp.route('/reorder', methods=['POST'])
@login_required
def reorder_groups():
    """重新排序分组"""
    data = request.get_json()
    if not data or 'order' not in data:
        return jsonify({'success': False, 'message': '缺少排序数据'}), 400
    
    order_list = data['order']  # [{id: 1, order: 1}, ...]
    
    for item in order_list:
        group = DeviceGroup.query.filter_by(
            id=item.get('id'),
            user_id=current_user.id
        ).first()
        if group:
            group.sort_order = item.get('order', 0)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '排序已更新'})


@groups_bp.route('/batch/move', methods=['POST'])
@login_required
def batch_move_devices():
    """批量移动设备到指定分组"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    device_ids = data.get('device_ids', [])
    target_group_id = data.get('target_group_id')
    
    if not device_ids:
        return jsonify({'success': False, 'message': '请选择要移动的设备'}), 400
    
    # 验证目标分组
    if target_group_id:
        target_group = DeviceGroup.query.filter_by(
            id=target_group_id,
            user_id=current_user.id
        ).first()
        if not target_group:
            return jsonify({'success': False, 'message': '目标分组不存在'}), 404
    
    # 批量更新
    updated = Device.query.filter(
        Device.id.in_(device_ids),
        Device.user_id == current_user.id
    ).update({'group_id': target_group_id}, synchronize_session=False)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已将 {updated} 个设备移动到{"未分组" if not target_group_id else target_group.name}'
    })


@groups_bp.route('/batch/delete', methods=['POST'])
@login_required
def batch_delete_devices():
    """批量删除设备"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    device_ids = data.get('device_ids', [])
    
    if not device_ids:
        return jsonify({'success': False, 'message': '请选择要删除的设备'}), 400
    
    # 批量删除
    deleted = Device.query.filter(
        Device.id.in_(device_ids),
        Device.user_id == current_user.id
    ).delete(synchronize_session=False)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已删除 {deleted} 个设备'
    })


@groups_bp.route('/batch/update-status', methods=['POST'])
@login_required
def batch_update_device_status():
    """批量更新设备状态"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    device_ids = data.get('device_ids', [])
    is_online = data.get('is_online')
    
    if not device_ids:
        return jsonify({'success': False, 'message': '请选择要更新的设备'}), 400
    
    if is_online is None:
        return jsonify({'success': False, 'message': '请指定设备状态'}), 400
    
    # 批量更新
    updated = Device.query.filter(
        Device.id.in_(device_ids),
        Device.user_id == current_user.id
    ).update({'is_online': is_online}, synchronize_session=False)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已更新 {updated} 个设备状态为{"在线" if is_online else "离线"}'
    })


@groups_bp.route('/batch/assign-tags', methods=['POST'])
@login_required
def batch_assign_tags():
    """批量为设备分配标签"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    device_ids = data.get('device_ids', [])
    tags = data.get('tags', [])
    
    if not device_ids:
        return jsonify({'success': False, 'message': '请选择要更新的设备'}), 400
    
    if not tags:
        return jsonify({'success': False, 'message': '请指定标签'}), 400
    
    # 获取设备并更新标签
    devices = Device.query.filter(
        Device.id.in_(device_ids),
        Device.user_id == current_user.id
    ).all()
    
    updated_count = 0
    for device in devices:
        # 假设 Device 模型有 tags 字段（JSON）
        existing_tags = device.tags if hasattr(device, 'tags') and device.tags else []
        if isinstance(existing_tags, str):
            import json
            try:
                existing_tags = json.loads(existing_tags)
            except:
                existing_tags = []
        
        # 合并标签（去重）
        new_tags = list(set(existing_tags + tags))
        
        if hasattr(device, 'tags'):
            import json
            device.tags = json.dumps(new_tags)
            updated_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已为 {updated_count} 个设备分配标签'
    })


@groups_bp.route('/statistics', methods=['GET'])
@login_required
def get_group_statistics():
    """获取分组统计信息"""
    groups = DeviceGroup.query.filter_by(user_id=current_user.id).all()
    
    stats = {
        'total_groups': len(groups),
        'total_devices': Device.query.filter_by(user_id=current_user.id).count(),
        'ungrouped_devices': Device.query.filter_by(user_id=current_user.id, group_id=None).count(),
        'groups': []
    }
    
    for group in groups:
        device_count = Device.query.filter_by(group_id=group.id).count()
        online_count = Device.query.filter_by(group_id=group.id, is_online=True).count()
        
        stats['groups'].append({
            'id': group.id,
            'name': group.name,
            'device_count': device_count,
            'online_count': online_count,
            'offline_count': device_count - online_count
        })
    
    return jsonify({'success': True, 'statistics': stats})
