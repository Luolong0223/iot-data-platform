"""
设备影子 API 路由
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.device_shadow import DeviceShadowService
from models.database import Device

shadow_bp = Blueprint('shadow', __name__, url_prefix='/api/shadow')


@shadow_bp.route('/<int:device_id>', methods=['GET'])
@login_required
def get_shadow(device_id):
    """获取设备影子"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404
    
    shadow = DeviceShadowService.get_shadow(device_id)
    if not shadow:
        # 自动创建空影子
        shadow = DeviceShadowService.get_or_create_shadow(device_id, current_user.id)
    
    return jsonify({
        'success': True,
        'data': shadow.to_dict()
    })


@shadow_bp.route('/<int:device_id>/desired', methods=['PUT'])
@login_required
def update_desired(device_id):
    """更新期望状态"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404
    
    data = request.get_json()
    if not data or 'state' not in data:
        return jsonify({'success': False, 'error': '缺少 state 参数'}), 400
    
    result = DeviceShadowService.update_desired_state(
        device_id=device_id,
        user_id=current_user.id,
        state=data['state'],
        operator=data.get('operator', 'user')
    )
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 500


@shadow_bp.route('/<int:device_id>/reported', methods=['PUT'])
@login_required
def update_reported(device_id):
    """更新报告状态（设备上报）"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404
    
    data = request.get_json()
    if not data or 'state' not in data:
        return jsonify({'success': False, 'error': '缺少 state 参数'}), 400
    
    result = DeviceShadowService.update_reported_state(
        device_id=device_id,
        user_id=current_user.id,
        state=data['state'],
        operator=data.get('operator', 'device')
    )
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 500


@shadow_bp.route('/<int:device_id>/sync', methods=['POST'])
@login_required
def sync_shadow(device_id):
    """同步设备影子"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404
    
    result = DeviceShadowService.sync_shadow(device_id, current_user.id)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 500


@shadow_bp.route('/<int:device_id>/history', methods=['GET'])
@login_required
def get_history(device_id):
    """获取设备影子变更历史"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404
    
    limit = request.args.get('limit', 50, type=int)
    history = DeviceShadowService.get_shadow_history(device_id, limit)
    
    return jsonify({
        'success': True,
        'data': history,
        'count': len(history)
    })


@shadow_bp.route('/pending', methods=['GET'])
@login_required
def get_pending():
    """获取待同步的设备影子列表"""
    pending = DeviceShadowService.get_pending_shadows(current_user.id)
    
    return jsonify({
        'success': True,
        'data': [s.to_dict() for s in pending],
        'count': len(pending)
    })


@shadow_bp.route('/batch-sync', methods=['POST'])
@login_required
def batch_sync():
    """批量同步所有待同步的设备影子"""
    result = DeviceShadowService.batch_sync(current_user.id)
    return jsonify(result)


@shadow_bp.route('/<int:device_id>', methods=['DELETE'])
@login_required
def delete_shadow(device_id):
    """删除设备影子"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404
    
    result = DeviceShadowService.delete_shadow(device_id)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 500
