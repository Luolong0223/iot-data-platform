import os
import sys
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
    start_tcp_server()
    
    # 启动Flask Web服务（禁用reloader避免TCP重复启动）
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
