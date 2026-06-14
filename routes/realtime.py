# -*- coding: utf-8 -*-
"""
实时数据流路由
提供SSE实时数据推送、数据流历史查询等功能
"""

import json
import time
import threading
from datetime import datetime, timedelta
from collections import deque

from flask import Blueprint, Response, stream_with_context, request, jsonify
from flask_login import login_required, current_user

from models.database import db, Device, SlaveChannel, DataPoint, AlarmRecord

realtime_bp = Blueprint('realtime', __name__, url_prefix='/api/realtime')

# 全局数据流缓存（每个用户最近100条）
data_stream_cache = {}
data_stream_lock = threading.Lock()

# SSE客户端管理
sse_clients = {}
sse_lock = threading.Lock()


def add_to_stream(user_id, data):
    """添加数据到用户的数据流缓存"""
    with data_stream_lock:
        if user_id not in data_stream_cache:
            data_stream_cache[user_id] = deque(maxlen=100)
        data_stream_cache[user_id].append({
            'timestamp': datetime.now().isoformat(),
            'data': data
        })


def get_stream_history(user_id, limit=50):
    """获取用户的数据流历史"""
    with data_stream_lock:
        if user_id in data_stream_cache:
            return list(data_stream_cache[user_id])[-limit:]
    return []


def register_sse_client(user_id):
    """注册SSE客户端"""
    client = {
        'user_id': user_id,
        'queue': [],
        'event': threading.Event(),
        'connected': True
    }
    with sse_lock:
        if user_id not in sse_clients:
            sse_clients[user_id] = []
        sse_clients[user_id].append(client)
    return client


def unregister_sse_client(client):
    """注销SSE客户端"""
    with sse_lock:
        if client['user_id'] in sse_clients:
            try:
                sse_clients[client['user_id']].remove(client)
            except ValueError:
                pass


def push_to_user(user_id, data):
    """推送数据给指定用户的所有SSE客户端"""
    with sse_lock:
        if user_id in sse_clients:
            for client in sse_clients[user_id]:
                client['queue'].append(data)
                client['event'].set()


@realtime_bp.route('/stream')
@login_required
def stream():
    """SSE实时数据流"""
    user_id = current_user.id
    client = register_sse_client(user_id)

    def generate():
        try:
            # 发送连接成功消息
            yield 'data: ' + json.dumps({
                'type': 'connected',
                'timestamp': datetime.now().isoformat()
            }) + '\n\n'

            # 发送最近的历史数据
            history = get_stream_history(user_id, 20)
            for item in reversed(history):
                yield 'data: ' + json.dumps({
                    'type': 'history',
                    'timestamp': item['timestamp'],
                    'data': item['data']
                }) + '\n\n'

            # 持续推送新数据
            while True:
                # 等待新数据，超时30秒发送心跳
                if client['event'].wait(timeout=30):
                    pending = list(client['queue'])
                    client['queue'].clear()
                    client['event'].clear()
                    for data in pending:
                        yield 'data: ' + json.dumps(data) + '\n\n'
                else:
                    # 发送心跳
                    yield 'data: ' + json.dumps({
                        'type': 'heartbeat',
                        'timestamp': datetime.now().isoformat()
                    }) + '\n\n'
        except GeneratorExit:
            pass
        finally:
            unregister_sse_client(client)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@realtime_bp.route('/history')
@login_required
def history():
    """获取实时数据流历史"""
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 100)
    
    history = get_stream_history(current_user.id, limit)
    return jsonify({
        'success': True,
        'data': history,
        'count': len(history)
    })


@realtime_bp.route('/stats')
@login_required
def stats():
    """获取实时统计数据"""
    user_id = current_user.id
    
    # 设备统计
    devices = Device.query.filter_by(user_id=user_id).all()
    total_devices = len(devices)
    online_devices = sum(1 for d in devices if d.is_online)
    
    # 通道统计
    device_ids = [d.id for d in devices]
    channels = SlaveChannel.query.filter(SlaveChannel.device_id.in_(device_ids)).all() if device_ids else []
    total_channels = len(channels)
    online_channels = sum(1 for c in channels if c.online)
    
    # 今日数据量
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = DataPoint.query.filter(
        DataPoint.channel_id.in_([c.id for c in channels]) if channels else False,
        DataPoint.timestamp >= today
    ).count() if channels else 0
    
    # 今日报警数
    alarm_count = AlarmRecord.query.filter(
        AlarmRecord.user_id == user_id,
        AlarmRecord.created_at >= today
    ).count()
    
    # 数据速率（最近1分钟）
    one_min_ago = datetime.now() - timedelta(minutes=1)
    rate = DataPoint.query.filter(
        DataPoint.channel_id.in_([c.id for c in channels]) if channels else False,
        DataPoint.timestamp >= one_min_ago
    ).count() if channels else 0
    
    return jsonify({
        'success': True,
        'data': {
            'devices': {
                'total': total_devices,
                'online': online_devices,
                'offline': total_devices - online_devices,
                'online_rate': round(online_devices / total_devices * 100, 1) if total_devices > 0 else 0
            },
            'channels': {
                'total': total_channels,
                'online': online_channels,
                'offline': total_channels - online_channels
            },
            'data': {
                'today': today_count,
                'rate_per_min': rate
            },
            'alarms': {
                'today': alarm_count
            }
        }
    })


