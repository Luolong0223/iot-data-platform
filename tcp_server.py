import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.database import db, User
from services.tcp_handler import TcpConnectionHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()
servers = {}


async def start_user_server(user_id, port):
    handler = TcpConnectionHandler(app, user_id)
    server = await asyncio.start_server(
        handler.handle_client,
        app.config.get('TCP_HOST', '0.0.0.0'),
        port
    )
    servers[user_id] = server
    logger.info(f"TCP server started for user {user_id} on port {port}")
    return server


async def stop_user_server(user_id):
    server = servers.pop(user_id, None)
    if server:
        server.close()
        await server.wait_closed()
        logger.info(f"TCP server stopped for user {user_id}")


async def refresh_servers():
    with app.app_context():
        users = User.query.filter(User.tcp_port.isnot(None)).all()

    active_user_ids = set()
    for user in users:
        active_user_ids.add(user.id)
        if user.id not in servers:
            try:
                await start_user_server(user.id, user.tcp_port)
            except Exception as e:
                logger.error(f"Failed to start server for user {user.id} on port {user.tcp_port}: {e}")

    for user_id in list(servers.keys()):
        if user_id not in active_user_ids:
            await stop_user_server(user_id)


async def server_main():
    await refresh_servers()

    try:
        while True:
            await asyncio.sleep(30)
            await refresh_servers()
    except asyncio.CancelledError:
        logger.info("TCP server main loop cancelled")
    finally:
        for user_id in list(servers.keys()):
            await stop_user_server(user_id)


if __name__ == '__main__':
    try:
        asyncio.run(server_main())
    except KeyboardInterrupt:
        logger.info("TCP server stopped by user")
