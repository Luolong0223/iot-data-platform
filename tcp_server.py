"""
TCP 服务器 - 基于 asyncio 的异步 TCP 服务
"""
import asyncio
import logging
import os
import sys
import threading
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 文件日志
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tcp_server.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 全局状态
servers = {}
tcp_loop = None
tcp_thread = None


class TcpConnectionHandler:
    """TCP 连接处理器"""

    def __init__(self, app, user_id):
        self.app = app
        self.user_id = user_id

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f"TCP connection from {addr} for user {self.user_id}")

        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        reader.read(self.app.config.get('TCP_BUFFER_SIZE', 4096)),
                        timeout=self.app.config.get('TCP_TIMEOUT', 300)
                    )
                except asyncio.TimeoutError:
                    logger.info(f"TCP connection timeout for {addr}")
                    break

                if not data:
                    logger.info(f"TCP client {addr} disconnected")
                    break

                raw_data = data.decode('utf-8', errors='replace').strip()
                if not raw_data:
                    continue

                # 处理数据
                try:
                    with self.app.app_context():
                        from services.tcp_handler import process_tcp_data
                        process_tcp_data(self.user_id, raw_data, addr[0] if addr else None)
                except Exception as e:
                    logger.error(f"TCP data processing error for {addr}: {e}", exc_info=True)

        except ConnectionResetError:
            logger.info(f"TCP connection reset by {addr}")
        except BrokenPipeError:
            logger.info(f"TCP connection broken pipe for {addr}")
        except Exception as e:
            logger.error(f"TCP connection error for {addr}: {e}", exc_info=True)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info(f"TCP connection closed for {addr}")


async def start_user_server(handler, user_id, port, host):
    """启动用户 TCP 服务器"""
    logger.info(f"[TCP] Attempting to start server for user {user_id} on {host}:{port}")
    try:
        server = await asyncio.start_server(
            handler.handle_client,
            host,
            port
        )
        servers[user_id] = server
        logger.info(f"[TCP] Server started for user {user_id} on port {port}")
        return server
    except OSError as e:
        logger.error(f"[TCP] OSError starting server for user {user_id} on port {port}: {e}")
        return None
    except Exception as e:
        logger.error(f"[TCP] Error starting server for user {user_id}: {e}", exc_info=True)
        raise


async def stop_user_server(user_id):
    """停止用户 TCP 服务器"""
    server = servers.pop(user_id, None)
    if server:
        server.close()
        await server.wait_closed()
        logger.info(f"[TCP] Server stopped for user {user_id}")


async def refresh_servers(app, handler_class):
    """刷新所有用户 TCP 服务器"""
    logger.info("[TCP] Refreshing servers...")
    try:
        with app.app_context():
            from models.database import User
            users = User.query.filter(User.is_active == True).all()
    except Exception as e:
        logger.error(f"[TCP] Failed to query users: {e}", exc_info=True)
        return

    logger.info(f"[TCP] Found {len(users)} active users")
    active_user_ids = set()
    for user in users:
        active_user_ids.add(user.id)
        if user.id not in servers:
            try:
                handler = handler_class(app, user.id)
                await start_user_server(
                    handler, user.id,
                    app.config.get('TCP_BASE_PORT', 9105) + user.id,
                    app.config.get('TCP_HOST', '0.0.0.0')
                )
            except Exception as e:
                logger.error(f"[TCP] Failed to start server for user {user.id}: {e}", exc_info=True)

    # 停止不再活跃的服务器
    for user_id in list(servers.keys()):
        if user_id not in active_user_ids:
            await stop_user_server(user_id)


async def server_main(app, handler_class):
    """TCP 服务器主循环"""
    logger.info("[TCP] Starting TCP server main loop...")
    await refresh_servers(app, handler_class)

    try:
        while True:
            await asyncio.sleep(30)
            await refresh_servers(app, handler_class)
    except asyncio.CancelledError:
        logger.info("[TCP] Main loop cancelled")
    finally:
        for user_id in list(servers.keys()):
            await stop_user_server(user_id)


def run_tcp_server(app, handler_class):
    """在新线程中启动 TCP 服务器"""
    global tcp_loop, tcp_thread

    def tcp_thread_target():
        global tcp_loop
        logger.info("[TCP] TCP thread started")
        tcp_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(tcp_loop)

        try:
            tcp_loop.run_until_complete(server_main(app, handler_class))
        except Exception as e:
            logger.error(f"[TCP] Server error: {e}", exc_info=True)
        finally:
            logger.info("[TCP] Closing event loop")
            tcp_loop.close()
            tcp_loop = None

    tcp_thread = threading.Thread(target=tcp_thread_target, daemon=True)
    tcp_thread.start()
    time.sleep(0.5)
    logger.info(f"[TCP] TCP server thread started (alive={tcp_thread.is_alive()})")
    return tcp_thread


def stop_tcp_server():
    """停止 TCP 服务器"""
    global tcp_loop
    if tcp_loop and tcp_loop.is_running():
        tcp_loop.call_soon_threadsafe(tcp_loop.stop)
        logger.info("[TCP] Stop requested")


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import create_app

    app = create_app()
    try:
        asyncio.run(server_main(app, TcpConnectionHandler))
    except KeyboardInterrupt:
        logger.info("[TCP] Stopped by user")
