"""
数据库迁移脚本 - 自动同步 SQLAlchemy 模型和现有数据库
用于修复"Unknown column xxx in field list"问题

使用: python migrate_db.py
"""
import sys
import os
from sqlalchemy import inspect, text

# 配置环境变量 (与 .env 或实际部署一致)
os.environ.setdefault('DATABASE_URL', 'sqlite:///iot_platform.db')

from app import create_app
from models.database import db

# 期望添加的列 (基于真实模型 models/database.py)
# 格式: {表名: [(列名, 列定义), ...]}
# 重要:列定义必须与模型中 db.Column 的类型严格匹配
EXPECTED_COLUMNS = {
    'users': [
        # 模型字段: id, username, email, password_hash, is_active, is_admin, created_at, last_login
        ('last_login', 'DATETIME NULL'),
    ],
    'devices': [
        # 模型字段: id, name, custom_name, voltage_mv, category_id, user_id, is_online, last_seen, first_seen, total_packets
        ('last_seen', 'DATETIME NULL'),
    ],
    'channels': [
        # 模型字段: id, device_id, name, is_online, last_seen, first_seen
        ('last_seen', 'DATETIME NULL'),
    ],
    'data_points': [
        # 模型字段: id, channel_id, name, value, last_value, last_updated, update_count
        ('last_value', 'FLOAT DEFAULT 0.0'),
        ('last_updated', 'DATETIME NULL'),
        ('update_count', 'INT DEFAULT 0'),
    ],
    'data_history': [
        # 模型字段: id, data_point_id, device_id, channel_id, value, timestamp
        # 全部已在基础表中
    ],
    'dashboard_widgets': [
        # 模型字段: id, user_id, device_id, channel_id, data_point_id, sort_order, is_visible, color, created_at
        # 全部已在基础表中
    ],
    'tcp_server_configs': [
        # 模型字段: id, name, port, host, is_active, description, created_at, last_started, total_connections, total_messages, error_count
        ('last_started', 'DATETIME NULL'),
        ('total_connections', 'INT DEFAULT 0'),
        ('total_messages', 'INT DEFAULT 0'),
        ('error_count', 'INT DEFAULT 0'),
    ],
    'tcp_logs': [
        # 模型字段: id, port, client_ip, direction, content, status, error_message, timestamp
        # 全部已在基础表中
    ],
    'system_configs': [
        # 模型字段: id, key, value, description, updated_at
        # 全部已在基础表中
    ],
    'login_logs': [
        # 模型字段: id, user_id, username, ip, user_agent, status, timestamp
        ('ip', 'VARCHAR(50) NULL'),
        ('user_agent', 'VARCHAR(255) NULL'),
    ],
}


def get_existing_columns(conn, table_name):
    """获取表的现有列"""
    inspector = inspect(conn)
    try:
        cols = inspector.get_columns(table_name)
        return {c['name'] for c in cols}
    except Exception:
        return set()


def get_all_tables(conn):
    """获取所有表"""
    inspector = inspect(conn)
    return set(inspector.get_table_names())


def is_sqlite():
    """检测是否为 SQLite"""
    return 'sqlite' in str(db.engine.url).lower()


def add_column(conn, table, col_name, col_def):
    """添加列(兼容 SQLite 和 MySQL) - SQLAlchemy 2.0 auto-commit"""
    if is_sqlite():
        sql = f"ALTER TABLE {table} ADD COLUMN {col_name} NULL"
    else:
        sql = f"ALTER TABLE `{table}` ADD COLUMN `{col_name}` {col_def}"
    try:
        # SQLAlchemy 2.0: db.engine.connect() 自动开启事务,执行后自动 commit
        conn.execute(text(sql))
        conn.commit()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return f"失败: {e}"


def create_table_if_missing(conn, table, model_class):
    """如果表不存在,使用模型创建"""
    inspector = inspect(conn)
    if table not in inspector.get_table_names():
        try:
            model_class.__table__.create(db.engine)
            return f"✅ 创建表 {table}"
        except Exception as e:
            return f"❌ 创建表 {table} 失败: {e}"
    return None


def main():
    print("=" * 60)
    print("📦 数据库迁移工具")
    print("=" * 60)

    app = create_app()
    with app.app_context():
        print(f"\n🔗 数据库: {db.engine.url}\n")

        with db.engine.connect() as conn:
            existing_tables = get_all_tables(conn)
            print(f"📊 现有表: {len(existing_tables)}")
            for t in sorted(existing_tables):
                print(f"   - {t}")
            print()

            # 1. 创建所有缺失的表
            print("=" * 60)
            print("🏗️  创建缺失的表")
            print("=" * 60)
            from models.database import (
                User, Device, Channel, DataPoint, DataHistory,
                DeviceCategory, DashboardWidget, TcpServerConfig,
                TcpLog, SystemConfig, LoginLog
            )
            all_models = [
                ('users', User), ('devices', Device), ('channels', Channel),
                ('data_points', DataPoint), ('data_history', DataHistory),
                ('device_categories', DeviceCategory),
                ('dashboard_widgets', DashboardWidget),
                ('tcp_server_configs', TcpServerConfig), ('tcp_logs', TcpLog),
                ('system_configs', SystemConfig), ('login_logs', LoginLog),
            ]
            for table_name, model_cls in all_models:
                result = create_table_if_missing(conn, table_name, model_cls)
                if result:
                    print(f"   {result}")

            # 2. 添加缺失的列
            print("\n" + "=" * 60)
            print("🔧 添加缺失的列")
            print("=" * 60)
            total_added = 0
            for table, columns in EXPECTED_COLUMNS.items():
                if table not in existing_tables and table not in {t for t in get_all_tables(conn)}:
                    print(f"⏭️  跳过 {table} (表不存在,需先创建)")
                    continue
                existing = get_existing_columns(conn, table)
                for col_name, col_def in columns:
                    if col_name in existing:
                        continue
                    print(f"   ➕ {table}.{col_name} ({col_def})... ", end='')
                    result = add_column(conn, table, col_name, col_def)
                    if result is True:
                        print("✅")
                        total_added += 1
                    else:
                        print(f"⚠️  {result}")

            print("\n" + "=" * 60)
            print(f"✅ 完成: 新增 {total_added} 个列")
            print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        print(f"\n❌ 迁移失败: {e}")
        traceback.print_exc()
        sys.exit(1)
