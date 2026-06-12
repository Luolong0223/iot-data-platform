"""
认证路由 - 用户登录、登出、个人信息管理
包含登录日志记录和限流保护
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models.database import db, User
from services.login_log import LoginLogService

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def get_limit_key():
    """获取限流键（用户名或IP）"""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    if username:
        return f"login_{username}"
    return f"login_ip_{get_remote_address()}"


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    包含登录日志记录和登录失败限制
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
    
    # 检查失败次数限制
    failed_attempts = LoginLogService.get_failed_attempts(username, minutes=5)
    max_attempts = 5  # 最大失败次数
    
    if failed_attempts >= max_attempts:
        LoginLogService.log_login(None, username, success=False, failure_reason='账户暂时锁定')
        return jsonify({
            'success': False,
            'message': f'登录失败次数过多，请5分钟后再试',
            'locked': True
        }), 429
    
    # 查找用户
    user = User.query.filter_by(username=username).first()
    
    # 验证用户和密码
    if not user:
        LoginLogService.log_login(None, username, success=False, failure_reason='用户不存在')
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
    
    # 检查账户是否激活
    if hasattr(user, 'is_active') and not user.is_active:
        LoginLogService.log_login(user.id, username, success=False, failure_reason='账户已禁用')
        return jsonify({'success': False, 'message': '账户已被禁用，请联系管理员'}), 403
    
    # 验证密码
    if not user.check_password(password):
        LoginLogService.log_login(user.id, username, success=False, failure_reason='密码错误')
        remaining = max_attempts - failed_attempts - 1
        return jsonify({
            'success': False,
            'message': f'用户名或密码错误，剩余尝试次数: {remaining}'
        }), 401
    
    # 登录成功
    login_user(user, remember=data.get('remember', False))
    
    # 更新最后登录信息
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = LoginLogService.get_client_ip()
    db.session.commit()
    
    # 记录登录日志
    LoginLogService.log_login(user.id, username, success=True)
    
    logger.info(f"User '{username}' logged in successfully from {user.last_login_ip}")
    
    return jsonify({
        'success': True,
        'message': '登录成功',
        'user': user.to_dict()
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    username = current_user.username
    user_id = current_user.id
    
    logout_user()
    
    # 记录登出日志
    LoginLogService.log_logout(user_id, username)
    
    return jsonify({'success': True, 'message': '已成功登出'})


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """获取当前用户信息"""
    return jsonify({'success': True, 'user': current_user.to_dict()})


@auth_bp.route('/me', methods=['PUT'])
@login_required
def update_me():
    """更新当前用户信息"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    # 更新邮箱
    if 'email' in data:
        email = data['email'].strip() if data['email'] else None
        if email:
            # 检查邮箱是否已被使用
            existing = User.query.filter(
                User.email == email,
                User.id != current_user.id
            ).first()
            if existing:
                return jsonify({'success': False, 'message': '该邮箱已被使用'}), 409
        current_user.email = email
    
    # 更新密码
    if 'password' in data and data['password']:
        old_password = data.get('old_password', '')
        
        # 验证旧密码
        if old_password and not current_user.check_password(old_password):
            return jsonify({'success': False, 'message': '原密码错误'}), 400
        
        # 验证新密码强度
        new_password = data['password']
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': '密码长度至少6位'}), 400
        
        current_user.set_password(new_password)
        logger.info(f"User '{current_user.username}' changed password")
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '信息已更新',
        'user': current_user.to_dict()
    })


@auth_bp.route('/login-history', methods=['GET'])
@login_required
def login_history():
    """获取登录历史"""
    limit = request.args.get('limit', default=20, type=int)
    limit = min(limit, 100)
    
    logs = LoginLogService.get_recent_logs(user_id=current_user.id, limit=limit)
    
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in logs]
    })


@auth_bp.route('/check-username', methods=['POST'])
def check_username():
    """检查用户名是否可用"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    username = data.get('username', '').strip()
    if not username:
        return jsonify({'success': False, 'message': '用户名不能为空'}), 400
    
    if len(username) < 3 or len(username) > 80:
        return jsonify({
            'success': True,
            'available': False,
            'message': '用户名长度需在3-80字符之间'
        })
    
    existing = User.query.filter_by(username=username).first()
    
    return jsonify({
        'success': True,
        'available': existing is None,
        'message': '用户名可用' if existing is None else '用户名已被使用'
    })
