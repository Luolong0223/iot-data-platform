#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TCP 服务器诊断和修复工具
"""

import os
import sys
import socket
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
    
    return None

def check_port_available(port):
    """检查端口是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0  # 0 表示端口有服务在监听
    except:
        return False

def check_port_listening(port):
    """检查端口是否在监听"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True  # 端口空闲，可以绑定
    except OSError:
        return False  # 端口被占用

def main():
    print("=" * 60)
    print("TCP 服务器诊断工具")
    print("=" * 60)
    
    # 1. 检查数据库
    print("\n[1] 检查数据库...")
    db_path = get_db_path()
    if not db_path:
        print("  ❌ 未找到数据库文件")
        return
    print(f"  ✅ 数据库: {db_path}")
    
    # 2. 检查用户和端口分配
    print("\n[2] 检查用户TCP端口分配...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, tcp_port, storage_enabled FROM users")
    users = cursor.fetchall()
    
    if not users:
        print("  ❌ 没有用户")
        conn.close()
        return
    
    for user_id, username, tcp_port, storage_enabled in users:
        print(f"\n  用户: {username} (ID: {user_id})")
        print(f"    TCP端口: {tcp_port}")
        print(f"    存储启用: {'是' if storage_enabled else '否'}")
        
        if tcp_port:
            listening = check_port_available(tcp_port)
            if listening:
                print(f"    ✅ 端口 {tcp_port} 有服务在监听")
            else:
                print(f"    ❌ 端口 {tcp_port} 没有服务监听")
    
    conn.close()
    
    # 3. 测试建议
    print("\n" + "=" * 60)
    print("诊断建议")
    print("=" * 60)
    
    print("""
如果TCP端口没有服务监听，请检查：

1. 确认服务已启动：
   - 在宝塔面板重启Python项目
   - 查看启动日志是否有 TCP 相关错误

2. 检查防火墙：
   - 宝塔面板 -> 安全 -> 放行TCP端口
   - 云服务器安全组 -> 开放TCP端口

3. 查看TCP日志：
   - cat tcp_server.log
   - cat tcp_handler.log

4. 手动测试TCP连接：
   - 在服务器上执行: telnet 127.0.0.1 <端口号>
   - 或: nc -v 127.0.0.1 <端口号>

5. 发送测试数据：
   echo '{"device":{"name":"Test-1","voltage_mv":3000},"s1":{"name":"Slave-1","online":1,"data":{"Data-1":123.45}}}' | nc 127.0.0.1 <端口号>
""")

if __name__ == '__main__':
    main()
