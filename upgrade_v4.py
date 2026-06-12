#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IoT 数据平台 v4.0 数据库升级脚本
用于从 v3.x 升级到 v4.0（设备层级管理、告警规则等）
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

def upgrade_database():
    """执行数据库升级"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("正在创建新数据库...")
    
    print(f"📦 数据库文件: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # ============ 1. 创建项目表 ============
        print("\n🔍 检查 projects 表...")
        
        if not check_table_exists(cursor, 'projects'):
            print("  ➕ 创建 projects 表")
            cursor.execute("""
                CREATE TABLE projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(64) NOT NULL,
                    description TEXT,
                    location VARCHAR(128),
                    user_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        else:
            print("  ✅ projects 表已存在")
        
        # ============ 2. 升级 device_groups 表 ============
        print("\n🔍 检查 device_groups 表...")
        
        if not check_table_exists(cursor, 'device_groups'):
            print("  ➕ 创建 device_groups 表")
            cursor.execute("""
                CREATE TABLE device_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(64) NOT NULL,
                    description TEXT,
                    color VARCHAR(20) DEFAULT '#3498db',
                    project_id INTEGER,
                    parent_id INTEGER,
                    user_id INTEGER NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (parent_id) REFERENCES device_groups(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        else:
            print("  ✅ device_groups 表已存在")
            # 检查是否需要添加新字段
            new_columns = [
                ('project_id', 'INTEGER REFERENCES projects(id)'),
                ('parent_id', 'INTEGER REFERENCES device_groups(id)'),
                ('sort_order', 'INTEGER DEFAULT 0'),
            ]
            for col, col_type in new_columns:
                if not check_column_exists(cursor, 'device_groups', col):
                    print(f"  ➕ 添加列 device_groups.{col}")
                    cursor.execute(f"ALTER TABLE device_groups ADD COLUMN {col} {col_type}")
        
        # ============ 3. 升级 devices 表 ============
        print("\n🔍 检查 devices 表...")
        
        new_device_columns = [
            ('project_id', 'INTEGER REFERENCES projects(id)'),
            ('device_key', 'VARCHAR(64)'),
            ('firmware_version', 'VARCHAR(32)'),
            ('last_maintenance_at', 'DATETIME'),
            ('maintenance_interval', 'INTEGER DEFAULT 30'),
            ('location_name', 'VARCHAR(128)'),
            ('install_date', 'DATETIME'),
        ]
        
        for col, col_type in new_device_columns:
            if not check_column_exists(cursor, 'devices', col):
                print(f"  ➕ 添加列 devices.{col}")
                try:
                    cursor.execute(f"ALTER TABLE devices ADD COLUMN {col} {col_type}")
                except Exception as e:
                    print(f"  ⚠️ 添加列失败: {e}")
            else:
                print(f"  ✅ devices.{col} 已存在")
        
        # ============ 4. 创建告警规则表 ============
        print("\n🔍 检查 alarm_rules 表...")
        
        if not check_table_exists(cursor, 'alarm_rules'):
            print("  ➕ 创建 alarm_rules 表")
            cursor.execute("""
                CREATE TABLE alarm_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(64) NOT NULL,
                    description TEXT,
                    rule_type VARCHAR(20) DEFAULT 'threshold',
                    device_filter TEXT,
                    channel_filter TEXT,
                    data_key VARCHAR(64),
                    operator VARCHAR(10),
                    threshold_value FLOAT,
                    duration_seconds INTEGER DEFAULT 0,
                    alarm_level VARCHAR(20) DEFAULT 'warning',
                    notification_channels TEXT,
                    is_enabled BOOLEAN DEFAULT 1,
                    user_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        else:
            print("  ✅ alarm_rules 表已存在")
        
        # ============ 5. 创建通知配置表 ============
        print("\n🔍 检查 notification_configs 表...")
        
        if not check_table_exists(cursor, 'notification_configs'):
            print("  ➕ 创建 notification_configs 表")
            cursor.execute("""
                CREATE TABLE notification_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(64) NOT NULL,
                    channel_type VARCHAR(20) NOT NULL,
                    config TEXT,
                    is_enabled BOOLEAN DEFAULT 1,
                    user_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        else:
            print("  ✅ notification_configs 表已存在")
        
        # ============ 6. 升级 alarm_records 表 ============
        print("\n🔍 检查 alarm_records 表...")
        
        if check_table_exists(cursor, 'alarms') and not check_table_exists(cursor, 'alarm_records'):
            print("  ➕ 重命名 alarms 表为 alarm_records")
            cursor.execute("ALTER TABLE alarms RENAME TO alarm_records")
        
        if check_table_exists(cursor, 'alarm_records'):
            new_alarm_columns = [
                ('rule_id', 'INTEGER REFERENCES alarm_rules(id)'),
                ('acknowledged_by', 'INTEGER REFERENCES users(id)'),
                ('acknowledged_at', 'DATETIME'),
                ('resolved_by', 'INTEGER REFERENCES users(id)'),
                ('resolved_at', 'DATETIME'),
                ('notes', 'TEXT'),
            ]
            for col, col_type in new_alarm_columns:
                if not check_column_exists(cursor, 'alarm_records', col):
                    print(f"  ➕ 添加列 alarm_records.{col}")
                    try:
                        cursor.execute(f"ALTER TABLE alarm_records ADD COLUMN {col} {col_type}")
                    except Exception as e:
                        print(f"  ⚠️ 添加列失败: {e}")
        
        # ============ 7. 创建索引 ============
        print("\n🔍 创建索引...")
        
        indexes = [
            ('idx_projects_user_id', 'projects(user_id)'),
            ('idx_device_groups_project_id', 'device_groups(project_id)'),
            ('idx_device_groups_parent_id', 'device_groups(parent_id)'),
            ('idx_devices_project_id', 'devices(project_id)'),
            ('idx_devices_device_key', 'devices(device_key)'),
            ('idx_alarm_rules_user_id', 'alarm_rules(user_id)'),
            ('idx_alarm_rules_is_enabled', 'alarm_rules(is_enabled)'),
            ('idx_alarm_records_rule_id', 'alarm_records(rule_id)'),
            ('idx_notification_configs_user_id', 'notification_configs(user_id)'),
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

if __name__ == '__main__':
    print("=" * 50)
    print("IoT 数据平台 v4.0 数据库升级工具")
    print("=" * 50)
    
    print("\n⚠️  重要提醒：请确保已备份数据库文件！")
    
    response = input("\n是否继续升级？(y/n): ")
    if response.lower() != 'y':
        print("❌ 升级已取消")
        sys.exit(0)
    
    success = upgrade_database()
    sys.exit(0 if success else 1)
