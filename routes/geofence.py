"""
地理围栏与轨迹追踪API路由
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from services.geofence_service import GeofenceService, TrackService

geofence_bp = Blueprint('geofence', __name__, url_prefix='/api/geofence')


# ========================================================================
# 地理围栏管理
# ========================================================================

@geofence_bp.route('/fences', methods=['POST'])
@login_required
def create_geofence():
    """创建地理围栏"""
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('fence_type'):
        return jsonify({'error': '缺少必填字段'}), 400
    
    fence_type = data.get('fence_type')
    
    # 验证围栏类型和参数
    if fence_type == 'circle':
        if not all(k in data for k in ['center_lat', 'center_lng', 'radius']):
            return jsonify({'error': '圆形围栏需要 center_lat, center_lng, radius'}), 400
    elif fence_type == 'polygon':
        if not data.get('vertices') or len(data['vertices']) < 3:
            return jsonify({'error': '多边形围栏需要至少3个顶点'}), 400
    else:
        return jsonify({'error': '不支持的围栏类型'}), 400
    
    try:
        geofence = GeofenceService.create_geofence(
            user_id=current_user.id,
            name=data['name'],
            fence_type=fence_type,
            center_lat=data.get('center_lat'),
            center_lng=data.get('center_lng'),
            radius=data.get('radius'),
            vertices=data.get('vertices'),
            alert_on_enter=data.get('alert_on_enter', True),
            alert_on_exit=data.get('alert_on_exit', True),
            alert_severity=data.get('alert_severity', 'warning'),
            description=data.get('description')
        )
        
        return jsonify({
            'message': '地理围栏创建成功',
            'geofence': geofence.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@geofence_bp.route('/fences', methods=['GET'])
@login_required
def get_geofences():
    """获取所有地理围栏"""
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
    geofences = GeofenceService.get_geofences(current_user.id, enabled_only)
    
    return jsonify({
        'geofences': [g.to_dict() for g in geofences],
        'count': len(geofences)
    })


@geofence_bp.route('/fences/<int:geofence_id>', methods=['GET'])
@login_required
def get_geofence(geofence_id):
    """获取单个地理围栏"""
    from models.database import Geofence
    geofence = Geofence.query.filter_by(id=geofence_id, user_id=current_user.id).first()
    
    if not geofence:
        return jsonify({'error': '地理围栏不存在'}), 404
    
    return jsonify({'geofence': geofence.to_dict()})


@geofence_bp.route('/fences/<int:geofence_id>', methods=['PUT'])
@login_required
def update_geofence(geofence_id):
    """更新地理围栏"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '缺少更新数据'}), 400
    
    geofence = GeofenceService.update_geofence(geofence_id, current_user.id, **data)
    
    if not geofence:
        return jsonify({'error': '地理围栏不存在'}), 404
    
    return jsonify({
        'message': '地理围栏更新成功',
        'geofence': geofence.to_dict()
    })


@geofence_bp.route('/fences/<int:geofence_id>', methods=['DELETE'])
@login_required
def delete_geofence(geofence_id):
    """删除地理围栏"""
    success = GeofenceService.delete_geofence(geofence_id, current_user.id)
    
    if not success:
        return jsonify({'error': '地理围栏不存在'}), 404
    
    return jsonify({'message': '地理围栏删除成功'})


@geofence_bp.route('/fences/<int:geofence_id>/toggle', methods=['POST'])
@login_required
def toggle_geofence(geofence_id):
    """启用/禁用地理围栏"""
    from models.database import Geofence
    geofence = Geofence.query.filter_by(id=geofence_id, user_id=current_user.id).first()
    
    if not geofence:
        return jsonify({'error': '地理围栏不存在'}), 404
    
    geofence.is_enabled = not geofence.is_enabled
    from models.database import db
    db.session.commit()
    
    return jsonify({
        'message': f'地理围栏已{"启用" if geofence.is_enabled else "禁用"}',
        'is_enabled': geofence.is_enabled
    })


# ========================================================================
# 地理围栏告警
# ========================================================================

