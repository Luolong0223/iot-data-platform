"""
设备生命周期管理路由
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.device_lifecycle import DeviceLifecycleService

logger = logging.getLogger(__name__)

lifecycle_bp = Blueprint('lifecycle', __name__, url_prefix='/api/lifecycle')


@lifecycle_bp.route('/devices/<int:device_id>/status', methods=['GET'])
@login_required
def get_device_status(device_id):
    """获取设备当前生命周期状态"""
    try:
        status = DeviceLifecycleService.get_current_status(device_id)
        return jsonify({
            'success': True,
            'device_id': device_id,
            'status': status
        })
    except Exception as e:
        logger.error(f"Get device status failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/devices/<int:device_id>/register', methods=['POST'])
@login_required
def register_device(device_id):
    """注册设备"""
    try:
        data = request.get_json() or {}
        result = DeviceLifecycleService.register_device(
            device_id=device_id,
            user_id=current_user.id,
            operator=data.get('operator'),
            metadata=data.get('metadata')
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Register device failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/devices/<int:device_id>/activate', methods=['POST'])
@login_required
def activate_device(device_id):
    """激活设备"""
    try:
        data = request.get_json() or {}
        result = DeviceLifecycleService.activate_device(
            device_id=device_id,
            user_id=current_user.id,
            operator=data.get('operator'),
            description=data.get('description'),
            metadata=data.get('metadata')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Activate device failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/devices/<int:device_id>/deactivate', methods=['POST'])
@login_required
def deactivate_device(device_id):
    """停用设备"""
    try:
        data = request.get_json() or {}
        result = DeviceLifecycleService.deactivate_device(
            device_id=device_id,
            user_id=current_user.id,
            operator=data.get('operator'),
            description=data.get('description'),
            metadata=data.get('metadata')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Deactivate device failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/devices/<int:device_id>/maintenance', methods=['POST'])
@login_required
def start_maintenance(device_id):
    """开始维护"""
    try:
        data = request.get_json() or {}
        result = DeviceLifecycleService.start_maintenance(
            device_id=device_id,
            user_id=current_user.id,
            operator=data.get('operator'),
            description=data.get('description'),
            metadata=data.get('metadata')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Start maintenance failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/devices/<int:device_id>/retire', methods=['POST'])
@login_required
def retire_device(device_id):
    """退役设备"""
    try:
        data = request.get_json() or {}
        result = DeviceLifecycleService.retire_device(
            device_id=device_id,
            user_id=current_user.id,
            operator=data.get('operator'),
            description=data.get('description'),
            metadata=data.get('metadata')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Retire device failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/devices/<int:device_id>/decommission', methods=['POST'])
@login_required
def decommission_device(device_id):
    """报废设备"""
    try:
        data = request.get_json() or {}
        result = DeviceLifecycleService.decommission_device(
            device_id=device_id,
            user_id=current_user.id,
            operator=data.get('operator'),
            description=data.get('description'),
            metadata=data.get('metadata')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Decommission device failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/devices/<int:device_id>/history', methods=['GET'])
@login_required
def get_lifecycle_history(device_id):
    """获取设备生命周期历史"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = DeviceLifecycleService.get_lifecycle_history(device_id, limit)
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        logger.error(f"Get lifecycle history failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/maintenance', methods=['POST'])
@login_required
def create_maintenance_record():
    """创建维护记录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        scheduled_at = None
        if data.get('scheduled_at'):
            try:
                scheduled_at = datetime.fromisoformat(data['scheduled_at'])
            except ValueError:
                pass
        
        result = DeviceLifecycleService.create_maintenance_record(
            device_id=data['device_id'],
            user_id=current_user.id,
            maintenance_type=data['maintenance_type'],
            title=data['title'],
            description=data.get('description'),
            scheduled_at=scheduled_at,
            assigned_to=data.get('assigned_to'),
            cost=data.get('cost', 0.0)
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Create maintenance record failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/maintenance/<int:record_id>', methods=['PUT'])
@login_required
def update_maintenance_record(record_id):
    """更新维护记录状态"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        result = DeviceLifecycleService.update_maintenance_status(
            record_id=record_id,
            status=data['status'],
            performed_by=data.get('performed_by'),
            result=data.get('result'),
            notes=data.get('notes')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Update maintenance record failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/maintenance', methods=['GET'])
@login_required
def get_maintenance_records():
    """获取维护记录"""
    try:
        device_id = request.args.get('device_id', type=int)
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        
        records = DeviceLifecycleService.get_maintenance_records(
            device_id=device_id,
            user_id=current_user.id,
            status=status,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'records': records,
            'count': len(records)
        })
    except Exception as e:
        logger.error(f"Get maintenance records failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@lifecycle_bp.route('/statistics', methods=['GET'])
@login_required
def get_lifecycle_statistics():
    """获取生命周期统计"""
    try:
        stats = DeviceLifecycleService.get_lifecycle_statistics(user_id=current_user.id)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Get lifecycle statistics failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
