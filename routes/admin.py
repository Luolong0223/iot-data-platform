from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models.database import db, User
from config import config

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def admin_required(f):
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def get_next_tcp_port():
    base_port = config['default'].TCP_BASE_PORT
    existing_ports = {u.tcp_port for u in User.query.filter(User.tcp_port.isnot(None)).all()}
    port = base_port
    while port in existing_ports:
        port += 1
    return port


@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    users = User.query.all()
    return jsonify({'success': True, 'users': [u.to_dict() for u in users]})


@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    is_admin = data.get('is_admin', False)
    storage_enabled = data.get('storage_enabled', True)
    tcp_port = data.get('tcp_port')

    if not username:
        return jsonify({'success': False, 'message': 'Username is required'}), 400
    if not password:
        return jsonify({'success': False, 'message': 'Password is required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username already exists'}), 409

    if tcp_port is None:
        tcp_port = get_next_tcp_port()
    else:
        tcp_port = int(tcp_port)
        existing = User.query.filter_by(tcp_port=tcp_port).first()
        if existing:
            return jsonify({'success': False, 'message': f'TCP port {tcp_port} already assigned'}), 409

    user = User(
        username=username,
        is_admin=bool(is_admin),
        tcp_port=tcp_port,
        storage_enabled=bool(storage_enabled)
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'success': True, 'user': user.to_dict()}), 201


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    if 'username' in data:
        new_username = data['username'].strip()
        if new_username and new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                return jsonify({'success': False, 'message': 'Username already exists'}), 409
            user.username = new_username

    if 'password' in data and data['password']:
        user.set_password(data['password'])

    if 'is_admin' in data:
        user.is_admin = bool(data['is_admin'])

    if 'storage_enabled' in data:
        user.storage_enabled = bool(data['storage_enabled'])

    if 'tcp_port' in data:
        new_port = int(data['tcp_port'])
        if new_port != user.tcp_port:
            existing = User.query.filter_by(tcp_port=new_port).first()
            if existing and existing.id != user.id:
                return jsonify({'success': False, 'message': f'TCP port {new_port} already assigned'}), 409
            user.tcp_port = new_port

    db.session.commit()
    return jsonify({'success': True, 'user': user.to_dict()})


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'User deleted'})


@admin_bp.route('/tcp-status', methods=['GET'])
@admin_required
def tcp_status():
    """获取 TCP 监听器状态"""
    try:
        from models.database import TcpServerConfig
        from services.tcp_listener import _server_state
        servers = TcpServerConfig.query.order_by(TcpServerConfig.port).all()
        return jsonify({
            'success': True,
            'running': bool(_server_state.get('running', False)),
            'servers': [
                {
                    'id': s.id,
                    'name': s.name,
                    'port': s.port,
                    'host': s.host,
                    'enabled': s.enabled,
                    'is_running': s.id in _server_state.get('servers', {})
                } for s in servers
            ],
            'server_count': len(servers)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@admin_bp.route('/system-config', methods=['GET'])
@login_required
def list_system_config():
    """获取系统配置"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': '无权限'}), 403
        from models.database import SystemConfig
        cfgs = SystemConfig.query.order_by(SystemConfig.key).all()
        return jsonify({'success': True, 'data': [
            {
                'id': c.id,
                'key': c.key,
                'value': c.value,
                'description': c.description if hasattr(c, 'description') else ''
            } for c in cfgs
        ]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/login-logs', methods=['GET'])
@login_required
def list_login_logs():
    """获取登录日志"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': '无权限'}), 403
        from models.database import LoginLog
        page = request.args.get('page', 1, type=int)
        page_size = min(request.args.get('page_size', 50, type=int), 200)
        q = LoginLog.query.order_by(LoginLog.id.desc())
        total = q.count()
        rows = q.offset((page-1)*page_size).limit(page_size).all()
        return jsonify({
            'success': True,
            'data': [{
                'id': r.id,
                'user_id': r.user_id,
                'username': r.username,
                'ip': r.ip,
                'user_agent': r.user_agent,
                'status': r.status,
                'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M:%S') if r.timestamp else None
            } for r in rows],
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
