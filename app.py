import os
import logging
import threading
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config
from models.database import db, User
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.devices import devices_bp
from routes.data import data_bp
from routes.tcp import tcp_bp
from routes.pages import pages_bp
from routes.alarms import alarms_bp
from routes.stream import stream_bp
from routes.health import health_bp
from routes.export import export_bp
from routes.groups import groups_bp
from routes.realtime import realtime_bp
from routes.dashboard_api import dashboard_bp
from routes.projects import projects_bp
from routes.alarm_rules import alarm_rules_bp
from routes.screen import screen_bp
from routes.platform import platform_bp
from routes.audit import audit_bp
from routes.notifications import notifications_bp
from routes.simulator import simulator_bp
from routes.monitor import monitor_bp
from routes.simulator import simulator_bp
from routes.protocol import protocol_bp
from services.api_docs import docs_bp

logging.basicConfig(level=logging.INFO)

login_manager = LoginManager()
csrf = CSRFProtect()

# 可选 gzip 压缩（无损加速）
try:
    from flask_compress import Compress
    Compress()  # 注册全局后 init
except Exception:
    pass

# 初始化限流器
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"]
)

# 防止 TCP 服务器被重复启动
_tcp_server_started = False


def _start_tcp_server_once(app):
    """在后台线程启动 TCP 服务器，确保只启动一次"""
    global _tcp_server_started
    if _tcp_server_started:
        logging.info("[TCP] Server already started, skipping")
        return
    _tcp_server_started = True

    def tcp_thread_target():
        try:
            from tcp_server import run_tcp_server
            from services.tcp_handler import TcpConnectionHandler
            logging.info("[TCP] Starting TCP server in background thread...")
            run_tcp_server(app, TcpConnectionHandler)
        except Exception as e:
            logging.error(f"[TCP] Failed to start TCP server: {e}", exc_info=True)

    t = threading.Thread(target=tcp_thread_target, daemon=True)
    t.start()
    logging.info(f"[TCP] TCP server thread launched (alive={t.is_alive()})")


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config.get(config_name, config['default']))

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # gzip 压缩
    try:
        from services.perf_init import init_perf
        init_perf(app)
    except Exception as e:
        try:
            from flask_compress import Compress
            Compress(app)
        except Exception:
            pass
    limiter.init_app(app)
    
    # API 路由免除 CSRF（所有 /api/ 前缀）
    csrf.exempt(auth_bp)
    csrf.exempt(devices_bp)
    csrf.exempt(data_bp)
    csrf.exempt(tcp_bp)
    csrf.exempt(alarms_bp)
    csrf.exempt(health_bp)
    csrf.exempt(export_bp)
    csrf.exempt(groups_bp)
    csrf.exempt(realtime_bp)
    csrf.exempt(dashboard_bp)
    csrf.exempt(projects_bp)
    csrf.exempt(alarm_rules_bp)
    csrf.exempt(screen_bp)
    csrf.exempt(audit_bp)
    csrf.exempt(notifications_bp)
    csrf.exempt(simulator_bp)
    csrf.exempt(monitor_bp)
    # 占位，平台/可视化/RBAC 蓝图在下方注册后会被 exempt
    
    login_manager.login_view = 'pages.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(tcp_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(alarms_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(realtime_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(alarm_rules_bp)
    app.register_blueprint(screen_bp)
    app.register_blueprint(platform_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(monitor_bp)
    from routes.visualization import viz_bp as visualization_bp
    app.register_blueprint(visualization_bp)
    from routes.rbac import rbac_bp
    app.register_blueprint(rbac_bp)
    from routes.alarm_engine import alarm_engine_bp
    app.register_blueprint(alarm_engine_bp)
    from routes.ota import ota_bp
    app.register_blueprint(ota_bp)
    from routes.shadow import shadow_bp
    app.register_blueprint(shadow_bp)
    from routes.rule_engine import rule_engine_bp
    app.register_blueprint(rule_engine_bp)
    from routes.custom_dashboard import custom_dashboard_bp
    app.register_blueprint(custom_dashboard_bp)
    app.register_blueprint(protocol_bp)

    app.register_blueprint(docs_bp)

    # 上面新注册的蓝图统一 exempt CSRF
    csrf.exempt(platform_bp)
    csrf.exempt(visualization_bp)
    csrf.exempt(rbac_bp)
    csrf.exempt(alarm_engine_bp)
    csrf.exempt(ota_bp)
    csrf.exempt(shadow_bp)
    csrf.exempt(rule_engine_bp)
    csrf.exempt(custom_dashboard_bp)
    csrf.exempt(protocol_bp)
    csrf.exempt(docs_bp)

    with app.app_context():
        db.create_all()
        create_default_admin()
        try:
            from services.rbac import RBACService
            n = RBACService.init_permissions()
            print(f'[RBAC] initialized {n} permissions')
        except Exception as e:
            print(f'[RBAC] init warning: {e}')

    # 初始化缓存后端（内存 / Redis）
    from services.cache import init_cache
    init_cache(app)

    # 初始化 WebSocket 路由
    try:
        from flask_sock import Sock
        sock = Sock(app)
        from services.websocket import init_ws_routes
        init_ws_routes(app, sock)
        app.logger.info('[WS] WebSocket routes registered at /ws and /ws/stats')
    except Exception as e:
        app.logger.warning(f'[WS] init failed: {e}')

    # 自动启动 TCP 服务器（无论通过 run.py 还是 wsgi.py 入口）
    _start_tcp_server_once(app)

    return app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_default_admin():
    """创建默认管理员账户"""
    admin_username = os.environ.get('ADMIN_USERNAME') or 'admin'
    admin_password = os.environ.get('ADMIN_PASSWORD') or 'admin123'

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(
            username=admin_username,
            is_admin=True,
            tcp_port=9105,
            storage_enabled=True,
            is_active=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        logging.info(f"Default admin user '{admin_username}' created")
