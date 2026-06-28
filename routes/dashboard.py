"""
仪表盘路由 - Widget 管理 + 仪表盘数据展示
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from models.database import db, Device, Channel, DataPoint, DataHistory, DashboardWidget, DeviceCategory

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


# ================= 页面 =================
@dashboard_bp.route('/')
@login_required
def page():
    return render_dashboard_page()


def render_dashboard_page():
    from flask import render_template
    return render_template('dashboard.html')


# ================= API: 仪表盘数据 =================
@dashboard_bp.route('/data', methods=['GET'])
@login_required
def get_dashboard_data():
    """获取仪表盘所有 widget 的最新数据 + 汇总"""
    try:
        widgets = DashboardWidget.query.filter_by(user_id=current_user.id, is_visible=True)\
            .order_by(DashboardWidget.sort_order).all()

        widget_data = []
        for w in widgets:
            widget_data.append(w.to_dict())

        # 汇总
        total_devices = Device.query.filter_by(user_id=current_user.id).count()
        online_devices = Device.query.filter_by(user_id=current_user.id, is_online=True).count()
        offline_devices = total_devices - online_devices

        return jsonify({
            'success': True,
            'data': {
                'widgets': widget_data,
                'summary': {
                    'total_devices': total_devices,
                    'online_devices': online_devices,
                    'offline_devices': offline_devices,
                    'total_widgets': len(widget_data)
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ================= API: 可添加的数据点 =================
@dashboard_bp.route('/available-points', methods=['GET'])
@login_required
def get_available_points():
    """获取用户所有设备的所有数据点,标记哪些已添加到仪表盘"""
    try:
        devices = Device.query.filter_by(user_id=current_user.id).all()
        added_dp_ids = {w.data_point_id for w in DashboardWidget.query.filter_by(user_id=current_user.id).all()}

        result = []
        for d in devices:
            device_data = {
                'id': d.id,
                'name': d.name,
                'display_name': d.custom_name or d.name,
                'is_online': d.is_online,
                'voltage': d.voltage,
                'channels': []
            }
            for ch in d.channels:
                ch_data = {
                    'id': ch.id,
                    'name': ch.name,
                    'is_online': ch.is_online,
                    'data_points': []
                }
                for dp in ch.data_points:
                    ch_data['data_points'].append({
                        'id': dp.id,
                        'name': dp.name,
                        'latest_value': dp.value,
                        'is_added': dp.id in added_dp_ids
                    })
                device_data['channels'].append(ch_data)
            result.append(device_data)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ================= API: 添加 widget =================
@dashboard_bp.route('/widgets', methods=['POST'])
@login_required
def add_widget():
    """添加数据点到仪表盘"""
    try:
        body = request.get_json() or {}
        data_point_id = body.get('data_point_id')

        if not data_point_id:
            return jsonify({'success': False, 'error': '缺少 data_point_id'}), 400

        dp = DataPoint.query.get(data_point_id)
        if not dp:
            return jsonify({'success': False, 'error': '数据点不存在'}), 404

        # 验证数据点归属
        ch = dp.channel
        if not ch or not ch.device:
            return jsonify({'success': False, 'error': '数据点无对应设备'}), 400
        if ch.device.user_id != current_user.id:
            return jsonify({'success': False, 'error': '无权操作'}), 403

        # 防止重复
        existing = DashboardWidget.query.filter_by(
            user_id=current_user.id, data_point_id=data_point_id
        ).first()
        if existing:
            return jsonify({'success': False, 'error': '该数据点已在仪表盘'}), 400

        # 最大排序
        max_order = db.session.query(func.coalesce(func.max(DashboardWidget.sort_order), 0))\
            .filter_by(user_id=current_user.id).scalar() or 0

        w = DashboardWidget(
            user_id=current_user.id,
            device_id=ch.device.id,
            channel_id=ch.id,
            data_point_id=dp.id,
            sort_order=max_order + 1,
            is_visible=True
        )
        db.session.add(w)
        db.session.commit()
        return jsonify({'success': True, 'data': w.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/widgets/<int:widget_id>', methods=['DELETE'])
@login_required
def delete_widget(widget_id):
    """删除 widget"""
    try:
        w = DashboardWidget.query.get(widget_id)
        if not w:
            return jsonify({'success': False, 'error': 'widget 不存在'}), 404
        if w.user_id != current_user.id:
            return jsonify({'success': False, 'error': '无权操作'}), 403
        db.session.delete(w)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/widgets/reorder', methods=['POST'])
@login_required
def reorder_widgets():
    """重新排序 widget"""
    try:
        body = request.get_json() or {}
        order = body.get('order', [])
        for i, wid in enumerate(order):
            w = DashboardWidget.query.get(wid)
            if w and w.user_id == current_user.id:
                w.sort_order = i
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
