"""
管理员路由 - 用户管理、系统配置
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models.database import db, User

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def admin_required(f):
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated


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
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    is_admin = data.get('is_admin', False)

    if not username:
        return jsonify({'success': False, 'message': '用户名不能为空'}), 400
    if not password:
        return jsonify({'success': False, 'message': '密码不能为空'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码长度至少6位'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 409

    user = User(
        username=username,
        is_admin=bool(is_admin)
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
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400

    if 'username' in data:
        new_username = data['username'].strip()
        if new_username and new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                return jsonify({'success': False, 'message': '用户名已存在'}), 409
            user.username = new_username

    if 'password' in data and data['password']:
        if len(data['password']) < 6:
            return jsonify({'success': False, 'message': '密码长度至少6位'}), 400
        user.set_password(data['password'])

    if 'is_admin' in data:
        user.is_admin = bool(data['is_admin'])

    if 'is_active' in data:
        user.is_active = bool(data['is_active'])

    db.session.commit()
    return jsonify({'success': True, 'user': user.to_dict()})


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除自己'}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': '用户已删除'})


@admin_bp.route('/system-config', methods=['GET'])
@admin_required
def list_system_config():
    from models.database import SystemConfig
    cfgs = SystemConfig.query.order_by(SystemConfig.key).all()
    return jsonify({'success': True, 'data': [c.to_dict() for c in cfgs]})


@admin_bp.route('/login-logs', methods=['GET'])
@admin_required
def list_login_logs():
    from models.database import LoginLog
    page = request.args.get('page', 1, type=int)
    page_size = min(request.args.get('page_size', 50, type=int), 200)
    q = LoginLog.query.order_by(LoginLog.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({
        'success': True,
        'data': [r.to_dict() for r in rows],
        'total': total,
        'page': page,
        'page_size': page_size
    })
