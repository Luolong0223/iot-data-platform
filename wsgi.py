import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

application = create_app()


def start_tcp_server():
    """在后台线程启动TCP服务器"""
    from tcp_server import run_tcp_server
    from services.tcp_handler import TcpConnectionHandler
    run_tcp_server(application, TcpConnectionHandler)


# 启动TCP服务器后台线程
tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
tcp_thread.start()
print("TCP server started in background thread")

if __name__ == '__main__':
    application.run()
