#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IoT 数据平台 v3.0 数据库升级脚本
用于从 v1.x/v2.x 升级到 v3.0
"""

import os
import sys
import sqlite3

def get_db_path():
    """获取数据库路径"""
    possible_paths = [
        'instance/database.db',
        'database.db',
        'data.sqlite',
        'instance/data.sqlite',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return 'instance/database.db'

def check_column_exists(cursor, table, column):
    """检查列是否存在"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def check_table_exists(cursor, table):
    """检查表是否存在"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None

def get_table_columns(cursor, table):
    """获取表的所有列名"""
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]

def upgrade_database():
    """执行数据库升级"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请确保数据库文件存在后再运行此脚本")
        return False
    
    print(f"📦 数据库文件: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # ============ 1. 处理表名问题 ============
        print("\n🔍 检查表结构...")
        
        # 检查是否有旧的 channels 表，需要迁移到 slave_channels
        if check_table_exists(cursor, 'channels') and not check_table_exists(cursor, 'slave_channels'):
            print("  ➕ 重命名 channels 表为 slave_channels")
            cursor.execute("ALTER TABLE channels RENAME TO slave_channels")
        elif check_table_exists(cursor, 'channels') and check_table_exists(cursor, 'slave_channels'):
            # 如果两个表都存在，迁移数据
            print("  ℹ️  channels 和 slave_channels 都存在，检查是否需要迁移数据...")
            old_cols = get_table_columns(cursor, 'channels')
            new_cols = get_table_columns(cursor, 'slave_channels')
            if set(old_cols) - set(new_cols):
                print("  ⚠️  表结构不同，请手动处理")
        
        # 检查 data_points 表是否存在（可能是 data_points 或 data）
        if check_table_exists(cursor, 'data') and not check_table_exists(cursor, 'data_points'):
            print("  ➕ 重命名 data 表为 data_points")
            cursor.execute("ALTER TABLE data RENAME TO data_points")
        
        conn.commit()
        
        # ============ 2. 升级 users 表 ============
        print("\n🔍 检查 users 表...")
        
        new_user_columns = [
            ('email', 'VARCHAR(120)'),
            ('is_active', 'BOOLEAN DEFAULT 1'),
            ('last_login_at', 'DATETIME'),
            ('last_login_ip', 'VARCHAR(45)'),
            ('failed_login_count', 'INTEGER DEFAULT 0'),
            ('locked_until', 'DATETIME'),
        ]
        
        for column, col_type in new_user_columns:
            if not check_column_exists(cursor, 'users', column):
                print(f"  ➕ 添加列 users.{column}")
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {col_type}")
                except Exception as e:
                    print(f"  ⚠️  添加列失败: {e}")
            else:
                print(f"  ✅ users.{column} 已存在")
        
        # 设置默认邮箱
        cursor.execute("UPDATE users SET email = username || '@example.com' WHERE email IS NULL OR email = ''")
        
        # ============ 3. 创建 device_groups 表 ============
        print("\n🔍 检查 device_groups 表...")
        
        if not check_table_exists(cursor, 'device_groups'):
            print("  ➕ 创建 device_groups 表")
            cursor.execute("""
                CREATE TABLE device_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(64) NOT NULL,
                    description TEXT,
                    color VARCHAR(20) DEFAULT '#3498db',
                    user_id INTEGER NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        else:
            print("  ✅ device_groups 表已存在")
        
        # ============ 4. 升级 devices 表 ============
        print("\n🔍 检查 devices 表...")
        
        device_columns = [
            ('group_id', 'INTEGER REFERENCES device_groups(id)'),
            ('is_online', 'BOOLEAN DEFAULT 0'),
            ('last_seen_at', 'DATETIME'),
            ('device_type', 'VARCHAR(50)'),
        ]
        
        for column, col_type in device_columns:
            if check_table_exists(cursor, 'devices') and not check_column_exists(cursor, 'devices', column):
                print(f"  ➕ 添加列 devices.{column}")
                try:
                    cursor.execute(f"ALTER TABLE devices ADD COLUMN {column} {col_type}")
                except Exception as e:
                    print(f"  ⚠️  添加列失败: {e}")
            elif check_table_exists(cursor, 'devices'):
                print(f"  ✅ devices.{column} 已存在")
            else:
                print("  ⚠️  devices 表不存在")
        
        # ============ 5. 升级 slave_channels 表 ============
        print("\n🔍 检查 slave_channels 表...")
        
        channel_columns = [
            ('last_data_at', 'DATETIME'),
        ]
        
        for column, col_type in channel_columns:
            if check_table_exists(cursor, 'slave_channels') and not check_column_exists(cursor, 'slave_channels', column):
                print(f"  ➕ 添加列 slave_channels.{column}")
                try:
                    cursor.execute(f"ALTER TABLE slave_channels ADD COLUMN {column} {col_type}")
                except Exception as e:
                    print(f"  ⚠️  添加列失败: {e}")
            elif check_table_exists(cursor, 'slave_channels'):
                print(f"  ✅ slave_channels.{column} 已存在")
        
        # ============ 6. 创建 login_logs 表 ============
        print("\n🔍 检查 login_logs 表...")
        
        if not check_table_exists(cursor, 'login_logs'):
            print("  ➕ 创建 login_logs 表")
            cursor.execute("""
                CREATE TABLE login_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username VARCHAR(64),
                    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    success BOOLEAN DEFAULT 1,
                    failure_reason VARCHAR(255),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        else:
            print("  ✅ login_logs 表已存在")
        
        # ============ 7. 创建 system_configs 表 ============
        print("\n🔍 检查 system_configs 表...")
        
        if not check_table_exists(cursor, 'system_configs'):
            print("  ➕ 创建 system_configs 表")
            cursor.execute("""
                CREATE TABLE system_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key VARCHAR(64) UNIQUE NOT NULL,
                    value TEXT,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            default_configs = [
                ('site_name', 'IoT 数据平台', '网站名称'),
                ('tcp_base_port', '9105', 'TCP基础端口'),
                ('max_login_attempts', '5', '最大登录尝试次数'),
                ('login_lockout_minutes', '5', '登录锁定分钟数'),
            ]
            cursor.executemany(
                "INSERT INTO system_configs (key, value, description) VALUES (?, ?, ?)",
                default_configs
            )
        else:
            print("  ✅ system_configs 表已存在")
        
        # ============ 8. 创建索引 ============
        print("\n🔍 创建索引...")
        
        indexes = [
            ('idx_users_username', 'users(username)'),
            ('idx_users_email', 'users(email)'),
            ('idx_devices_user_id', 'devices(user_id)'),
            ('idx_devices_group_id', 'devices(group_id)'),
            ('idx_devices_is_online', 'devices(is_online)'),
            ('idx_slave_channels_device_id', 'slave_channels(device_id)'),
            ('idx_data_points_channel_id', 'data_points(channel_id)'),
            ('idx_data_points_timestamp', 'data_points(timestamp)'),
            ('idx_device_groups_user_id', 'device_groups(user_id)'),
            ('idx_login_logs_user_id', 'login_logs(user_id)'),
            ('idx_login_logs_login_time', 'login_logs(login_time)'),
        ]
        
        for idx_name, idx_def in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
                print(f"  ✅ 索引 {idx_name}")
            except Exception as e:
                print(f"  ⚠️ 索引 {idx_name}: {e}")
        
        conn.commit()
        print("\n✅ 数据库升级完成！")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 升级失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def show_db_info():
    """显示数据库信息"""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n📊 数据库表结构:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"\n  {table_name} ({count} 条记录)")
        print(f"    列: {', '.join(columns)}")
    
    conn.close()

if __name__ == '__main__':
    print("=" * 50)
    print("IoT 数据平台 v3.0 数据库升级工具")
    print("=" * 50)
    
    db_path = get_db_path()
    print(f"\n📦 数据库路径: {db_path}")
    
    if os.path.exists(db_path):
        show_db_info()
    
    print("\n⚠️  重要提醒：请确保已备份数据库文件！")
    print(f"   备份命令: cp {db_path} {db_path}.backup")
    
    response = input("\n是否继续升级？(y/n): ")
    if response.lower() != 'y':
        print("❌ 升级已取消")
        sys.exit(0)
    
    success = upgrade_database()
    
    if success:
        print("\n📊 升级后的数据库结构:")
        show_db_info()
    
    sys.exit(0 if success else 1)
