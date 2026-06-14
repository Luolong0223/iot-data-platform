from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func

from models.database import db, Device, SlaveChannel, DataPoint

devices_bp = Blueprint('devices', __name__, url_prefix='/api/devices')


@devices_bp.route('', methods=['GET'])
@login_required
def list_devices():
    from services.cache import get_cache, make_key
    from utils.perf import paginated_response
    cache = get_cache()
    # 分页参数
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        size = min(100, max(1, int(request.args.get('size', 20))))
    except (ValueError, TypeError):
        size = 20
    # 仅第一页缓存（避免缓存膨胀）
    cache_key = make_key('devices_list', current_user.id, page, size) if page == 1 else None
    if cache_key:
        cached = cache.get(cache_key)
        if cached is not None:
            cached['_cached'] = True
            return jsonify(cached)
    base = Device.query.filter_by(user_id=current_user.id)
    # 轻量字段
    items, meta = paginated_response_lambda(base, page, size)
    data = [d.to_dict() for d in items]
    result = {'success': True, 'devices': data, 'meta': meta}
    if cache_key:
        try:
            cache.set(cache_key, {**result}, ttl=20)
        except Exception:
            pass
    return jsonify(result)


def paginated_response_lambda(query, page, size):
    from sqlalchemy.orm import Query
    total = query.count()
    items = query.limit(size).offset((page - 1) * size).all()
    pages = (total + size - 1) // size if size else 1
    return items, {'page': page, 'size': size, 'total': total, 'pages': pages,
                   'has_next': page < pages, 'has_prev': page > 1}


@devices_bp.route('', methods=['POST'])
@login_required
def create_device():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Device name is required'}), 400

    existing = Device.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({'success': False, 'message': 'Device name already exists'}), 409

    device = Device(
        user_id=current_user.id,
        name=name,
        voltage_mv=data.get('voltage_mv')
    )
    db.session.add(device)
    db.session.commit()

    # 失效设备列表缓存
    from services.cache import invalidate, make_key
    invalidate(make_key('devices_list', current_user.id) + '*')

    return jsonify({'success': True, 'device': device.to_dict()}), 201


@devices_bp.route('/<int:device_id>', methods=['PUT'])
@login_required
def update_device(device_id):
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    if 'name' in data:
        new_name = data['name'].strip()
        if new_name and new_name != device.name:
            existing = Device.query.filter_by(user_id=current_user.id, name=new_name).first()
            if existing:
                return jsonify({'success': False, 'message': 'Device name already exists'}), 409
            device.name = new_name

    if 'voltage_mv' in data:
        device.voltage_mv = data['voltage_mv']

    db.session.commit()
    from services.cache import invalidate, make_key
    invalidate(make_key('devices_list', current_user.id) + '*')
    return jsonify({'success': True, 'device': device.to_dict()})


@devices_bp.route('/<int:device_id>', methods=['DELETE'])
@login_required
def delete_device(device_id):
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    db.session.delete(device)
    db.session.commit()
    from services.cache import invalidate, make_key
    invalidate(make_key('devices_list', current_user.id) + '*')
    return jsonify({'success': True, 'message': 'Device deleted'})


@devices_bp.route('/<int:device_id>/location', methods=['POST'])
@login_required
def set_location(device_id):
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    latitude = data.get('latitude')
    longitude = data.get('longitude')
    location_name = data.get('location_name', '').strip()

    if latitude is not None:
        try:
            device.latitude = float(latitude)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid latitude'}), 400

    if longitude is not None:
        try:
            device.longitude = float(longitude)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid longitude'}), 400

    if location_name:
        device.location_name = location_name

    db.session.commit()
    return jsonify({'success': True, 'device': device.to_dict()})


