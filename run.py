import os
import sys
import threading
from app import create_app

app = create_app()


def start_tcp_server():
    """在后台线程启动TCP服务器"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from tcp_server import run_tcp_server
    from services.tcp_handler import TcpConnectionHandler
    run_tcp_server(app, TcpConnectionHandler)


if __name__ == '__main__':
    # 启动TCP服务器后台线程
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_thread.start()
    print("TCP server started in background thread")

    # 启动Flask Web服务
    app.run(host='0.0.0.0', port=5000, debug=True)
