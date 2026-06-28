"""
数据查看路由 - 历史数据查询
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import and_, desc
from models.database import db, Device, Channel, DataPoint, DataHistory

data_view_bp = Blueprint('data_view', __name__, url_prefix='/api/data')


# ================= 页面 =================
@data_view_bp.route('/')
@login_required
def page():
    return render_template('data_view.html')


# ================= API: 数据列表 =================
@data_view_bp.route('', methods=['GET'])
@login_required
def list_data():
    """获取历史数据,支持筛选+分页"""
    try:
        device_id = request.args.get('device_id', type=int)
        channel_id = request.args.get('channel_id', type=int)
        hours = request.args.get('hours', 24, type=int)
        page = request.args.get('page', 1, type=int)
        page_size = min(request.args.get('page_size', 20, type=int), 1000)

        # 起始时间
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except Exception:
                start_time = datetime.utcnow() - timedelta(hours=hours)
        else:
            start_time = datetime.utcnow() - timedelta(hours=hours)

        if end_time:
            try:
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except Exception:
                end_time = datetime.utcnow()
        else:
            end_time = datetime.utcnow()

        # 用户的所有设备 ID 列表
        user_device_ids = [d.id for d in Device.query.filter_by(user_id=current_user.id).all()]
        if not user_device_ids:
            return jsonify({'success': True, 'data': [], 'total': 0, 'page': page, 'page_size': page_size})

        q = DataHistory.query.filter(
            DataHistory.device_id.in_(user_device_ids),
            DataHistory.timestamp >= start_time,
            DataHistory.timestamp <= end_time
        )
        if device_id and device_id in user_device_ids:
            q = q.filter(DataHistory.device_id == device_id)
        if channel_id:
            q = q.filter(DataHistory.channel_id == channel_id)
        # 筛选特定数据点:用 data_point_id 传
        data_point_id = request.args.get('data_point_id', type=int)
        if data_point_id:
            q = q.filter(DataHistory.data_point_id == data_point_id)

        total = q.count()
        rows = q.order_by(desc(DataHistory.timestamp))\
            .offset((page - 1) * page_size).limit(page_size).all()

        dp_ids = list({r.data_point_id for r in rows if r.data_point_id})
        ch_ids = list({r.channel_id for r in rows if r.channel_id})
        dev_ids = list({r.device_id for r in rows if r.device_id})

        dp_map = {dp.id: dp for dp in DataPoint.query.filter(DataPoint.id.in_(dp_ids)).all()} if dp_ids else {}
        ch_map = {ch.id: ch for ch in Channel.query.filter(Channel.id.in_(ch_ids)).all()} if ch_ids else {}
        dev_map = {d.id: d for d in Device.query.filter(Device.id.in_(dev_ids)).all()} if dev_ids else {}

        result = []
        for r in rows:
            dp = dp_map.get(r.data_point_id)
            ch = ch_map.get(r.channel_id)
            dev = dev_map.get(r.device_id)
            result.append({
                'id': r.id,
                'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M:%S') if r.timestamp else None,
                'value': r.value,
                'data_point_id': r.data_point_id,
                'data_point_name': dp.name if dp else None,
                'channel_id': r.channel_id,
                'channel_name': ch.name if ch else None,
                'device_id': r.device_id,
                'device_name': (dev.custom_name or dev.name) if dev else None,
                'unit': ''
            })
        return jsonify({
            'success': True,
            'data': result,
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@data_view_bp.route('/<int:record_id>', methods=['DELETE'])
@login_required
def delete_data(record_id):
    """删除单条数据"""
    try:
        r = DataHistory.query.get(record_id)
        if not r:
            return jsonify({'success': False, 'error': '数据不存在'}), 404
        # 权限
        dev = Device.query.get(r.device_id)
        if not dev or dev.user_id != current_user.id:
            return jsonify({'success': False, 'error': '无权操作'}), 403
        db.session.delete(r)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@data_view_bp.route('/cleanup', methods=['POST'])
@login_required
def cleanup_data():
    """清理 N 天前的数据"""
    try:
        body = request.get_json() or {}
        days = body.get('days', 30)
        if days < 1:
            return jsonify({'success': False, 'error': 'days 必须 >= 1'}), 400
        cutoff = datetime.utcnow() - timedelta(days=days)
        user_device_ids = [d.id for d in Device.query.filter_by(user_id=current_user.id).all()]
        if not user_device_ids:
            return jsonify({'success': True, 'deleted': 0})
        deleted = DataHistory.query.filter(
            DataHistory.device_id.in_(user_device_ids),
            DataHistory.timestamp < cutoff
        ).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ================= API: 筛选下拉 =================
@data_view_bp.route('/devices', methods=['GET'])
@login_required
def list_devices():
    try:
        devices = Device.query.filter_by(user_id=current_user.id).order_by(Device.name).all()
        return jsonify({'success': True, 'data': [
            {'id': d.id, 'name': d.name, 'custom_name': d.custom_name} for d in devices
        ]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_view_bp.route('/channels', methods=['GET'])
@login_required
def list_channels():
    try:
        user_device_ids = [d.id for d in Device.query.filter_by(user_id=current_user.id).all()]
        if not user_device_ids:
            return jsonify({'success': True, 'data': []})
        channels = Channel.query.filter(Channel.device_id.in_(user_device_ids)).order_by(Channel.name).all()
        return jsonify({'success': True, 'data': [
            {'id': c.id, 'name': c.name, 'device_id': c.device_id} for c in channels
        ]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_view_bp.route('/data-points', methods=['GET'])
@login_required
def list_data_points():
    try:
        user_device_ids = [d.id for d in Device.query.filter_by(user_id=current_user.id).all()]
        if not user_device_ids:
            return jsonify({'success': True, 'data': []})
        channels = Channel.query.filter(Channel.device_id.in_(user_device_ids)).all()
        ch_ids = [c.id for c in channels]
        if not ch_ids:
            return jsonify({'success': True, 'data': []})
        dps = DataPoint.query.filter(DataPoint.channel_id.in_(ch_ids)).order_by(DataPoint.name).all()
        return jsonify({'success': True, 'data': [
            {'id': dp.id, 'name': dp.name, 'channel_id': dp.channel_id} for dp in dps
        ]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_view_bp.route('/chart', methods=['GET'])
@login_required
def chart_data():
    """图表数据 - 趋势"""
    try:
        data_point_id = request.args.get('data_point_id', type=int)
        hours = request.args.get('hours', 24, type=int)
        if not data_point_id:
            return jsonify({'success': False, 'error': '缺少 data_point_id'}), 400
        # 权限
        dp = DataPoint.query.get(data_point_id)
        if not dp or not dp.channel or not dp.channel.device or dp.channel.device.user_id != current_user.id:
            return jsonify({'success': False, 'error': '无权访问'}), 403
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        rows = DataHistory.query.filter(
            DataHistory.data_point_id == data_point_id,
            DataHistory.timestamp >= cutoff
        ).order_by(DataHistory.timestamp).all()
        return jsonify({
            'success': True,
            'data': [
                {
                    'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'value': r.value
                } for r in rows
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
