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