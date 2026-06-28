"""
TCP 端口管理路由 - 基于 TcpServerConfig
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models.database import db, TcpServerConfig, TcpLog

tcp_bp = Blueprint('tcp', __name__, url_prefix='/api/tcp')


def admin_required(f):
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated


@tcp_bp.route('/config', methods=['GET'])
@admin_required
def get_config():
    """获取 TCP 配置"""
    servers = TcpServerConfig.query.order_by(TcpServerConfig.port).all()
    return jsonify({
        'success': True,
        'config': {
            'tcp_host': current_app.config.get('TCP_HOST', '0.0.0.0'),
            'tcp_base_port': current_app.config.get('TCP_BASE_PORT', 9105),
            'tcp_buffer_size': current_app.config.get('TCP_BUFFER_SIZE', 4096),
            'tcp_timeout': current_app.config.get('TCP_TIMEOUT', 30),
            'servers': [s.to_dict() for s in servers]
        }
    })


@tcp_bp.route('/config', methods=['PUT'])
@admin_required
def update_config():
    """更新 TCP 端口配置"""
    data = request.get_json() or {}
    msg = []
    if 'servers' in data and isinstance(data['servers'], list):
        for s in data['servers']:
            sid = s.get('id')
            sv = TcpServerConfig.query.get(sid)
            if sv and 'is_active' in s:
                sv.is_active = bool(s['is_active'])
                msg.append(f"端口 {sv.port} 已{'启用' if sv.is_active else '禁用'}")
    db.session.commit()
    return jsonify({'success': True, 'message': '; '.join(msg) or '无修改'})


@tcp_bp.route('/logs', methods=['GET'])
@admin_required
def list_logs():
    """TCP 通信日志"""
    page = request.args.get('page', 1, type=int)
    page_size = min(request.args.get('page_size', 50, type=int), 200)
    q = TcpLog.query.order_by(TcpLog.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({
        'success': True,
        'data': [r.to_dict() for r in rows],
        'total': total,
        'page': page,
        'page_size': page_size
    })


@tcp_bp.route('/status', methods=['GET'])
@admin_required
def tcp_status():
    """获取 TCP 监听状态"""
    try:
        from services.tcp_listener import get_active_ports
        active_ports = get_active_ports()
        return jsonify({
            'success': True,
            'active_ports': active_ports,
            'port_count': len(active_ports)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
