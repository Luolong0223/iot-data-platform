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
    # 尝试多个可能的数据库路径
    possible_paths = [
        'instance/database.db',  # Flask 默认 instance 目录
        'database.db',           # 根目录
        'data.sqlite',           # 旧版本命名
        'instance/data.sqlite',  # instance 目录旧版本
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # 如果都不存在，返回默认路径（会在后面提示错误）
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

def upgrade_database():
    """执行数据库升级"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请确保数据库文件存在后再运行此脚本")
        return False
    
    print(f"📦 数据库文件: {db_path}")
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # ========== 1. 升级 users 表 ==========
        print("\n🔍 检查 users 表...")
        
        # 需要添加的新列
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
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {col_type}")
            else:
                print(f"  ✅ users.{column} 已存在")
        
        # 为已存在的用户设置默认邮箱
        cursor.execute("UPDATE users SET email = username || '@example.com' WHERE email IS NULL OR email = ''")
        
        # ========== 2. 创建设备分组表 ==========
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
        
        # ========== 3. 为 devices 表添加分组字段 ==========
        print("\n🔍 检查 devices 表...")
        
        if not check_column_exists(cursor, 'devices', 'group_id'):
            print("  ➕ 添加列 devices.group_id")
            cursor.execute("ALTER TABLE devices ADD COLUMN group_id INTEGER REFERENCES device_groups(id)")
        else:
            print("  ✅ devices.group_id 已存在")
        
        if not check_column_exists(cursor, 'devices', 'is_online'):
            print("  ➕ 添加列 devices.is_online")
            cursor.execute("ALTER TABLE devices ADD COLUMN is_online BOOLEAN DEFAULT 0")
        else:
            print("  ✅ devices.is_online 已存在")
        
        if not check_column_exists(cursor, 'devices', 'last_seen_at'):
            print("  ➕ 添加列 devices.last_seen_at")
            cursor.execute("ALTER TABLE devices ADD COLUMN last_seen_at DATETIME")
        else:
            print("  ✅ devices.last_seen_at 已存在")
        
        # ========== 4. 创建登录日志表 ==========
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
        
        # ========== 5. 创建系统配置表 ==========
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
            
            # 插入默认配置
            default_configs = [
                ('site_name', 'IoT 数据平台', '网站名称'),
                ('tcp_base_port', '9000', 'TCP基础端口'),
                ('max_login_attempts', '5', '最大登录尝试次数'),
                ('login_lockout_minutes', '5', '登录锁定分钟数'),
            ]
            cursor.executemany(
                "INSERT INTO system_configs (key, value, description) VALUES (?, ?, ?)",
                default_configs
            )
        else:
            print("  ✅ system_configs 表已存在")
        
        # ========== 6. 创建索引 ==========
        print("\n🔍 创建索引...")
        
        indexes = [
            ('idx_users_username', 'users(username)'),
            ('idx_users_email', 'users(email)'),
            ('idx_devices_user_id', 'devices(user_id)'),
            ('idx_devices_group_id', 'devices(group_id)'),
            ('idx_devices_is_online', 'devices(is_online)'),
            ('idx_channels_device_id', 'channels(device_id)'),
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
        
        # 提交更改
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

if __name__ == '__main__':
    print("=" * 50)
    print("IoT 数据平台 v3.0 数据库升级工具")
    print("=" * 50)
    
    # 备份提醒
    print("\n⚠️  重要提醒：请确保已备份数据库文件！")
    print("   备份命令: cp data.sqlite data.sqlite.backup")
    
    response = input("\n是否继续升级？(y/n): ")
    if response.lower() != 'y':
        print("❌ 升级已取消")
        sys.exit(0)
    
    success = upgrade_database()
    sys.exit(0 if success else 1)
