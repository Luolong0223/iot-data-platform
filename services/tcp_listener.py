"""
TCP 监听器 - 多端口可配置
解析协议格式:
{
  "device": {"name": "Collector-1", "voltage_mv": 3037},
  "s1": {"name": "Slave-1", "online": 1, "data": {"Data-1": 0.0000}},
  "s2": {"name": "Slave-2", "online": 1, "data": {"P1": 0.0000}}
}
"""
import os
import json
import socket
import logging
import threading
import time
from datetime import datetime
from flask import Flask

logger = logging.getLogger(__name__)

# 服务端全局状态
_server_state = {
    "running": False,
    "servers": {},   # port -> server_thread
    "configs": {},   # port -> TcpServerConfig
}

# 状态：保存当前应用的引用
_current_app = None
_tcp_servers = {}  # {port: server_socket}
_listener_threads = {}  # {port: thread}


def parse_message(raw_data: str) -> dict:
    """
    解析一条 TCP 消息,返回规范化字典
    格式: {"device": {"name": ..., "voltage_mv": ...}, "<key>": {"name": ..., "online": ..., "data": {...}}}
    """
    raw_data = raw_data.strip()
    if not raw_data:
        return None

    try:
        msg = json.loads(raw_data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}, data={raw_data[:200]}")
        return None

    if 'device' not in msg:
        logger.warning(f"消息缺少 device 字段: {raw_data[:200]}")
        return None

    return msg


