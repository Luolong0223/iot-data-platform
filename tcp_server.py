import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

servers = {}


async def start_user_server(handler, user_id, port, host):
    try:
        server = await asyncio.start_server(
            handler.handle_client,
            host,
            port
        )
        servers[user_id] = server
        logger.info(f"TCP server started for user {user_id} on port {port}")
        return server
    except OSError as e:
        if e.errno == 48:  # Address already in use
            logger.info(f"Port {port} already in use, skipping")
            return None
        raise


async def stop_user_server(user_id):
    server = servers.pop(user_id, None)
    if server:
        server.close()
        await server.wait_closed()
        logger.info(f"TCP server stopped for user {user_id}")


async def refresh_servers(app, handler_class):
    with app.app_context():
        from models.database import User
        users = User.query.filter(User.tcp_port.isnot(None)).all()

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
                logger.error(f"Failed to start server for user {user.id} on port {user.tcp_port}: {e}")

    for user_id in list(servers.keys()):
        if user_id not in active_user_ids:
            await stop_user_server(user_id)


async def server_main(app, handler_class):
    await refresh_servers(app, handler_class)

    try:
        while True:
            await asyncio.sleep(30)
            await refresh_servers(app, handler_class)
    except asyncio.CancelledError:
        logger.info("TCP server main loop cancelled")
    finally:
        for user_id in list(servers.keys()):
            await stop_user_server(user_id)


def run_tcp_server(app, handler_class):
    """同步入口，用于后台线程启动"""
    try:
        asyncio.run(server_main(app, handler_class))
    except Exception as e:
        logger.error(f"TCP server error: {e}")


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import create_app
    from services.tcp_handler import TcpConnectionHandler

    app = create_app()
    try:
        asyncio.run(server_main(app, TcpConnectionHandler))
    except KeyboardInterrupt:
        logger.info("TCP server stopped by user")
