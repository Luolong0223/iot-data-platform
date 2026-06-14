from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user, login_user, logout_user

from models.database import User

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
@pages_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('pages.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('用户名或密码错误', 'error')
            return render_template('login.html')
        
        remember = request.form.get('remember') == 'on'
        login_user(user, remember=remember)
        return redirect(url_for('pages.dashboard'))
    
    return render_template('login.html')


@pages_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功退出登录', 'success')
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


@pages_bp.route('/map')
@login_required
def map_view():
    return render_template('map.html', baidu_map_ak=current_app.config.get('BAIDU_MAP_AK', ''))


@pages_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@pages_bp.route('/alarms')
@login_required
def alarms():
    return render_template('alarms.html')


@pages_bp.route('/alarm-rules')
@login_required
def alarm_rules():
    """告警规则配置页面"""
    return render_template('alarm_rules.html')


@pages_bp.route('/hierarchy')
@login_required
def hierarchy():
    """设备层级管理页面"""
    return render_template('hierarchy.html')


@pages_bp.route('/screen')
@login_required
def screen():
    """数据大屏"""
    return render_template('screen.html')


@pages_bp.route('/platform')
@login_required
def platform():
    """平台增强中心：设备影子/标签/命令/协议/通知/审计/报表"""
    return render_template('platform.html')


@pages_bp.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('需要管理员权限', 'error')
        return redirect(url_for('pages.dashboard'))
    return redirect(url_for('pages.admin_users'))


@pages_bp.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('需要管理员权限', 'error')
        return redirect(url_for('pages.dashboard'))
    return render_template('admin/users.html')


@pages_bp.route('/admin/tcp')
@login_required
def admin_tcp():
    if not current_user.is_admin:
        flash('需要管理员权限', 'error')
        return redirect(url_for('pages.dashboard'))
    return render_template('admin/tcp_manage.html')


@pages_bp.route('/admin/system')
@login_required
def admin_system():
    if not current_user.is_admin:
        flash('需要管理员权限', 'error')
        return redirect(url_for('pages.dashboard'))
    return render_template('admin/system.html')


@pages_bp.route('/docs')
def swagger_ui():
    """Swagger UI API 文档"""
    return render_template('swagger.html')


@pages_bp.route('/redoc')
def redoc_ui():
    """ReDoc API 文档"""
    return render_template('redoc.html')
