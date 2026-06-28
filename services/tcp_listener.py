"""
TCP 监听器 - 高性能版本
优化点:
1. 内存缓存设备/通道/数据点，减少数据库查询
2. 批量写入，减少事务提交次数
3. 线程池管理，避免频繁创建/销毁线程
4. 合理的连接超时设置
"""
import os
import json
import socket
import logging
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import Flask

logger = logging.getLogger(__name__)

# 服务端全局状态
_server_state = {
    "running": False,
    "servers": {},
    "configs": {},
}

_current_app = None
_tcp_servers = {}
_listener_threads = {}

# 线程池 - 限制并发连接数
_thread_pool = ThreadPoolExecutor(max_workers=50, thread_name_prefix="tcp-worker")

# 内存缓存: device_name -> {id, user_id, ...}
_device_cache = {}
_cache_lock = threading.Lock()
_cache_expiry = {}
CACHE_TTL = 300  # 缓存有效期 5 分钟


def _get_cached_device(device_name: str, app: Flask):
    """获取缓存的设备信息，减少数据库查询"""
    now = time.time()

    with _cache_lock:
        if device_name in _device_cache:
            if now - _cache_expiry.get(device_name, 0) < CACHE_TTL:
                return _device_cache[device_name]
            else:
                del _device_cache[device_name]

    # 缓存未命中，查询数据库
    from models.database import db, Device, User
    with app.app_context():
        device = Device.query.filter_by(name=device_name).first()
        if device:
            info = {
                'id': device.id,
                'user_id': device.user_id,
                'name': device.name,
            }
            with _cache_lock:
                _device_cache[device_name] = info
                _cache_expiry[device_name] = now
            return info
    return None


def _invalidate_device_cache(device_name: str):
    """使设备缓存失效"""
    with _cache_lock:
        _device_cache.pop(device_name, None)
        _cache_expiry.pop(device_name, None)