def store_message(app: Flask, msg: dict) -> bool:
    """
    存储一条消息到数据库
    - 创建或更新 Device
    - 为每个通道 (s1, s2, ...) 创建或更新 Channel
    - 存储每个数据点 DataPoint
    """
    from models.database import db, Device, Channel, DataPoint

    with app.app_context():
        try:
            device_info = msg.get('device', {})
            device_name = device_info.get('name')
            if not device_name:
                logger.warning("device.name 缺失")
                return False

            voltage_mv = device_info.get('voltage_mv', 0)
            now = datetime.utcnow()

            # 1. 设备 upsert
            from models.database import User
            device = Device.query.filter_by(name=device_name).first()
            if not device:
                # 找到第一个 admin 用户(TCP 接收的数据归属)
                owner = User.query.filter_by(is_admin=True).order_by(User.id).first()
                if not owner:
                    owner = User.query.order_by(User.id).first()
                if not owner:
                    logger.error("无用户,无法创建设备")
                    return False
                device = Device(
                    name=device_name,
                    voltage_mv=voltage_mv,
                    is_online=True,
                    last_seen=now,
                    first_seen=now,
                    user_id=owner.id
                )
                db.session.add(device)
            else:
                device.voltage_mv = voltage_mv
                device.is_online = True
                device.last_seen = now
            db.session.flush()  # 获取 device.id

            # 2. 遍历所有通道 (s1, s2, ...)
            for key, val in msg.items():
                if key == 'device':
                    continue
                if not isinstance(val, dict):
                    continue

                channel_name = val.get('name', key)
                is_online = bool(val.get('online', 0))
                data_dict = val.get('data', {})

                # 通道 upsert
                channel = Channel.query.filter_by(
                    device_id=device.id,
                    name=channel_name
                ).first()

                if not channel:
                    channel = Channel(
                        device_id=device.id,
                        name=channel_name,
                        is_online=is_online,
                        last_seen=now,
                        first_seen=now
                    )
                    db.session.add(channel)
                else:
                    channel.is_online = is_online
                    channel.last_seen = now
                db.session.flush()

                # 3. 存储所有数据点 (upsert + 历史)
                from models.database import DataHistory
                for dp_name, dp_value in data_dict.items():
                    val = float(dp_value) if dp_value is not None else 0.0
                    dp = DataPoint.query.filter_by(
                        channel_id=channel.id, name=dp_name
                    ).first()
                    if not dp:
                        dp = DataPoint(
                            channel_id=channel.id,
                            name=dp_name,
                            value=val,
                            last_value=0.0,
                            last_updated=now,
                            update_count=1
                        )
                        db.session.add(dp)
                        db.session.flush()
                    else:
                        dp.last_value = dp.value
                        dp.value = val
                        dp.last_updated = now
                        dp.update_count = (dp.update_count or 0) + 1
                    # 写入历史
                    hist = DataHistory(
                        data_point_id=dp.id,
                        device_id=device.id,
                        channel_id=channel.id,
                        value=val,
                        timestamp=now
                    )
                    db.session.add(hist)

            db.session.commit()
            logger.info(f"存储成功: 设备={device_name}, 通道数={len(msg) - 1}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"存储消息失败: {e}", exc_info=True)
            return False


def _handle_client(client_socket: socket.socket, client_addr, app: Flask, port: int):
    """处理单个客户端连接"""
    logger.info(f"[TCP:{port}] 新连接: {client_addr}")
    buffer = ''
    try:
        client_socket.settimeout(60)
        while True:
            chunk = client_socket.recv(4096).decode('utf-8', errors='ignore')
            if not chunk:
                break
            buffer += chunk

            # 尝试按行或按 JSON 完整对象处理
            # 简单策略: 尝试逐个解析 buffer
            while True:
                # 寻找一个完整的 JSON 对象
                buffer = buffer.lstrip()
                if not buffer:
                    break

                # 尝试从 buffer 开头解析一个 JSON
                try:
                    decoder = json.JSONDecoder()
                    obj, idx = decoder.raw_decode(buffer)
                    buffer = buffer[idx:].lstrip()

                    # 存储
                    store_message(app, obj)

                except json.JSONDecodeError:
                    # 还没收到完整 JSON, 继续接收
                    break

    except socket.timeout:
        logger.info(f"[TCP:{port}] 连接超时: {client_addr}")
    except Exception as e:
        logger.error(f"[TCP:{port}] 处理异常: {e}", exc_info=True)
    finally:
        try:
            client_socket.close()
        except:
            pass
        logger.info(f"[TCP:{port}] 连接关闭: {client_addr}")


def _accept_loop(server_sock: socket.socket, port: int, app: Flask):
    """在独立线程中接受客户端连接"""
    logger.info(f"[TCP:{port}] 监听线程已启动")
    try:
        while True:
            try:
                client_sock, client_addr = server_sock.accept()
                t = threading.Thread(
                    target=_handle_client,
                    args=(client_sock, client_addr, app, port),
                    daemon=True
                )
                t.start()
            except OSError:
                # 服务器 socket 被关闭
                break
            except Exception as e:
                logger.error(f"[TCP:{port}] accept 异常: {e}")
                time.sleep(1)
    except Exception as e:
        logger.error(f"[TCP:{port}] 监听线程异常: {e}", exc_info=True)
    finally:
        logger.info(f"[TCP:{port}] 监听线程退出")


def start_tcp_listener(app: Flask, default_port: int = 9105):
    """
    启动默认端口的 TCP 监听
    """
    global _current_app
    _current_app = app

    # 读取用户配置 (从系统设置)
    from models.database import SystemConfig
    port = default_port
    try:
        with app.app_context():
            cfg = SystemConfig.query.filter_by(key='tcp_default_port').first()
            if cfg and cfg.value:
                port = int(cfg.value)
    except Exception as e:
        logger.warning(f"读取 TCP 端口配置失败: {e}, 使用默认 {default_port}")

    # 启动
    ok = _start_on_port(app, port)
    if ok:
        _server_state['running'] = True
        _server_state['servers'][port] = True
    return port


def _start_on_port(app: Flask, port: int) -> bool:
    """在指定端口启动 TCP 服务"""
    global _tcp_servers, _listener_threads

    if port in _tcp_servers:
        logger.warning(f"[TCP:{port}] 已在运行")
        return True

    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('0.0.0.0', port))
        server_sock.listen(128)

        thread = threading.Thread(
            target=_accept_loop,
            args=(server_sock, port, app),
            daemon=True
        )
        thread.start()

        _tcp_servers[port] = server_sock
        _listener_threads[port] = thread
        logger.info(f"[TCP:{port}] ✅ 监听已启动")
        return True
    except OSError as e:
        logger.error(f"[TCP:{port}] 启动失败: {e}")
        return False
    except Exception as e:
        logger.error(f"[TCP:{port}] 启动异常: {e}")
        return False


def stop_tcp_listener(port: int = None):
    """停止 TCP 监听"""
    global _tcp_servers
    if port is None:
        # 停止所有
        for p, sock in list(_tcp_servers.items()):
            try:
                sock.close()
            except:
                pass
        _tcp_servers.clear()
    elif port in _tcp_servers:
        try:
            _tcp_servers[port].close()
        except:
            pass
        del _tcp_servers[port]


def get_active_ports() -> list:
    """返回所有正在监听的端口"""
    return list(_tcp_servers.keys())


def is_listening(port: int) -> bool:
    return port in _tcp_servers
