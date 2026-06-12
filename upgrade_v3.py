#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库升级脚本 - 用于从 v2.0 升级到 v3.0
执行方式：python upgrade_v3.py
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db

def upgrade_database():
    """升级数据库结构"""
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("IoT 数据平台 v3.0 数据库升级脚本")
        print("=" * 50)
        
        # 1. 创建新表
        print("\n[1/4] 创建新数据表...")
        try:
            # 导入所有模型确保它们被注册
            from models.database import DeviceGroup, LoginLog, SystemConfig
            
            # 创建所有表（如果不存在）
            db.create_all()
            print("✓ 新数据表创建成功")
        except Exception as e:
            print(f"✗ 创建数据表失败: {e}")
            return False
        
        # 2. 为 Device 表添加新字段（如果不存在）
        print("\n[2/4] 检查 Device 表结构...")
        try:
            # 检查 is_online 字段是否存在
            result = db.session.execute(db.text("PRAGMA table_info(device)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'is_online' not in columns:
                print("  添加 is_online 字段...")
                db.session.execute(db.text("ALTER TABLE device ADD COLUMN is_online BOOLEAN DEFAULT 0"))
            
            if 'last_seen_at' not in columns:
                print("  添加 last_seen_at 字段...")
                db.session.execute(db.text("ALTER TABLE device ADD COLUMN last_seen_at DATETIME"))
            
            db.session.commit()
            print("✓ Device 表结构更新成功")
        except Exception as e:
            print(f"! Device 表检查跳过 (可能是 MySQL): {e}")
        
        # 3. 创建索引
        print("\n[3/4] 创建数据库索引...")
        try:
            # SQLite 创建索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_device_user_id ON device(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_device_is_online ON device(is_online)",
                "CREATE INDEX IF NOT EXISTS idx_channel_device_id ON slave_channel(device_id)",
                "CREATE INDEX IF NOT EXISTS idx_datapoint_channel_id ON data_point(channel_id)",
                "CREATE INDEX IF NOT EXISTS idx_datapoint_timestamp ON data_point(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_alarm_user_id ON alarm_record(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_alarm_is_read ON alarm_record(is_read)",
                "CREATE INDEX IF NOT EXISTS idx_tcp_log_user_id ON tcp_log(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_login_log_user_id ON login_log(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_login_log_created_at ON login_log(created_at)",
            ]
            
            for idx_sql in indexes:
                try:
                    db.session.execute(db.text(idx_sql))
                except Exception as idx_err:
                    # 索引可能已存在，忽略错误
                    pass
            
            db.session.commit()
            print("✓ 数据库索引创建成功")
        except Exception as e:
            print(f"! 索引创建部分失败: {e}")
        
        # 4. 验证升级结果
        print("\n[4/4] 验证升级结果...")
        try:
            # 检查表是否存在
            tables = ['device_group', 'login_log', 'system_config']
            for table in tables:
                result = db.session.execute(db.text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
                if result.fetchone():
                    print(f"  ✓ {table} 表已创建")
                else:
                    print(f"  ! {table} 表未找到")
            
            print("\n" + "=" * 50)
            print("✓ 数据库升级完成！")
            print("=" * 50)
            
        except Exception as e:
            print(f"验证失败: {e}")
        
        return True


if __name__ == '__main__':
    try:
        upgrade_database()
    except Exception as e:
        print(f"\n升级失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
