"""
Dashboard API - 增强版仪表盘数据接口
提供统计数据、实时数据流、趋势分析等功能
"""

import os
import time
import psutil
import socket
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import json

# 记录服务启动时间
_SERVICE_START_TIME = time.time()

dashboard_bp = Blueprint('dashboard_api', __name__)


@dashboard_bp.route('/api/dashboard/stats')
@login_required
def get_stats():
    """获取仪表盘统计数据"""
    from models.database import db, Device, SlaveChannel, DataPoint, AlarmRecord, User
    
    try:
        # 设备统计
        if current_user.is_admin:
            total_devices = Device.query.count()
            online_devices = Device.query.filter_by(is_online=True).count()
        else:
            total_devices = Device.query.filter_by(user_id=current_user.id).count()
            online_devices = Device.query.filter_by(user_id=current_user.id, is_online=True).count()
        
        offline_devices = total_devices - online_devices
        online_rate = round(online_devices / total_devices * 100, 1) if total_devices > 0 else 0
        
        # 数据点统计
        if current_user.is_admin:
            total_data_points = DataPoint.query.count()
            today_data_points = DataPoint.query.filter(
                DataPoint.timestamp >= datetime.now().replace(hour=0, minute=0, second=0)
            ).count()
        else:
            device_ids = [d.id for d in Device.query.filter_by(user_id=current_user.id).all()]
            channel_ids = [c.id for c in SlaveChannel.query.filter(SlaveChannel.device_id.in_(device_ids)).all()]
            total_data_points = DataPoint.query.filter(DataPoint.channel_id.in_(channel_ids)).count()
            today_data_points = DataPoint.query.filter(
                DataPoint.channel_id.in_(channel_ids),
                DataPoint.timestamp >= datetime.now().replace(hour=0, minute=0, second=0)
            ).count()
        
        # 报警统计
        if current_user.is_admin:
            total_alarms = AlarmRecord.query.filter_by(is_read=False).count()
            today_alarms = AlarmRecord.query.filter(
                AlarmRecord.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
            ).count()
        else:
            total_alarms = AlarmRecord.query.filter_by(user_id=current_user.id, is_read=False).count()
            today_alarms = AlarmRecord.query.filter(
                AlarmRecord.user_id == current_user.id,
                AlarmRecord.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
            ).count()
        
        # 用户统计（仅管理员）
        user_stats = None
        if current_user.is_admin:
            user_stats = {
                'total': User.query.count(),
                'active': User.query.filter_by(is_active=True).count(),
                'tcp_enabled': User.query.filter_by(storage_enabled=True).count()
            }
        
        return jsonify({
            'success': True,
            'data': {
                # 扁平化数据格式，便于前端直接使用
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': offline_devices,
                'online_rate': online_rate,
                'total_alarms': total_alarms,
                'unhandled_alarms': total_alarms,  # 未处理告警 = 未读告警
                'active_rules': 0,  # TODO: 从规则表统计
                'data_points_today': today_data_points,
                # 保留原有嵌套格式（兼容）
                'devices': {
                    'total': total_devices,
                    'online': online_devices,
                    'offline': offline_devices,
                    'online_rate': online_rate
                },
                'data_points': {
                    'total': total_data_points,
                    'today': today_data_points
                },
                'alarms': {
                    'unread': total_alarms,
                    'today': today_alarms
                },
                'users': user_stats
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取统计数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/system-info')
@login_required
def get_system_info():
    """获取系统信息（运行时长、TCP/WS连接、CPU/内存使用率）"""
    try:
        # 运行时长
        uptime_seconds = int(time.time() - _SERVICE_START_TIME)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        if days > 0:
            uptime_str = f"{days}天{hours}小时"
        elif hours > 0:
            uptime_str = f"{hours}小时{minutes}分钟"
        else:
            uptime_str = f"{minutes}分钟"

        # CPU和内存
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        mem_percent = memory.percent

        # TCP连接数
        tcp_connections = 0
        ws_connections = 0
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'ESTABLISHED':
                    if conn.type == socket.SOCK_STREAM:
                        tcp_connections += 1
        except (psutil.AccessDenied, OSError):
            pass

        # 从全局变量获取WS连接数
        try:
            from app import ws_connection_count
            ws_connections = ws_connection_count
        except (ImportError, AttributeError):
            ws_connections = 0

        return jsonify({
            'success': True,
            'data': {
                'uptime': uptime_str,
                'uptime_seconds': uptime_seconds,
                'tcp_connections': tcp_connections,
                'ws_connections': ws_connections,
                'cpu_percent': round(cpu_percent, 1),
                'mem_percent': round(mem_percent, 1)
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取系统信息失败: {e}")
        return jsonify({
            'success': True,
            'data': {
                'uptime': '0分钟',
                'uptime_seconds': 0,
                'tcp_connections': 0,
                'ws_connections': 0,
                'cpu_percent': 0,
                'mem_percent': 0
            }
        })
    """获取数据趋势（24小时）"""
    from models.database import db, Device, SlaveChannel, DataPoint
    
    try:
        hours = request.args.get('hours', 24, type=int)
        device_id = request.args.get('device_id', type=int)
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 构建查询 - 兼容MySQL和SQLite
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        
        if 'mysql' in str(db_uri).lower():
            # MySQL 使用 DATE_FORMAT
            query = db.session.query(
                func.date_format(DataPoint.timestamp, '%Y-%m-%d %H:00').label('hour'),
                func.count(DataPoint.id).label('count')
            ).filter(DataPoint.timestamp >= start_time)
        else:
            # SQLite 使用 strftime
            query = db.session.query(
                func.strftime('%Y-%m-%d %H:00', DataPoint.timestamp).label('hour'),
                func.count(DataPoint.id).label('count')
            ).filter(DataPoint.timestamp >= start_time)
        
        # 权限过滤
        if not current_user.is_admin:
            device_ids = [d.id for d in Device.query.filter_by(user_id=current_user.id).all()]
            channel_ids = [c.id for c in SlaveChannel.query.filter(SlaveChannel.device_id.in_(device_ids)).all()]
            query = query.filter(DataPoint.channel_id.in_(channel_ids))
        
        # 设备过滤
        if device_id:
            channel_ids = [c.id for c in SlaveChannel.query.filter_by(device_id=device_id).all()]
            query = query.filter(DataPoint.channel_id.in_(channel_ids))
        
        query = query.group_by('hour').order_by('hour')
        
        results = query.all()
        
        # 构建返回数据 - 适配前端期望格式
        timestamps = []
        data_points = []
        alarms = []  # TODO: 从告警表统计
        
        for row in results:
            timestamps.append(row.hour)
            data_points.append(row.count)
            alarms.append(0)  # 暂时填充0
        
        return jsonify({
            'success': True,
            'data': {
                'timestamps': timestamps,
                'data_points': data_points,
                'alarms': alarms
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取趋势数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/recent-data')
@login_required
def get_recent_data():
    """获取最新数据"""
    from models.database import db, Device, SlaveChannel, DataPoint
    
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # 构建查询
        query = DataPoint.query.join(SlaveChannel).join(Device)
        
        # 权限过滤
        if not current_user.is_admin:
            query = query.filter(Device.user_id == current_user.id)
        
        query = query.order_by(desc(DataPoint.timestamp)).limit(limit)
        
        results = query.all()
        
        # 构建返回数据
        data_list = []
        for dp in results:
            data_list.append({
                'id': dp.id,
                'device_name': dp.channel.device.name if dp.channel and dp.channel.device else None,
                'channel_name': dp.channel.name if dp.channel else None,
                'data_key': dp.name,
                'data_value': dp.value,
                'timestamp': dp.timestamp.strftime('%Y-%m-%d %H:%M:%S') if dp.timestamp else None
            })
        
        return jsonify({
            'success': True,
            'data': data_list
        })
    except Exception as e:
        current_app.logger.error(f"获取最新数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/device-ranking')
@login_required
def get_device_ranking():
    """获取设备数据量排行"""
    from models.database import db, Device, SlaveChannel, DataPoint
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # 查询每个设备的数据量
        query = db.session.query(
            Device.id,
            Device.name,
            Device.is_online,
            func.count(DataPoint.id).label('data_count')
        ).select_from(Device).outerjoin(SlaveChannel).outerjoin(DataPoint)
        
        # 权限过滤
        if not current_user.is_admin:
            query = query.filter(Device.user_id == current_user.id)
        
        query = query.group_by(Device.id).order_by(desc('data_count')).limit(limit)
        
        results = query.all()
        
        # 构建返回数据
        ranking = []
        for row in results:
            ranking.append({
                'device_id': row.id,
                'device_name': row.name,
                'is_online': row.is_online,
                'data_count': row.data_count
            })
        
        return jsonify({
            'success': True,
            'data': ranking
        })
    except Exception as e:
        current_app.logger.error(f"获取设备排行失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/recent-alarms')
@login_required
def get_recent_alarms():
    """获取最新报警"""
    from models.database import db, AlarmRecord
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # 构建查询 - AlarmRecord使用device_name字段而非device关系
        query = AlarmRecord.query
        
        # 权限过滤
        if not current_user.is_admin:
            query = query.filter(AlarmRecord.user_id == current_user.id)
        
        query = query.order_by(desc(AlarmRecord.created_at)).limit(limit)
        
        results = query.all()
        
        # 构建返回数据
        alarms = []
        for alarm in results:
            alarms.append({
                'id': alarm.id,
                'device_name': alarm.device_name,
                'channel_name': alarm.channel_name,
                'severity': alarm.severity,
                'message': alarm.message,
                'value': alarm.value,
                'threshold': alarm.threshold,
                'is_read': alarm.is_read,
                'is_handled': alarm.is_handled,
                'created_at': alarm.created_at.strftime('%Y-%m-%d %H:%M:%S') if alarm.created_at else None
            })
        
        return jsonify({
            'success': True,
            'data': alarms
        })
    except Exception as e:
        current_app.logger.error(f"获取最新报警失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/active-devices')
@login_required
def get_active_devices():
    """获取活跃设备列表"""
    from models.database import db, Device, SlaveChannel, DataPoint
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # 获取有数据的设备
        query = db.session.query(
            Device.id, Device.name, Device.device_type, Device.is_online,
            Device.location_name, Device.last_seen_at,
            func.count(DataPoint.id).label('data_count'),
            func.max(DataPoint.timestamp).label('last_data_time')
        ).join(SlaveChannel, SlaveChannel.device_id == Device.id
        ).join(DataPoint, DataPoint.channel_id == SlaveChannel.id
        ).group_by(Device.id
        ).order_by(desc('last_data_time')
        ).limit(limit)
        
        if not current_user.is_admin:
            query = query.filter(Device.user_id == current_user.id)
        
        results = query.all()
        
        devices = []
        for row in results:
            devices.append({
                'id': row.id,
                'name': row.name,
                'device_type': row.device_type or '未知',
                'is_online': row.is_online,
                'location_name': row.location_name or '-',
                'last_seen_at': row.last_seen_at.strftime('%Y-%m-%d %H:%M:%S') if row.last_seen_at else '-',
                'last_data_time': row.last_data_time.strftime('%Y-%m-%d %H:%M:%S') if row.last_data_time else '-',
                'data_count': row.data_count
            })
        
        return jsonify({
            'success': True,
            'data': devices
        })
    except Exception as e:
        current_app.logger.error(f"获取活跃设备失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/realtime-stream')
@login_required
def realtime_stream():
    """SSE实时数据流"""
    from flask import Response
    import queue
    
    def event_stream():
        # 获取用户的设备ID列表
        from models.database import Device
        if current_user.is_admin:
            device_ids = [d.id for d in Device.query.all()]
        else:
            device_ids = [d.id for d in Device.query.filter_by(user_id=current_user.id).all()]
        
        # 简单实现：轮询数据库
        last_id = 0
        while True:
            try:
                from models.database import DataPoint, SlaveChannel
                # 查询新数据
                new_data = DataPoint.query.join(SlaveChannel).filter(
                    SlaveChannel.device_id.in_(device_ids),
                    DataPoint.id > last_id
                ).order_by(DataPoint.id).limit(10).all()
                
                for dp in new_data:
                    last_id = dp.id
                    data = {
                        'id': dp.id,
                        'device_name': dp.channel.device.name if dp.channel and dp.channel.device else None,
                        'channel_name': dp.channel.name if dp.channel else None,
                        'data_key': dp.data_key,
                        'data_value': dp.data_value,
                        'timestamp': dp.timestamp.strftime('%Y-%m-%d %H:%M:%S') if dp.timestamp else None
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                
                # 发送心跳
                yield f": heartbeat\n\n"
                
                import time
                time.sleep(1)
            except GeneratorError:
                break
            except Exception as e:
                current_app.logger.error(f"SSE错误: {e}")
                break
    
    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


# ============= 设备分布接口 =============

@dashboard_bp.route('/api/dashboard/device-distribution', methods=['GET'])
@login_required
def device_distribution():
    """设备类型分布和地域分布"""
    from sqlalchemy import func as sqlfunc
    from models.database import Device

    # 按类型统计
    type_stats = db.session.query(
        Device.device_type, sqlfunc.count(Device.id)
    ).group_by(Device.device_type).all()

    type_dist = [{'name': t or '未分类', 'value': c} for t, c in type_stats]

    # 按地域统计（location_name 字段）
    region_stats = db.session.query(
        Device.location_name, sqlfunc.count(Device.id)
    ).group_by(Device.location_name).all()

    region_dist = [{'name': r or '未分配', 'value': c} for r, c in region_stats]

    # 按状态统计
    online_count = Device.query.filter_by(is_online=True).count()
    offline_count = Device.query.filter_by(is_online=False).count()

    return jsonify({
        'success': True,
        'data': {
            'by_type': type_dist,
            'by_region': region_dist,
            'by_status': [
                {'name': '在线', 'value': online_count},
                {'name': '离线', 'value': offline_count}
            ]
        }
    })


# ============= 系统信息接口 =============

@dashboard_bp.route('/api/dashboard/system-info', methods=['GET'])
@login_required
def system_info():
    """系统运行时信息"""
    import os
    import time
    import psutil

    # 进程启动时间
    proc = psutil.Process(os.getpid())
    create_time = proc.create_time()
    uptime_seconds = int(time.time() - create_time)

    # 转换为可读格式
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        uptime_human = f"{days}天{hours}时{minutes}分"
    elif hours > 0:
        uptime_human = f"{hours}时{minutes}分{seconds}秒"
    else:
        uptime_human = f"{minutes}分{seconds}秒"

    # CPU和内存
    cpu_usage = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    memory_usage = mem.percent

    # TCP连接数（尝试统计psutil中所有ESTABLISHED连接）
    tcp_count = 0
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'ESTABLISHED':
                tcp_count += 1
    except (psutil.AccessDenied, Exception):
        tcp_count = 0

    # WS连接数（从全局状态获取，如果存在的话）
    ws_count = 0
    try:
        from flask import current_app
        # 尝试从socketio获取
        if hasattr(current_app, 'socketio_clients'):
            ws_count = len(current_app.socketio_clients)
        else:
            # 模拟数据：基于活跃设备数估算
            from models.database import Device
            ws_count = Device.query.filter_by(is_online=True).count()
    except Exception:
        ws_count = 0

    return jsonify({
        'success': True,
        'data': {
            'uptime': uptime_human,
            'uptime_seconds': uptime_seconds,
            'tcp_connections': tcp_count,
            'ws_connections': ws_count,
            'cpu_usage': round(cpu_usage, 1),
            'memory_usage': round(memory_usage, 1),
            'memory_total_gb': round(mem.total / (1024**3), 2),
            'memory_used_gb': round(mem.used / (1024**3), 2)
        }
    })


# ============= 趋势数据接口 =============

@dashboard_bp.route('/api/dashboard/trend', methods=['GET'])
@login_required
def get_trend():
    """获取数据趋势（按小时聚合）"""
    from sqlalchemy import func
    from models.database import db, DataPoint, AlarmRecord
    from datetime import datetime, timedelta

    try:
        hours = int(request.args.get('hours', 24))
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)

        # 数据点按小时聚合
        data_query = db.session.query(
            func.strftime('%Y-%m-%d %H:00', DataPoint.timestamp).label('hour'),
            func.count(DataPoint.id).label('count')
        ).filter(DataPoint.timestamp >= start_time).group_by('hour').all()

        # 告警按小时聚合
        alarm_query = db.session.query(
            func.strftime('%Y-%m-%d %H:00', AlarmRecord.created_at).label('hour'),
            func.count(AlarmRecord.id).label('count')
        ).filter(AlarmRecord.created_at >= start_time).group_by('hour').all()

        # 构建完整时间序列
        data_dict = {h: c for h, c in data_query}
        alarm_dict = {h: c for h, c in alarm_query}

        timestamps = []
        data_points = []
        alarms = []

        for i in range(hours):
            t = now - timedelta(hours=hours - i - 1)
            hour_key = t.strftime('%Y-%m-%d %H:00')
            label = t.strftime('%m-%d %H:00')
            timestamps.append(label)
            data_points.append(data_dict.get(hour_key, 0))
            alarms.append(alarm_dict.get(hour_key, 0))

        return jsonify({
            'success': True,
            'data': {
                'timestamps': timestamps,
                'hours': timestamps,
                'data_points': data_points,
                'alarms': alarms,
                'values': data_points
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取趋势数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============= 设备分布接口(修复版) =============

@dashboard_bp.route('/api/dashboard/device-distribution-v2', methods=['GET'])
@login_required
def device_distribution_v2():
    """设备类型分布和地域分布"""
    from sqlalchemy import func
    from models.database import db, Device
    from flask_login import current_user

    try:
        # 按类型统计
        type_stats = db.session.query(
            Device.device_type, func.count(Device.id)
        ).filter(Device.user_id == current_user.id).group_by(Device.device_type).all()

        type_dist = [{'name': t or '未分类', 'value': c} for t, c in type_stats]

        # 按地域统计
        region_stats = db.session.query(
            Device.location_name, func.count(Device.id)
        ).filter(Device.user_id == current_user.id).group_by(Device.location_name).all()

        region_dist = [{'name': r or '未分配', 'value': c} for r, c in region_stats]

        # 按状态统计
        online_count = Device.query.filter_by(user_id=current_user.id, is_online=True).count()
        offline_count = Device.query.filter_by(user_id=current_user.id, is_online=False).count()

        return jsonify({
            'success': True,
            'data': {
                'by_type': type_dist,
                'by_region': region_dist,
                'by_status': [
                    {'name': '在线', 'value': online_count},
                    {'name': '离线', 'value': offline_count}
                ]
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取设备分布失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
