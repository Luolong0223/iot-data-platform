import os
import logging
import threading
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import config
from models.database import db, User
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.tcp import tcp_bp
from routes.pages import pages_bp
# 新建的核心路由
from routes.dashboard import dashboard_bp
from routes.devices import devices_bp
from routes.data_view import data_view_bp

logging.basicConfig(level=logging.INFO)

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name=None):
    """应用工厂函数"""
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config[config_name])

    # 确保instance目录存在
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_path, exist_ok=True)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # 登录管理器配置
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        # 防御:如果 MySQL 缺少列(权限不足导致迁移失败),尝试懒加载修复
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            err_msg = str(e)
            if 'Unknown column' in err_msg or '1054' in err_msg:
                # 提取缺失的列名
                import re
                m = re.search(r"Unknown column '([^']+)'", err_msg)
                missing_col = m.group(1) if m else '?'
                app.logger.error(
                    f"[load_user] 数据库缺少列 '{missing_col}',请运行 migration_manual.sql"
                )
                # 尝试执行迁移
                try:
                    from migrate_db import EXPECTED_COLUMNS, get_existing_columns, get_all_tables, add_column
                    with db.engine.connect() as conn:
                        for table, columns in EXPECTED_COLUMNS.items():
                            for col_name, col_def in columns:
                                if col_name == missing_col.split('.')[-1]:
                                    if table in get_all_tables(conn) and missing_col.split('.')[-1] not in get_existing_columns(conn, table):
                                        result = add_column(conn, table, col_name, col_def)
                                        app.logger.info(f"[load_user] 紧急迁移 {table}.{col_name}: {result}")
                    # 重试查询
                    return User.query.get(int(user_id))
                except Exception as migrate_err:
                    app.logger.error(f"[load_user] 紧急迁移失败: {migrate_err}")
            raise

    # 注册蓝图（API 路由 - CSRF豁免）
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(tcp_bp, url_prefix='/api/tcp')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(devices_bp, url_prefix='/api/devices')
    app.register_blueprint(data_view_bp, url_prefix='/api/data')

    # 页面路由
    app.register_blueprint(pages_bp)

    # API 路由 CSRF 豁免
    from flask_wtf.csrf import CSRFProtect
    csrf.exempt(auth_bp)
    csrf.exempt(admin_bp)
    csrf.exempt(tcp_bp)
    csrf.exempt(dashboard_bp)
    csrf.exempt(devices_bp)
    csrf.exempt(data_view_bp)

    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('errors/500.html'), 500

    # 创建数据库表
    with app.app_context():
        db.create_all()

        # 自动迁移: 补全缺失列(防止生产 MySQL 与模型不同步)
        # 关键:把结果直接打印到 stdout,你重启时能直接看到
        print("=" * 60)
        print("🔧 [数据库迁移 v2] 模型自动扫描模式 ...")
        print("=" * 60)
        try:
            from migrate_db import auto_migrate
            auto_migrate()
        except Exception as e:
            import traceback
            print(f"❌ [数据库迁移] 异常: {e}")
            traceback.print_exc()
            print("=" * 60)
            print("⚠️  迁移失败不影响应用启动,但部分查询可能报错")
            print("⚠️  请参考 migration_manual.sql 手动执行")
            print("=" * 60)

        # 启动 TCP 服务
        from services.tcp_listener import start_tcp_listener
        start_tcp_listener(app)

    return app
