"""
Dashboard API - 增强版仪表盘数据接口
提供统计数据、实时数据流、趋势分析等功能
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import json

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


@dashboard_bp.route('/api/dashboard/trend')
@login_required
def get_trend():
    """获取数据趋势（24小时）"""
    from models.database import db, Device, SlaveChannel, DataPoint
    
    try:
        hours = request.args.get('hours', 24, type=int)
        device_id = request.args.get('device_id', type=int)
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 构建查询
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
        
        # 构建返回数据
        trend_data = []
        for row in results:
            trend_data.append({
                'time': row.hour,
                'count': row.count
            })
        
        return jsonify({
            'success': True,
            'data': trend_data
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
                'data_key': dp.data_key,
                'data_value': dp.data_value,
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
    from models.database import db, Device, Alarm
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # 构建查询
        query = Alarm.query.join(Device)
        
        # 权限过滤
        if not current_user.is_admin:
            query = query.filter(Device.user_id == current_user.id)
        
        query = query.order_by(desc(Alarm.created_at)).limit(limit)
        
        results = query.all()
        
        # 构建返回数据
        alarms = []
        for alarm in results:
            alarms.append({
                'id': alarm.id,
                'device_name': alarm.device.name if alarm.device else None,
                'alarm_type': alarm.alarm_type,
                'alarm_level': alarm.alarm_level,
                'message': alarm.message,
                'is_read': alarm.is_read,
                'created_at': alarm.created_at.strftime('%Y-%m-%d %H:%M:%S') if alarm.created_at else None
            })
        
        return jsonify({
            'success': True,
            'data': alarms
        })
    except Exception as e:
        current_app.logger.error(f"获取最新报警失败: {e}")
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
