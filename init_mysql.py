#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IoT 数据平台 MySQL 数据库初始化脚本
用于在MySQL数据库中创建所有表结构
"""

import sys

def init_database():
    """初始化MySQL数据库"""
    try:
        # 先安装pymysql
        import pymysql
        pymysql.install_as_MySQLdb()
        
        from app import create_app
        from models.database import db
        
        print("=" * 50)
        print("IoT 数据平台 MySQL 数据库初始化")
        print("=" * 50)
        
        app = create_app()
        
        with app.app_context():
            print("\n📦 正在连接MySQL数据库...")
            
            # 测试连接
            try:
                connection = db.engine.connect()
                connection.close()
                print("✅ 数据库连接成功！")
            except Exception as e:
                print(f"❌ 数据库连接失败: {e}")
                print("\n请检查:")
                print("1. MySQL服务是否启动")
                print("2. 数据库 'iot-platform' 是否已创建")
                print("3. 用户名密码是否正确")
                print("\n创建数据库命令:")
                print("CREATE DATABASE `iot-platform` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                print("CREATE USER 'iot-platform'@'%' IDENTIFIED BY 'cRwLGPScNejLEeBt';")
                print("GRANT ALL PRIVILEGES ON `iot-platform`.* TO 'iot-platform'@'%';")
                print("FLUSH PRIVILEGES;")
                return False
            
            print("\n📦 正在创建数据表...")
            
            # 创建所有表
            db.create_all()
            
            print("✅ 数据表创建成功！")
            
            # 检查是否有管理员用户
            from models.database import User
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                print("\n📦 创建默认管理员账号...")
                admin = User(
                    username='admin',
                    is_admin=True,
                    is_active=True,
                    tcp_port=9105
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ 管理员账号创建成功！")
                print("   用户名: admin")
                print("   密码: admin123")
            else:
                print("\n✅ 管理员账号已存在")
            
            print("\n" + "=" * 50)
            print("✅ 数据库初始化完成！")
            print("=" * 50)
            
            # 显示创建的表
            print("\n📋 已创建的数据表:")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            for table in sorted(tables):
                print(f"   - {table}")
            
            return True
            
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("\n请先安装依赖:")
        print("pip install PyMySQL cryptography")
        return False
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
