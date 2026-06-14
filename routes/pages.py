"""
页面路由 - 仪表盘、设备管理、数据查看
"""
import logging
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)
pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
@login_required
def index():
    """首页 → 仪表盘"""
    return redirect(url_for('pages.dashboard'))


@pages_bp.route('/login', methods=['GET'])
def login():
    """登录页(未登录)"""
    if current_user.is_authenticated:
        return redirect(url_for('pages.dashboard'))
    return render_template('login_v2.html')


@pages_bp.route('/logout', methods=['GET'])
@login_required
def logout():
    """登出"""
    from flask_login import logout_user
    logout_user()
    return redirect(url_for('pages.login'))


@pages_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@pages_bp.route('/devices')
@login_required
def devices():
    return render_template('devices.html')


@pages_bp.route('/data')
@login_required
def data_view():
    return render_template('data_view.html')


# ============ 系统管理页面(用户/TCP/系统设置) ============

@pages_bp.route('/admin/users')
@login_required
def admin_users():
    """用户管理"""
    if not current_user.is_admin:
        return redirect(url_for('pages.dashboard'))
    return render_template('admin/users.html')


@pages_bp.route('/admin/tcp')
@login_required
def admin_tcp():
    """TCP管理"""
    if not current_user.is_admin:
        return redirect(url_for('pages.dashboard'))
    return render_template('admin/tcp_manage.html')


@pages_bp.route('/admin/system')
@login_required
def admin_system():
    """系统设置"""
    if not current_user.is_admin:
        return redirect(url_for('pages.dashboard'))
    return render_template('admin/system.html')
