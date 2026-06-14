"""
TCP 端口管理路由 - 基于 TcpServerConfig
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models.database import db, TcpServerConfig, TcpLog

tcp_bp = Blueprint('tcp', __name__, url_prefix='/api/tcp')


@tcp_bp.route('/config', methods=['GET'])
@login_required
def get_config():
    """获取 TCP 配置(所有监听端口)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': '无权限'}), 403
    servers = TcpServerConfig.query.order_by(TcpServerConfig.port).all()
    return jsonify({
        'success': True,
        'config': {
            'tcp_host': current_app.config.get('TCP_HOST', '0.0.0.0'),
            'tcp_base_port': current_app.config.get('TCP_BASE_PORT', 9105),
            'tcp_buffer_size': current_app.config.get('TCP_BUFFER_SIZE', 4096),
            'tcp_timeout': current_app.config.get('TCP_TIMEOUT', 30),
            'servers': [s.to_dict() if hasattr(s, 'to_dict') else {
                'id': s.id, 'name': s.name, 'host': s.host,
                'port': s.port, 'enabled': s.enabled
            } for s in servers]
        }
    })


@tcp_bp.route('/config', methods=['PUT'])
@login_required
def update_config():
    """更新 TCP 端口(简化版)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': '无权限'}), 403
    data = request.get_json() or {}
    msg = []
    if 'servers' in data and isinstance(data['servers'], list):
        for s in data['servers']:
            sid = s.get('id')
            sv = TcpServerConfig.query.get(sid)
            if sv and 'enabled' in s:
                sv.enabled = bool(s['enabled'])
                msg.append(f"端口 {sv.port} 已{'启用' if sv.enabled else '禁用'}")
    db.session.commit()
    return jsonify({'success': True, 'message': '; '.join(msg) or '无修改'})


@tcp_bp.route('/logs', methods=['GET'])
@login_required
def list_logs():
    """TCP 日志"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': '无权限'}), 403
    page = request.args.get('page', 1, type=int)
    page_size = min(request.args.get('page_size', 50, type=int), 200)
    q = TcpLog.query.order_by(TcpLog.id.desc())
    total = q.count()
    rows = q.offset((page-1)*page_size).limit(page_size).all()
    return jsonify({
        'success': True,
        'data': [{
            'id': r.id,
            'device_ip': r.device_ip if hasattr(r, 'device_ip') else (r.ip if hasattr(r, 'ip') else ''),
            'device_port': r.device_port if hasattr(r, 'device_port') else '',
            'server_port': r.server_port if hasattr(r, 'server_port') else (r.port if hasattr(r, 'port') else 0),
            'direction': r.direction if hasattr(r, 'direction') else 'in',
            'payload': r.payload if hasattr(r, 'payload') else '',
            'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(r, 'timestamp') and r.timestamp else None
        } for r in rows],
        'total': total
    })