@geofence_bp.route('/alerts', methods=['GET'])
@login_required
def get_alerts():
    """获取地理围栏告警"""
    geofence_id = request.args.get('geofence_id', type=int)
    device_id = request.args.get('device_id', type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = request.args.get('limit', 100, type=int)
    
    alerts = GeofenceService.get_alerts(
        current_user.id, geofence_id, device_id, unread_only, limit
    )
    
    return jsonify({
        'alerts': [a.to_dict() for a in alerts],
        'count': len(alerts)
    })


@geofence_bp.route('/alerts/<int:alert_id>/read', methods=['POST'])
@login_required
def mark_alert_read(alert_id):
    """标记告警为已读"""
    success = GeofenceService.mark_alert_read(alert_id, current_user.id)
    
    if not success:
        return jsonify({'error': '告警不存在'}), 404
    
    return jsonify({'message': '告警已标记为已读'})


@geofence_bp.route('/alerts/read-all', methods=['POST'])
@login_required
def mark_all_alerts_read():
    """标记所有告警为已读"""
    from models.database import GeofenceAlert
    GeofenceAlert.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    from models.database import db
    db.session.commit()
    
    return jsonify({'message': '所有告警已标记为已读'})


# ========================================================================
# 围栏检查
# ========================================================================

@geofence_bp.route('/check', methods=['POST'])
@login_required
def check_geofence():
    """检查设备是否在围栏内"""
    data = request.get_json()
    
    if not data or not all(k in data for k in ['device_id', 'latitude', 'longitude']):
        return jsonify({'error': '缺少必填字段'}), 400
    
    try:
        alerts = GeofenceService.check_device_in_geofence(
            device_id=data['device_id'],
            lat=data['latitude'],
            lng=data['longitude'],
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'alert_count': len(alerts)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================================================================
# 轨迹追踪
# ========================================================================

@geofence_bp.route('/tracks', methods=['POST'])
@login_required
def add_track_point():
    """添加轨迹点"""
    data = request.get_json()
    
    if not data or not all(k in data for k in ['device_id', 'latitude', 'longitude']):
        return jsonify({'error': '缺少必填字段'}), 400
    
    try:
        recorded_at = None
        if data.get('recorded_at'):
            recorded_at = datetime.fromisoformat(data['recorded_at'].replace('Z', '+00:00'))
        
        track_point = TrackService.add_track_point(
            device_id=data['device_id'],
            user_id=current_user.id,
            latitude=data['latitude'],
            longitude=data['longitude'],
            altitude=data.get('altitude'),
            speed=data.get('speed'),
            heading=data.get('heading'),
            accuracy=data.get('accuracy'),
            recorded_at=recorded_at,
            metadata=data.get('metadata')
        )
        
        return jsonify({
            'message': '轨迹点添加成功',
            'track_point': track_point.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@geofence_bp.route('/tracks/<int:device_id>', methods=['GET'])
@login_required
def get_track(device_id):
    """获取设备轨迹"""
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    limit = request.args.get('limit', 1000, type=int)
    
    start_dt = None
    end_dt = None
    
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    track_points = TrackService.get_track(device_id, current_user.id, start_dt, end_dt, limit)
    
    return jsonify({
        'track_points': [tp.to_dict() for tp in track_points],
        'count': len(track_points)
    })


@geofence_bp.route('/tracks/<int:device_id>/latest', methods=['GET'])
@login_required
def get_latest_position(device_id):
    """获取设备最新位置"""
    track_point = TrackService.get_latest_position(device_id, current_user.id)
    
    if not track_point:
        return jsonify({'error': '没有位置数据'}), 404
    
    return jsonify({'position': track_point.to_dict()})


@geofence_bp.route('/tracks/<int:device_id>/statistics', methods=['GET'])
@login_required
def get_track_statistics(device_id):
    """获取轨迹统计信息"""
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    start_dt = None
    end_dt = None
    
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    stats = TrackService.get_track_statistics(device_id, current_user.id, start_dt, end_dt)
    
    return jsonify({'statistics': stats})


@geofence_bp.route('/tracks/cleanup', methods=['POST'])
@login_required
def cleanup_tracks():
    """清理旧轨迹数据"""
    data = request.get_json() or {}
    days = data.get('days', 30)
    
    deleted_count = TrackService.cleanup_old_tracks(days)
    
    return jsonify({
        'message': f'已清理 {deleted_count} 条旧轨迹数据',
        'deleted_count': deleted_count
    })