@realtime_bp.route('/trend')
@login_required
def trend():
    """获取数据趋势（支持指定数据点）"""
    period = request.args.get('period', '24h')
    channel_id = request.args.get('channel_id', type=int)
    point_name = request.args.get('point_name')
    user_id = current_user.id
    
    # 确定时间范围
    now = datetime.now()
    if period == '7d':
        start = now - timedelta(days=7)
    elif period == '30d':
        start = now - timedelta(days=30)
    else:  # 24h
        start = now - timedelta(hours=24)
    
    # 如果指定了具体数据点，查询该点的数值趋势
    if channel_id and point_name:
        points = DataPoint.query.filter(
            DataPoint.channel_id == channel_id,
            DataPoint.name == point_name,
            DataPoint.timestamp >= start
        ).order_by(DataPoint.timestamp).all()
        
        labels = [p.timestamp.strftime('%H:%M') if period == '24h' else p.timestamp.strftime('%m-%d %H:%M') for p in points]
        values = [p.value for p in points]
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values,
                'title': f'{point_name} 趋势'
            }
        })
    
    # 没有指定数据点，返回整体数据量趋势（原有逻辑）
    devices = Device.query.filter_by(user_id=user_id).all()
    device_ids = [d.id for d in devices]
    
    if not device_ids:
        return jsonify({
            'success': True,
            'data': {
                'labels': [],
                'values': [],
                'title': '数据趋势'
            }
        })
    
    channels = SlaveChannel.query.filter(SlaveChannel.device_id.in_(device_ids)).all()
    channel_ids = [c.id for c in channels]
    
    if not channel_ids:
        return jsonify({
            'success': True,
            'data': {
                'labels': [],
                'values': [],
                'title': '数据趋势'
            }
        })
    
    from sqlalchemy import func
    
    if period in ('7d', '30d'):
        day_format = '%Y-%m-%d' if period == '30d' else '%Y-%m-%d %H:00'
        query = db.session.query(
            func.strftime(day_format, DataPoint.timestamp).label('t'),
            func.count(DataPoint.id).label('count')
        ).filter(
            DataPoint.channel_id.in_(channel_ids),
            DataPoint.timestamp >= start
        ).group_by('t').order_by('t')
        
        results = query.all()
        labels = [r.t for r in results]
        values = [r.count for r in results]
    else:  # 24h
        query = db.session.query(
            func.strftime('%Y-%m-%d %H:00', DataPoint.timestamp).label('hour'),
            func.count(DataPoint.id).label('count')
        ).filter(
            DataPoint.channel_id.in_(channel_ids),
            DataPoint.timestamp >= start
        ).group_by('hour').order_by('hour')
        
        results = query.all()
        labels = [r.hour for r in results]
        values = [r.count for r in results]
    
    return jsonify({
        'success': True,
        'data': {
            'labels': labels,
            'values': values,
            'title': '数据趋势'
        }
    })


@realtime_bp.route('/latest')
@login_required
def latest():
    """获取最新数据"""
    user_id = current_user.id
    limit = request.args.get('limit', 20, type=int)
    limit = min(limit, 100)
    
    # 获取用户设备
    devices = Device.query.filter_by(user_id=user_id).all()
    device_ids = [d.id for d in devices]
    
    if not device_ids:
        return jsonify({
            'success': True,
            'data': []
        })
    
    # 获取通道
    channels = SlaveChannel.query.filter(SlaveChannel.device_id.in_(device_ids)).all()
    channel_map = {c.id: c for c in channels}
    device_map = {d.id: d for d in devices}
    
    if not channels:
        return jsonify({
            'success': True,
            'data': []
        })
    
    # 查询最新数据点
    latest_data = []
    for channel in channels:
        point = DataPoint.query.filter_by(channel_id=channel.id).order_by(DataPoint.timestamp.desc()).first()
        if point:
            device = device_map.get(channel.device_id)
            latest_data.append({
                'device_name': device.name if device else 'Unknown',
                'channel_name': channel.name,
                'data_point': point.data_point_name,
                'value': point.value,
                'timestamp': point.timestamp.isoformat()
            })
    
    # 按时间排序
    latest_data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({
        'success': True,
        'data': latest_data[:limit]
    })