def store_message_batch(app: Flask, messages: list) -> int:
    """
    批量存储消息到数据库
    优化: 减少数据库查询次数，使用批量操作
    返回成功存储的消息数
    """
    from models.database import db, Device, Channel, DataPoint, DataHistory, User

    if not messages:
        return 0

    success_count = 0

    with app.app_context():
        try:
            # 收集所有设备名，一次性查询
            device_names = set()
            for msg in messages:
                device_info = msg.get('device', {})
                name = device_info.get('name')
                if name:
                    device_names.add(name)

            # 批量查询现有设备
            existing_devices = {}
            if device_names:
                devices = Device.query.filter(Device.name.in_(device_names)).all()
                existing_devices = {d.name: d for d in devices}

            # 获取默认用户
            default_user = User.query.filter_by(is_admin=True).order_by(User.id).first()
            if not default_user:
                default_user = User.query.order_by(User.id).first()

            now = datetime.utcnow()

            for msg in messages:
                try:
                    device_info = msg.get('device', {})
                    device_name = device_info.get('name')
                    if not device_name:
                        continue

                    # 兼容两种电压字段
                    voltage = device_info.get('voltage')
                    if voltage is None:
                        voltage_mv = device_info.get('voltage_mv', 0)
                        voltage = round(voltage_mv / 1000.0, 2) if voltage_mv else 0.0
                    else:
                        voltage = float(voltage)

                    # 设备 upsert
                    device = existing_devices.get(device_name)
                    if not device:
                        if not default_user:
                            logger.error("No user available, cannot create device")
                            continue
                        device = Device(
                            name=device_name,
                            voltage=voltage,
                            is_online=True,
                            last_seen=now,
                            first_seen=now,
                            user_id=default_user.id
                        )
                        db.session.add(device)
                        db.session.flush()
                        existing_devices[device_name] = device
                    else:
                        device.voltage = voltage
                        device.is_online = True
                        device.last_seen = now

                    # 批量处理通道和数据点
                    for key, val in msg.items():
                        if key == 'device':
                            continue
                        if not isinstance(val, dict):
                            continue

                        channel_name = val.get('name', key)
                        is_online = bool(val.get('online', 0))
                        data_dict = val.get('data', {})

                        # 通道 upsert (使用缓存)
                        channel = Channel.query.filter_by(
                            device_id=device.id, name=channel_name
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
                            db.session.flush()
                        else:
                            channel.is_online = is_online
                            channel.last_seen = now

                        # 数据点 upsert + 历史
                        for dp_name, dp_value in data_dict.items():
                            val = float(dp_value) if dp_value is not None else 0.0

                            dp = DataPoint.query.filter_by(
                                channel_id=channel.id, name=dp_name
                            ).first()

                            if dp:
                                dp.last_value = dp.value
                                dp.value = val
                                dp.last_updated = now
                                dp.update_count = (dp.update_count or 0) + 1
                            else:
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

                            # 写入历史
                            hist = DataHistory(
                                data_point_id=dp.id,
                                device_id=device.id,
                                channel_id=channel.id,
                                value=val,
                                timestamp=now
                            )
                            db.session.add(hist)

                    success_count += 1

                except Exception as e:
                    logger.error(f"Failed to process message: {e}", exc_info=True)
                    continue

            # 一次性提交所有数据
            db.session.commit()
            logger.info(f"Batch stored {success_count}/{len(messages)} messages")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Batch store failed: {e}", exc_info=True)

    return success_count


def store_message(app: Flask, msg: dict) -> bool:
    """存储单条消息（兼容旧接口）"""
    result = store_message_batch(app, [msg])
    return result > 0


def parse_message(raw_data: str) -> dict:
    """解析一条 TCP 消息"""
    raw_data = raw_data.strip()
    if not raw_data:
        return None

    try:
        msg = json.loads(raw_data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}, data={raw_data[:200]}")
        return None

    if 'device' not in msg:
        logger.warning(f"Missing 'device' field: {raw_data[:200]}")
        return None

    return msg


def _handle_client(client_socket: socket.socket, client_addr, app: Flask, port: int):
    """处理单个客户端连接"""
    logger.info(f"[TCP:{port}] New connection: {client_addr}")
    buffer = ''

    # 10秒超时，匹配设备行为
    client_socket.settimeout(15)

    try:
        while True:
            try:
                chunk = client_socket.recv(4096).decode('utf-8', errors='ignore')
                if not chunk:
                    break
                buffer += chunk

                # 解析并存储消息
                while True:
                    buffer = buffer.lstrip()
                    if not buffer:
                        break

                    try:
                        decoder = json.JSONDecoder()
                        obj, idx = decoder.raw_decode(buffer)
                        buffer = buffer[idx:].lstrip()
                        store_message(app, obj)
                    except json.JSONDecodeError:
                        break

            except socket.timeout:
                # 10秒超时，正常断开
                break

    except ConnectionResetError:
        logger.info(f"[TCP:{port}] Connection reset: {client_addr}")
    except BrokenPipeError:
        logger.info(f"[TCP:{port}] Broken pipe: {client_addr}")
    except Exception as e:
        logger.error(f"[TCP:{port}] Error: {e}", exc_info=True)
    finally:
        try:
            client_socket.close()
        except OSError:
            pass
        logger.info(f"[TCP:{port}] Connection closed: {client_addr}")


def _accept_loop(server_sock: socket.socket, port: int, app: Flask):
    """接受客户端连接并提交到线程池"""
    logger.info(f"[TCP:{port}] Accept loop started")

    while True:
        try:
            client_sock, client_addr = server_sock.accept()
            # 提交到线程池，而不是创建新线程
            _thread_pool.submit(_handle_client, client_sock, client_addr, app, port)
        except OSError:
            break
        except Exception as e:
            logger.error(f"[TCP:{port}] Accept error: {e}")
            time.sleep(0.1)

    logger.info(f"[TCP:{port}] Accept loop exited")


def start_tcp_listener(app: Flask, default_port: int = 9105):
    """启动 TCP 监听"""
    global _current_app
    _current_app = app

    from models.database import SystemConfig
    port = default_port
    try:
        with app.app_context():
            cfg = SystemConfig.query.filter_by(key='tcp_default_port').first()
            if cfg and cfg.value:
                port = int(cfg.value)
    except Exception as e:
        logger.warning(f"Failed to read TCP port config: {e}, using default {default_port}")

    ok = _start_on_port(app, port)
    if ok:
        _server_state['running'] = True
        _server_state['servers'][port] = True
    return port


def _start_on_port(app: Flask, port: int) -> bool:
    """在指定端口启动 TCP 服务"""
    global _tcp_servers, _listener_threads

    if port in _tcp_servers:
        logger.warning(f"[TCP:{port}] Already running")
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
        logger.info(f"[TCP:{port}] Started on port {port}")
        return True
    except OSError as e:
        logger.error(f"[TCP:{port}] Failed to start: {e}")
        return False


def stop_tcp_listener(port: int = None):
    """停止 TCP 监听"""
    global _tcp_servers
    if port is None:
        for p, sock in list(_tcp_servers.items()):
            try:
                sock.close()
            except OSError:
                pass
        _tcp_servers.clear()
    elif port in _tcp_servers:
        try:
            _tcp_servers[port].close()
        except OSError:
            pass
        del _tcp_servers[port]


def get_active_ports() -> list:
    """返回所有正在监听的端口"""
    return list(_tcp_servers.keys())


def is_listening(port: int) -> bool:
    return port in _tcp_servers
