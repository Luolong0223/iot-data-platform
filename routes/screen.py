#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大屏数据API - 支持可选展示数据点
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import json

screen_bp = Blueprint('screen_api', __name__)


@screen_bp.route('/api/screen/data-points', methods=['GET'])
@login_required
def get_data_points():
    """获取用户所有的设备/通道/数据点树形结构"""
    from models.database import db, Device, SlaveChannel, DataPoint

    device_id = request.args.get('device_id', type=int)

    try:
        query = Device.query.filter_by(user_id=current_user.id)
        if device_id:
            query = query.filter_by(id=device_id)
        devices = query.all()

        result = []
        for device in devices:
            channels = SlaveChannel.query.filter_by(device_id=device.id).all()
            channel_list = []
            for ch in channels:
                # 获取该通道最近10个数据点名称（去重）
                points = db.session.query(
                    DataPoint.name, func.count(DataPoint.id).label('count')
                ).filter(
                    DataPoint.channel_id == ch.id
                ).group_by(DataPoint.name).order_by(desc('count')).limit(20).all()

                point_list = [{'name': p.name, 'count': p.count} for p in points]

                # 获取最新值
                latest = DataPoint.query.filter_by(channel_id=ch.id)\
                    .order_by(DataPoint.timestamp.desc()).first()
                latest_value = latest.value if latest else None
                latest_time = latest.timestamp.isoformat() if latest and latest.timestamp else None

                channel_list.append({
                    'id': ch.id,
                    'name': ch.name,
                    'online': ch.online if hasattr(ch, 'online') else True,
                    'points': point_list,
                    'latest_value': latest_value,
                    'latest_time': latest_time
                })

            result.append({
                'id': device.id,
                'name': device.name,
                'is_online': device.is_online,
                'channels': channel_list
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        current_app.logger.error(f"获取数据点列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@screen_bp.route('/api/screen/selected-data', methods=['GET'])
@login_required
def get_selected_data():
    """获取选中数据点的最新数值"""
    from models.database import db, Device, SlaveChannel, DataPoint

    channel_id = request.args.get('channel_id', type=int)
    point_name = request.args.get('point_name')
    device_id = request.args.get('device_id', type=int)

    try:
        query = DataPoint.query

        if device_id:
            channels = SlaveChannel.query.filter_by(device_id=device_id).all()
            channel_ids = [c.id for c in channels]
            if channel_ids:
                query = query.filter(DataPoint.channel_id.in_(channel_ids))
        elif channel_id:
            query = query.filter_by(channel_id=channel_id)

        if point_name:
            query = query.filter_by(name=point_name)

        # 获取每个通道/数据点组合的最新值
        latest_records = query.order_by(
            DataPoint.channel_id, DataPoint.name, DataPoint.timestamp.desc()
        ).all()

        # 去重 - 每个channel+name组合取最新一条
        seen = set()
        data = []
        for dp in latest_records:
            key = (dp.channel_id, dp.name)
            if key not in seen:
                seen.add(key)
                ch = SlaveChannel.query.get(dp.channel_id)
                dev = Device.query.get(ch.device_id) if ch else None
                data.append({
                    'id': dp.id,
                    'device_id': dev.id if dev else None,
                    'device_name': dev.name if dev else None,
                    'channel_id': dp.channel_id,
                    'channel_name': ch.name if ch else None,
                    'point_name': dp.name,
                    'value': dp.value,
                    'timestamp': dp.timestamp.isoformat() if dp.timestamp else None
                })

        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"获取选中数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@screen_bp.route('/api/screen/saved-points', methods=['GET'])
@login_required
def get_saved_points():
    """获取用户已保存的选定数据点"""
    from models.database import ScreenSelectedPoint, Device, SlaveChannel, DataPoint

    try:
        saved = ScreenSelectedPoint.query.filter_by(user_id=current_user.id)\
            .order_by(ScreenSelectedPoint.created_at).all()

        result = []
        for sp in saved:
            # 查询最新值
            ch = SlaveChannel.query.get(sp.channel_id)
            latest = None
            if ch:
                latest = DataPoint.query.filter_by(channel_id=sp.channel_id, name=sp.point_name)\
                    .order_by(DataPoint.timestamp.desc()).first()

            result.append({
                'id': sp.id,
                'key': f"{sp.device_id}_{sp.channel_id}_{sp.point_name}",
                'device_id': sp.device_id,
                'device_name': sp.device_name,
                'channel_id': sp.channel_id,
                'channel_name': sp.channel_name,
                'point_name': sp.point_name,
                'value': latest.value if latest else '-',
                'timestamp': latest.timestamp.isoformat() if latest and latest.timestamp else None
            })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        current_app.logger.error(f"获取已保存数据点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@screen_bp.route('/api/screen/saved-points', methods=['POST'])
@login_required
def save_selected_point():
    """保存选定的数据点"""
    from models.database import db, ScreenSelectedPoint

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供数据'}), 400

        device_id = data.get('device_id')
        device_name = data.get('device_name')
        channel_id = data.get('channel_id')
        channel_name = data.get('channel_name')
        point_name = data.get('point_name')

        if not all([device_id, channel_id, point_name]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 检查是否已存在
        existing = ScreenSelectedPoint.query.filter_by(
            user_id=current_user.id,
            device_id=device_id,
            channel_id=channel_id,
            point_name=point_name
        ).first()

        if existing:
            return jsonify({'success': True, 'message': '已存在', 'id': existing.id})

        sp = ScreenSelectedPoint(
            user_id=current_user.id,
            device_id=device_id,
            device_name=device_name or '',
            channel_id=channel_id,
            channel_name=channel_name or '',
            point_name=point_name
        )
        db.session.add(sp)
        db.session.commit()

        return jsonify({'success': True, 'id': sp.id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"保存数据点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@screen_bp.route('/api/screen/saved-points/<int:point_id>', methods=['DELETE'])
@login_required
def delete_selected_point(point_id):
    """删除已保存的选定数据点"""
    from models.database import db, ScreenSelectedPoint

    try:
        sp = ScreenSelectedPoint.query.filter_by(
            id=point_id, user_id=current_user.id
        ).first()

        if not sp:
            return jsonify({'success': False, 'error': '数据点不存在'}), 404

        db.session.delete(sp)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除数据点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@screen_bp.route('/api/screen/point-trend')
@login_required
def get_point_trend():
    """获取指定数据点的历史趋势"""
    from models.database import db, DataPoint

    channel_id = request.args.get('channel_id', type=int)
    point_name = request.args.get('point_name')
    period = request.args.get('period', '1h')

    if not channel_id or not point_name:
        return jsonify({'success': False, 'error': '缺少参数 channel_id 和 point_name'}), 400

    try:
        now = datetime.now()
        if period == '1h':
            since = now - timedelta(hours=1)
            interval = 'minute'
        elif period == '6h':
            since = now - timedelta(hours=6)
            interval = '5min'
        elif period == '24h':
            since = now - timedelta(days=1)
            interval = '15min'
        elif period == '7d':
            since = now - timedelta(days=7)
            interval = 'hour'
        else:
            since = now - timedelta(hours=1)
            interval = 'minute'

        points = DataPoint.query.filter(
            DataPoint.channel_id == channel_id,
            DataPoint.name == point_name,
            DataPoint.timestamp >= since
        ).order_by(DataPoint.timestamp.asc()).all()

        labels = [p.timestamp.strftime('%H:%M') if p.timestamp else '' for p in points]
        values = [p.value for p in points]

        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values,
                'point_name': point_name,
                'channel_id': channel_id
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取数据点趋势失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500