@devices_bp.route('/<int:device_id>', methods=['GET'])
@login_required
def get_device(device_id):
    """获取设备详情"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    # 获取通道信息
    channels = SlaveChannel.query.filter_by(device_id=device.id).all()
    channels_data = []
    
    for channel in channels:
        # 获取最新数据点
        latest_data = DataPoint.query.filter_by(channel_id=channel.id)\
            .order_by(DataPoint.timestamp.desc()).first()
        
        channels_data.append({
            'id': channel.id,
            'name': channel.name,
            'online': channel.online,
            'data_points_count': DataPoint.query.filter_by(channel_id=channel.id).count(),
            'latest_data': latest_data.to_dict() if latest_data else None
        })

    # 获取今日数据量
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_count = db.session.query(func.count(DataPoint.id))\
        .join(SlaveChannel)\
        .filter(SlaveChannel.device_id == device.id)\
        .filter(DataPoint.timestamp >= today_start)\
        .scalar() or 0

    return jsonify({
        'success': True,
        'device': device.to_dict(),
        'channels': channels_data,
        'stats': {
            'channels_count': len(channels),
            'online_channels': sum(1 for c in channels if c.online),
            'today_data_count': today_count
        }
    })


@devices_bp.route('/<int:device_id>/data', methods=['GET'])
@login_required
def get_device_data(device_id):
    """获取设备历史数据"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    # 获取参数
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 1000, type=int)
    channel_id = request.args.get('channel_id', type=int)

    # 计算时间范围
    start_time = datetime.utcnow() - timedelta(hours=hours)

    # 查询数据
    query = db.session.query(DataPoint, SlaveChannel.name)\
        .join(SlaveChannel)\
        .filter(SlaveChannel.device_id == device.id)\
        .filter(DataPoint.timestamp >= start_time)

    if channel_id:
        query = query.filter(DataPoint.channel_id == channel_id)

    query = query.order_by(DataPoint.timestamp.desc()).limit(limit)

    results = query.all()

    data = []
    for dp, channel_name in results:
        data.append({
            'id': dp.id,
            'channel_name': channel_name,
            'data_key': dp.name,
            'data_value': dp.value,
            'timestamp': dp.timestamp.isoformat() if dp.timestamp else None
        })

    return jsonify({
        'success': True,
        'device_id': device_id,
        'data': data,
        'count': len(data)
    })


@devices_bp.route('/<int:device_id>/stats', methods=['GET'])
@login_required
def get_device_stats(device_id):
    """获取设备统计数据"""
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    # 时间范围
    hours = request.args.get('hours', 24, type=int)
    start_time = datetime.utcnow() - timedelta(hours=hours)

    # 按小时统计数据量
    hourly_stats = db.session.query(
        func.strftime('%Y-%m-%d %H:00', DataPoint.timestamp).label('hour'),
        func.count(DataPoint.id).label('count')
    ).join(SlaveChannel)\
     .filter(SlaveChannel.device_id == device.id)\
     .filter(DataPoint.timestamp >= start_time)\
     .group_by('hour')\
     .order_by('hour')\
     .all()

    return jsonify({
        'success': True,
        'hourly_stats': [{'time': h, 'count': c} for h, c in hourly_stats]
    })


@devices_bp.route('/batch-delete', methods=['POST'])
@login_required
def batch_delete_devices():
    """批量删除设备"""
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({'success': False, 'message': 'Missing device IDs'}), 400

    ids = data.get('ids', [])
    if not ids:
        return jsonify({'success': False, 'message': 'No device IDs provided'}), 400

    deleted = 0
    for device_id in ids:
        device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
        if device:
            db.session.delete(device)
            deleted += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Deleted {deleted} devices',
        'deleted_count': deleted
    })


@devices_bp.route('/with-location', methods=['GET'])
@login_required
def get_devices_with_location():
    """获取有位置的设备列表（用于地图）"""
    devices = Device.query.filter_by(user_id=current_user.id)\
        .filter(Device.latitude.isnot(None))\
        .filter(Device.longitude.isnot(None))\
        .all()

    return jsonify({
        'success': True,
        'devices': [d.to_dict() for d in devices]
    })
