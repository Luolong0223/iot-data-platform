import asyncio
import logging
import os
import sys
import threading
import time

# 配置日志：同时输出到控制台和文件
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加文件日志处理器（确保日志写入文件，方便宝塔排查）
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tcp_server.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

servers = {}
tcp_loop = None
tcp_thread = None


async def start_user_server(handler, user_id, port, host):
    try:
        server = await asyncio.start_server(
            handler.handle_client,
            host,
            port,
            reuse_address=True
        )
        servers[user_id] = server
        logger.info(f"[TCP] Server started for user {user_id} on port {port}")
        return server
    except OSError as e:
        if e.errno == 10048 or e.errno == 48:  # Address already in use (Windows/Linux)
            logger.info(f"[TCP] Port {port} already in use, skipping")
            return None
        raise


async def stop_user_server(user_id):
    server = servers.pop(user_id, None)
    if server:
        server.close()
        await server.wait_closed()
        logger.info(f"[TCP] Server stopped for user {user_id}")


async def refresh_servers(app, handler_class):
    try:
        with app.app_context():
            from models.database import User
            users = User.query.filter(User.tcp_port.isnot(None)).all()
    except Exception as e:
        logger.error(f"[TCP] Failed to query users: {e}")
        return

    active_user_ids = set()
    for user in users:
        active_user_ids.add(user.id)
        if user.id not in servers:
            try:
                handler = handler_class(app, user.id)
                await start_user_server(
                    handler, user.id, user.tcp_port,
                    app.config.get('TCP_HOST', '0.0.0.0')
                )
            except Exception as e:
                logger.error(f"[TCP] Failed to start server for user {user.id} on port {user.tcp_port}: {e}")

    for user_id in list(servers.keys()):
        if user_id not in active_user_ids:
            await stop_user_server(user_id)


async def server_main(app, handler_class):
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
    """在新线程中启动TCP服务器，使用独立的事件循环"""
    global tcp_loop, tcp_thread

    def tcp_thread_target():
        global tcp_loop
        logger.info("[TCP] TCP thread started")
        
        # 显式创建新的事件循环（线程安全）
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
    
    # 等待一小段时间确认线程已启动
    time.sleep(0.5)
    logger.info(f"[TCP] TCP server thread started (alive={tcp_thread.is_alive()})")
    return tcp_thread


def stop_tcp_server():
    """停止TCP服务器"""
    global tcp_loop
    if tcp_loop and tcp_loop.is_running():
        tcp_loop.call_soon_threadsafe(tcp_loop.stop)
        logger.info("[TCP] Stop requested")


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import create_app
    from services.tcp_handler import TcpConnectionHandler

    app = create_app()
    try:
        asyncio.run(server_main(app, TcpConnectionHandler))
    except KeyboardInterrupt:
        logger.info("[TCP] Stopped by user")
